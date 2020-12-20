# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
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
# -----------------------------------------------------------------------------

""" The main window for GTG, listing tags, and open and closed tasks """

import threading
import datetime

from gi.repository import GObject, Gtk, Gdk, Gio

from GTG.core import info
from GTG.backends.backend_signals import BackendSignals
from GTG.core.dirs import ICONS_DIR
from GTG.core.search import parse_search_query, InvalidQuery
from GTG.core.tag import SEARCH_TAG
from GTG.core.task import Task
from gettext import gettext as _
from GTG.gtk.browser import GnomeConfig
from GTG.gtk.browser import quick_add
from GTG.gtk.browser.backend_infobar import BackendInfoBar
from GTG.gtk.browser.modify_tags import ModifyTagsDialog
from GTG.gtk.browser.delete_tag import DeleteTagsDialog
from GTG.gtk.browser.tag_context_menu import TagContextMenu
from GTG.gtk.browser.treeview_factory import TreeviewFactory
from GTG.gtk.editor.calendar import GTGCalendar
from GTG.gtk.tag_completion import TagCompletion
from GTG.core.dates import Date
from GTG.core.logger import log

PANE_STACK_NAMES_MAP = {
    'closed_view': 'closed',
    'open_view': 'active',
    'actionable_view': 'workview',
}
PANE_STACK_NAMES_MAP_INVERTED = {v: k for k, v in PANE_STACK_NAMES_MAP.items()}


class MainWindow(Gtk.ApplicationWindow):
    """ The UI for browsing open and closed tasks,
    and listing tags in a tree """

    __string_signal__ = (GObject.SignalFlags.RUN_FIRST, None, (str, ))
    __none_signal__ = (GObject.SignalFlags.RUN_FIRST, None, tuple())
    __gsignals__ = {'task-added-via-quick-add': __string_signal__,
                    'visibility-toggled': __none_signal__,
                    }

    def __init__(self, requester, app):
        super().__init__(application=app)

        # Object prime variables
        self.req = requester
        self.app = app
        self.config = self.req.get_config('browser')
        self.tag_active = False

        # Treeviews handlers
        self.vtree_panes = {}
        self.tv_factory = TreeviewFactory(self.req, self.config)

        # Active Tasks
        self.activetree = self.req.get_tasks_tree(name='active', refresh=False)
        self.activetree.apply_filter('active', refresh=False)
        self.vtree_panes['active'] = \
            self.tv_factory.active_tasks_treeview(self.activetree)

        # Workview Tasks
        self.workview_tree = \
            self.req.get_tasks_tree(name='workview', refresh=False)
        self.workview_tree.apply_filter('workview', refresh=False)
        self.vtree_panes['workview'] = \
            self.tv_factory.active_tasks_treeview(self.workview_tree)

        # Closed Tasks
        self.closedtree = \
            self.req.get_tasks_tree(name='closed', refresh=False)
        self.closedtree.apply_filter('closed', refresh=False)
        self.vtree_panes['closed'] = \
            self.tv_factory.closed_tasks_treeview(self.closedtree)

        # YOU CAN DEFINE YOUR INTERNAL MECHANICS VARIABLES BELOW
        # Setup GTG icon theme
        self._init_icon_theme()

        # Init Actions
        self._set_actions()

        # Tags
        self.tagtree = None
        self.tagtreeview = None

        # Load window tree
        self.builder = Gtk.Builder()
        self.builder.add_from_file(GnomeConfig.BROWSER_UI_FILE)
        self.builder.add_from_file(GnomeConfig.HELP_OVERLAY_UI_FILE)

        # Define aliases for specific widgets to reuse them easily in the code
        self._init_widget_aliases()

        self.set_titlebar(self.headerbar)
        self.set_title('Getting Things GNOME!')
        self.add(self.main_box)

        # Setup help overlay (shortcuts window)
        self.set_help_overlay(self.help_overlay)

        # Init non-GtkBuilder widgets
        self._init_ui_widget()
        self._init_context_menus()

        # Initialize "About" dialog
        self._init_about_dialog()

        # Create our dictionary and connect it
        self._init_signal_connections()

        self.restore_state_from_conf()

        self.on_select_tag()
        self._set_defer_days()
        self.browser_shown = False

        app.timer.connect('refresh', self.refresh_all_views)
        app.timer.connect('refresh', self._set_defer_days)

        self.stack_switcher.get_stack().connect('notify::visible-child', self.on_pane_switch)

        # This needs to be called again after setting everything up,
        # so the buttons start disabled
        self.on_cursor_changed()

# INIT HELPER FUNCTIONS #######################################################
    def _init_context_menus(self):
        builder = Gtk.Builder()
        builder.add_from_file(GnomeConfig.MENUS_UI_FILE)

        closed_menu_model = builder.get_object('closed_task_menu')
        self.closed_menu = Gtk.Menu.new_from_model(closed_menu_model)
        self.closed_menu.attach_to_widget(self.main_box)

        open_menu_model = builder.get_object('task_menu')
        self.open_menu = Gtk.Menu.new_from_model(open_menu_model)
        self.open_menu.attach_to_widget(self.main_box)

    def _set_actions(self):
        """Setup actions."""

        action_entries = [
            ('toggle_sidebar', self.on_sidebar_toggled, ('win.toggle_sidebar', ['F9'])),
            ('change_tags', self.on_modify_tags, ('win.change_tags', ['<ctrl>T'])),
            ('search', self.toggle_search, ('win.search', ['<ctrl>F'])),
            ('focus_quickentry', self.focus_quickentry, ('win.focus_quickentry', ['<ctrl>L'])),
            ('delete_task', self.on_delete_tasks, ('win.delete_task', ['<ctrl>Delete'])),
            ('help_overlay', None, ('win.show-help-overlay', ['<ctrl>question'])),
            ('mark_as_started', self.on_mark_as_started, None),
            ('start_today', self.on_start_for_today, None),
            ('start_tomorrow', self.on_start_for_tomorrow, None),
            ('start_next_day_2', self.on_start_for_next_day_2, None),
            ('start_next_day_3', self.on_start_for_next_day_3, None),
            ('start_next_day_4', self.on_start_for_next_day_4, None),
            ('start_next_day_5', self.on_start_for_next_day_5, None),
            ('start_next_day_6', self.on_start_for_next_day_6, None),
            ('start_next_week', self.on_start_for_next_week, None),
            ('start_next_month', self.on_start_for_next_month, None),
            ('start_next_year', self.on_start_for_next_year, None),
            ('start_custom', self.on_start_for_specific_date, None),
            ('start_clear', self.on_start_clear, None),
            ('due_tomorrow', self.on_set_due_tomorrow, None),
            ('due_next_week', self.on_set_due_next_week, None),
            ('due_next_month', self.on_set_due_next_month, None),
            ('due_next_year', self.on_set_due_next_year, None),
            ('due_clear', self.on_set_due_clear, None),
            ('due_now', self.on_set_due_now, None),
            ('due_soon', self.on_set_due_soon, None),
            ('due_custom', self.on_set_due_for_specific_date, None),
            ('due_someday', self.on_set_due_someday, None),
            ('save_search', self.on_save_search, None),
            ('recurring_day', self.on_set_recurring_every_day, None),
            ('recurring_other_day', self.on_set_recurring_every_otherday, None),
            ('recurring_week', self.on_set_recurring_every_week, None),
            ('recurring_month', self.on_set_recurring_every_month, None),
            ('recurring_year', self.on_set_recurring_every_year, None),
            ('recurring_toggle', self.on_toggle_recurring, None),
        ]

        for action, callback, accel in action_entries:
            if callback is not None:
                simple_action = Gio.SimpleAction.new(action, None)
                simple_action.connect('activate', callback)
                simple_action.set_enabled(True)

                self.add_action(simple_action)

            if accel is not None:
                self.app.set_accels_for_action(*accel)

    def _init_icon_theme(self):
        """
        sets the deafault theme for icon and its directory
        """
        # TODO(izidor): Add icon dirs on app level
        Gtk.IconTheme.get_default().prepend_search_path(ICONS_DIR)
        # TODO(izidor): Set it outside browser as it applies to every window
        Gtk.Window.set_default_icon_name("gtg")

    def _init_widget_aliases(self):
        """
        Defines aliases for UI elements found in the GtkBuilder file
        """

        self.taskpopup = self.builder.get_object("task_context_menu")
        self.defertopopup = self.builder.get_object("defer_to_context_menu")
        self.ctaskpopup = self.builder.get_object("closed_task_context_menu")
        self.about = self.builder.get_object("about_dialog")
        self.open_pane = self.builder.get_object("open_pane")
        self.actionable_pane = self.builder.get_object("actionable_pane")
        self.closed_pane = self.builder.get_object("closed_pane")
        self.menu_view_workview = self.builder.get_object("view_workview")
        self.toggle_workview = self.builder.get_object("workview_toggle")
        self.search_entry = self.builder.get_object("search_entry")
        self.searchbar = self.builder.get_object("searchbar")
        self.search_button = self.builder.get_object("search_button")
        self.quickadd_entry = self.builder.get_object("quickadd_field")
        self.quickadd_pane = self.builder.get_object("quickadd_pane")
        self.sidebar = self.builder.get_object("sidebar_vbox")
        self.sidebar_container = self.builder.get_object("sidebar-scroll")
        self.sidebar_notebook = self.builder.get_object("sidebar_notebook")
        self.main_notebook = self.builder.get_object("main_notebook")
        self.accessory_notebook = self.builder.get_object("accessory_notebook")
        self.vbox_toolbars = self.builder.get_object("vbox_toolbars")
        self.stack_switcher = self.builder.get_object("stack_switcher")
        self.headerbar = self.builder.get_object("browser_headerbar")
        self.main_box = self.builder.get_object("main_view_box")
        self.defer_btn = self.builder.get_object("defer_task_button")
        self.defer_menu_btn = self.builder.get_object("defer_menu_btn")
        self.help_overlay = self.builder.get_object("shortcuts")

        self.tagpopup = TagContextMenu(self.req, self.app)

    def _init_ui_widget(self):
        """ Sets the main pane with three trees for active tasks,
        actionable tasks (workview), closed tasks and creates
        ModifyTagsDialog & Calendar """
        # Tasks treeviews
        self.open_pane.add(self.vtree_panes['active'])
        self.actionable_pane.add(self.vtree_panes['workview'])
        self.closed_pane.add(self.vtree_panes['closed'])

        tag_completion = TagCompletion(self.req.get_tag_tree())
        self.modifytags_dialog = ModifyTagsDialog(tag_completion, self.req)
        self.modifytags_dialog.dialog.set_transient_for(self)
        self.deletetags_dialog = DeleteTagsDialog(self.req, self)
        self.calendar = GTGCalendar()
        self.calendar.set_transient_for(self)
        self.calendar.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.calendar.connect("date-changed", self.on_date_changed)

    def _set_defer_days(self, timer=None):
        """Set days for the defer task menu."""

        # Today is day 0, tomorrow is day 1. We don't need
        # to calculate the weekday for those.

        today = datetime.datetime.today()

        for i in range(2, 7):
            defer_btn = self.builder.get_object(f"defer_{i}_btn")
            name = (today + datetime.timedelta(days=i)).strftime('%A')
            defer_btn.props.text = name

    def init_tags_sidebar(self):
        """
        initializes the tagtree (left area with tags and searches)
        """
        self.tagtree = self.req.get_tag_tree()
        self.tagtreeview = self.tv_factory.tags_treeview(self.tagtree)
        self.tagtreeview.get_selection().connect('changed', self.on_select_tag)
        self.tagtreeview.connect('button-press-event', self.on_tag_treeview_button_press_event)
        self.tagtreeview.connect('key-press-event', self.on_tag_treeview_key_press_event)
        self.tagtreeview.connect('node-expanded', self.on_tag_expanded)
        self.tagtreeview.connect('node-collapsed', self.on_tag_collapsed)
        self.sidebar_container.add(self.tagtreeview)

        for path_t in self.config.get("expanded_tags"):
            # the tuple was stored as a string. we have to reconstruct it
            path = ()
            for p in path_t[1:-1].split(","):
                p = p.strip(" '")
                path += (p, )
            if path[-1] == '':
                path = path[:-1]
            self.tagtreeview.expand_node(path)

        # expanding search tag does not work automatically, request it
        self.expand_search_tag()

    def _init_about_dialog(self):
        """
        Show the about dialog
        """
        # These lines should be in info.py, but due to their dynamic nature
        # there'd be no way to show them translated in Gtk's About dialog:

        translated_copyright = _("Copyright © 2008-%d the GTG contributors.") % datetime.date.today().year

        UNITED_AUTHORS_OF_GTGETTON = [
            # GTK prefixes the first line with "Created by ",
            # but we can't split the string because it would cause trouble for some languages.
            _("GTG was made by many contributors around the world."),
            _("The GTG project is maintained/administered by:"),
            info.AUTHORS_MAINTAINERS,
            _("This release was brought to you by the efforts of these people:"),
            info.AUTHORS_RELEASE_CONTRIBUTORS,
            _("Many others contributed to GTG over the years.\nYou can see them on {OH_stats} and {GH_stats}.").format(
                    OH_stats = '<a href="https://www.openhub.net/p/gtg/contributors">OpenHub</a>',
                    GH_stats = '<a href="https://github.com/getting-things-gnome/gtg/graphs/contributors">GitHub</a>'),
            "\n"]

        self.about.set_transient_for(self)
        self.about.set_program_name(info.NAME)
        self.about.set_website(info.URL)
        self.about.set_logo_icon_name(self.app.props.application_id)
        self.about.set_website_label(_("GTG website"))
        self.about.set_version(info.VERSION)
        self.about.set_comments(_(info.SHORT_DESCRIPTION))  # This line translated in info.py works, as it has no strings replacements
        self.about.set_copyright(translated_copyright)
        self.about.set_license_type(Gtk.License.GPL_3_0)

        self.about.set_authors(UNITED_AUTHORS_OF_GTGETTON)
        self.about.set_artists(info.ARTISTS)
        self.about.set_documenters(info.DOCUMENTERS)

        # Translators for a particular language should put their names here.
        # Please keep the width at 80 chars max, as GTK3's About dialog won't wrap text.
        # GtkAboutDialog will detect if “translator-credits” is untranslated and auto-hide the tab.
        self.about.set_translator_credits(_("translator-credits"))

    def _init_signal_connections(self):
        """
        connects signals on UI elements
        """
        SIGNAL_CONNECTIONS_DIC = {
            "on_edit_done_task": self.on_edit_done_task,
            "on_add_subtask": self.on_add_subtask,
            "on_tagcontext_deactivate": self.on_tagcontext_deactivate,
            "on_quickadd_field_activate": self.on_quickadd_activate,
            "on_quickadd_field_focus_in": self.on_quickadd_focus_in,
            "on_quickadd_field_focus_out": self.on_quickadd_focus_out,
            "on_about_delete": self.on_about_close,
            "on_about_close": self.on_about_close,
            "on_search": self.on_search,
        }
        self.builder.connect_signals(SIGNAL_CONNECTIONS_DIC)

        # When destroying this window, quit GTG
        self.connect("destroy", self.quit)

        # Store window position
        self.connect('configure-event', self.on_move)

        # Store window position
        self.connect('size-allocate', self.on_size_allocate)

        # Active tasks TreeView
        self.vtree_panes['active'].connect('row-activated', self.on_edit_active_task)
        self.vtree_panes['active'].connect('cursor-changed', self.on_cursor_changed)

        tsk_treeview_btn_press = self.on_task_treeview_button_press_event
        self.vtree_panes['active'].connect('button-press-event', tsk_treeview_btn_press)
        task_treeview_key_press = self.on_task_treeview_key_press_event
        self.vtree_panes['active'].connect('key-press-event', task_treeview_key_press)
        self.vtree_panes['active'].connect('node-expanded', self.on_task_expanded)
        self.vtree_panes['active'].connect('node-collapsed', self.on_task_collapsed)

        # Workview tasks TreeView
        self.vtree_panes['workview'].connect('row-activated', self.on_edit_active_task)
        self.vtree_panes['workview'].connect('cursor-changed', self.on_cursor_changed)

        tsk_treeview_btn_press = self.on_task_treeview_button_press_event
        self.vtree_panes['workview'].connect('button-press-event', tsk_treeview_btn_press)
        task_treeview_key_press = self.on_task_treeview_key_press_event
        self.vtree_panes['workview'].connect('key-press-event', task_treeview_key_press)
        self.vtree_panes['workview'].connect('node-expanded', self.on_task_expanded)
        self.vtree_panes['workview'].connect('node-collapsed', self.on_task_collapsed)
        self.vtree_panes['workview'].set_col_visible('startdate', False)

        # Closed tasks Treeview
        self.vtree_panes['closed'].connect('row-activated', self.on_edit_done_task)
        # I did not want to break the variable and there was no other
        # option except this name:(Nimit)
        clsd_tsk_btn_prs = self.on_closed_task_treeview_button_press_event
        self.vtree_panes['closed'].connect('button-press-event', clsd_tsk_btn_prs)
        clsd_tsk_key_prs = self.on_closed_task_treeview_key_press_event
        self.vtree_panes['closed'].connect('key-press-event', clsd_tsk_key_prs)
        self.vtree_panes['closed'].connect('cursor-changed', self.on_cursor_changed)

        self.closedtree.apply_filter(self.get_selected_tags()[0], refresh=True)

        b_signals = BackendSignals()
        b_signals.connect(b_signals.BACKEND_FAILED, self.on_backend_failed)
        b_signals.connect(b_signals.BACKEND_STATE_TOGGLED, self.remove_backend_infobar)
        b_signals.connect(b_signals.INTERACTION_REQUESTED, self.on_backend_needing_interaction)
        self.selection = self.vtree_panes['active'].get_selection()


# HELPER FUNCTIONS ##########################################################

    def toggle_search(self, action, param):
        """Callback to toggle search bar."""

        self.on_search_toggled()

    def on_search_toggled(self, widget=None):
        if self.searchbar.get_search_mode():
            self.search_button.set_active(False)
            self.searchbar.set_search_mode(False)
            self.search_entry.set_text('')
            self.get_selected_tree().unapply_filter(SEARCH_TAG)
        else:
            self.search_button.set_active(True)
            self.searchbar.set_search_mode(True)
            self.search_entry.grab_focus()

    def _try_filter_by_query(self, query, refresh: bool = True):
        log.debug("Searching for %r", query)
        vtree = self.get_selected_tree()
        try:
            vtree.apply_filter(SEARCH_TAG, parse_search_query(query),
                               refresh=refresh)
        except InvalidQuery as error:
            log.debug("Invalid query %r: %r", query, error)
            vtree.unapply_filter(SEARCH_TAG)

    def on_search(self, data):
        self._try_filter_by_query(self.search_entry.get_text())

    def on_save_search(self, action, param):
        query = self.search_entry.get_text()

        # Try if this is a new search tag and save it correctly
        tag_id = self.req.new_search_tag(query)

        # Apply new search right now
        if self.tagtreeview is not None:
            self.select_search_tag(tag_id)
        else:
            self.get_selected_tree().apply_filter(tag_id)

    def select_search_tag(self, tag_id):
        tag = self.req.get_tag(tag_id)
        """Select new search in tagsidebar and apply it"""

        # Make sure search tag parent is expanded
        # (otherwise selection does not work)
        self.expand_search_tag()

        # Get iterator for new search tag
        model = self.tagtreeview.get_model()
        path = self.tagtree.get_paths_for_node(tag.get_id())[0]
        tag_iter = model.my_get_iter(path)

        # Select only it and apply filters on top of that
        selection = self.tagtreeview.get_selection()
        selection.unselect_all()
        selection.select_iter(tag_iter)
        self.on_select_tag()

    def quit(self, widget=None, data=None):
        self.app.quit()

    def on_window_state_event(self, widget, event, data=None):
        """ This event checks for the window state: maximized?
        and stores the state in self.config.max
        This is used to check the window state afterwards
        and maximize it if needed """
        mask = Gdk.WindowState.MAXIMIZED
        is_maximized = widget.get_window().get_state() & mask == mask
        self.config.set("max", is_maximized)

    def restore_collapsed_tasks(self):
        for path_s in self.config.get("collapsed_tasks"):
            # the tuple was stored as a string. we have to reconstruct it
            path = ()
            for p in path_s[1:-1].split(","):
                p = p.strip(" '")
                path += (p, )
            if path[-1] == '':
                path = path[:-1]
            try:
                self.vtree_panes['active'].collapse_node(path)
            except IndexError:
                print(f"Invalid liblarch path {path}")

    def restore_state_from_conf(self):
        # Extract state from configuration dictionary
        # if "browser" not in self.config:
        #     #necessary to have the minimum width of the tag pane
        #     # inferior to the "first run" width
        #     self.builder.get_object("hpaned1").set_position(250)
        #     return

        width = self.config.get('width')
        height = self.config.get('height')
        if width and height:
            self.resize(width, height)

        # checks for maximum size of window
        self.connect('window-state-event', self.on_window_state_event)
        if self.config.get("max"):
            self.maximize()

        xpos = self.config.get("x_pos")
        ypos = self.config.get("y_pos")
        if ypos and xpos:
            self.move(xpos, ypos)

        tag_pane = self.config.get("tag_pane")

        if not tag_pane:
            self.sidebar.hide()
        else:
            if not self.tagtreeview:
                self.init_tags_sidebar()

            self.sidebar.show()

        self.switch_sidebar_name(tag_pane)

        sidebar_width = self.config.get("sidebar_width")
        self.builder.get_object("main_hpanes").set_position(sidebar_width)
        self.builder.get_object("main_hpanes").connect('notify::position',
                                                       self.on_sidebar_width)

        # Callbacks for sorting and restoring previous state
        model = self.vtree_panes['active'].get_model()
        model.connect('sort-column-changed', self.on_sort_column_changed)
        sort_column = self.config.get('tasklist_sort_column')
        sort_order = self.config.get('tasklist_sort_order')

        if sort_column and sort_order:
            sort_column, sort_order = int(sort_column), int(sort_order)
            model.set_sort_column_id(sort_column, sort_order)

        self.restore_collapsed_tasks()

        view_name = PANE_STACK_NAMES_MAP_INVERTED.get(self.config.get('view'),
                                                      PANE_STACK_NAMES_MAP_INVERTED['active'])
        self.stack_switcher.get_stack().set_visible_child_name(view_name)

        def open_task(req, t):
            """ Open the task if loaded. Otherwise ask for next iteration """
            if req.has_task(t):
                self.app.open_task(t)
                return False
            else:
                return True

        for t in self.config.get("opened_tasks"):
            GObject.idle_add(open_task, self.req, t)

    def refresh_all_views(self, timer):
        active_tree = self.req.get_tasks_tree(name='active', refresh=False)
        active_tree.refresh_all()

        workview_tree = self.req.get_tasks_tree(name='workview', refresh=False)
        workview_tree.refresh_all()

        closed_tree = self.req.get_tasks_tree(name='closed', refresh=False)
        closed_tree.refresh_all()

    def find_value_in_treestore(self, store, treeiter, value):
        """Search for value in tree store recursively."""

        while treeiter is not None:
            if store[treeiter][1] == value:
                return(treeiter)
                break

            if store.iter_has_child(treeiter):
                childiter = store.iter_children(treeiter)
                ret = self.find_value_in_treestore(store, childiter, value)

                if ret is not None:
                    return ret

            treeiter = store.iter_next(treeiter)

# SIGNAL CALLBACKS ############################################################
# Typically, reaction to user input & interactions with the GUI
    def on_sort_column_changed(self, model):
        sort_column, sort_order = model.get_sort_column_id()

        if sort_order == Gtk.SortType.ASCENDING:
            sort_order = 0
        else:
            sort_order = 1

        self.config.set('tasklist_sort_column', sort_column)
        self.config.set('tasklist_sort_order', sort_order)

    def on_move(self, widget=None, data=None):
        xpos, ypos = self.get_position()
        self.config.set('x_pos', xpos)
        self.config.set('y_pos', ypos)

    def on_size_allocate(self, widget=None, data=None):
        width, height = self.get_size()
        self.config.set('width', width)
        self.config.set('height', height)

    def on_sidebar_width(self, widget, data=None):
        self.config.set('sidebar_width', widget.get_position())

    def on_about_clicked(self, widget):
        """
        show the about dialog
        """
        self.about.show()

    def on_about_close(self, widget, response):
        """
        close the about dialog
        """
        self.about.hide()
        return True

    def on_cursor_changed(self, widget=None):
        """Callback when the treeview's cursor changes."""

        if self.has_any_selection():
            self.defer_btn.set_sensitive(True)
            self.defer_menu_btn.set_sensitive(True)
        else:
            self.defer_btn.set_sensitive(False)
            self.defer_menu_btn.set_sensitive(False)

    def on_tagcontext_deactivate(self, menushell):
        self.reset_cursor()

    def switch_sidebar_name(self, visible):
        """Change text on sidebar button."""

        button = self.builder.get_object('toggle_sidebar_button')
        if visible:
            button.props.text = _("Hide Sidebar")
        else:
            button.props.text = _("Show Sidebar")

    def on_sidebar_toggled(self, action, param):
        """Toggle tags sidebar."""

        visible = self.sidebar.get_property("visible")

        if visible:
            self.config.set("tag_pane", False)
            self.sidebar.hide()
        else:
            if not self.tagtreeview:
                self.init_tags_sidebar()

            self.sidebar.show()
            self.config.set("tag_pane", True)

        self.switch_sidebar_name(not visible)

    def _expand_not_collapsed(self, model, path, iter, colt):
        """ Expand all not collapsed nodes

        Workaround around bug in Gtk, see LP #1076909 """
        # Generate tid from treeview
        tid_build = []
        current_iter = iter
        while current_iter is not None:
            tid = str(model.get_value(current_iter, 0))
            tid_build.insert(0, tid)
            current_iter = model.iter_parent(current_iter)
        tid = str(tuple(tid_build))

        # expand if the node was not stored as collapsed
        if tid not in colt:
            self.vtree_panes['active'].expand_row(path, False)

    def on_task_expanded(self, sender, tid):
        colt = self.config.get("collapsed_tasks")
        if tid in colt:
            colt.remove(tid)
        # restore expanded state of subnodes
        self.vtree_panes['active'].get_model().foreach(
            self._expand_not_collapsed, colt)
        self.config.set("collapsed_tasks", colt)

    def on_task_collapsed(self, sender, tid):
        colt = self.config.get("collapsed_tasks")
        if tid not in colt:
            colt.append(str(tid))
        self.config.set("collapsed_tasks", colt)

    def on_tag_expanded(self, sender, tag):
        colt = self.config.get("expanded_tags")

        # Directly appending tag to colt causes GTG to forget the state of
        # sub-tags (expanded/collapsed) in specific scenarios. Below is an
        # updated way which checks if any child of the tag is in colt or not
        # If yes, then the tag is inserted before the first child.
        # If no, it's appended to colt
        if tag not in colt:
            tag_has_been_inserted = False
            for index, colt_tag in enumerate(colt):
                if tag[1:-1] in colt_tag:
                    colt.insert(index, tag)
                    tag_has_been_inserted = True
                    break
            if not tag_has_been_inserted:
                colt.append(tag)
        self.config.set("expanded_tags", colt)

    def on_tag_collapsed(self, sender, tag):
        colt = self.config.get("expanded_tags")

        # When a tag is collapsed, we should also remove it's children
        # from colt, otherwise when parent tag is expanded, they also get
        # expanded (unwanted situation)
        colt = [colt_tag for colt_tag in colt if tag[1:-1] not in colt_tag]
        self.config.set("expanded_tags", colt)

    def focus_quickentry(self, action, param):
        """Callback to focus the quick entry widget."""

        self.quickadd_entry.grab_focus()

    def on_quickadd_focus_in(self, widget, event):
        self.toggle_delete_accel(False)

    def on_quickadd_focus_out(self, widget, event):
        self.toggle_delete_accel(True)

    def toggle_delete_accel(self, enable_delete_accel):
        """
        enable/disabled delete task shortcut.
        """
        accels = ['<ctrl>Delete'] if enable_delete_accel else []
        self.app.set_accels_for_action('win.delete_task', accels)

    def on_quickadd_activate(self, widget):
        """ Add a new task from quickadd toolbar """
        text = str(self.quickadd_entry.get_text())
        text = text.strip()
        if text:
            tags = self.get_selected_tags(nospecial=True)

            # We will select quick-added task in browser.
            # This has proven to be quite complex and deserves an explanation.
            # We register a callback on the sorted treemodel that we're
            # displaying, which is a TreeModelSort. When a row gets added,
            # we're notified of it.
            # We have to verify that that row belongs to the task we should
            # select. So, we have to wait for the task to be created, and then
            # wait for its tid to show up (invernizzi)
            def select_next_added_task_in_browser(treemodelsort, path, iter, self):
                # copy() is required because boxed structures are not copied
                # when passed in a callback without transfer
                # See https://bugzilla.gnome.org/show_bug.cgi?id=722899
                iter = iter.copy()

                def selecter(treemodelsort, path, iter, self):
                    self.__last_quick_added_tid_event.wait()
                    treeview = self.vtree_panes['active']
                    treemodelsort.disconnect(self.__quick_add_select_handle)
                    selection = treeview.get_selection()
                    selection.unselect_all()
                    # Since we use iter for selection,
                    # the task selected is bound to be correct
                    selection.select_iter(iter)

                # It cannot be another thread than the main gtk thread !
                GObject.idle_add(selecter, treemodelsort, path, iter, self)

            data = quick_add.parse(text)
            # event that is set when the new task is created
            self.__last_quick_added_tid_event = threading.Event()
            self.__quick_add_select_handle = \
                self.vtree_panes['active'].get_model().connect(
                    "row-inserted", select_next_added_task_in_browser,
                    self)
            task = self.req.new_task(newtask=True)
            self.__last_quick_added_tid = task.get_id()
            self.__last_quick_added_tid_event.set()

            # Combine tags from selection with tags from parsed text
            data['tags'].update(tags)

            if data['title'] != '':
                task.set_title(data['title'])
                task.set_to_keep()

            for tag in data['tags']:
                if not tag.startswith('@'):
                    tag = '@' + tag

                task.add_tag(tag)

            task.set_start_date(data['start'])
            task.set_due_date(data['due'])

            if data['recurring']:
                task.set_recurring(True, data['recurring'], newtask=True)

            self.quickadd_entry.set_text('')

            # signal the event for the plugins to catch
            GObject.idle_add(self.emit, "task-added-via-quick-add", task.get_id())
        else:
            # if no text is selected, we open the currently selected task
            nids = self.vtree_panes['active'].get_selected_nodes()
            for nid in nids:
                self.app.open_task(nid)

    def on_tag_treeview_button_press_event(self, treeview, event):
        """
        deals with mouse click event on the tag tree
        """
        log.debug("Received button event #%d at %d, %d" % (
            event.button, event.x, event.y))
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                # The location we want the cursor to return to
                # after we're done.
                self.previous_cursor = treeview.get_cursor()
                # For use in is_task_visible
                self.previous_tag = self.get_selected_tags()
                # Let's us know that we're working on a tag.
                self.tag_active = True

                # This location is stored in case we need to work with it
                # later on.
                self.target_cursor = path, col
                treeview.set_cursor(path, col, 0)
                # the nospecial=True disable right clicking for special tags
                selected_tags = self.get_selected_tags(nospecial=True)
                selected_search = self.get_selected_search()
                # popup menu for searches
                # FIXME thos two branches could be simplified
                # (there is no difference betweenn search and normal tag
                if selected_search is not None:
                    my_tag = self.req.get_tag(selected_search)
                    self.tagpopup.set_tag(my_tag)
                    self.tagpopup.popup(None, None, None, None, event.button, time)
                elif len(selected_tags) > 0:
                    # Then we are looking at single, normal tag rather than
                    # the special 'All tags' or 'Tasks without tags'. We only
                    # want to popup the menu for normal tags.
                    my_tag = self.req.get_tag(selected_tags[0])
                    self.tagpopup.set_tag(my_tag)
                    self.tagpopup.popup(None, None, None, None, event.button, time)
                else:
                    self.reset_cursor()
            return True

    def on_tag_treeview_key_press_event(self, treeview, event):
        keyname = Gdk.keyval_name(event.keyval)
        is_shift_f10 = (keyname == "F10" and
                        event.get_state() & Gdk.ModifierType.SHIFT_MASK)
        if is_shift_f10 or keyname == "Menu":
            selected_tags = self.get_selected_tags(nospecial=True)
            selected_search = self.get_selected_search()
            # FIXME thos two branches could be simplified (there is
            # no difference betweenn search and normal tag
            # popup menu for searches
            if selected_search is not None:
                self.tagpopup.set_tag(selected_search)
                self.tagpopup.popup(None, None, None, None, 0, event.time)
            elif len(selected_tags) > 0:
                # Then we are looking at single, normal tag rather than
                # the special 'All tags' or 'Tasks without tags'. We only
                # want to popup the menu for normal tags.
                selected_tag = self.req.get_tag(selected_tags[0])
                self.tagpopup.set_tag(selected_tag)
                self.tagpopup.popup(None, None, None, None, 0, event.time)
            else:
                self.reset_cursor()
            return True
        if keyname == "Delete":
            self.on_delete_tag_activate(event)
            return True

    def on_delete_tag_activate(self, event):
        tags = self.get_selected_tags()
        self.deletetags_dialog.delete_tags(tags)

    def on_delete_tag(self, event):
        tags = self.get_selected_tags()
        for tagname in tags:
            self.req.delete_tag(tagname)
            tag = self.req.get_tag(tagname)
            self.app.reload_opened_editors(tag.get_related_tasks())
        self.tagtreeview.set_cursor(0)
        self.on_select_tag()

    def on_task_treeview_button_press_event(self, treeview, event):
        """ Pop up context menu on right mouse click in the main
        task tree view """
        log.debug(f"Received button event #{event.button} at {event.x},{event.y}")
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                selection = treeview.get_selection()
                if selection.count_selected_rows() > 0:
                    if not selection.path_is_selected(path):
                        treeview.set_cursor(path, col, 0)
                else:
                    treeview.set_cursor(path, col, 0)
                treeview.grab_focus()
                self.app.action_enabled_changed('add_parent', True)
                if not self.have_same_parent():
                    self.app.action_enabled_changed('add_parent', False)
                self.open_menu.popup_at_pointer(event)

            return True

    def on_task_treeview_key_press_event(self, treeview, event):
        keyname = Gdk.keyval_name(event.keyval)
        is_shift_f10 = (keyname == "F10" and
                        event.get_state() & Gdk.ModifierType.SHIFT_MASK)

        if is_shift_f10 or keyname == "Menu":
            self.open_menu.popup_at_pointer(event)
            return True

    def on_closed_task_treeview_button_press_event(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            pthinfo = treeview.get_path_at_pos(x, y)

            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                selection = treeview.get_selection()
                if selection.count_selected_rows() > 0:
                    if not selection.path_is_selected(path):
                        treeview.set_cursor(path, col, 0)
                else:
                    treeview.set_cursor(path, col, 0)

                treeview.grab_focus()
                self.closed_menu.popup_at_pointer(event)

            return True

    def on_closed_task_treeview_key_press_event(self, treeview, event):
        keyname = Gdk.keyval_name(event.keyval)
        is_shift_f10 = (keyname == "F10" and
                        event.get_state() & Gdk.ModifierType.SHIFT_MASK)

        if is_shift_f10 or keyname == "Menu":
            self.closed_menu.popup_at_pointer(event)
            return True

    def on_add_task(self, widget=None):
        tags = [tag for tag in self.get_selected_tags() if tag.startswith('@')]
        task = self.req.new_task(tags=tags, newtask=True)
        uid = task.get_id()
        self.app.open_task(uid, new=True)

    def on_add_subtask(self, widget=None):
        uid = self.get_selected_task()
        if uid:
            zetask = self.req.get_task(uid)
            tags = [t.get_name() for t in zetask.get_tags()]
            task = self.req.new_task(tags=tags, newtask=True)
            # task.add_parent(uid)
            zetask.add_child(task.get_id())

            # if the parent task is recurring, its child must be also.
            task.inherit_recursion()

            self.app.open_task(task.get_id(), new=True)

    def on_add_parent(self, widget=None):
        selected_tasks = self.get_selected_tasks()
        first_task = self.req.get_task(selected_tasks[0])
        if len(selected_tasks):
            parents = first_task.get_parents()
            if parents:
                # Switch parents
                for p_tid in parents:
                    par = self.req.get_task(p_tid)
                    if par.get_status() == Task.STA_ACTIVE:
                        new_parent = par.new_subtask()
                        for uid_task in selected_tasks:
                            par.remove_child(uid_task)
                            new_parent.add_child(uid_task)
            else:
                # If the tasks have no parent already, no need to switch parents
                new_parent = self.req.new_task(newtask=True)
                for uid_task in selected_tasks:
                    new_parent.add_child(uid_task)

            self.app.open_task(new_parent.get_id(), new=True)

    def on_edit_active_task(self, widget=None, row=None, col=None):
        tid = self.get_selected_task()
        if tid:
            self.app.open_task(tid)

    def on_edit_done_task(self, widget, row=None, col=None):
        tid = self.get_selected_task('closed')
        if tid:
            self.app.open_task(tid)

    def on_delete_tasks(self, widget=None, tid=None):
        # If we don't have a parameter, then take the selection in the
        # treeview
        if not tid:
            # tid_to_delete is a [project, task] tuple
            tids_todelete = self.get_selected_tasks()
            if not tids_todelete:
                return
        else:
            tids_todelete = [tid]

        log.debug(f"going to delete {tids_todelete}")
        self.app.delete_tasks(tids_todelete, self)

    def update_start_date(self, widget, new_start_date):
        tasks = [self.req.get_task(uid)
                 for uid in self.get_selected_tasks()
                 if uid is not None]

        start_date = Date.parse(new_start_date)

        # FIXME:If the task dialog is displayed, refresh its start_date widget
        for task in tasks:
            task.set_start_date(start_date)

    def update_start_to_next_day(self, day_number):
        """Update start date to N days from today."""

        tasks = [self.req.get_task(uid)
                 for uid in self.get_selected_tasks()
                 if uid is not None]

        next_day = Date.today() + datetime.timedelta(days=day_number)

        for task in tasks:
            task.set_start_date(next_day)

    def on_mark_as_started(self, action, param):
        self.update_start_date(None, "today")

    def on_start_for_today(self, action, param):
        """Set a task to start today."""

        self.update_start_date(None, "today")

    def on_start_for_tomorrow(self, action, param):
        """Set a task to start tomorrow."""

        self.update_start_date(None, "tomorrow")

    def on_start_for_next_day_2(self, action, param):
        """Set a task to start two days from today."""

        self.update_start_to_next_day(2)

    def on_start_for_next_day_3(self, action, param):
        """Set a task to start three days from today."""

        self.update_start_to_next_day(3)

    def on_start_for_next_day_4(self, action, param):
        """Set a task to start four days from today."""

        self.update_start_to_next_day(4)

    def on_start_for_next_day_5(self, action, param):
        """Set a task to start five days from today."""

        self.update_start_to_next_day(5)

    def on_start_for_next_day_6(self, action, param):
        """Set a task to start six days from today."""

        self.update_start_to_next_day(6)

    def on_start_for_next_week(self, action, param):
        self.update_start_date(None, "next week")

    def on_start_for_next_month(self, action, param):
        self.update_start_date(None, "next month")

    def on_start_for_next_year(self, action, param):
        self.update_start_date(None, "next year")

    def on_start_clear(self, action, param):
        self.update_start_date(None, None)

    def update_due_date(self, widget, new_due_date):
        tasks = [self.req.get_task(uid)
                 for uid in self.get_selected_tasks()
                 if uid is not None]

        due_date = Date.parse(new_due_date)

        # FIXME: If the task dialog is displayed, refresh its due_date widget
        for task in tasks:
            task.set_due_date(due_date)

    def on_set_due_today(self, action, param):
        self.update_due_date(None, "today")

    def on_set_due_tomorrow(self, action, param):
        self.update_due_date(None, "tomorrow")

    def on_set_due_next_week(self, action, param):
        self.update_due_date(None, "next week")

    def on_set_due_next_month(self, action, param):
        self.update_due_date(None, "next month")

    def on_set_due_next_year(self, action, param):
        self.update_due_date(None, "next year")

    def on_set_due_now(self, action, param):
        self.update_due_date(None, "now")

    def on_set_due_soon(self, action, param):
        self.update_due_date(None, "soon")

    def on_set_due_someday(self, action, param):
        self.update_due_date(None, "someday")

    def on_set_due_clear(self, action, param):
        self.update_due_date(None, None)

    def on_start_for_specific_date(self, action, param):
        """ Display Calendar to set start date of selected tasks """

        self.calendar.set_title(_("Set Start Date"))

        # Get task from task name
        task = self.req.get_task(self.get_selected_tasks()[0])
        date = task.get_start_date()
        self.calendar.set_date(date, GTGCalendar.DATE_KIND_START)
        self.calendar.show()

    def on_set_due_for_specific_date(self, action, param):
        """ Display Calendar to set due date of selected tasks """

        self.calendar.set_title(_("Set Due Date"))

        # Get task from task name
        task = self.req.get_task(self.get_selected_tasks()[0])

        if not task.get_due_date():
            date = task.get_start_date()
        else:
            date = task.get_due_date()

        self.calendar.set_date(date, GTGCalendar.DATE_KIND_DUE)
        self.calendar.show()

    def update_recurring(self, recurring, recurring_term):
        tasks = [self.req.get_task(uid)
                 for uid in self.get_selected_tasks()
                 if uid is not None]

        for task in tasks:
            task.set_recurring(recurring, recurring_term, True)

    def update_toggle_recurring(self):
        tasks = [self.req.get_task(uid)
                 for uid in self.get_selected_tasks()
                 if uid is not None]
        for task in tasks:
            task.toggle_recurring()

    def on_set_recurring_every_day(self, action, param):
        self.update_recurring(True, 'day')

    def on_set_recurring_every_otherday(self, action, param):
        self.update_recurring(True, 'other-day')

    def on_set_recurring_every_week(self, action, param):
        self.update_recurring(True, 'week')

    def on_set_recurring_every_month(self, action, param):
        self.update_recurring(True, 'month')

    def on_set_recurring_every_year(self, action, param):
        self.update_recurring(True, 'year')

    def on_toggle_recurring(self, action, param):
        self.update_toggle_recurring()

    def on_date_changed(self, calendar):
        # Get tasks' list from task names' list
        tasks = [self.req.get_task(task) for task in self.get_selected_tasks()]
        date, date_kind = calendar.get_selected_date()
        if date_kind == GTGCalendar.DATE_KIND_DUE:
            for task in tasks:
                task.set_due_date(date)
        elif date_kind == GTGCalendar.DATE_KIND_START:
            for task in tasks:
                task.set_start_date(date)

    def on_modify_tags(self, action, params):
        """Open modify tags dialog for selected tasks."""

        tasks = self.get_selected_tasks()
        self.modifytags_dialog.modify_tags(tasks)

    def close_all_task_editors(self, task_id):
        """ Including editors of subtasks """
        all_subtasks = []

        def trace_subtasks(root):
            all_subtasks.append(root)
            for i in root.get_subtasks():
                if i not in all_subtasks:
                    trace_subtasks(i)

        trace_subtasks(self.req.get_task(task_id))

        for task in all_subtasks:
            self.app.close_task(task.get_id())

    def on_mark_as_done(self, widget=None):
        tasks_uid = [uid for uid in self.get_selected_tasks()
                     if uid is not None]
        if len(tasks_uid) == 0:
            return
        tasks = [self.req.get_task(uid) for uid in tasks_uid]
        tasks_status = [task.get_status() for task in tasks]
        for uid, task, status in zip(tasks_uid, tasks, tasks_status):
            if status == Task.STA_DONE:
                # Marking as undone
                task.set_status(Task.STA_ACTIVE)
                # Parents of that task must be updated - not to be shown
                # in workview, update children count, etc.
                for parent_id in task.get_parents():
                    parent = self.req.get_task(parent_id)
                    parent.modified()
            else:
                task.set_status(Task.STA_DONE)
                self.close_all_task_editors(uid)

    def on_dismiss_task(self, widget=None):
        tasks_uid = [uid for uid in self.get_selected_tasks()
                     if uid is not None]
        if len(tasks_uid) == 0:
            return
        tasks = [self.req.get_task(uid) for uid in tasks_uid]
        tasks_status = [task.get_status() for task in tasks]
        for uid, task, status in zip(tasks_uid, tasks, tasks_status):
            if status == Task.STA_DISMISSED:
                task.set_status(Task.STA_ACTIVE)
            else:
                task.set_status(Task.STA_DISMISSED)
                self.close_all_task_editors(uid)

    def _reapply_filter(self, current_pane):
        filters = self.get_selected_tags()
        filters.append(current_pane)
        vtree = self.req.get_tasks_tree(name=current_pane, refresh=False)
        # Re-applying search if some search is specified
        search = self.search_entry.get_text()
        if search:
            filters.append(SEARCH_TAG)
        # only resetting filters if the applied filters are different from
        # current ones, leaving a chance for liblarch to make the good call on
        # whether to refilter or not
        if sorted(filters) != sorted(vtree.list_applied_filters()):
            vtree.reset_filters(refresh=False)
        # Browsing and applying filters. For performance optimization, only
        # allowing liblarch to trigger a refresh on last item. This way the
        # refresh is never triggered more than once and we let the possibility
        # to liblarch not to trigger refresh is filters did not change.
        for filter_name in filters:
            is_last = filter_name == filters[-1]
            if filter_name == SEARCH_TAG:
                self._try_filter_by_query(search, refresh=is_last)
            else:
                vtree.apply_filter(filter_name, refresh=is_last)

    def on_select_tag(self, widget=None, row=None, col=None):
        """ Callback for tag(s) selection from left sidebar.

        Using liblarch built-in cache.
        Optim: reseting it on first item, allows trigger refresh on last.
        """
        for tagname in self.get_selected_tags():
            # In case of search tag, set query in quickadd for
            # refining search query
            tag = self.req.get_tag(tagname)
            if tag.is_search_tag():
                self.quickadd_entry.set_text(tag.get_attribute("query"))
                break

        self._reapply_filter(self.get_selected_pane())

    def on_pane_switch(self, obj, pspec):
        """ Callback for pane switching.
        No reset of filters, allows trigger refresh on last tag filtering.
        """
        current_pane = self.get_selected_pane()
        self.config.set('view', current_pane)
        self._reapply_filter(current_pane)

# PUBLIC METHODS ###########################################################
    def have_same_parent(self):
        """Determine whether the selected tasks have the same parent"""
        selected_tasks = self.get_selected_tasks()
        first_task = self.req.get_task(selected_tasks[0])
        parents = first_task.get_parents()

        for uid in selected_tasks[1:]:
            task = self.req.get_task(uid)
            if parents != task.get_parents():
                return False
        return True

    def has_any_selection(self):
        """Determine if the current pane has any task selected."""

        current_pane = self.get_selected_pane()
        selected = self.vtree_panes[current_pane].get_selected_nodes()

        return bool(selected)

    def get_selected_pane(self):
        """ Get the selected pane in the stack switcher """

        current = self.stack_switcher.get_stack().get_visible_child_name()

        return PANE_STACK_NAMES_MAP[current]

    def get_selected_tree(self, refresh: bool = False):
        return self.req.get_tasks_tree(name=self.get_selected_pane(),
                                       refresh=refresh)

    def get_selected_task(self, tv=None):
        """
        Returns the'uid' of the selected task, if any.
        If multiple tasks are selected, returns only the first and
        takes care of selecting only that (unselecting the others)

        @param tv: The tree view to find the selected task in. Defaults to
            the task_tview.
        """
        ids = self.get_selected_tasks(tv)
        if len(ids) > 0:
            # FIXME: we should also unselect all the others
            return ids[0]
        else:
            return None

    def get_selected_tasks(self, tv=None):
        """
        Returns a list of 'uids' of the selected tasks, and the corresponding
        iters

        @param tv: The tree view to find the selected task in. Defaults to
            the task_tview.
        """

        selected = []
        if tv:
            selected = self.vtree_panes[tv].get_selected_nodes()
        else:
            current_pane = self.get_selected_pane()
            selected = self.vtree_panes[current_pane].get_selected_nodes()
            for i in self.vtree_panes:
                if len(selected) == 0:
                    selected = self.vtree_panes[i].get_selected_nodes()
        return selected

    # If nospecial=True, only normal @tag are considered
    def get_selected_tags(self, nospecial=False):
        """
        Returns the selected nodes from the tagtree

        @param nospecial: doesn't return tags that do not stat with
        """
        taglist = []
        if self.tagtreeview:
            taglist = self.tagtreeview.get_selected_nodes()
        # If no selection, we display all
        if not nospecial and (not taglist or len(taglist) < 0):
            taglist = ['gtg-tags-all']
        if nospecial:
            for t in list(taglist):
                if not t.startswith('@'):
                    taglist.remove(t)
        return taglist

    def select_on_sidebar(self, value):
        """Select a row in the tag treeview (by value)."""

        try:
            selection = self.tagtreeview.get_selection()

        except AttributeError:
            # tagtreeview is None if it's hidden
            return

        model = self.tagtreeview.get_model()
        tree_iter = model.get_iter_first()

        result = self.find_value_in_treestore(model, tree_iter, value)
        selection.select_iter(result)

    def reset_cursor(self):
        """ Returns the cursor to the tag that was selected prior
            to any right click action. Should be used whenever we're done
            working with any tag through a right click menu action.
            """
        if self.tag_active:
            self.tag_active = False
            path, col = self.previous_cursor
            if self.tagtreeview:
                self.tagtreeview.set_cursor(path, col, 0)

    def set_target_cursor(self):
        """ Selects the last tag to be right clicked.

            We need this because the context menu will deactivate
            (and in turn, call reset_cursor()) before, for example, the color
            picker dialog begins. Should be used at the beginning of any tag
            editing function to remind the user which tag they're working with.
            """
        if not self.tag_active:
            self.tag_active = True
            path, col = self.target_cursor
            if self.tagtreeview:
                self.tagtreeview.set_cursor(path, col, 0)

    def add_page_to_sidebar_notebook(self, icon, page):
        """Adds a new page tab to the left panel.  The tab will
        be added as the last tab.  Also causes the tabs to be
        shown if they're not.
        @param icon: a Gtk.Image picture to display on the tab
        @param page: Gtk.Frame-based panel to be added
        """
        return self._add_page(self.sidebar_notebook, icon, page)

    def add_page_to_main_notebook(self, title, page):
        """Adds a new page tab to the top right main panel.  The tab
        will be added as the last tab.  Also causes the tabs to be
        shown.
        @param title: Short text to use for the tab label
        @param page: Gtk.Frame-based panel to be added
        """
        return self._add_page(self.main_notebook, Gtk.Label(label=title), page)

    def remove_page_from_sidebar_notebook(self, page):
        """Removes a new page tab from the left panel.  If this leaves
        only one tab in the notebook, the tab selector will be hidden.
        @param page: Gtk.Frame-based panel to be removed
        """
        return self._remove_page(self.sidebar_notebook, page)

    def remove_page_from_main_notebook(self, page):
        """Removes a new page tab from the top right main panel.  If
        this leaves only one tab in the notebook, the tab selector will
        be hidden.
        @param page: Gtk.Frame-based panel to be removed
        """
        return self._remove_page(self.main_notebook, page)

    def hide(self):
        """ Hides the task browser """
        self.browser_shown = False
        self.hide()
        GObject.idle_add(self.emit, "visibility-toggled")

    def show(self):
        """ Unhides the MainWindow """
        self.browser_shown = True
        # redraws the GDK window, bringing it to front
        self.show()
        self.present()
        self.grab_focus()
        self.quickadd_entry.grab_focus()
        GObject.idle_add(self.emit, "visibility-toggled")

    def iconify(self):
        """ Minimizes the MainWindow """
        self.iconify()

    def is_visible(self):
        """ Returns true if window is shown or false if hidden. """
        return self.get_property("visible")

    def is_active(self):
        """ Returns true if window is the currently active window """

        return self.get_property("is-active") or self.menu.is_visible()

    def get_builder(self):
        return self.builder

    def get_window(self):
        return self

    def is_shown(self):
        return self.browser_shown

# BACKENDS RELATED METHODS ###################################################
    def on_backend_failed(self, sender, backend_id, error_code):
        """
        Signal callback.
        When a backend fails to work, loads a Gtk.Infobar to alert the user

        @param sender: not used, only here for signal compatibility
        @param backend_id: the id of the failing backend
        @param error_code: a backend error code, as specified
            in BackendsSignals
        """
        infobar = self._new_infobar(backend_id)
        infobar.set_error_code(error_code)

    def on_backend_needing_interaction(self, sender, backend_id, description,
                                       interaction_type, callback):
        """
        Signal callback.
        When a backend needs some kind of feedback from the user,
        loads a Gtk.Infobar to alert the user.
        This is used, for example, to request confirmation after authenticating
        via OAuth.

        @param sender: not used, only here for signal compatibility
        @param backend_id: the id of the failing backend
        @param description: a string describing the interaction needed
        @param interaction_type: a string describing the type of interaction
                                 (yes/no, only confirm, ok/cancel...)
        @param callback: the function to call when the user provides the
                         feedback
        """
        infobar = self._new_infobar(backend_id)
        infobar.set_interaction_request(description, interaction_type, callback)

    def __remove_backend_infobar(self, child, backend_id):
        """
        Helper function to remove an Gtk.Infobar related to a backend

        @param child: a Gtk.Infobar
        @param backend_id: the id of the backend which Gtk.Infobar should be
                            removed.
        """
        if isinstance(child, BackendInfoBar) and\
                child.get_backend_id() == backend_id:
            if self.vbox_toolbars:
                self.vbox_toolbars.remove(child)

    def remove_backend_infobar(self, sender, backend_id):
        """
        Signal callback.
        Deletes the Gtk.Infobars related to a backend

        @param sender: not used, only here for signal compatibility
        @param backend_id: the id of the backend which Gtk.Infobar should be
                            removed.
        """
        backend = self.req.get_backend(backend_id)
        if not backend or (backend and backend.is_enabled()):
            # remove old infobar related to backend_id, if any
            if self.vbox_toolbars:
                self.vbox_toolbars.foreach(self.__remove_backend_infobar, backend_id)

    def _new_infobar(self, backend_id):
        """
        Helper function to create a new infobar for a backend

        @param backend_id: the backend for which we're creating the infobar
        @returns Gtk.Infobar: the created infobar
        """
        # remove old infobar related to backend_id, if any
        if not self.vbox_toolbars:
            return
        self.vbox_toolbars.foreach(self.__remove_backend_infobar, backend_id)
        # add a new one
        infobar = BackendInfoBar(self.req, self, self.app, backend_id)
        self.vbox_toolbars.pack_start(infobar, True, True, 0)
        return infobar

# SEARCH RELATED STUFF ########################################################
    def get_selected_search(self):
        """ return just one selected view """
        if self.tagtreeview:
            tags = self.tagtreeview.get_selected_nodes()
            if len(tags) > 0:
                tag = self.tagtree.get_node(tags[0])
                if tag.is_search_tag():
                    return tags[0]
        return None

    def expand_search_tag(self):
        """ For some unknown reason, search tag is not expanded correctly and
        it must be done manually """
        if self.tagtreeview is not None:
            model = self.tagtreeview.get_model()
            search_iter = model.my_get_iter((SEARCH_TAG, ))
            search_path = model.get_path(search_iter)
            self.tagtreeview.expand_row(search_path, False)
