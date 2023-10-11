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
from GTG.gtk.editor import GnomeConfig
from GTG.gtk.editor.calendar import GTGCalendar
from GTG.gtk.editor.recurring_menu import RecurringMenu
from GTG.gtk.editor.taskview import TaskView
from GTG.gtk.tag_completion import tag_filter
from GTG.gtk.colors import rgb_to_hex
from GTG.core.tasks import Task, Status, DEFAULT_TITLE


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

    def __init__(self, app, task):
        super().__init__()

        self.app = app
        self.ds = app.ds
        self.task = task
        self.config = app.config_core
        self.task_config = self.config.get_task_config(str(task.id))
        self.time = None
        self.clipboard = app.clipboard
        use_dark = self.config.get_subconfig('browser')

        self.set_application(app)

        if task.parent:
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
        self.textview = TaskView(app.ds, task, self.clipboard, use_dark)
        self.textview.set_vexpand(True)
        self.scrolled.set_child(self.textview)

        browser_config = self.config.get_subconfig('browser')
        conf_font_name = browser_config.get("font_name")
        conf_font_size = browser_config.get("font_size")

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

        # self.textview.browse_tag_cb = app.select_tag
        # self.textview.new_subtask_cb = self.new_subtask
        # self.textview.get_subtasks_cb = task.get_children
        # self.textview.delete_subtask_cb = self.remove_subtask
        # self.textview.rename_subtask_cb = self.rename_subtask
        # self.textview.open_subtask_cb = self.open_subtask
        # self.textview.save_cb = self.light_save
        # self.textview.add_tasktag_cb = self.tag_added
        # self.textview.remove_tasktag_cb = self.tag_removed
        # self.textview.refresh_cb = self.refresh_editor
        # self.textview.get_tagslist_cb = task.get_tags_name
        # self.textview.tid = task.id

        self.textview.browse_tag_cb = app.select_tag
        self.textview.new_subtask_cb = self.new_subtask
        self.textview.delete_subtask_cb = self.remove_subtask
        self.textview.rename_subtask_cb = self.rename_subtask
        self.textview.open_subtask_cb = self.open_subtask
        self.textview.save_cb = self.light_save
        self.textview.add_tasktag_cb = self.tag_added
        self.textview.remove_tasktag_cb = self.tag_removed
        self.textview.refresh_cb = self.refresh_editor
        self.textview.tid = task.id

        # Voila! it's done
        textview_focus_controller = Gtk.EventControllerFocus()
        textview_focus_controller.connect("enter", self.on_textview_focus_in)
        textview_focus_controller.connect("leave", self.on_textview_focus_out)
        self.textview.add_controller(textview_focus_controller)

        tags = task.tags
        text = self.task.content
        title = self.task.title

        # Insert text and tags as a non_undoable action, otherwise
        # the user can CTRL+Z even this inserts.
        self.textview.buffer.begin_irreversible_action()
        self.textview.buffer.set_text(f"{title}\n")

        if text:
            self.textview.insert(text)

            # Insert any remaining tags
            if tags:
                tag_names = [t.name for t in tags]
                self.textview.insert_tags(tag_names)
        else:
            # If not text, we insert tags
            if tags:
                tag_names = [t.name for t in tags]
                self.textview.insert_tags(tag_names)
                start = self.textview.buffer.get_end_iter()
                self.textview.buffer.insert(start, '\n')

        # Insert subtasks if they weren't inserted in the text
        subtasks = task.children
        for sub in subtasks:
            if sub.id not in self.textview.subtasks['tags']:
                self.textview.insert_existing_subtask(sub)

        # if thisisnew:
        #     self.textview.select_title()
        # else:
            # self.task.set_to_keep()

        self.textview.buffer.end_irreversible_action()

        # Connect search field to tags popup
        self.tags_tree.set_search_entry(self.tags_entry)
        self.tags_tree.set_search_equal_func(self.search_function, None)

        # Recurrence
        self.recurring_menu = RecurringMenu(self, task)
        self.recurring_menu.connect('notify::is-task-recurring', self.sync_repeat_button)
        self.repeat_button.set_popover(self.recurring_menu)
        self.sync_repeat_button()

        # Plugins
        self.pengine = PluginEngine()
        self.plugin_api = PluginAPI(self.app, self)
        self.pengine.register_api(self.plugin_api)
        self.pengine.onTaskLoad(self.plugin_api)

        # Putting the refresh callback at the end make the start a lot faster
        self.refresh_editor()
        self.textview.grab_focus()

        self.init_dimensions()

        self.connect("close-request", self.destruction)
        self.textview.set_editable(True)
        self.set_transient_for(self.app.browser)
        self.show()


    def tag_added(self, name):

        self.task.add_tag(self.ds.tags.new(name))
        self.ds.tasks.notify('task_count_no_tags')
        self.app.browser.sidebar.refresh_tags()


    def tag_removed(self, name):

        self.task.remove_tag(name)
        self.ds.tasks.notify('task_count_no_tags')
        self.app.browser.sidebar.refresh_tags()


    def show_popover_start(self, _=None):
        """Open the start date calendar popup."""

        start_date = (self.task.date_start or Date.today()).date()

        with signal_handler_block(self.start_calendar, self.start_handle):
            gtime = GLib.DateTime.new_local(start_date.year, start_date.month, start_date.day, 0, 0, 0)
            self.start_calendar.select_day(gtime)

        self.start_popover.popup()

    def show_popover_due(self, _=None):
        """Open the due date calendar popup."""

        due_date = self.task.date_due

        if not due_date or due_date.is_fuzzy():
            due_date = Date.today()

        due_date = due_date.date()

        with signal_handler_block(self.due_calendar, self.due_handle):
            gtime = GLib.DateTime.new_local(due_date.year, due_date.month, due_date.day, 0, 0, 0)
            self.due_calendar.select_day(gtime)

        self.due_popover.popup()

    def show_popover_closed(self, _=None):
        """Open the closed date calendar popup."""

        closed_date = self.task.date_closed

        with signal_handler_block(self.closed_calendar, self.closed_handle):
            gtime = GLib.DateTime.new_local(closed_date.year, closed_date.month, closed_date.day, 0, 0, 0)
            self.closed_calendar.select_day(gtime)

        self.closed_popover.popup()

    @Gtk.Template.Callback()
    def sync_tag_store(self, widget=None):

        self.tag_store.clear()
        used = set()
        
        for used_tag in self.task.tags:
            # First parameter marks the tag as used
            self.tag_store.append((True, used_tag.name))
            used.add(used_tag.name)

        for tag_name in self.ds.tags.lookup_names.keys():
            if tag_name not in used:
                self.tag_store.append((False, tag_name))
            

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
    def startdate_today(self, w):
        # change the day to something other than the current day
        # so that we could select it
        current_day = self.start_calendar.get_property('day')
        self.start_calendar.set_property('day', 1 if current_day > 1 else 2)
        self.start_calendar.select_day(GLib.DateTime.new_now_local())

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

        size = self.task_config.get('size')

        if size:
            try:
                self.set_default_size(int(size[0]), int(size[1]))
            except ValueError as e:
                log.warning('Invalid size configuration for task %s: %s',
                            self.task.id, size)

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
            self.set_title(self.task.title)

        status = self.task.status
        if status == Status.ACTIVE:
            self.donebutton.show()
            self.undonebutton.hide()
            self.set_dismissable_in_menu(False)
        elif status == Status.DONE:
            self.donebutton.hide()
            self.undonebutton.show()
            self.set_dismissable_in_menu(True)
        else:
            self.donebutton.show()
            self.undonebutton.hide()
            self.set_dismissable_in_menu(True)

        # Refreshing the parent button
        if self.task.parent:
            # Translators: Button label to open the parent task
            self.parent_button.set_label(_('Open Parent'))
        else:
            # Translators: Button label to add an new parent task
            self.parent_button.set_label(_('Add Parent'))

        # Refreshing the status bar labels and date boxes
        if status in [Status.DISMISSED, Status.DONE]:
            self.start_box.hide()
            self.closed_box.show()
        else:
            self.closed_box.hide()
            self.start_box.show()

        # refreshing the start date field
        startdate = self.task.date_start
        try:
            prevdate = Date.parse(self.start_entry.get_text())
            update_date = startdate != prevdate
        except ValueError:
            update_date = True

        if update_date:
            self.start_entry.set_text(startdate.localized_str)

        # refreshing the due date field
        duedate = self.task.date_due
        try:
            prevdate = Date.parse(self.due_entry.get_text())
            update_date = duedate != prevdate
        except ValueError:
            update_date = True

        if update_date:
            self.due_entry.set_text(duedate.localized_str)

        # refreshing the closed date field
        closeddate = self.task.date_closed
        prevcldate = Date.parse(self.closed_entry.get_text())

        if closeddate != prevcldate:
            self.closed_entry.set_text(closeddate.localized_str)


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
        task_text = task.content
        task_title = task.title
        
        textview.set_text(f"{task_title}\n")

        if task_text:
            textview.insert(f"{task_text}")

        task.title = task_title
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
                self.task.date_start = datetoset
                self.start_popover.popdown()

            elif date_kind == GTGCalendar.DATE_KIND_DUE:
                self.task.date_due = datetoset
                self.due_popover.popdown()

            elif date_kind == GTGCalendar.DATE_KIND_CLOSED:
                self.task.date_closed = datetoset
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

        self.task.date_due = date
        self.due_entry.set_text(date.localized_str)

    def on_date_cleared(self, widget, kind):
        """ Callback when a date is cleared through the popups. """

        if kind == GTGCalendar.DATE_KIND_START:
            self.task.date_start = Date.no_date()
            self.start_entry.set_text('')

        elif kind == GTGCalendar.DATE_KIND_DUE:
            self.task.date_due = Date.no_date()
            self.due_entry.set_text('')

    def on_date_selected(self, calendar, kind):
        """ Callback when a day is selected in the calendars."""

        date = self.calendar_to_datetime(calendar)

        if kind == GTGCalendar.DATE_KIND_START:
            self.task.date_start = Date(date)
            self.start_entry.set_text(Date(date).localized_str)

        elif kind == GTGCalendar.DATE_KIND_DUE:
            self.task.date_due = Date(date)
            self.due_entry.set_text(Date(date).localized_str)

        elif kind == GTGCalendar.DATE_KIND_CLOSED:
            self.task.date_closed = Date(date)
            self.closed_entry.set_text(Date(date).localized_str)

    def on_date_changed(self, calendar):
        date, date_kind = calendar.get_selected_date()
        if date_kind == GTGCalendar.DATE_KIND_DUE:
            self.task.date_due = date
        elif date_kind == GTGCalendar.DATE_KIND_START:
            self.task.date_start = date
        elif date_kind == GTGCalendar.DATE_KIND_CLOSED:
            self.task.date_closed = date
        self.refresh_editor()

    def close_all_subtasks(self):
        all_subtasks = []

        def trace_subtasks(root):
            for c in root.children:
                if c.id not in all_subtasks:
                    all_subtasks.append(c)
                    trace_subtasks(c)

        trace_subtasks(self.task)

        for task in all_subtasks:
            self.app.close_task(task.id)

    def dismiss(self):
        self.task.toggle_dismissed()
        self.refresh_editor()

        if self.task.status != Status.ACTIVE:
            self.close_all_subtasks()
            self.close()


    def change_status(self):
        self.task.toggle_active()
        self.refresh_editor()

        if self.task.status != Status.ACTIVE:
            self.close_all_subtasks()
            self.close()


    def reopen(self):
        self.task.toggle_active()
        self.refresh_editor()

    def open_subtask(self, tid):
        """Open subtask (closing parent task)."""

        task = self.ds.tasks.lookup[tid]
        self.app.open_task(task)
        
        if task.parent:
            self.app.close_task(task.parent.id)

    def new_subtask(self, title=None, tid=None):
        if tid:
            self.app.ds.tasks.parent(self.task.id, tid)

            return self.app.ds.tasks.lookup[tid]
        
        elif title and not tid:
            t = self.app.ds.tasks.new(title, self.task.id)
            tid = t.id
            self.app.ds.tasks.refresh_lookup_cache()

            return t
        
        elif title and tid:
            t = self.app.ds.tasks.new(title, self.task.id)
            t.id = tid
            self.app.ds.tasks.refresh_lookup_cache()
            
            return t

    def remove_subtask(self, tid):
        """Remove a subtask of this task."""

        self.app.ds.tasks.unparent(tid, self.task.id)

    def rename_subtask(self, tid, new_title):
        """Rename a subtask of this task."""

        try:
            self.app.ds.tasks.get(tid).title = new_title
        except (AttributeError, KeyError):
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
        parent = self.task.parent
        self.save()

        if not parent:
            parent = self.ds.tasks.new()
            parent.tags = self.task.tags
            self.app.ds.tasks.parent(self.task.id, parent.id)

            self.app.open_task(parent)

            # Prevent WM issues and risks of conflicting content changes:
            self.close()

        else:
            self.app.open_task(parent)
            self.close()


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
        t = self.app.ds.tasks.get(self.task.id)
        t.title = self.textview.get_title()
        t.content = self.textview.get_text()
        self.app.ds.save()

        if self.task_config is not None:
            self.task_config.save()

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
            self.task_config.set('size', list(self.get_default_size()))

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
            super().close()
            self = None


    def is_new(self) -> bool:
        return (self.task.title == DEFAULT_TITLE 
                and self.textview.get_text() == '')
        

    def destruction(self, _=None):
        """Callback when closing the window."""

        # Save should be also called when buffer is modified
        # self.pengine.onTaskClose(self.plugin_api)
        # self.pengine.remove_api(self.plugin_api)

        tid = self.task.id

        if self.is_new():
            self.app.ds.tasks.remove(tid)
        else:
            self.save()

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
