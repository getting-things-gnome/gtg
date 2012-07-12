# -*- coding: utf-8 -*-
# Copyright (c) 2009 - Paulo Cabido <paulo.cabido@gmail.com>
#                    - Luca Invernizzi <invernizzi.l@gmail.com>
#                    - Izidor Matušov <izidor.matusov@gmail.com>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import gtk
try:
    import appindicator
except:
    pass

from GTG                   import _
from GTG                   import PLUGIN_DIR
from GTG.tools.borg        import Borg
from GTG.tools.dates       import Date


def _due_within(task, danger_zone):
    """
    Determine if a task is the danger zone.
    Convention: a danger zone of 1 day includes tasks due today.
    """
    ddate = task.get_due_date()
    if (ddate != Date.no_date()):
        if ddate.days_left() < danger_zone:
            return True
    return False


class _Attention:

    """
    Define need attention state depending on whether there
    are tasks in danger zone.

    There are two levels of attention:
    "normal": there are no tasks in danger zone
    "high": there is at least one task in danger zone

    A task is in danger zone if the number of days left is less
    than time span (in days) defined by danger_zone.
    """

    STATUS = {'normal': appindicator.STATUS_ACTIVE,
              'high': appindicator.STATUS_ATTENTION}

    def __init__(self, tree, req, indicator, danger_zone=1):
        self.__tree = tree
        self.__req = req
        self.__indicator = indicator
        self.danger_zone = danger_zone

        # Setup list of tasks in danger zone
        """ Setup a list of tasks in danger zone, use task id """
        self.tasks_danger = []
        for tid in self.__tree.get_all_nodes():
            task = self.__req.get_task(tid)
            if _due_within(task, self.danger_zone):
                self.tasks_danger.append(tid)

        # Set initial status
        self.__update_indicator(self.level())

    def level(self):
        """ Two states only: attention is either needed or not """
        return 'high' if len(self.tasks_danger)>0 else 'normal'

    def __update_indicator(self, new, old=None):
        """ Reset indicator status or update upon change in status """
        if old is None or not old == new:
            self.__indicator.set_status(self.STATUS[new])

    def update_on_task_modified(self, tid):
        # Store current attention level
        old_lev = self.level()
        task = self.__req.get_task(tid)
        if tid in self.tasks_danger:
            if not _due_within(task, self.danger_zone):
                self.tasks_danger.remove(tid)
        else:
            if _due_within(task, self.danger_zone):
                self.tasks_danger.append(tid)
                
        # Update icon only if attention level has changed
        self.__update_indicator(self.level(), old_lev)

    def update_on_task_deleted(self, tid):
        # Store current attention level
        old_lev = self.level()

        if tid in self.tasks_danger:
            self.tasks_danger.remove(tid)

        # Update icon only if attention level has changed
        self.__update_indicator(self.level(), old_lev)


class NotificationArea:
    """
    Plugin that display a notification area widget or an indicator
    to quickly access tasks.
    """

    DEFAULT_PREFERENCES = {"start_minimized": False,
                           "danger_zone": 1}
    PLUGIN_NAME = "notification_area"
    MAX_TITLE_LEN = 30
    MAX_ITEMS = 10

    class TheIndicator(Borg):
        """
        Application indicator can be instantiated only once. The
        plugin api, when toggling the activation state of a plugin,
        instantiates different objects from the plugin class. Therefore,
        we need to keep a reference to the indicator object. This class
        does that.
        """

        def __init__(self):
            super(NotificationArea.TheIndicator, self).__init__()
            if not hasattr(self, "_indicator"):
                try:
                    self._indicator = appindicator.Indicator( \
                                  "gtg",
                                  "indicator-messages",
                                   appindicator.CATEGORY_APPLICATION_STATUS)
                    icon_theme = os.path.join('notification_area', 'data', 'icons')
                    abs_theme_path = os.path.join(PLUGIN_DIR[0], icon_theme)
                    # TODO: theme sees the icon but indicator doesn't
                    # theme = gtk.icon_theme_get_default()
                    # theme.append_search_path(abs_theme_path)
                    # print theme.has_icon("gtg_need_attention")
                    self._indicator.set_icon_theme_path(abs_theme_path)
                    self._indicator.set_icon("gtg")
                    self._indicator.set_attention_icon("gtg_need_attention")
                except:
                    self._indicator = None

        def get_indicator(self):
            return self._indicator

    def __init__(self):
        self.__indicator = NotificationArea.TheIndicator().get_indicator()
        self.__browser_handler = None
        self.__liblarch_callbacks = []

    def activate(self, plugin_api):
        """ Set up the plugin, set callbacks, etc """
        self.__plugin_api = plugin_api
        self.__view_manager = plugin_api.get_view_manager()
        self.__requester = plugin_api.get_requester()
        # Tasks_in_menu will hold the menu_items in the menu, to quickly access
        # them given the task id. Contains tuple of this format:
        # (title, key, gtk.MenuItem)
        self.__init_gtk()

        # We load preferences before connecting to tree
        self.preference_dialog_init()
        self.preferences_load()

        # Enable attention monitor.
        self.__attention = None
        self.__tree_att = self.__connect_to_tree([
                ("node-added-inview", self.__on_task_added_att),
                ("node-modified-inview", self.__on_task_added_att),
                ("node-deleted-inview", self.__on_task_deleted_att),
                ])
        self.__tree_att.apply_filter('workview')
        self.__init_attention()

        self.__tree = self.__connect_to_tree([
                ("node-added-inview", self.__on_task_added),
                ("node-modified-inview", self.__on_task_added),
                ("node-deleted-inview", self.__on_task_deleted),
                ])
        self.__tree.apply_filter('workview')

        # When no windows (browser or text editors) are shown, it tries to quit
        # With hidden browser and closing the only single text editor,
        # GTG would quit no matter what
        self.__view_manager.set_daemon_mode(True)

        # Don't quit GTG after closing browser
        self.__set_browser_close_callback(self.__on_browser_minimize)

        if self.preferences["start_minimized"]:
            self.__view_manager.start_browser_hidden()

    def deactivate(self, plugin_api):
        """ Set everything back to normal """
        if self.__indicator:
            self.__indicator.set_status(appindicator.STATUS_PASSIVE)
        else:
            self.status_icon.set_visible(False)

        # Allow to close browser after deactivation
        self.__set_browser_close_callback(None)

        # Allow closing GTG after the last window
        self.__view_manager.set_daemon_mode(True)

        # Deactivate LibLarch callbacks
        for key, event in self.__liblarch_callbacks:
            self.__tree.deregister_cllbck(event, key)
        self.__tree = None
        self.__liblarch_callbacks = []

## Helper methods #############################################################
    def __init_gtk(self):
        browser = self.__view_manager.get_browser()

        self.__menu = gtk.Menu()

        #add "new task"
        menuItem = gtk.ImageMenuItem(gtk.STOCK_ADD)
        menuItem.get_children()[0].set_label(_('Add _New Task'))
        menuItem.connect('activate', self.__open_task)
        self.__menu.append(menuItem)

        #view in main window checkbox
        view_browser_checkbox = gtk.CheckMenuItem(_("_View Main Window"))
        view_browser_checkbox.set_active(browser.is_shown())
        self.__signal_handler = view_browser_checkbox.connect('activate',
                                                       self.__toggle_browser)
        browser.connect('visibility-toggled', self.__on_browser_toggled,
                                                view_browser_checkbox)
        self.__menu.append(view_browser_checkbox)
        self.checkbox = view_browser_checkbox

        #separator (it's intended to be after show_all)
        # separator should be shown only when having tasks
        self.__task_separator = gtk.SeparatorMenuItem()
        self.__menu.append(self.__task_separator)
        self.__menu_top_length = len(self.__menu)

        self.__menu.append(gtk.SeparatorMenuItem())

        #quit item
        menuItem = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        menuItem.connect('activate', self.__view_manager.close_browser)
        self.__menu.append(menuItem)

        self.__menu.show_all()
        self.__task_separator.hide()

        self.__tasks_menu = SortedLimitedMenu(self.MAX_ITEMS,
                            self.__menu, self.__menu_top_length)

        if self.__indicator:
            self.__indicator.set_menu(self.__menu)
            self.__indicator.set_status(appindicator.STATUS_ACTIVE)
        else:
            icon_theme = os.path.join('notification_area', 'data', 'icons')
            abs_theme_path = os.path.join(PLUGIN_DIR[0], icon_theme)
            theme = gtk.icon_theme_get_default()
            theme.append_search_path(abs_theme_path)
            print theme.has_icon("gtg_need_attention")

            self.status_icon = gtk.StatusIcon()
            self.status_icon.set_from_icon_name("gtg")
            self.status_icon.set_tooltip("Getting Things Gnome!")
            self.status_icon.set_visible(True)
            self.status_icon.connect('activate', self.__toggle_browser)
            self.status_icon.connect('popup-menu',
                                     self.__on_icon_popup, self.__menu)

    def __init_attention(self):
        # Use two different viewtree for attention and menu
        # This way we can filter them independently.
        # Convention: if danger zone is <=0, disable attention
        # Attention is also disabled if there is no indicator
        if self.__indicator:
            if self.preferences['danger_zone'] > 0:
                self.__attention = _Attention(self.__tree_att,
                                              self.__requester,
                                              self.__indicator,
                                              self.preferences['danger_zone'])
            else:
                self.__attention = None

    def __open_task(self, widget, task_id = None):
        """
        Opens a task in the TaskEditor, if it's not currently opened.
        If task_id is None, it creates a new task and opens it
        """
        if task_id == None:
            task_id = self.__requester.new_task().get_id()
            new_task = True
        else:
            new_task = False

        self.__view_manager.open_task(task_id, thisisnew=new_task)

    def __connect_to_tree(self, signal_cllbck):
        """ Return a new view tree """
        tree = self.__requester.get_tasks_tree()
        # Request a new view so we do not influence anybody
        tree = tree.get_basetree().get_viewtree(refresh=False)

        self.__liblarch_callbacks = []
        for signal, cllbck in signal_cllbck:
            cb_id = tree.register_cllbck(signal, cllbck)
            self.__liblarch_callbacks.append((cb_id, signal))
        return tree

    def __on_task_added_att(self, tid, path):
        # Update icon on modification
        if self.__attention:
            self.__attention.update_on_task_modified(tid)

    def __on_task_added(self, tid, path):
        self.__task_separator.show()
        task = self.__requester.get_task(tid)
        if task is None:
            return

        #ellipsis of the title
        title = self.__create_short_title(task.get_title())

        #creating the menu item
        menu_item = gtk.MenuItem(title, False)
        menu_item.connect('activate', self.__open_task, tid)
        self.__tasks_menu.add(tid, (task.get_due_date(), title), menu_item)

        if self.__indicator:
            self.__indicator.set_menu(self.__menu)

    def __on_task_deleted_att(self, tid, path):
        # Update icon on deletion
        if self.__attention:
            self.__attention.update_on_task_deleted(tid)

    def __on_task_deleted(self, tid, path):
        self.__tasks_menu.remove(tid)
        if self.__tasks_menu.empty():
            self.__task_separator.hide()

    def __create_short_title(self, title):
        """ Make title short if it is long.  Replace '_' by '__' so
        it is not ignored or  interpreted as an accelerator."""
        title =title.replace("_", "__")
        short_title = title[0:self.MAX_TITLE_LEN]
        if len(title) > self.MAX_TITLE_LEN:
            short_title = short_title.strip() + "..."
        return short_title

    def __on_icon_popup(self, icon, button, timestamp, menu=None):
        if not self.__indicator:
            menu.popup(None, None, gtk.status_icon_position_menu, \
                       button, timestamp, icon)

### Preferences methods #######################################################
    def preferences_load(self):
        data = self.__plugin_api.load_configuration_object(self.PLUGIN_NAME,
                                                         "preferences")
        # We first load the preferences then update the dict
        # This way new default options are recognized with old cfg files
        self.preferences = self.DEFAULT_PREFERENCES
        if isinstance(data, dict):
            self.preferences.update(data)

    def preferences_store(self):
        self.__plugin_api.save_configuration_object(self.PLUGIN_NAME,
                                                  "preferences",
                                                  self.preferences)

    def is_configurable(self):
        """A configurable plugin should have this method and return True"""
        return True

    def preference_dialog_init(self):
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "notification_area.ui"))
        self.preferences_dialog = self.builder.get_object("preferences_dialog")
        self.chbox_minimized = self.builder.get_object("pref_chbox_minimized")
        self.spinbutton_dangerzone = \
            self.builder.get_object("pref_spinbutton_dangerzone")
        SIGNAL_CONNECTIONS_DIC = {
            "on_preferences_dialog_delete_event":
                self.on_preferences_cancel,
            "on_btn_preferences_cancel_clicked":
                self.on_preferences_cancel,
            "on_btn_preferences_ok_clicked":
                self.on_preferences_ok,
        }
        self.builder.connect_signals(SIGNAL_CONNECTIONS_DIC)

    def configure_dialog(self, manager_dialog):
        self.chbox_minimized.set_active(self.preferences["start_minimized"])
        self.spinbutton_dangerzone.set_value(self.preferences["danger_zone"])
        self.preferences_dialog.show_all()
        self.preferences_dialog.set_transient_for(manager_dialog)

    def on_preferences_cancel(self, widget = None, data = None):
        self.preferences_dialog.hide()
        return True

    def on_preferences_ok(self, widget = None, data = None):
        dzone = self.spinbutton_dangerzone.get_value()
        # update danger zone only if it has changed
        # and refresh attention monitor
        if not dzone == self.preferences["danger_zone"]:
            self.preferences["danger_zone"] = dzone
            self.__init_attention()

        self.preferences["start_minimized"] = self.chbox_minimized.get_active()
        self.preferences_store()
        self.preferences_dialog.hide()

### Browser methods ###########################################################
    def __on_browser_toggled(self, sender, checkbox):
        checkbox.disconnect(self.__signal_handler)
        is_shown = self.__view_manager.get_browser().is_shown()
        checkbox.set_active(is_shown)
        self.__signal_handler = checkbox.connect('activate',
                                               self.__toggle_browser)

    def __on_browser_minimize(self, widget = None, plugin_api = None):
        self.__view_manager.hide_browser()
        return True

    def __toggle_browser(self, sender = None, data = None):
        manager = self.__plugin_api.get_view_manager()
        if manager.is_browser_visible():
            manager.hide_browser()
        else:
            manager.show_browser()

    def __set_browser_close_callback(self, method):
        """ Set a callback for browser's close event. If method is None,
        unset the previous callback """

        browser = self.__view_manager.get_browser()

        if self.__browser_handler is not None:
            browser.window.disconnect(self.__browser_handler)

        if method is not None:
            self.__browser_handler = browser.window.connect(
                "delete-event", method)


class SortedLimitedMenu:
    """ Sorted GTK Menu which shows only first N elements """

    def __init__(self, max_items, gtk_menu, offset):
        """ max_items - how many items could be shown
            gtk_menu - items are added to this menu
            offset - add to position this offset
        """
        self.max_items = max_items
        self.menu = gtk_menu
        self.offset = offset

        self.sorted_keys = []
        self.elements = {}

    def add(self, key, sort_elem, menu_item):
        """ Add/modify item """
        if key in self.elements:
            self.remove(key)

        item = (sort_elem, key)
        self.sorted_keys.append(item)
        self.sorted_keys.sort()
        position = self.sorted_keys.index(item)
        self.elements[key] = menu_item
        self.menu.insert(menu_item, position + self.offset)

        # Show/hide elements
        if position < self.max_items:
            menu_item.show()

            if len(self.sorted_keys) > self.max_items:
                hidden_key = self.sorted_keys[self.max_items][1]
                self.elements[hidden_key].hide()

    def remove(self, key):
        """ Remove item """
        menu_item = self.elements.pop(key)
        self.menu.remove(menu_item)

        for item in self.sorted_keys:
            if item[1] == key:
                position = self.sorted_keys.index(item)
                self.sorted_keys.remove(item)
                break

        # show element which takes the freed place
        was_displayed = position < self.max_items
        hidden_elements = len(self.sorted_keys) >= self.max_items
        if was_displayed and hidden_elements:
            shown_key = self.sorted_keys[self.max_items-1][1]
            self.elements[shown_key].show()

    def empty(self):
        """ Menu is without items """
        return self.sorted_keys == []
