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
from __future__ import annotations

import datetime
import logging
import ast
import re
from uuid import UUID
from typing import Optional

from gi.repository import GObject, Gtk, Gdk, Gio, GLib, Xdp
from webbrowser import open as openurl
from textwrap import dedent

from GTG.core import info
from GTG.core.system_info import SystemInfo
from GTG.backends.backend_signals import BackendSignals
from GTG.core.dirs import ICONS_DIR
from gettext import gettext as _
from GTG.gtk.browser import GnomeConfig
from GTG.gtk.browser import quick_add
from GTG.gtk.browser.backend_infobar import BackendInfoBar
from GTG.gtk.browser.modify_tags import ModifyTagsDialog
from GTG.gtk.browser.delete_tag import DeleteTagsDialog
from GTG.gtk.browser.sidebar import Sidebar
from GTG.gtk.browser.task_pane import TaskPane
from GTG.gtk.editor.calendar import GTGCalendar
from GTG.gtk.tag_completion import TagCompletion
from GTG.core.dates import Date
from GTG.core.tasks import Filter, Status, Task

log = logging.getLogger(__name__)
PANE_STACK_NAMES_MAP = {
    'closed_view': 'closed',
    'open_view': 'active',
    'actionable_view': 'workview',
}
PANE_STACK_NAMES_MAP_INVERTED = {v: k for k, v in PANE_STACK_NAMES_MAP.items()}


@Gtk.Template(filename=GnomeConfig.BROWSER_UI_FILE)
class MainWindow(Gtk.ApplicationWindow):
    """ The UI for browsing open and closed tasks,
    and listing tags in a tree """

    __gtype_name__ = 'MainWindow'

    __string_signal__ = (GObject.SignalFlags.RUN_FIRST, None, (str, ))
    __none_signal__ = (GObject.SignalFlags.RUN_FIRST, None, tuple())
    __gsignals__ = {'task-added-via-quick-add': __string_signal__,
                    'task-marked-as-done': __string_signal__,
                    'task-marked-as-not-done': __string_signal__,
                    'visibility-toggled': __none_signal__,
                    }

    main_hpanes = Gtk.Template.Child()
    open_pane = Gtk.Template.Child()
    actionable_pane = Gtk.Template.Child()
    closed_pane = Gtk.Template.Child()
    tree_stack = Gtk.Template.Child('stack')

    search_entry = Gtk.Template.Child()
    searchbar = Gtk.Template.Child()
    search_button = Gtk.Template.Child()

    quickadd_entry = Gtk.Template.Child('quickadd_field')
    quickadd_pane = Gtk.Template.Child()

    sidebar_vbox = Gtk.Template.Child('sidebar_vbox')

    vbox_toolbars = None
    stack_switcher = Gtk.Template.Child()
    main_box = Gtk.Template.Child('main_view_box')

    defer_btn = Gtk.Template.Child('defer_task_button')
    defer_menu_btn = Gtk.Template.Child()
    defer_menu_days_section = Gtk.Template.Child()

    sort_btn = Gtk.Template.Child('sort_menu_btn')

    headerbar = Gtk.Template.Child('browser_headerbar')
    main_menu_btn = Gtk.Template.Child()
    main_menu = Gtk.Template.Child()
    help_overlay = Gtk.Template.Child('shortcuts')
    about = Gtk.Template.Child('about_dialog')

    def __init__(self, app):
        super().__init__(application=app)

        # Object prime variables
        self.app = app
        self.config = app.config
        self.tag_active = False

        self.sidebar = Sidebar(app, app.ds, self)
        self.sidebar_vbox.append(self.sidebar)

        self.panes: dict[str, TaskPane] = {
            'active': TaskPane(self, 'active'),
            'workview': TaskPane(self, 'workview'),
            'closed': TaskPane(self, 'closed')
        }

        self.open_pane.append(self.panes['active'])
        self.actionable_pane.append(self.panes['workview'])
        self.closed_pane.append(self.panes['closed'])

        self._init_context_menus()

        # YOU CAN DEFINE YOUR INTERNAL MECHANICS VARIABLES BELOW
        # Setup GTG icon theme
        self._init_icon_theme()

        # Init Actions
        self._set_actions()

        # Tags
        self.tagtree = None
        self.tagtreeview = None

        self.sidebar_vbox.connect('notify::visible', self._on_sidebar_visible)
        self.add_action(Gio.PropertyAction.new('sidebar', self.sidebar_vbox, 'visible'))

        # Setup help overlay (shortcuts window)
        self.set_help_overlay(self.help_overlay)

        # Init non-GtkBuilder widgets
        self._init_ui_widget()

        # Initialize "About" dialog
        self._init_about_dialog()

        # Connect manual signals
        self._init_signal_connections()

        self.restore_state_from_conf()

        self._set_defer_days()
        self.browser_shown = False

        app.timer.connect('refresh', self.refresh_all_views)
        app.timer.connect('refresh', self._set_defer_days)

        self.stack_switcher.get_stack().connect('notify::visible-child', self.on_pane_switch)

        # This needs to be called again after setting everything up,
        # so the buttons start disabled
        self.on_selection_changed()

# INIT HELPER FUNCTIONS #######################################################
    def _init_context_menus(self):
        builder = Gtk.Builder()
        builder.add_from_file(GnomeConfig.MENUS_UI_FILE)

        closed_menu_model = builder.get_object('closed_task_menu')
        self.closed_menu = Gtk.PopoverMenu.new_from_model_full(
            closed_menu_model, Gtk.PopoverMenuFlags.NESTED
        )

        self.closed_menu.set_has_arrow(False)
        self.closed_menu.set_parent(self)
        self.closed_menu.set_halign(Gtk.Align.START)
        self.closed_menu.set_position(Gtk.PositionType.BOTTOM)

        open_menu_model = builder.get_object('task_menu')
        self.open_menu = Gtk.PopoverMenu.new_from_model_full(
            open_menu_model, Gtk.PopoverMenuFlags.NESTED
        )

        self.open_menu.set_has_arrow(False)
        self.open_menu.set_parent(self)
        self.open_menu.set_halign(Gtk.Align.START)
        self.open_menu.set_position(Gtk.PositionType.BOTTOM)

        sort_menu_model = builder.get_object('sort_menu')
        self.sort_menu = Gtk.PopoverMenu.new_from_model(sort_menu_model)
        self.panes['active'].sort_btn.set_popover(self.sort_menu)


    def switch_tab_open(self, t=None , a = None):
        """switch tab 'open_view'."""
        stack = self.stack_switcher.get_stack()
        stack.set_visible_child_name('open_view')

    def switch_tab_actionable(self, t=None , a = None):
        """switch tab 'actionable_view'."""
        stack = self.stack_switcher.get_stack()
        stack.set_visible_child_name('actionable_view')

    def switch_tab_closed(self, t=None , a = None):
        """switch tab 'closed_view'."""
        stack = self.stack_switcher.get_stack()
        stack.set_visible_child_name('closed_view')


    def _set_actions(self):
        """Setup actions."""

        action_entries = [
            ('toggle_sidebar', self.on_sidebar_toggled, ('win.toggle_sidebar', ['F9'])),
            ('show_main_menu', self._show_main_menu, ('win.show_main_menu', ['F10'])),
            ('collapse_all_tasks', self.on_collapse_all_tasks, None),
            ('expand_all_tasks', self.on_expand_all_tasks, None),
            ('change_tags', self.on_modify_tags, ('win.change_tags', ['<ctrl>T'])),
            ('focus_sidebar', self.focus_sidebar, ('win.focus_sidebar', ['<ctrl>B'])),
            ('toggle_search', self.toggle_search, ('win.toggle_search', [])),
            ('search', self.activate_search, ('win.search', ['<ctrl>f'])),
            ('close_search', self.toggle_search, ('win.close_search', ['Escape'])),
            ('focus_quickentry', self.focus_quickentry, ('win.focus_quickentry', ['<ctrl>L'])),
            ('delete_task', self.on_delete_tasks, ('win.delete_task', ['<ctrl>Delete'])),
            ('help_overlay', None, ('win.show-help-overlay', ['<ctrl>question'])),
            ('switch_tab_open' , self.switch_tab_open, ('win.switch_tab_open' , ['<alt>1'])),
            ('switch_tab_actionable' , self.switch_tab_actionable, ('win.switch_tab_actionable' , ['<alt>2'])),
            ('switch_tab_closed' , self.switch_tab_closed, ('win.switch_tab_closed' , ['<alt>3'])),
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
            ('due_today', self.on_set_due_today, None),
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


        # Stateful actions from now on
        sort_variant = GLib.Variant.new_string('Title')
        sort_action = Gio.SimpleAction.new_stateful('sort',
                                                    sort_variant.get_type(),
                                                    sort_variant)

        sort_action.connect('change-state', self.on_sort)
        self.add_action(sort_action)

        order_variant = GLib.Variant.new_string('ASC')
        order_action = Gio.SimpleAction.new_stateful('sort_order',
                                                    order_variant.get_type(),
                                                    order_variant)

        order_action.connect('change-state', self.on_sort_order)
        self.add_action(order_action)


    def _init_icon_theme(self):
        """
        sets the deafault theme for icon and its directory
        """
        # TODO(izidor): Add icon dirs on app level
        Gtk.IconTheme.get_for_display(self.get_display()).add_search_path(ICONS_DIR)

    def _init_ui_widget(self):
        """ Sets the main pane with three trees for active tasks,
        actionable tasks (workview), closed tasks and creates
        ModifyTagsDialog & Calendar """
        # Tasks treeviews
        # self.open_pane.add(self.vtree_panes['active'])
        # self.actionable_pane.add(self.vtree_panes['workview'])
        # self.closed_pane.add(self.vtree_panes['closed'])

        quickadd_focus_controller = Gtk.EventControllerFocus()
        quickadd_focus_controller.connect('enter', self.on_quickadd_focus_in)
        quickadd_focus_controller.connect('leave', self.on_quickadd_focus_out)
        self.quickadd_entry.add_controller(quickadd_focus_controller)

        tag_completion = TagCompletion(self.app.ds.tags)
        self.modifytags_dialog = ModifyTagsDialog(tag_completion, self.app)
        self.modifytags_dialog.set_transient_for(self)

        self.deletetags_dialog = DeleteTagsDialog(self)
        self.calendar = GTGCalendar()
        self.calendar.set_transient_for(self)
        self.calendar.connect("date-changed", self.on_date_changed)

    def _set_defer_days(self, timer=None):
        """
        Set dynamic day labels for the toolbar's task deferring menubutton.
        """
        today = datetime.datetime.today()

        # Day 0 is "Today", day 1 is "Tomorrow",
        # so we don't need to calculate the weekday name for those.
        for i in range(0, 5):
            weekday_name = (today + datetime.timedelta(days=i + 2)).strftime('%A')
            translated_weekday_combo = _("In {number_of_days} days — {weekday}").format(
                weekday=weekday_name, number_of_days=i + 2)

            action = ''.join(self.defer_menu_days_section.get_item_attribute_value(
                i,
                'action',
                GLib.VariantType.new('s')).get_string()
            )
            replacement_item = Gio.MenuItem.new(translated_weekday_combo, action)
            self.defer_menu_days_section.remove(i)
            self.defer_menu_days_section.insert_item(i, replacement_item)


    def _init_about_dialog(self):
        """
        Show the about dialog
        """

        # Create `GtkButton`s and add to size group
        def create_uri_button(string=None, uri=None):
            btn = Gtk.Button.new_with_mnemonic(string)
            btn.connect("clicked", lambda _: openurl(uri))
            btn.set_tooltip_text(uri)
            size_group.add_widget(btn)
            return btn

        ohstats_url = f'<a href="{info.OPENHUB_URL}">OpenHub</a>'
        ghstats_url = '<a href="https://github.com/getting-things-gnome/gtg/graphs/contributors">GitHub</a>'

        UNITED_AUTHORS_OF_GTGETTON = dedent(
            _(
                """\
        Many others contributed to GTG over the years.
        You can find them on {OH_stats} and {GH_stats}."""
            ).format(OH_stats=ohstats_url, GH_stats=ghstats_url)
        )

        self.about.set_transient_for(self)
        self.about.set_modal(True)
        self.about.set_program_name(info.NAME)
        self.about.set_logo_icon_name(self.app.props.application_id)
        self.about.set_version(info.VERSION)

        # This line translated in info.py works, as it has no strings replacements
        self.about.set_comments(_(info.SHORT_DESCRIPTION))

        self.about.set_copyright(info.COPYRIGHT)
        self.about.set_license_type(Gtk.License.GPL_3_0)

        self.about.set_authors([info.AUTHORS])
        self.about.set_artists(info.ARTISTS)
        self.about.set_documenters(info.DOCUMENTERS)

        self.about.set_system_information(SystemInfo().get_system_info())

        self.about.add_credit_section(
            _("Maintained/Administered by"), info.AUTHORS_MAINTAINERS
        )

        authors = info.AUTHORS_RELEASE_CONTRIBUTORS
        authors.append(UNITED_AUTHORS_OF_GTGETTON)

        self.about.add_credit_section(
            _("Contributed by"), info.AUTHORS_RELEASE_CONTRIBUTORS
        )

        # Translators for a particular language should put their names here.
        # Please keep the width at 80 chars max, as GTK4's About dialog won't wrap text.
        # GtkAboutDialog will detect if “translator-credits” is untranslated and auto-hide the tab.
        self.about.set_translator_credits(_("translator-credits"))

        # Retrieve the `GtkBox` within GtkDialog,
        # and create `GtkSizeGroup` to group buttons
        about_box = self.about.get_first_child()
        size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)

        # Create new `GtkBox` to add button links
        uri_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 6)
        uri_box.set_halign(Gtk.Align.CENTER)
        uri_box.append(create_uri_button(_("_Website"), info.URL))
        uri_box.append(create_uri_button(_("_Dev Chatroom"), info.CHAT_URL))
        uri_box.append(create_uri_button(_("_GitHub"), info.SOURCE_CODE_URL))

        about_box.append(uri_box)


    def _init_signal_connections(self):
        """
        connects signals on UI elements
        """
        # When destroying this window, quit GTG
        self.connect("close-request", self.quit)

        # Store window position
        self.connect('notify::default-width', self.on_window_resize)
        self.connect('notify::default-height', self.on_window_resize)

        for p in PANE_STACK_NAMES_MAP.keys():
            pane = self.get_pane_by_name(p)
            pane.task_selection.connect('selection-changed', self.on_selection_changed)

        self.sidebar.connect('selection_changed', self.on_sidebar_select_changed)

        # # Active tasks TreeView
        # tsk_treeview_btn_press = self.on_task_treeview_click_begin
        # active_pane_gesture_single = Gtk.GestureSingle(
        #     button=Gdk.BUTTON_SECONDARY, propagation_phase=Gtk.PropagationPhase.CAPTURE
        # )
        # active_pane_gesture_single.connect('begin', tsk_treeview_btn_press)
        # task_treeview_key_press = self.on_task_treeview_key_press_event
        # active_pane_key_controller = Gtk.EventControllerKey()
        # active_pane_key_controller.connect('key-pressed', task_treeview_key_press)
        # self.vtree_panes['active'].add_controller(active_pane_gesture_single)
        # self.vtree_panes['active'].add_controller(active_pane_key_controller)
        # self.vtree_panes['active'].connect('node-expanded', self.on_task_expanded)
        # self.vtree_panes['active'].connect('node-collapsed', self.on_task_collapsed)

        # # Workview tasks TreeView
        # tsk_treeview_btn_press = self.on_task_treeview_click_begin
        # workview_pane_gesture_single = Gtk.GestureSingle(
        #     button=Gdk.BUTTON_SECONDARY, propagation_phase=Gtk.PropagationPhase.CAPTURE
        # )
        # workview_pane_gesture_single.connect('begin', tsk_treeview_btn_press)
        # task_treeview_key_press = self.on_task_treeview_key_press_event
        # workview_pane_key_controller = Gtk.EventControllerKey()
        # workview_pane_key_controller.connect('key-pressed', task_treeview_key_press)
        # self.vtree_panes['workview'].add_controller(workview_pane_gesture_single)
        # self.vtree_panes['workview'].add_controller(workview_pane_key_controller)
        # self.vtree_panes['workview'].set_col_visible('startdate', False)

        # Closed tasks Treeview
        # self.vtree_panes['closed'].connect('row-activated', self.on_edit_done_task)
        # I did not want to break the variable and there was no other
        # option except this name:(Nimit)
        # clsd_tsk_btn_prs = self.on_closed_task_treeview_click_begin
        # closed_pane_gesture_single = Gtk.GestureSingle(
        #     button=Gdk.BUTTON_SECONDARY, propagation_phase=Gtk.PropagationPhase.CAPTURE
        # )
        # closed_pane_gesture_single.connect('begin', clsd_tsk_btn_prs)
        # clsd_tsk_key_prs = self.on_closed_task_treeview_key_press_event
        # closed_pane_key_controller = Gtk.EventControllerKey()
        # closed_pane_key_controller.connect('key-pressed', clsd_tsk_key_prs)
        # self.vtree_panes['closed'].add_controller(closed_pane_gesture_single)
        # self.vtree_panes['closed'].add_controller(closed_pane_key_controller)
        # self.vtree_panes['closed'].connect('cursor-changed', self.on_cursor_changed)
        # # Closed tasks Treeview
        # self.vtree_panes['closed'].connect('row-activated', self.on_edit_done_task)
        # # I did not want to break the variable and there was no other
        # # option except this name:(Nimit)
        # clsd_tsk_btn_prs = self.on_closed_task_treeview_click_begin
        # self.closed_pane_gesture_single = Gtk.GestureSingle(widget=self.vtree_panes['closed'], button=Gdk.BUTTON_SECONDARY,
        #     propagation_phase=Gtk.PropagationPhase.CAPTURE)
        # self.closed_pane_gesture_single.connect('begin', clsd_tsk_btn_prs)
        # clsd_tsk_key_prs = self.on_closed_task_treeview_key_press_event
        # self.closed_pane_key_controller = Gtk.EventControllerKey(widget=self.vtree_panes['closed'])
        # self.closed_pane_key_controller.connect('key-pressed', clsd_tsk_key_prs)
        # self.vtree_panes['closed'].connect('cursor-changed', self.on_cursor_changed)

        b_signals = BackendSignals()
        b_signals.connect(b_signals.BACKEND_FAILED, self.on_backend_failed)
        b_signals.connect(b_signals.BACKEND_STATE_TOGGLED, self.remove_backend_infobar)
        b_signals.connect(b_signals.INTERACTION_REQUESTED, self.on_backend_needing_interaction)
        # self.selection = self.vtree_panes['active'].get_selection()


# HELPER FUNCTIONS ##########################################################

    def show_popup_at(self, popup, x, y):
        rect = Gdk.Rectangle()
        rect.x = x
        rect.y = y
        popup.set_pointing_to(rect)
        popup.popup()

    def show_popup_at_tree_cursor(self, popup, treeview):
        _, selected_paths = treeview.get_selection().get_selected_rows()
        rect = treeview.get_cell_area(selected_paths[0], None)
        self.show_popup_at(popup, 0, rect.y+2*rect.height)

    def toggle_search(self, *args):
        """Callback to toggle search bar."""
        if self.searchbar.get_search_mode():
            self.searchbar.set_search_mode(False)
            self.get_pane().set_search_query('')
        else:
            self.activate_search()

    def activate_search(self, *args):
          self.search_button.set_active(True)
          self.searchbar.set_search_mode(True)
          self.search_entry.select_region(0, -1)
          self.search_entry.grab_focus()
          if self.search_entry.get_text():
            self.on_search()

    @Gtk.Template.Callback()
    def on_search(self, *args):
        """Callback everytime a character is inserted in the search field."""
        self.get_pane().set_search_query(self.search_entry.get_text())


    def on_save_search(self, *args):
        query = self.search_entry.get_text()
        name = re.sub(r'!(?=\w)+', '', query)

        self.app.ds.saved_searches.new(name, query)


    def quit(self, widget=None, data=None):
        self.app.quit()

    def on_maximize(self, window, pspec):
        """ This event checks for the maximization state: maximized?
        and stores the state in self.config.max
        This is used to check the window state afterwards
        and maximize it if needed """
        self.config.set("maximized", self.is_maximized())

    def restore_collapsed_tasks(self, tasks=None):
        tasks = tasks or self.config.get("collapsed_tasks")

        for path_s in tasks:
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
                print(f"Invalid path {path}")


    def restore_tag_selection(self) -> None:
        """Restore tag selection from config."""

        # NOTE: This needs to run after MainWindow has been initialized
        # otherwise tag filtering will throw an error

        selected_tag = self.config.get('selected_tag')

        if not selected_tag:
            return

        self.sidebar.select_tag(selected_tag)


    def restore_state_from_conf(self):
        # NOTE: for the window state to be restored, this must
        # be called **before** the window is realized. The size
        # of the window cannot manually be changed later.
        width = self.config.get('width')
        height = self.config.get('height')
        if width and height:
            self.set_default_size(width, height)

        # checks for maximization window
        self.connect('notify::maximized', self.on_maximize)

        if self.config.get("maximized"):
            self.maximize()

        tag_pane = self.config.get("tag_pane")
        self.sidebar_vbox.props.visible = tag_pane

        sidebar_width = self.config.get("sidebar_width")
        self.main_hpanes.set_position(sidebar_width)
        self.main_hpanes.connect('notify::position', self.on_sidebar_width)

        pane_name = self.config.get('view')
        self.set_pane(pane_name)

        match pane_name:
            case 'actionable_view':
                sort_mode = self.config.get('sort_mode_active')
            case 'closed_view':
                sort_mode = self.config.get('sort_mode_closed')
            case _:
                sort_mode = self.config.get('sort_mode_open')

        self.set_sorter(sort_mode.capitalize())


        # Callbacks for sorting and restoring previous state
        # model = self.vtree_panes['active'].get_model()
        # model.connect('sort-column-changed', self.on_sort_column_changed)
        # sort_column = self.config.get('tasklist_sort_column')
        # sort_order = self.config.get('tasklist_sort_order')

        # if sort_column and sort_order:
        #     sort_column, sort_order = int(sort_column), int(sort_order)
        #     model.set_sort_column_id(sort_column, sort_order)

        # self.restore_collapsed_tasks()

        # view_name = PANE_STACK_NAMES_MAP_INVERTED.get(self.config.get('view'),
        #                                               PANE_STACK_NAMES_MAP_INVERTED['active'])
        # self.stack_switcher.get_stack().set_visible_child_name(view_name)

        # def open_task(ds, tid):
        #     """ Open the task if loaded. Otherwise ask for next iteration """
        #     try:
        #         task = ds.tasks.lookup[tid]
        #         self.app.open_task(task)
        #         return False
        #     except KeyError:
        #         return True

        # for t in self.config.get("opened_tasks"):
        #     GLib.idle_add(open_task, self.app.ds, t)


    def restore_editor_windows(self):
        """Restore editor window for tasks."""

        for tid in self.config.get("opened_tasks"):
            try:
                task = self.app.ds.tasks.lookup[UUID(tid)]
                self.app.open_task(task)
            except KeyError:
                log.warning("Could not restore task with id %s", tid)


    def refresh_all_views(self, timer = None) -> None:
        """Refresh all taskpanes."""

        for page in self.stack_switcher.get_stack().get_pages():
            pane = page.get_child().get_first_child()
            pane.refresh()


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

    def on_window_resize(self, widget=None, gparam=None):
        width, height = self.get_default_size()
        self.config.set('width', width)
        self.config.set('height', height)

    def on_sidebar_width(self, widget, data=None):
        self.config.set('sidebar_width', widget.get_position())

    def on_about_clicked(self, widget):
        """
        show the about dialog
        """
        self.about.show()

    @Gtk.Template.Callback()
    def on_about_close(self, widget):
        """
        close the about dialog
        """
        self.about.hide()
        return True


    def on_sidebar_select_changed(self, widget=None) -> None:
        """Callback when the sidebar selection changes. """

        for p in PANE_STACK_NAMES_MAP.keys():
            pane = self.stack_switcher.get_stack().get_child_by_name(p).get_first_child()
            pane.task_selection.unselect_all()

        # This isn't called automatically for some reason
        self.on_selection_changed()


    def on_selection_changed(self, position=None, n_items=None, user_data=None) -> None:
        """Callback when selection changes."""

        pane = self.get_pane()

        if pane.get_selected_number():
            self.defer_btn.set_sensitive(True)
            self.defer_menu_btn.set_sensitive(True)
        else:
            self.defer_btn.set_sensitive(False)
            self.defer_menu_btn.set_sensitive(False)


    def on_tagcontext_deactivate(self, menushell):
        self.reset_cursor()

    def _show_main_menu(self, action, param):
        """
        Action callback to show the main menu.
        """
        main_menu_btn = self.main_menu_btn
        main_menu_btn.props.active = not main_menu_btn.props.active

    def on_sidebar_toggled(self, action, param):
        """Toggle tags sidebar via the action."""

        self.sidebar_vbox.props.visible = not self.sidebar_vbox.props.visible

    def _on_sidebar_visible(self, obj, param):
        """Visibility of the sidebar changed."""

        assert param.name == 'visible'
        visible = obj.get_property(param.name)
        self.config.set("tag_pane", visible)

    def on_collapse_all_tasks(self, action, param):
        """Collapse all tasks."""

        self.get_pane().emit('collapse-all')

    def on_expand_all_tasks(self, action, param):
        """Expand all tasks."""

        self.get_pane().emit('expand-all')

    def on_task_expanded(self, sender, path: str):
        # For some reason, path is turned from a tuple into a string of a
        # tuple
        if type(path) is str:
            path = ast.literal_eval(path)
        tid = path[-1]

        collapsed_tasks = self.config.get("collapsed_tasks")
        stringified_path = str(path)
        if stringified_path in collapsed_tasks:
            collapsed_tasks.remove(stringified_path)
            self.config.set("collapsed_tasks", collapsed_tasks)

        # restore expanded state of subnodes
        model = sender.get_model()
        for child_id in model.tree.node_all_children(tid):
            child_path = path + (child_id,)
            if str(child_path) not in collapsed_tasks:
                # Warning: Recursion. We expect having not too many nested
                # subtasks for now.
                sender.expand_node(child_path)

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


    def focus_sidebar(self, action, param):
        """Callback to focus the sidebar widget."""

        self.sidebar_vbox.props.visible = True
        self.sidebar.general_box.get_row_at_index(0).grab_focus()


    def on_quickadd_focus_in(self, controller):
        self.toggle_delete_accel(False)

    def on_quickadd_focus_out(self, controller):
        self.toggle_delete_accel(True)

    def toggle_delete_accel(self, enable_delete_accel):
        """
        enable/disabled delete task shortcut.
        """
        accels = ['<ctrl>Delete'] if enable_delete_accel else []
        self.app.set_accels_for_action('win.delete_task', accels)

    @Gtk.Template.Callback()
    def on_quickadd_activate(self, widget) -> None:
        """ Add a new task from quickadd toolbar """

        text = self.quickadd_entry.get_text().strip()

        if not text:
            tasks = self.get_pane().get_selection()
            for t in tasks:
                self.app.open_task(t)

            return

        tags = self.sidebar.selected_tags(names_only=True)
        data = quick_add.parse(text)

        # Combine tags from selection with tags from parsed text
        data['tags'].update(tags)
        self.quickadd_entry.set_text('')

        task = self.app.ds.tasks.new(data['title'])
        task.date_start = data['start']
        task.date_due = data['due']
        self.app.ds.tasks.refresh_lookup_cache()

        #TODO: Add back recurring

        for tag in data['tags']:
            _tag = self.app.ds.tags.new(tag)
            task.add_tag(_tag)

        # signal the event for the plugins to catch
        GLib.idle_add(self.emit, "task-added-via-quick-add", task.id)
        self.get_pane().select_last()


    def on_tag_treeview_click_begin(self, gesture, sequence):
        """
        deals with mouse click event on the tag tree
        """
        _, x, y = gesture.get_point(sequence)
        log.debug("Received button event #%d at %d, %d",
                  gesture.get_current_button(), x, y)
        if gesture.get_current_button() == 3:
            pthinfo = self.tagtreeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                self.tagtreeview.grab_focus()
                # The location we want the cursor to return to
                # after we're done.
                self.previous_cursor = self.tagtreeview.get_cursor()
                # For use in is_task_visible
                self.previous_tag = self.get_selected_tags()
                # Let's us know that we're working on a tag.
                self.tag_active = True

                # This location is stored in case we need to work with it
                # later on.
                self.target_cursor = path, col
                self.tagtreeview.set_cursor(path, col, 0)
                # the nospecial=True disable right clicking for special tags
                selected_tags = self.get_selected_tags(nospecial=True)
                selected_search = self.get_selected_search()
                # popup menu for searches
                # FIXME thos two branches could be simplified
                # (there is no difference betweenn search and normal tag
                if selected_search is not None:
                    my_tag = self.req.get_tag(selected_search)
                    self.tagpopup.set_tag(my_tag)
                    self.show_popup_at(self.tagpopup, x, y)
                elif len(selected_tags) > 0:
                    # Then we are looking at single, normal tag rather than
                    # the special 'All tags' or 'Tasks without tags'. We only
                    # want to popup the menu for normal tags.
                    my_tag = self.req.get_tag(selected_tags[0])
                    self.tagpopup.set_tag(my_tag)
                    self.show_popup_at(self.tagpopup, x, y)
                else:
                    self.reset_cursor()

    def on_tag_treeview_key_press_event(self, controller, keyval, keycode, state):
        keyname = Gdk.keyval_name(keyval)
        is_shift_f10 = (keyname == "F10" and state & Gdk.ModifierType.SHIFT_MASK)
        if is_shift_f10 or keyname == "Menu":
            selected_tags = self.get_selected_tags(nospecial=True)
            selected_search = self.get_selected_search()
            # FIXME thos two branches could be simplified (there is
            # no difference betweenn search and normal tag
            # popup menu for searches
            if selected_search is not None:
                self.tagpopup.set_tag(selected_search)
                self.show_popup_at_tree_cursor(self.tagpopup, self.tagtreeview)
            elif len(selected_tags) > 0:
                # Then we are looking at single, normal tag rather than
                # the special 'All tags' or 'Tasks without tags'. We only
                # want to popup the menu for normal tags.
                selected_tag = self.req.get_tag(selected_tags[0])
                self.tagpopup.set_tag(selected_tag)
                model, titer = self.tagtreeview.get_selection().get_selected()
                self.show_popup_at_tree_cursor(self.tagpopup, self.tagtreeview)
            else:
                self.reset_cursor()
            return True
        if keyname == "Delete":
            self.on_delete_tag_activate()
            return True

    def on_delete_tag_activate(self, tags=[]):
        tags = tags or self.get_selected_tags()
        self.deletetags_dialog.show(tags)

    def on_delete_tag(self, event):
        tags = self.get_selected_tags()
        for tagname in tags:
            self.req.delete_tag(tagname)
            tag = self.req.get_tag(tagname)
            self.app.reload_opened_editors(tag.get_related_tasks())

            # TODO: New core
            self.app.ds.tags.remove(self.app.ds.tags.find(tagname).id)
            tasks = self.app.ds.tasks.filter(Filter.TAG, tagname)
            for t in tasks:
                t.remove_tag(tagname)

        self.tagtreeview.set_cursor(0)
        self.on_select_tag()

    def on_task_treeview_click_begin(self, gesture, sequence):
        """ Pop up context menu on right mouse click in the main
        task tree view """
        treeview = gesture.get_widget()
        _, x, y = gesture.get_point(sequence)
        log.debug("Received button event #%s at %d,%d",
                  gesture.get_current_button(), x, y)
        if gesture.get_current_button() == 3:
            # Only when using a filtered treeview (you have selected a specific
            # tag in tagtree), for some reason the standard coordinates become
            # wrong and you must convert them.
            # The original coordinates are still needed to put the popover
            # in the correct place
            tx, ty = treeview.convert_widget_to_bin_window_coords(x, y)
            pthinfo = treeview.get_path_at_pos(tx, ty)
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
                self.show_popup_at(self.open_menu, x, y)

    def on_task_treeview_key_press_event(self, controller, keyval, keycode, state):
        keyname = Gdk.keyval_name(keyval)
        is_shift_f10 = (keyname == "F10" and state & Gdk.ModifierType.SHIFT_MASK)

        if is_shift_f10 or keyname == "Menu":
            self.show_popup_at_tree_cursor(self.open_menu, controller.get_widget())

    def on_closed_task_treeview_click_begin(self, gesture, sequence):
        treeview = gesture.get_widget()
        _, x, y = gesture.get_point(sequence)
        if gesture.get_current_button() == 3:
            tx, ty = treeview.convert_widget_to_bin_window_coords(x, y)
            pthinfo = treeview.get_path_at_pos(tx, ty)

            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                selection = treeview.get_selection()
                if selection.count_selected_rows() > 0:
                    if not selection.path_is_selected(path):
                        treeview.set_cursor(path, col, 0)
                else:
                    treeview.set_cursor(path, col, 0)

                treeview.grab_focus()
                self.show_popup_at(self.closed_menu, x, y)

    def on_closed_task_treeview_key_press_event(self, controller, keyval, keycode, state):
        keyname = Gdk.keyval_name(keyval)
        is_shift_f10 = (keyname == "F10" and state & Gdk.ModifierType.SHIFT_MASK)

        if is_shift_f10 or keyname == "Menu":
            self.show_popup_at_tree_cursor(self.closed_menu, controller.get_widget())

    def on_add_task(self, widget=None):
        new_task = self.app.ds.tasks.new()

        for tag in self.sidebar.selected_tags():
            new_task.add_tag(tag)

        self.app.open_task(new_task)


    def on_add_subtask(self, widget=None):

        pane = self.get_pane()

        for task in pane.get_selection():
            new_task = self.app.ds.tasks.new(parent=task.id)
            new_task.tags = task.tags
            self.app.open_task(new_task)
            pane.refresh()


    def on_add_parent(self, widget=None):
        selection = self.get_pane().get_selection()

        if not selection:
            return

        parent = selection[0].parent

        # Check all tasks have the same parent
        if any(t.parent != parent for t in selection):
            return

        if parent:
            if parent.status == Status.ACTIVE:
                new_parent = self.app.ds.tasks.new(parent=parent.id)

                for task in selection:
                    self.app.ds.tasks.refresh_lookup_cache()
                    self.app.ds.tasks.unparent(task.id)
                    self.app.ds.tasks.parent(task.id, new_parent.id)
        else:
            new_parent = self.app.ds.tasks.new()

            for task in selection:
                self.app.ds.tasks.refresh_lookup_cache()
                self.app.ds.tasks.parent(task.id, new_parent.id)

            self.app.open_task(new_parent)
            self.get_pane().refresh()


    def on_edit_active_task(self, widget=None, row=None, col=None):
        for task in self.get_pane().get_selection():
            self.app.open_task(task)

    def on_edit_done_task(self, widget, row=None, col=None):
        tid = self.get_selected_task('closed')
        if tid:
            self.app.open_task(tid)


    def on_delete_tasks(self, widget=None, tid=None):
        # If we don't have a parameter, then take the selection in the
        # treeview
        if not tid:
            tasks_todelete = self.get_pane().get_selection()

            if not tasks_todelete:
                return
        else:
            tasks_todelete = [self.ds.tasks.lookup[tid]]

        log.debug("going to delete %r", tasks_todelete)
        self.app.delete_tasks(tasks_todelete, self)


    def update_start_date(self, widget, new_start_date):
        for task in self.get_pane().get_selection():
            task.date_start = new_start_date

        # Changing the start date of a task may take it out of the current pane
        # (e.g. setting the start date of an Actionable task to tomorrow)
        # See #1039
        self.get_pane().refresh()

    def update_start_to_next_day(self, day_number):
        """Update start date to N days from today."""

        next_day = Date.today() + datetime.timedelta(days=day_number)

        for task in self.get_pane().get_selection():
            task.date_start = next_day

        # Changing the start date of a task may take it out of the current pane
        # (e.g. setting the start date of an Actionable task to tomorrow)
        # See #1039
        self.get_pane().refresh()


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
        due_date = Date.parse(new_due_date)

        for task in self.get_pane().get_selection():
            task.date_due = due_date

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
        task = self.get_pane().get_selection()[0]
        date = task.date_start
        self.calendar.set_date(date, GTGCalendar.DATE_KIND_START)
        self.calendar.show()

    def on_set_due_for_specific_date(self, action, param):
        """ Display Calendar to set due date of selected tasks """

        self.calendar.set_title(_("Set Due Date"))

        # Get task from task name
        task = self.get_pane().get_selection()[0]

        if not task.date_due:
            date = task.date_start
        else:
            date = task.date_due

        self.calendar.set_date(date, GTGCalendar.DATE_KIND_DUE)
        self.calendar.show()

    def update_recurring(self, recurring, recurring_term):
        for task in self.get_pane().get_selection():
            task.set_recurring(recurring, recurring_term, True)

    def update_toggle_recurring(self):
        for task in self.get_pane().get_selection():
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
        tasks = self.get_pane().get_selection()
        date, date_kind = calendar.get_selected_date()
        if date_kind == GTGCalendar.DATE_KIND_DUE:
            for task in tasks:
                task.date_due = date
        elif date_kind == GTGCalendar.DATE_KIND_START:
            for task in tasks:
                task.date_start = date
        self.get_pane().refresh()


    def on_modify_tags(self, action, params):
        """Open modify tags dialog for selected tasks."""

        tasks = self.get_pane().get_selection()
        self.modifytags_dialog.modify_tags(tasks)


    def on_sort(self, action, value) -> None:

        action.set_state(value)
        value_str = value.get_string()

        self.set_sorter(value_str)
        self.store_sorting(value_str.lower())


    def on_sort_order(self, action, value) -> None:

        action.set_state(value)
        value_str = value.get_string()

        if value_str == 'ASC':
            self.get_pane().set_sort_order(reverse=False)
            self.change_sort_icon('ASC')
        else:
            self.get_pane().set_sort_order(reverse=True)
            self.change_sort_icon('DESC')


    def store_sorting(self, mode: str) -> None:
        """Store sorting mode."""

        match self.get_selected_pane():
            case 'actionable':
                self.config.set('sort_mode_active', mode)
            case 'closed':
                self.config.set('sort_mode_closed', mode)
            case _:
                self.config.set('sort_mode_open', mode)


    def set_sorter(self, value: str) -> None:
        """Set sorter for current task pane."""

        self.get_pane().set_sorter(value)


    def change_sort_icon(self, order: str) -> None:
        """Change icon for sorting menu button."""

        if order == 'ASC':
            self.sort_btn.set_icon_name('view-sort-ascending-symbolic')
        elif order == 'DESC':
            self.sort_btn.set_icon_name('view-sort-descending-symbolic')


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
            self.app.close_task(task.id)


    def on_mark_as_done(self, widget=None):
        for task in self.get_pane().get_selection():
            task.set_status(Status.DONE)

    def on_dismiss_task(self, widget=None):
        for task in self.get_pane().get_selection():
            task.set_status(Status.DISMISSED)

    def on_reopen_task(self, widget=None):
        for task in self.get_pane().get_selection():
            task.set_status(Status.ACTIVE)

    def on_select_tag(self, widget=None, row=None, col=None):
        """ Callback for tag(s) selection from left sidebar.

        Using liblarch built-in cache.
        Optim: reseting it on first item, allows trigger refresh on last.
        """
        for tagname in self.get_selected_tags():
            # In case of search tag, refining search query
            tag = self.req.get_tag(tagname)
            if tag.is_search_tag():
                break

        self.reapply_filter()

    def on_pane_switch(self, obj, pspec):
        """ Callback for pane switching.
        No reset of filters, allows trigger refresh on last tag filtering.
        """
        current_pane = self.get_selected_pane(old_names=False)
        self.config.set('view', current_pane)

        # HACK: We expand all the tasks in the open tab
        #       so their subtasks "exist" when switching
        #       to actionable
        self.stack_switcher.get_stack().get_first_child().get_first_child().emit('expand-all')

        self.get_pane().set_filter_tags(set(self.sidebar.selected_tags()))
        self.sidebar.change_pane(current_pane)
        self.get_pane().sort_btn.set_popover(None)
        self.get_pane().sort_btn.set_popover(self.sort_menu)

        if search_query := self.search_entry.get_text():
            self.get_pane().set_search_query(search_query)

        self.notify('is_pane_open')
        self.notify('is_pane_actionable')
        self.notify('is_pane_closed')

# PUBLIC METHODS ###########################################################
    def get_menu(self):
        """Get the primary application menu"""
        return self.main_menu

    def get_headerbar(self):
        """Get the headerbar for the window"""
        return self.headerbar

    def get_quickadd_pane(self):
        """Get the quickadd pane"""
        return self.quickadd_pane

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


    def set_pane(self, name: str) -> None:
        """Set the selected pane by name."""

        self.stack_switcher.get_stack().set_visible_child_name(name)


    def get_selected_pane(self, old_names: bool = True) -> str:
        """ Get the selected pane in the stack switcher """

        current = self.stack_switcher.get_stack().get_visible_child_name()

        if old_names:
            return PANE_STACK_NAMES_MAP[current]
        else:
            return current


    def get_pane_by_name(self, name: str) -> TaskPane:
        """Get a task pane by name."""

        return self.stack_switcher.get_stack().get_child_by_name(name).get_first_child()


    def get_pane(self):
        """Get the selected pane."""


        return self.stack_switcher.get_stack().get_visible_child().get_first_child()


    @GObject.Property(type=bool, default=True)
    def is_pane_open(self) -> bool:
        return self.get_selected_pane() == 'active'


    @GObject.Property(type=bool, default=False)
    def is_pane_actionable(self) -> bool:
        return self.get_selected_pane() == 'workview'


    @GObject.Property(type=bool, default=False)
    def is_pane_closed(self) -> bool:
        return self.get_selected_pane() == 'closed'


    def get_selected_tree(self, refresh: bool = False):
        return self.req.get_tasks_tree(name=self.get_selected_pane(),
                                       refresh=refresh)

    def get_selected_task(self, tree_view: str = '') -> Optional[Task]:
        """
        Returns the'uid' of the selected task, if any.
        If multiple tasks are selected, returns only the first and
        takes care of selecting only that (unselecting the others)

        @param tree_view: The tree view to find the selected task in.
                          Defaults to the task_tview.
        """
        ids = self.get_selected_tasks(tree_view)
        if ids:
            # FIXME: we should also unselect all the others
            return ids[0]
        else:
            return None

    def get_selected_tasks(self, tree_view: str = ''):
        """
        Returns a list of 'uids' of the selected tasks, and the corresponding
        iters

        @param tree_view: The tree view to find the selected task in.
                          Defaults to the task_tview.
        """

        selected = []
        if tree_view:
            selected = self.panes[tree_view].get_selected_nodes()
        else:
            current_pane = self.get_selected_pane()
            selected = self.panes[current_pane].get_selected_nodes()
            for i in self.panes:
                if not selected:
                    selected = self.panes[i].get_selected_nodes()
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
        if not nospecial and not taglist:
            taglist = ['gtg-tags-all']
        if nospecial:
            special = ['gtg-tags-all', 'gtg-tags-none',
                       'search', 'gtg-tags-sep']

            for t in list(taglist):
                if t in special:
                    taglist.remove(t)
                else:
                    tag = self.req.get_tag(t)
                    if tag and tag.is_search_tag():
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

    def hide(self):
        """ Hides the task browser """
        self.browser_shown = False
        self.hide()
        GLib.idle_add(self.emit, "visibility-toggled")

    def show(self):
        """ Unhides the MainWindow """
        self.browser_shown = True
        # redraws the GDK window, bringing it to front
        self.show()
        self.present()
        self.grab_focus()
        self.quickadd_entry.grab_focus()
        GLib.idle_add(self.emit, "visibility-toggled")

    def iconify(self):
        """ Minimizes the MainWindow """
        self.iconify()

    def is_visible(self):
        """ Returns true if window is shown or false if hidden. """
        return self.get_property("visible")

    def is_active(self):
        """ Returns true if window is the currently active window """

        return self.get_property("is-active") or self.menu.is_visible()

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
        backend = self.app.ds.get_backend(backend_id)
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
        infobar.set_vexpand(True)
        self.vbox_toolbars.add(infobar)
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
