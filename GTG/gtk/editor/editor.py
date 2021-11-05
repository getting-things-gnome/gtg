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
"""
This is the TaskEditor

It's the window you see when you double-click on a Task
The main text widget is a home-made TextView called TaskView (see taskview.py)
The rest is the logic of the widget: date changing widgets, buttons, ...
"""
import datetime
import logging
import os
import time
from gettext import gettext as _, ngettext

from gi.repository import Gdk, Gtk, GLib, Pango
from gi.repository.GObject import signal_handler_block
from GTG.core.dates import Accuracy, Date
from GTG.core.dirs import UI_DIR
from GTG.core.plugins.api import PluginAPI
from GTG.core.plugins.engine import PluginEngine
from GTG.core.task import Task
from GTG.gtk.editor import GnomeConfig
from GTG.gtk.editor.calendar import GTGCalendar
from GTG.gtk.editor.recurring_menu import RecurringMenu
from GTG.gtk.editor.taskview import TaskView
from GTG.gtk.tag_completion import tag_filter
from GTG.gtk.colors import rgb_to_hex
"""
TODO (jakubbrindza): re-factor tag_filter into a separate module
"""

log = logging.getLogger(__name__)


@Gtk.Template(filename=os.path.join(UI_DIR, "task_editor.ui"))
class TaskEditor(Gtk.Window):
    __gtype_name__ = "TaskEditor"

    editormenu = Gtk.Template.Child("editor_menu")
    donebutton = Gtk.Template.Child("mark_as_done")
    undonebutton = Gtk.Template.Child("mark_as_undone")
    add_subtask = Gtk.Template.Child()
    tag_store = Gtk.Template.Child()
    parent_button = Gtk.Template.Child("parent")
    repeat_button = Gtk.Template.Child('set_repeat')
    scrolled = Gtk.Template.Child("scrolledtask")
    plugin_box = Gtk.Template.Child("pluginbox")

    tags_entry = Gtk.Template.Child()
    tags_tree = Gtk.Template.Child()

    # Closed date
    closed_box = Gtk.Template.Child()
    closed_popover = Gtk.Template.Child()
    closed_entry = Gtk.Template.Child("closeddate_entry")
    closed_calendar = Gtk.Template.Child("calendar_closed")

    # Start date
    start_box = Gtk.Template.Child()
    start_popover = Gtk.Template.Child()
    start_entry = Gtk.Template.Child("startdate_entry")
    start_calendar = Gtk.Template.Child("calendar_start")

    # Due date
    due_popover = Gtk.Template.Child()
    due_entry = Gtk.Template.Child("duedate_entry")
    due_calendar = Gtk.Template.Child("calendar_due")

    def __init__(self,
                 requester,
                 app,
                 task,
                 thisisnew=False,
                 clipboard=None):
        """
        req is the requester
        app is the view manager
        thisisnew is True when a new task is created and opened
        """
        super().__init__()
        self.req = requester
        self.app = app
        self.browser_config = self.req.get_config('browser')
        self.config = self.req.get_task_config(task.get_id())
        self.time = None
        self.clipboard = clipboard

        self.set_application(app)

        if task.has_parent():
            self.parent_button.set_label(_('Open Parent'))
        else:
            self.parent_button.set_label(_('Add Parent'))

        # Connect signals for the calendar
        self.start_handle = self.start_calendar.connect(
            'day-selected', lambda c: self.on_date_selected(c, GTGCalendar.DATE_KIND_START))

        self.due_handle = self.due_calendar.connect(
            'day-selected', lambda c: self.on_date_selected(c, GTGCalendar.DATE_KIND_DUE))

        self.closed_handle = self.closed_calendar.connect(
            'day-selected', lambda c: self.on_date_selected(c, GTGCalendar.DATE_KIND_CLOSED))
        start_entry_controller = Gtk.EventControllerFocus()
        start_entry_controller.connect("enter", self.show_popover_start)
        start_entry_controller.connect("leave", self.startdate_focus_out)
        self.start_entry.add_controller(start_entry_controller)
        due_entry_controller = Gtk.EventControllerFocus()
        due_entry_controller.connect("enter", self.show_popover_due)
        due_entry_controller.connect("leave", self.duedate_focus_out)
        self.due_entry.add_controller(due_entry_controller)
        closed_entry_controller = Gtk.EventControllerFocus()
        closed_entry_controller.connect("enter", self.show_popover_closed)
        closed_entry_controller.connect("leave", self.closeddate_focus_out)
        self.closed_entry.add_controller(closed_entry_controller)

        self.connect("notify::is-active", self.on_window_focus_change)

        # Removing the Normal textview to replace it by our own
        # So don't try to change anything with glade, this is a home-made
        # widget
        self.scrolled.set_child(None)
        self.textview = TaskView(self.req, self.clipboard)
        self.textview.set_vexpand(True)
        self.scrolled.set_child(self.textview)
        conf_font_name = self.browser_config.get("font_name")
        conf_font_size = self.browser_config.get("font_size")
        if conf_font_name or conf_font_size:
            provider = Gtk.CssProvider.new()
            family_string = f'font-family:{conf_font_name};' if conf_font_name else ''
            size_string = f'font-size:{conf_font_size}pt;' if conf_font_size else ''
            provider.load_from_data(
            f""".taskview {{
                    {family_string}
                    {size_string}
                }}""".encode('utf-8')
            )
            self.textview.get_style_context().add_provider(
                provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        self.textview.browse_tag_cb = app.select_tag
        self.textview.new_subtask_cb = self.new_subtask
        self.textview.get_subtasks_cb = task.get_children
        self.textview.delete_subtask_cb = self.remove_subtask
        self.textview.rename_subtask_cb = self.rename_subtask
        self.textview.open_subtask_cb = self.open_subtask
        self.textview.save_cb = self.light_save
        self.textview.add_tasktag_cb = task.tag_added
        self.textview.remove_tasktag_cb = task.remove_tag
        self.textview.refresh_cb = self.refresh_editor
        self.textview.get_tagslist_cb = task.get_tags_name
        self.textview.tid = task.tid

        # Voila! it's done
        textview_focus_controller = Gtk.EventControllerFocus()
        textview_focus_controller.connect("enter", self.on_textview_focus_in)
        textview_focus_controller.connect("leave", self.on_textview_focus_out)
        self.textview.add_controller(textview_focus_controller)

        """
        TODO(jakubbrindza): Once all the functionality in editor is back and
        working, bring back also the accelerators! Dayleft_label needs to be
        brought back, however its position is unsure.
        """
        # self.dayleft_label = self.builder.get_object("dayleft")

        self.task = task
        tags = task.get_tags()
        text = self.task.get_text()
        title = self.task.get_title()

        # Insert text and tags as a non_undoable action, otherwise
        # the user can CTRL+Z even this inserts.
        self.textview.buffer.begin_not_undoable_action()
        self.textview.buffer.set_text(f"{title}\n")

        if text:
            self.textview.insert(text)

            # Insert any remaining tags
            if tags:
                tag_names = [t.get_name() for t in tags]
                self.textview.insert_tags(tag_names)
        else:
            # If not text, we insert tags
            if tags:
                tag_names = [t.get_name() for t in tags]
                self.textview.insert_tags(tag_names)
                start = self.textview.buffer.get_end_iter()
                self.textview.buffer.insert(start, '\n')

        # Insert subtasks if they weren't inserted in the text
        subtasks = task.get_children()
        for sub in subtasks:
            if sub not in self.textview.subtasks['tags']:
                self.textview.insert_existing_subtask(sub)

        if thisisnew:
            self.textview.select_title()
        else:
            self.task.set_to_keep()

        self.textview.buffer.end_not_undoable_action()
        self.connect("close-request", self.destruction)

        # Connect search field to tags popup
        self.tags_tree.set_search_entry(self.tags_entry)
        self.tags_tree.set_search_equal_func(self.search_function, None)

        # Recurrence
        self.recurring_menu = RecurringMenu(self.req, task.tid, self)
        self.recurring_menu.connect('notify::is-task-recurring', self.sync_repeat_button)
        self.repeat_button.set_popover(self.recurring_menu)
        self.sync_repeat_button()

        # plugins
        self.pengine = PluginEngine()
        self.plugin_api = PluginAPI(self.req, self.app, self)
        self.pengine.register_api(self.plugin_api)
        self.pengine.onTaskLoad(self.plugin_api)

        # Putting the refresh callback at the end make the start a lot faster
        self.refresh_editor()
        self.textview.grab_focus()

        self.init_dimensions()

        self.textview.set_editable(True)
        self.set_transient_for(self.app.browser)
        self.show()

    def show_popover_start(self, _=None):
        """Open the start date calendar popup."""

        start_date = (self.task.get_start_date() or Date.today()).date()

        with signal_handler_block(self.start_calendar, self.start_handle):
            gtime = GLib.DateTime.new_local(start_date.year, start_date.month, start_date.day, 0, 0, 0)
            self.start_calendar.select_day(gtime)

        self.start_popover.popup()

    def show_popover_due(self, _=None):
        """Open the due date calendar popup."""

        due_date = self.task.get_due_date()

        if not due_date or due_date.is_fuzzy():
            due_date = Date.today()

        due_date = due_date.date()

        with signal_handler_block(self.due_calendar, self.due_handle):
            gtime = GLib.DateTime.new_local(due_date.year, due_date.month, due_date.day, 0, 0, 0)
            self.due_calendar.select_day(gtime)

        self.due_popover.popup()

    def show_popover_closed(self, _=None):
        """Open the closed date calendar popup."""

        closed_date = self.task.get_closed_date().date()

        with signal_handler_block(self.closed_calendar, self.closed_handle):
            gtime = GLib.DateTime.new_local(closed_date.year, closed_date.month, closed_date.day, 0, 0, 0)
            self.closed_calendar.select_day(gtime)

        self.closed_popover.popup()

    @Gtk.Template.Callback()
    def sync_tag_store(self, widget=None):
        self.tag_store.clear()

        tags = self.req.get_tag_tree().get_all_nodes()

        used_tags = self.task.get_tags()

        for tagname in tags:
            tag = self.req.get_tag(tagname)
            if tag_filter(tag):
                is_used = tag in used_tags
                self.tag_store.append([is_used, tagname])
                """
                TODO(jakubbrindza): add sorting of the tags based on
                True | False and within each sub-group arrange them
                alphabetically
                """

    def sync_repeat_button(self, object=None, pspec=None):
        if self.recurring_menu.is_task_recurring:
            self.repeat_button.add_css_class('recurring-active')
        else:
            self.repeat_button.remove_css_class('recurring-active')

    def set_dismissable_in_menu(self, dismissable):
        """
        Set the task editor's menu items to how they are when the
        task is already dismissed/isn't. This shouldn't be called more than once with
        different arguments
        """
        # For some reason here using the menu section directly from the UI file
        # causes a crash and a weird reference count assertion error. Retrieving it from
        # the main menu instead avoids the cryptic crash
        __, __, editor_menu_con_sec = self.editormenu.iterate_item_links(0).get_next()

        # Plugins may add menu items to here, which is why we need to only remove
        # the specific item that we need instead of everything
        # Manual iteration without GI overrides is ugly
        length = editor_menu_con_sec.get_n_items()
        i = 0
        while i < length:
            name = ''.join(editor_menu_con_sec.get_item_attribute_value(
                i,
                'label',
                GLib.VariantType.new('s')).get_string()
            )
            # this might cause problems with localization if it isn't translated
            # here the same
            if name == (_("Undismiss") if dismissable else _("Dismiss")):
                editor_menu_con_sec.remove(i)
                return
            i += 1

    @Gtk.Template.Callback()
    def on_tag_toggled(self, widget, path, column):
        """We toggle by tag_row variable. tag_row is
        meant to be a tuple (is_used, tagname)"""
        tag_row = self.tag_store[path]
        tag_row[0] = not tag_row[0]

        if tag_row[0]:
            self.textview.insert_tags([tag_row[1]])
        """
        TODO(jakubbrindza): Add else case that will remove tag.
        """

    @Gtk.Template.Callback()
    def startingdate_changed(self, w):
        self.date_changed(w, GTGCalendar.DATE_KIND_START)

    @Gtk.Template.Callback()
    def startdate_cleared(self, w):
        self.on_date_cleared(w, GTGCalendar.DATE_KIND_START)

    def startdate_focus_out(self, c):
        self.date_focus_out(c.get_widget(), GTGCalendar.DATE_KIND_START)

    @Gtk.Template.Callback()
    def duedate_changed(self, w):
        self.date_changed(w, GTGCalendar.DATE_KIND_DUE)

    @Gtk.Template.Callback()
    def duedate_now_selected(self, w):
        self.on_duedate_fuzzy(w, Date.now())

    @Gtk.Template.Callback()
    def duedate_soon_selected(self, w):
        self.on_duedate_fuzzy(w, Date.soon())

    @Gtk.Template.Callback()
    def duedate_someday_selected(self, w):
        self.on_duedate_fuzzy(w, Date.someday())

    @Gtk.Template.Callback()
    def duedate_cleared(self, w):
        self.on_date_cleared(w, GTGCalendar.DATE_KIND_DUE)

    def duedate_focus_out(self, c):
        self.date_focus_out(c.get_widget(), GTGCalendar.DATE_KIND_DUE)

    @Gtk.Template.Callback()
    def closeddate_changed(self, w):
        self.date_changed(w, GTGCalendar.DATE_KIND_CLOSED)

    def closeddate_focus_out(self, c):
        self.date_focus_out(c.get_widget(), GTGCalendar.DATE_KIND_CLOSED)

    def search_function(self, model, column, key, iter, *search_data):
        """Callback when searching in the tags popup."""

        if not key.startswith('@'):
            key = f'@{key}'

        # The return value is reversed. False if it matches, True
        # otherwise.
        return not model.get(iter, column)[0].startswith(key)

    @staticmethod
    def get_monitor_dimensions() -> Gdk.Rectangle:
        """Get dimensions for the first monitor."""
        return Gdk.Display.get_default().get_monitor(0).get_geometry()

    def init_dimensions(self):
        """ Sets up size of task if possible """

        size = self.config.get('size')

        if size:
            try:
                self.set_default_size(int(size[0]), int(size[1]))
            except ValueError as e:
                log.warning('Invalid size configuration for task %s: %s',
                            self.task.get_id(), size)

    # Can be called at any time to reflect the status of the Task
    # Refresh should never interfere with the TaskView.
    # If a title is passed as a parameter, it will become
    # the new window title. If not, we will look for the task title.
    # Refreshtext is whether or not we should refresh the TaskView
    # (doing it all the time is dangerous if the task is empty)
    def refresh_editor(self, title=None, refreshtext=False):
        if self is None:
            return
        to_save = False
        # title of the window
        if title:
            self.set_title(title)
            to_save = True
        else:
            self.set_title(self.task.get_title())

        status = self.task.get_status()
        if status == Task.STA_DISMISSED:
            self.donebutton.show()
            self.undonebutton.hide()
            self.set_dismissable_in_menu(False)
        elif status == Task.STA_DONE:
            self.donebutton.hide()
            self.undonebutton.show()
            self.set_dismissable_in_menu(True)
        else:
            self.donebutton.show()
            self.undonebutton.hide()
            self.set_dismissable_in_menu(True)

        # Refreshing the parent button
        if self.task.has_parent():
            # Translators: Button label to open the parent task
            self.parent_button.set_label(_('Open Parent'))
        else:
            # Translators: Button label to add an new parent task
            self.parent_button.set_label(_('Add Parent'))

        # Refreshing the status bar labels and date boxes
        if status in [Task.STA_DISMISSED, Task.STA_DONE]:
            self.start_box.hide()
            self.closed_box.show()
        else:
            self.closed_box.hide()
            self.start_box.show()

        # refreshing the start date field
        startdate = self.task.get_start_date()
        try:
            prevdate = Date.parse(self.start_entry.get_text())
            update_date = startdate != prevdate
        except ValueError:
            update_date = True

        if update_date:
            self.start_entry.set_text(startdate.localized_str)

        # refreshing the due date field
        duedate = self.task.get_due_date()
        try:
            prevdate = Date.parse(self.due_entry.get_text())
            update_date = duedate != prevdate
        except ValueError:
            update_date = True

        if update_date:
            self.due_entry.set_text(duedate.localized_str)

        # refreshing the closed date field
        closeddate = self.task.get_closed_date()
        prevcldate = Date.parse(self.closed_entry.get_text())
        if closeddate != prevcldate:
            self.closed_entry.set_text(closeddate.localized_str)

        # refreshing the day left label
        """
        TODO(jakubbrindza): re-enable refreshing the day left.
        We need to come up how and where this information is viewed
        in the editor window.
        """
        # self.refresh_day_left()

        if refreshtext:
            self.textview.modified(refresheditor=False)
        if to_save:
            self.light_save()

    def refresh_day_left(self):
        # If the task is marked as done, we display the delay between the
        # due date and the actual closing date. If the task isn't marked
        # as done, we display the number of days left.
        status = self.task.get_status()
        if status in [Task.STA_DISMISSED, Task.STA_DONE]:
            delay = self.task.get_days_late()
            if delay is None:
                txt = ""
            elif delay == 0:
                txt = "Completed on time"
            elif delay >= 1:
                txt = ngettext("Completed %(days)d day late",
                               "Completed %(days)d days late", delay) % \
                    {'days': delay}
            elif delay <= -1:
                abs_delay = abs(delay)
                txt = ngettext("Completed %(days)d day early",
                               "Completed %(days)d days early", abs_delay) % \
                    {'days': abs_delay}
        else:
            due_date = self.task.get_due_date()
            result = due_date.days_left()
            if due_date.is_fuzzy():
                txt = ""
            elif result > 0:
                txt = ngettext("Due tomorrow!", "%(days)d days left", result)\
                    % {'days': result}
            elif result == 0:
                txt = _("Due today!")
            elif result < 0:
                abs_result = abs(result)
                txt = ngettext("Due yesterday!", "Was %(days)d days ago",
                               abs_result) % {'days': abs_result}

        style_context = self.get_style_context()
        color = style_context.get_color()
        self.dayleft_label.set_markup(
            f"<span color='{rgb_to_hex(color)}'>{txt}</span>")

    def reload_editor(self):
        task = self.task
        textview = self.textview
        task_text = task.get_text()
        task_title = task.get_title()
        textview.set_text(f"{task_title}\n")
        if task_text:
            textview.insert(f"{task_text}")
        task.set_title(task_title)
        textview.modified(full=True)

    def date_changed(self, widget, data):
        try:
            Date.parse(widget.get_text())
            valid = True
        except ValueError:
            valid = False

        if valid:
            widget.remove_css_class("error")
        else:
            # We should write in red in the entry if the date is not valid
            widget.add_css_class("error")

    def date_focus_out(self, widget, date_kind):
        try:
            datetoset = Date.parse(widget.get_text())
        except ValueError:
            datetoset = None

        if datetoset is not None:
            if date_kind == GTGCalendar.DATE_KIND_START:
                self.task.set_start_date(datetoset)
                self.start_popover.popdown()

            elif date_kind == GTGCalendar.DATE_KIND_DUE:
                self.task.set_due_date(datetoset)
                self.due_popover.popdown()

            elif date_kind == GTGCalendar.DATE_KIND_CLOSED:
                self.task.set_closed_date(datetoset)
                self.closed_popover.popdown()

            self.refresh_editor()

    def calendar_to_datetime(self, calendar):
        """
        Gtk.Calendar uses a GLib based convention for counting time.
        The rest of the world, including the datetime module, doesn't use GLib.
        This is a converter between the two. GTG follows the datetime
        convention.
        """
        gtime = calendar.get_date()
        year, month, day = gtime.get_year(), gtime.get_month(), gtime.get_day_of_month()
        return datetime.date(year, month, day)

    def on_duedate_fuzzy(self, widget, date):
        """ Callback when a fuzzy date is selected through the popup. """

        self.task.set_due_date(date)
        self.due_entry.set_text(date.localized_str)

    def on_date_cleared(self, widget, kind):
        """ Callback when a date is cleared through the popups. """

        if kind == GTGCalendar.DATE_KIND_START:
            self.task.set_start_date(Date.no_date())
            self.start_entry.set_text('')

        elif kind == GTGCalendar.DATE_KIND_DUE:
            self.task.set_due_date(Date.no_date())
            self.due_entry.set_text('')

    def on_date_selected(self, calendar, kind):
        """ Callback when a day is selected in the calendars."""

        date = self.calendar_to_datetime(calendar)

        if kind == GTGCalendar.DATE_KIND_START:
            self.task.set_start_date(Date(date))
            self.start_entry.set_text(Date(date).localized_str)

        elif kind == GTGCalendar.DATE_KIND_DUE:
            self.task.set_due_date(Date(date))
            self.due_entry.set_text(Date(date).localized_str)

        elif kind == GTGCalendar.DATE_KIND_CLOSED:
            self.task.set_closed_date(Date(date))
            self.closed_entry.set_text(Date(date).localized_str)

    def on_date_changed(self, calendar):
        date, date_kind = calendar.get_selected_date()
        if date_kind == GTGCalendar.DATE_KIND_DUE:
            self.task.set_due_date(date)
        elif date_kind == GTGCalendar.DATE_KIND_START:
            self.task.set_start_date(date)
        elif date_kind == GTGCalendar.DATE_KIND_CLOSED:
            self.task.set_closed_date(date)
        self.refresh_editor()

    def close_all_subtasks(self):
        all_subtasks = []

        def trace_subtasks(root):
            for i in root.get_subtasks():
                if i not in all_subtasks:
                    all_subtasks.append(i)
                    trace_subtasks(i)

        trace_subtasks(self.task)

        for task in all_subtasks:
            self.app.close_task(task.get_id())

    def dismiss(self):
        stat = self.task.get_status()
        if stat == Task.STA_DISMISSED:
            self.task.set_status(Task.STA_ACTIVE)
            self.refresh_editor()
        else:
            self.task.set_status(Task.STA_DISMISSED)
            self.close_all_subtasks()
            self.close(None)

    def change_status(self):
        stat = self.task.get_status()
        if stat == Task.STA_DONE:
            self.task.set_status(Task.STA_ACTIVE)
            self.refresh_editor()
        else:
            self.task.set_status(Task.STA_DONE)
            self.close_all_subtasks()
            self.close(None)

    def reopen(self):
        self.task.set_status(Task.STA_ACTIVE)
        self.refresh_editor()

    def open_subtask(self, tid):
        """Open subtask (closing parent task)."""

        task = self.req.get_task(tid)
        self.app.open_task(tid)
        self.app.close_task(task.parents[0])

    # Take the title as argument and return the subtask ID
    def new_subtask(self, title=None, tid=None):
        if tid:
            self.task.add_child(tid)
        elif title:
            subt = self.task.new_subtask()
            subt.set_title(title)
            tid = subt.get_id()
        return tid

    def remove_subtask(self, tid):
        """Remove a subtask of this task."""

        self.task.remove_child(tid)

    def rename_subtask(self, tid, new_title):
        """Rename a subtask of this task."""

        try:
            self.req.get_task(tid).set_title(new_title)
        except AttributeError:
            # There's no task at that tid
            pass


    def insert_subtask(self, action=None, param=None):
        self.textview.insert_new_subtask()
        self.textview.grab_focus()

    def inserttag_clicked(self, widget):
        itera = self.textview.get_insert()
        if itera.starts_line():
            self.textview.insert_text("@", itera)
        else:
            self.textview.insert_text(" @", itera)

    def open_parent(self):
        """
        Open (or create) the parent task,
        then close the child to avoid various window management issues
        and to prevent visible content divergence when the child title changes.
        """
        parents = self.task.get_parents()

        if not parents:
            tags = [t.get_name() for t in self.task.get_tags()]
            parent = self.req.new_task(tags=tags, newtask=True)
            parent_id = parent.get_id()

            self.task.set_parent(parent_id)
            self.app.open_task(parent_id)
            # Prevent WM issues and risks of conflicting content changes:
            self.close()

        elif len(parents) == 1:
            self.app.open_task(parents[0])
            # Prevent WM issues and risks of conflicting content changes:
            self.close()

        elif len(parents) > 1:
            self.show_multiple_parent_popover(parents)

    def show_multiple_parent_popover(self, parent_ids):
        parent_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        for parent in parent_ids:
            parent_name = self.req.get_task(parent).get_title()
            button = Gtk.ToolButton.new(None, parent_name)
            button.connect("clicked", self.on_parent_item_clicked, parent)
            parent_box.append(button)

        self.parent_popover = Gtk.Popover.new(self.parent_button)
        self.parent_popover.set_child(parent_box)
        self.parent_popover.set_transitions_enabled(True)
        self.parent_popover.show()

    # On click handler for open_parent menu items in the case of multiple parents
    def on_parent_item_clicked(self, widget, parent_id):
        self.app.open_task(parent_id)
        if self.parent_popover.get_visible():
            self.parent_popover.hide()
        # Prevent WM issues and risks of conflicting content changes:
        self.close()

    def save(self):
        self.task.set_title(self.textview.get_title())
        self.task.set_text(self.textview.get_text())
        self.task.sync()
        if self.config is not None:
            self.config.save()
        self.time = time.time()
    # light_save save the task without refreshing every 30seconds
    # We will reduce the time when the get_text will be in another thread

    def light_save(self):
        # if self.time is none, we never called any save
        if self.time:
            diff = time.time() - self.time
            tosave = diff > GnomeConfig.SAVETIME
        else:
            # we don't want to save a task while opening it
            tosave = self.textview.get_editable()
            diff = None
        if tosave:
            self.save()

    @Gtk.Template.Callback()
    def on_resize(self, widget, gparam):
        """ Save size of window """
        if self.get_realized():
            self.config.set('size', list(self.get_default_size()))

    def on_textview_focus_in(self, controller):
        self.app.browser.toggle_delete_accel(False)

    def on_textview_focus_out(self, controller):
        self.app.browser.toggle_delete_accel(True)

    def on_window_focus_change(self, window, gparam):
        # if they are not popped down, alt-tab will look broken
        if not self.is_active():
            self.start_popover.popdown()
            self.due_popover.popdown()
            self.closed_popover.popdown()
        # when focus returns on the window, the focus hasn't moved,
        # so the focus callbacks won't fire to bring back the popovers
        else:
            # HACK: the text inside the entry is focused, not the entry itself.
            # so we get the parent of the text, which is one of the entries.
            # This is an implementation detail and can change at any moment.
            # (get_parent() is basically undefined)
            focus = self.get_focus().get_parent()
            if focus == self.start_entry:
                self.show_popover_start()
            elif focus == self.due_entry:
                self.show_popover_due()
            elif focus == self.closed_entry:
                self.show_popover_closed()

    # We define dummy variable for when close is called from a callback
    def close(self, action=None, param=None):

        # We should also destroy the whole taskeditor object.
        if self:
            self.destruction()
            self.destroy()
            self = None

    def destruction(self, _=None):
        """Callback when closing the window."""

        # Save should be also called when buffer is modified
        self.pengine.onTaskClose(self.plugin_api)
        self.pengine.remove_api(self.plugin_api)

        tid = self.task.get_id()

        if self.task.is_new():
            self.req.delete_task(tid)
        else:
            self.save()
            [sub.set_to_keep() for sub in self.task.get_subtasks() if sub]

        try:
            del self.app.open_tasks[tid]
        except KeyError:
            log.debug('Task %s was already removed from the open list', tid)

    def get_task(self):
        return self.task

    def get_textview(self):
        return self.textview

    def get_window(self):
        return self

    def get_menu(self):
        return self.editormenu

    def get_plugin_box(self):
        return self.plugin_box
# -----------------------------------------------------------------------------
