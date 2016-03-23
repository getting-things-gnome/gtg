# -*- coding: utf-8 -*-
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

from webbrowser import open as openurl
import threading

from gi.repository import GObject, Gtk, Gdk

from GTG import info
from GTG.backends.backendsignals import BackendSignals
from GTG.core.dirs import ICONS_DIR
from GTG.core.search import parse_search_query, InvalidQuery
from GTG.core.tag import SEARCH_TAG
from GTG.core.task import Task
from GTG.gtk.browser import GnomeConfig
from GTG.gtk.browser.custominfobar import CustomInfoBar
from GTG.gtk.browser.modifytags_dialog import ModifyTagsDialog
from GTG.gtk.browser.tag_context_menu import TagContextMenu
from GTG.gtk.browser.treeview_factory import TreeviewFactory
from GTG.gtk.editor.calendar import GTGCalendar
from GTG.gtk.tag_completion import TagCompletion
from GTG.tools.dates import Date
from GTG.tools.logger import Log
from GTG.gtk.help import add_help_shortcut

class TaskBrowser(GObject.GObject):
    """ The UI for browsing open and closed tasks,
    and listing tags in a tree """

    __string_signal__ = (GObject.SignalFlags.RUN_FIRST, None, (str, ))
    __none_signal__ = (GObject.SignalFlags.RUN_FIRST, None, tuple())
    __gsignals__ = {'task-added-via-quick-add': __string_signal__,
                    'visibility-toggled': __none_signal__,
                    }

    def __init__(self, requester, vmanager):
        super().__init__()
        # Object prime variables
        self.req = requester
        self.vmanager = vmanager
        self.config = self.req.get_config('browser')
        self.tag_active = False
        self.applied_tags = []

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

        # Tags
        self.tagtree = None
        self.tagtreeview = None

        # Load window tree
        self.builder = Gtk.Builder()
        self.builder.add_from_file(GnomeConfig.BROWSER_UI_FILE)

        # Define aliases for specific widgets
        self._init_widget_aliases()

        # Init non-GtkBuilder widgets
        self._init_ui_widget()

        # Initialize tooltip for GtkEntry button
        self._init_toolbar_tooltips()

        # Initialize "About" dialog
        self._init_about_dialog()

        # Create our dictionary and connect it
        self._init_signal_connections()

        # Define accelerator keys
        self._init_accelerators()

        self.restore_state_from_conf()

        # F1 shows help
        add_help_shortcut(self.window, "browser")

        self.on_select_tag()
        self.browser_shown = False

        vmanager.timer.connect('refresh', self.refresh_all_views)

# INIT HELPER FUNCTIONS #######################################################
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
        defines aliases for UI elements found in the glide file
        """
        self.window = self.builder.get_object("MainWindow")
        self.taskpopup = self.builder.get_object("task_context_menu")
        self.defertopopup = self.builder.get_object("defer_to_context_menu")
        self.ctaskpopup = self.builder.get_object("closed_task_context_menu")
        self.about = self.builder.get_object("about_dialog")
        self.main_pane = self.builder.get_object("main_pane")
        self.workview_pane = self.builder.get_object("workview_pane")
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

        self.tagpopup = TagContextMenu(self.req, self.vmanager)

    def _init_ui_widget(self):
        """ Sets the main pane with three trees for active tasks,
        actionable tasks (workview), closed tasks and creates
        ModifyTagsDialog & Calendar """
        # Tasks treeviews
        self.main_pane.add(self.vtree_panes['active'])
        self.workview_pane.add(self.vtree_panes['workview'])
        self.closed_pane.add(self.vtree_panes['closed'])

        tag_completion = TagCompletion(self.req.get_tag_tree())
        self.modifytags_dialog = ModifyTagsDialog(tag_completion, self.req)
        self.calendar = GTGCalendar()
        self.calendar.set_transient_for(self.window)
        self.calendar.connect("date-changed", self.on_date_changed)

    def init_tags_sidebar(self):
        """
        initializes the tagtree (left area with tags and searches)
        """
        # The tags treeview
        self.tagtree = self.req.get_tag_tree()
        self.tagtreeview = self.tv_factory.tags_treeview(self.tagtree)
        # Tags treeview
        self.tagtreeview.get_selection().connect('changed',
                                                 self.on_select_tag)
        self.tagtreeview.connect('button-press-event',
                                 self.on_tag_treeview_button_press_event)
        self.tagtreeview.connect('key-press-event',
                                 self.on_tag_treeview_key_press_event)
        self.tagtreeview.connect('node-expanded',
                                 self.on_tag_expanded)
        self.tagtreeview.connect('node-collapsed',
                                 self.on_tag_collapsed)
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

    def _init_toolbar_tooltips(self):
        """
        Sets tooltips for widgets which cannot be setup in .ui yet
        """
        quick_add_icon_tooltip = GnomeConfig.QUICKADD_ICON_TOOLTIP
        self.quickadd_entry.set_icon_tooltip_text(1, quick_add_icon_tooltip)

    def _init_about_dialog(self):
        """
        Show the about dialog
        """
        self.about.set_website(info.URL)
        self.about.set_website_label(info.URL)
        self.about.set_version(info.VERSION)
        self.about.set_authors(info.AUTHORS)
        self.about.set_artists(info.ARTISTS)
        self.about.set_documenters(info.DOCUMENTERS)
        self.about.set_translator_credits(info.TRANSLATORS)

    def _init_signal_connections(self):
        """
        connects signals on UI elements
        """
        SIGNAL_CONNECTIONS_DIC = {
            "on_add_task":
            self.on_add_task,
            "on_edit_active_task":
            self.on_edit_active_task,
            "on_edit_done_task":
            self.on_edit_done_task,
            "on_delete_task":
            self.on_delete_tasks,
            "on_modify_tags":
            self.on_modify_tags,
            "on_mark_as_done":
            self.on_mark_as_done,
            "on_mark_as_started":
            self.on_mark_as_started,
            "on_start_for_tomorrow":
            self.on_start_for_tomorrow,
            "on_start_for_next_week":
            self.on_start_for_next_week,
            "on_start_for_next_month":
            self.on_start_for_next_month,
            "on_start_for_next_year":
            self.on_start_for_next_year,
            "on_start_for_specific_date":
            self.on_start_for_specific_date,
            "on_start_clear":
            self.on_start_clear,
            "on_set_due_today":
            self.on_set_due_today,
            "on_set_due_tomorrow":
            self.on_set_due_tomorrow,
            "on_set_due_next_week":
            self.on_set_due_next_week,
            "on_set_due_next_month":
            self.on_set_due_next_month,
            "on_set_due_next_year":
            self.on_set_due_next_year,
            "on_set_due_soon":
            self.on_set_due_soon,
            "on_set_due_someday":
            self.on_set_due_someday,
            "on_set_due_for_specific_date":
            self.on_set_due_for_specific_date,
            "on_set_due_clear":
            self.on_set_due_clear,
            "on_dismiss_task":
            self.on_dismiss_task,
            "on_move":
            self.on_move,
            "on_size_allocate":
            self.on_size_allocate,
            "gtk_main_quit":
            self.on_close,
            "on_add_subtask":
            self.on_add_subtask,
            "on_tagcontext_deactivate":
            self.on_tagcontext_deactivate,
            "on_view_sidebar_toggled":
            self.on_sidebar_toggled,
            "on_quickadd_field_activate":
            self.on_quickadd_activate,
            "on_quickadd_field_icon_press":
            self.on_quickadd_iconpress,
            "on_view_quickadd_toggled":
            self.on_toggle_quickadd,
            "on_about_clicked":
            self.on_about_clicked,
            "on_about_delete":
            self.on_about_close,
            "on_about_close":
            self.on_about_close,
            "on_documentation_clicked":
            lambda w: openurl(info.HELP_URI),
            "on_translate_clicked":
            lambda w: openurl(info.TRANSLATE_URL),
            "on_report_bug_clicked":
            lambda w: openurl(info.REPORT_BUG_URL),
            "on_preferences_activate":
            self.open_preferences,
            "on_edit_plugins_activate":
            self.open_plugins,
            "on_edit_backends_activate":
            self.open_edit_backends,
            "on_search_activate":
            self.on_search_toggled,
            "on_save_search":
            self.on_save_search,
            "on_search":
            self.on_search,
        }
        self.builder.connect_signals(SIGNAL_CONNECTIONS_DIC)

        # When destroying this window, quit GTG
        self.window.connect("destroy", self.quit)
        self.window.connect("delete-event", self.quit)

        # Active tasks TreeView
        self.vtree_panes['active'].connect('row-activated',
                                           self.on_edit_active_task)
        tsk_treeview_btn_press = self.on_task_treeview_button_press_event
        self.vtree_panes['active'].connect('button-press-event',
                                           tsk_treeview_btn_press)
        task_treeview_key_press = self.on_task_treeview_key_press_event
        self.vtree_panes['active'].connect('key-press-event',
                                           task_treeview_key_press)
        self.vtree_panes['active'].connect('node-expanded',
                                           self.on_task_expanded)
        self.vtree_panes['active'].connect('node-collapsed',
                                           self.on_task_collapsed)

        # Workview tasks TreeView
        self.vtree_panes['workview'].connect('row-activated',
                                             self.on_edit_active_task)
        tsk_treeview_btn_press = self.on_task_treeview_button_press_event
        self.vtree_panes['workview'].connect('button-press-event',
                                             tsk_treeview_btn_press)
        task_treeview_key_press = self.on_task_treeview_key_press_event
        self.vtree_panes['workview'].connect('key-press-event',
                                             task_treeview_key_press)
        self.vtree_panes['workview'].connect('node-expanded',
                                             self.on_task_expanded)
        self.vtree_panes['workview'].connect('node-collapsed',
                                             self.on_task_collapsed)
        self.vtree_panes['workview'].set_col_visible('startdate', False)

        # Closed tasks Treeview
        self.vtree_panes['closed'].connect('row-activated',
                                           self.on_edit_done_task)
        # I did not want to break the variable and there was no other
        # option except this name:(Nimit)
        clsd_tsk_btn_prs = self.on_closed_task_treeview_button_press_event
        self.vtree_panes['closed'].connect('button-press-event',
                                           clsd_tsk_btn_prs)
        clsd_tsk_key_prs = self.on_closed_task_treeview_key_press_event
        self.vtree_panes['closed'].connect('key-press-event',
                                           clsd_tsk_key_prs)
        self.closedtree.apply_filter(self.get_selected_tags()[0], refresh=True)

        b_signals = BackendSignals()
        b_signals.connect(b_signals.BACKEND_FAILED, self.on_backend_failed)
        b_signals.connect(b_signals.BACKEND_STATE_TOGGLED,
                          self.remove_backend_infobar)
        b_signals.connect(b_signals.INTERACTION_REQUESTED,
                          self.on_backend_needing_interaction)
        self.selection = self.vtree_panes['active'].get_selection()

    def _add_accelerator_for_widget(self, agr, name, accel):
        widget = self.builder.get_object(name)
        key, mod = Gtk.accelerator_parse(accel)
        widget.add_accelerator("activate", agr, key, mod,
                               Gtk.AccelFlags.VISIBLE)

    def _init_accelerators(self):
        """
        initialize gtk accelerators for different interface elements
        """
        agr = Gtk.AccelGroup()
        self.builder.get_object("MainWindow").add_accel_group(agr)

        self._add_accelerator_for_widget(agr, "tags", "F9")
        # self._add_accelerator_for_widget(agr, "file_quit", "<Control>q")
        self._add_accelerator_for_widget(agr, "new_task", "<Control>n")
        self._add_accelerator_for_widget(agr, "tcm_add_subtask",
                                         "<Control><Shift>n")
        self._add_accelerator_for_widget(agr, "tcm_edit", "<Control>e")
        self._add_accelerator_for_widget(agr, "tcm_mark_as_done", "<Control>d")
        self._add_accelerator_for_widget(agr, "tcm_dismiss", "<Control>i")
        self._add_accelerator_for_widget(agr, "tcm_modifytags", "<Control>t")
        # TODO(jakubbrindza): We cannot apply this function to closed_pane
        # widget since it yields the following issue:
        # widget `GtkScrolledWindow' has no activatable signal "activate"
        # without arguments. This will be handled before 0.4
        # release and shortcuts for active/workview and closed will be added.
        # self._add_accelerator_for_widget(agr, "closed_pane", "<Control>F9")
        # self._add_accelerator_for_widget(agr, "help_contents", "F1")

        quickadd_field = self.builder.get_object("quickadd_field")
        key, mod = Gtk.accelerator_parse("<Control>l")
        quickadd_field.add_accelerator("grab-focus", agr, key, mod,
                                       Gtk.AccelFlags.VISIBLE)

# HELPER FUNCTIONS ##########################################################

    def on_search_toggled(self, widget):
        if self.searchbar.get_search_mode():
            self.search_button.set_active(False)
            self.searchbar.set_search_mode(False)
        else:
            self.search_button.set_active(True)
            self.searchbar.set_search_mode(True)
            self.search_entry.grab_focus()

    def on_search(self, key, widget):
        query = self.search_entry.get_text()
        Log.debug("Searching for '%s'", query)

        try:
            parsed_query = parse_search_query(query)
        except InvalidQuery as e:
            Log.warning("Invalid query '%s' : '%s'", query, e)
            return

        self.apply_filter_on_panes(SEARCH_TAG, parameters=parsed_query)

    def on_save_search(self, widget):
        query = self.search_entry.get_text()

        # Try if this is a new search tag and save it correctly
        tag_id = self.req.new_search_tag(query)

        # Apply new search right now
        if self.tagtreeview is not None:
            self.select_search_tag(tag_id)
        else:
            self.apply_filter_on_panes(tag_id)

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

    def open_preferences(self, widget):
        self.vmanager.open_preferences(self.config)

    def open_plugins(self, widget):
        self.vmanager.configure_plugins()

    def open_edit_backends(self, widget):
        self.vmanager.open_edit_backends()

    def quit(self, widget=None, data=None):
        self.vmanager.close_browser()

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
                print("Invalid liblarch path {0}".format(path))

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
            self.window.resize(width, height)

        # checks for maximum size of window
        self.window.connect('window-state-event', self.on_window_state_event)
        if self.config.get("max"):
            self.window.maximize()

        xpos = self.config.get("x_pos")
        ypos = self.config.get("y_pos")
        if ypos and xpos:
            self.window.move(xpos, ypos)

        tag_pane = self.config.get("tag_pane")
        if not tag_pane:
            self.builder.get_object("tags").set_active(False)
            self.sidebar.hide()
        else:
            self.builder.get_object("tags").set_active(True)
            if not self.tagtreeview:
                self.init_tags_sidebar()
            self.sidebar.show()

        sidebar_width = self.config.get("sidebar_width")
        self.builder.get_object("main_hpanes").set_position(sidebar_width)
        self.builder.get_object("main_hpanes").connect('notify::position',
                                                       self.on_sidebar_width)

        botpos = self.config.get("bottom_pane_position")
        self.builder.get_object("main_vpanes").set_position(botpos)
        on_bottom_pan_position = self.on_bottom_pane_position
        self.builder.get_object("main_vpanes").connect('notify::position',
                                                       on_bottom_pan_position)

        # Callbacks for sorting and restoring previous state
        model = self.vtree_panes['active'].get_model()
        model.connect('sort-column-changed', self.on_sort_column_changed)
        sort_column = self.config.get('tasklist_sort_column')
        sort_order = self.config.get('tasklist_sort_order')

        if sort_column and sort_order:
            sort_column, sort_order = int(sort_column), int(sort_order)
            model.set_sort_column_id(sort_column, sort_order)

        self.restore_collapsed_tasks()

        def open_task(req, t):
            """ Open the task if loaded. Otherwise ask for next iteration """
            if req.has_task(t):
                self.vmanager.open_task(t)
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
        xpos, ypos = self.window.get_position()
        self.config.set('x_pos', xpos)
        self.config.set('y_pos', ypos)

    def on_size_allocate(self, widget=None, data=None):
        width, height = self.window.get_size()
        self.config.set('width', width)
        self.config.set('height', height)

    def on_bottom_pane_position(self, widget, data=None):
        self.config.set('bottom_pane_position', widget.get_position())

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

    def on_tagcontext_deactivate(self, menushell):
        self.reset_cursor()

    def on_sidebar_toggled(self, widget):
        tags = self.builder.get_object("tags")
        if self.sidebar.get_property("visible"):
            tags.set_active(False)
            self.config.set("tag_pane", False)
            self.sidebar.hide()
        else:
            tags.set_active(True)
            if not self.tagtreeview:
                self.init_tags_sidebar()
            self.sidebar.show()
            self.config.set("tag_pane", True)

    def on_toggle_quickadd(self, widget):
        if widget.get_active():
            self.quickadd_pane.show()
            self.config.set('quick_add', True)
        else:
            self.quickadd_pane.hide()
            self.config.set('quick_add', False)

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
            def select_next_added_task_in_browser(treemodelsort, path,
                                                  iter, self):
                # copy() is required because boxed structures are not copied
                # when passed in a callback without transfer
                # See https://bugzilla.gnome.org/show_bug.cgi?id=722899
                iter = iter.copy()

                def selecter(treemodelsort, path, iter, self):
                    self.__last_quick_added_tid_event.wait()
                    treeview = self.vtree_panes['active']
                    treemodelsort.disconnect(
                        self.__quick_add_select_handle)
                    selection = treeview.get_selection()
                    selection.unselect_all()
                    # Since we use iter for selection,
                    # the task selected is bound to be correct
                    selection.select_iter(iter)

                # It cannot be another thread than the main gtk thread !
                GObject.idle_add(selecter, treemodelsort, path, iter, self)
            # event that is set when the new task is created
            self.__last_quick_added_tid_event = threading.Event()
            self.__quick_add_select_handle = \
                self.vtree_panes['active'].get_model().connect(
                    "row-inserted", select_next_added_task_in_browser,
                    self)
            task = self.req.new_task(newtask=True)
            self.__last_quick_added_tid = task.get_id()
            self.__last_quick_added_tid_event.set()
            task.set_complex_title(text, tags=tags)
            self.quickadd_entry.set_text('')

            # signal the event for the plugins to catch
            GObject.idle_add(self.emit, "task-added-via-quick-add",
                             task.get_id())
        else:
            # if no text is selected, we open the currently selected task
            nids = self.vtree_panes['active'].get_selected_nodes()
            for nid in nids:
                self.vmanager.open_task(nid)

    def on_quickadd_iconpress(self, widget, icon, event):
        """ Clear the text in quickadd field by clicking on 'clear' icon """
        if icon == Gtk.EntryIconPosition.SECONDARY:
            self.quickadd_entry.set_text('')

    def on_tag_treeview_button_press_event(self, treeview, event):
        """
        deals with mouse click event on the tag tree
        """
        Log.debug("Received button event #%d at %d, %d" % (
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
                    self.tagpopup.popup(None, None, None, None, event.button,
                                        time)
                elif len(selected_tags) > 0:
                    # Then we are looking at single, normal tag rather than
                    # the special 'All tags' or 'Tasks without tags'. We only
                    # want to popup the menu for normal tags.
                    my_tag = self.req.get_tag(selected_tags[0])
                    self.tagpopup.set_tag(my_tag)
                    self.tagpopup.popup(None, None, None, None, event.button,
                                        time)
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

    def on_task_treeview_button_press_event(self, treeview, event):
        """ Pop up context menu on right mouse click in the main
        task tree view """
        Log.debug("Received button event #%d at %d,%d" % (
            event.button, event.x, event.y))
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
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
                self.taskpopup.popup(None, None, None, None, event.button,
                                     time)
            return True

    def on_task_treeview_key_press_event(self, treeview, event):
        keyname = Gdk.keyval_name(event.keyval)
        is_shift_f10 = (keyname == "F10" and
                        event.get_state() & Gdk.ModifierType.SHIFT_MASK)

        if keyname == "Delete":
            self.on_delete_tasks()
            return True
        elif is_shift_f10 or keyname == "Menu":
            self.taskpopup.popup(None, None, None, None, 0, event.time)
            return True

    def on_closed_task_treeview_button_press_event(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor(path, col, 0)
                self.ctaskpopup.popup(None, None, None, None, event.button,
                                      time)
            return True

    def on_closed_task_treeview_key_press_event(self, treeview, event):
        keyname = Gdk.keyval_name(event.keyval)
        is_shift_f10 = (keyname == "F10" and
                        event.get_state() & Gdk.ModifierType.SHIFT_MASK)

        if keyname == "Delete":
            self.on_delete_tasks()
            return True
        elif is_shift_f10 or keyname == "Menu":
            self.ctaskpopup.popup(None, None, None, None, 0, event.time)
            return True

    def on_add_task(self, widget):
        tags = [tag for tag in self.get_selected_tags() if tag.startswith('@')]
        task = self.req.new_task(tags=tags, newtask=True)
        uid = task.get_id()
        self.vmanager.open_task(uid, thisisnew=True)

    def on_add_subtask(self, widget):
        uid = self.get_selected_task()
        if uid:
            zetask = self.req.get_task(uid)
            tags = [t.get_name() for t in zetask.get_tags()]
            task = self.req.new_task(tags=tags, newtask=True)
            # task.add_parent(uid)
            zetask.add_child(task.get_id())
            self.vmanager.open_task(task.get_id(), thisisnew=True)

    def on_edit_active_task(self, widget, row=None, col=None):
        tid = self.get_selected_task()
        if tid:
            self.vmanager.open_task(tid)

    def on_edit_done_task(self, widget, row=None, col=None):
        tid = self.get_selected_task('closed')
        if tid:
            self.vmanager.open_task(tid)

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
        Log.debug("going to delete %s" % tids_todelete)
        self.vmanager.ask_delete_tasks(tids_todelete)

    def update_start_date(self, widget, new_start_date):
        tasks = [self.req.get_task(uid)
                 for uid in self.get_selected_tasks()
                 if uid is not None]

        start_date = Date.parse(new_start_date)

        # FIXME:If the task dialog is displayed, refresh its start_date widget
        for task in tasks:
            task.set_start_date(start_date)

    def on_mark_as_started(self, widget):
        self.update_start_date(widget, "today")

    def on_start_for_tomorrow(self, widget):
        self.update_start_date(widget, "tomorrow")

    def on_start_for_next_week(self, widget):
        self.update_start_date(widget, "next week")

    def on_start_for_next_month(self, widget):
        self.update_start_date(widget, "next month")

    def on_start_for_next_year(self, widget):
        self.update_start_date(widget, "next year")

    def on_start_clear(self, widget):
        self.update_start_date(widget, None)

    def update_due_date(self, widget, new_due_date):
        tasks = [self.req.get_task(uid)
                 for uid in self.get_selected_tasks()
                 if uid is not None]

        due_date = Date.parse(new_due_date)

        # FIXME: If the task dialog is displayed, refresh its due_date widget
        for task in tasks:
            task.set_due_date(due_date)

    def on_set_due_today(self, widget):
        self.update_due_date(widget, "today")

    def on_set_due_tomorrow(self, widget):
        self.update_due_date(widget, "tomorrow")

    def on_set_due_next_week(self, widget):
        self.update_due_date(widget, "next week")

    def on_set_due_next_month(self, widget):
        self.update_due_date(widget, "next month")

    def on_set_due_next_year(self, widget):
        self.update_due_date(widget, "next year")

    def on_set_due_soon(self, widget):
        self.update_due_date(widget, "soon")

    def on_set_due_someday(self, widget):
        self.update_due_date(widget, "someday")

    def on_set_due_clear(self, widget):
        self.update_due_date(widget, None)

    def on_start_for_specific_date(self, widget):
        """ Display Calendar to set start date of selected tasks """
        self.calendar.set_title("Set Start Date")
        # Get task from task name
        task = self.req.get_task(self.get_selected_tasks()[0])
        date = task.get_start_date()
        self.calendar.set_date(date, GTGCalendar.DATE_KIND_START)
        # Shows the calendar just above the mouse on widget's line of symmetry
        rect = widget.get_allocation()
        result, x, y = widget.get_window().get_origin()
        self.calendar.show_at_position(x + rect.x + rect.width,
                                       y + rect.y)

    def on_set_due_for_specific_date(self, widget):
        """ Display Calendar to set due date of selected tasks """
        self.calendar.set_title("Set Due Date")
        # Get task from task name
        task = self.req.get_task(self.get_selected_tasks()[0])
        if not task.get_due_date():
            date = task.get_start_date()
        else:
            date = task.get_due_date()
        self.calendar.set_date(date, GTGCalendar.DATE_KIND_DUE)
        # Shows the calendar just above the mouse on widget's line of symmetry
        rect = widget.get_allocation()
        result, x, y = widget.get_window().get_origin()
        self.calendar.show_at_position(x + rect.x + rect.width,
                                       y + rect.y)

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

    def on_modify_tags(self, widget):
        """ Run Modify Tags dialog on selected tasks """
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
            self.vmanager.close_task(task.get_id())

    def on_mark_as_done(self, widget):
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

    def on_dismiss_task(self, widget):
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

    def apply_filter_on_panes(self, filter_name, refresh=True,
                              parameters=None):
        """ Apply filters for every pane: active tasks, closed tasks """
        # Reset quickadd_entry if another filter is applied
        self.quickadd_entry.set_text("")
        for pane in self.vtree_panes:
            vtree = self.req.get_tasks_tree(name=pane, refresh=False)
            vtree.apply_filter(filter_name, refresh=refresh,
                               parameters=parameters)

    def unapply_filter_on_panes(self, filter_name, refresh=True):
        """ Apply filters for every pane: active tasks, closed tasks """
        for pane in self.vtree_panes:
            vtree = self.req.get_tasks_tree(name=pane, refresh=False)
            vtree.unapply_filter(filter_name, refresh=refresh)

    def on_select_tag(self, widget=None, row=None, col=None):
        """
        callback for when selecting an element of the tagtree (left sidebar)
        """
        # FIXME add support for multiple selection of tags in future

        # When you click on a tag, you want to unselect the tasks
        new_taglist = self.get_selected_tags()

        for tagname in self.applied_tags:
            if tagname not in new_taglist:
                self.unapply_filter_on_panes(tagname, refresh=False)

        for tagname in new_taglist:
            if tagname not in self.applied_tags:
                self.apply_filter_on_panes(tagname)
                # In case of search tag, set query in quickadd for
                # refining search query
                tag = self.req.get_tag(tagname)
                if tag.is_search_tag():
                    self.quickadd_entry.set_text(tag.get_attribute("query"))

        self.applied_tags = new_taglist

    def on_close(self, widget=None):
        """Closing the window."""
        # Saving is now done in main.py
        self.quit()

# PUBLIC METHODS ###########################################################
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
        # FIXME Why we have active as back case? is that so? Study this code
        selected = []
        if tv:
            selected = self.vtree_panes[tv].get_selected_nodes()
        else:
            if 'active' in self.vtree_panes:
                selected = self.vtree_panes['active'].get_selected_nodes()
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
        self.window.hide()
        GObject.idle_add(self.emit, "visibility-toggled")

    def show(self):
        """ Unhides the TaskBrowser """
        self.browser_shown = True
        # redraws the GDK window, bringing it to front
        self.window.show()
        self.window.present()
        self.window.grab_focus()
        self.quickadd_entry.grab_focus()
        GObject.idle_add(self.emit, "visibility-toggled")

    def iconify(self):
        """ Minimizes the TaskBrowser """
        self.window.iconify()

    def is_visible(self):
        """ Returns true if window is shown or false if hidden. """
        return self.window.get_property("visible")

    def is_active(self):
        """ Returns true if window is the currently active window """
        return self.window.get_property("is-active")

    def get_builder(self):
        return self.builder

    def get_window(self):
        return self.window

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
        '''
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
        '''
        infobar = self._new_infobar(backend_id)
        infobar.set_interaction_request(description, interaction_type,
                                        callback)

    def __remove_backend_infobar(self, child, backend_id):
        '''
        Helper function to remove an Gtk.Infobar related to a backend

        @param child: a Gtk.Infobar
        @param backend_id: the id of the backend which Gtk.Infobar should be
                            removed.
        '''
        if isinstance(child, CustomInfoBar) and\
                child.get_backend_id() == backend_id:
            if self.vbox_toolbars:
                self.vbox_toolbars.remove(child)

    def remove_backend_infobar(self, sender, backend_id):
        '''
        Signal callback.
        Deletes the Gtk.Infobars related to a backend

        @param sender: not used, only here for signal compatibility
        @param backend_id: the id of the backend which Gtk.Infobar should be
                            removed.
        '''
        backend = self.req.get_backend(backend_id)
        if not backend or (backend and backend.is_enabled()):
            # remove old infobar related to backend_id, if any
            if self.vbox_toolbars:
                self.vbox_toolbars.foreach(self.__remove_backend_infobar,
                                           backend_id)

    def _new_infobar(self, backend_id):
        '''
        Helper function to create a new infobar for a backend

        @param backend_id: the backend for which we're creating the infobar
        @returns Gtk.Infobar: the created infobar
        '''
        # remove old infobar related to backend_id, if any
        if not self.vbox_toolbars:
            return
        self.vbox_toolbars.foreach(self.__remove_backend_infobar, backend_id)
        # add a new one
        infobar = CustomInfoBar(self.req, self, self.vmanager, backend_id)
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
