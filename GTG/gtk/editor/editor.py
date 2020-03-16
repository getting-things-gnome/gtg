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
import time
import datetime
import os

from gi.repository import Gdk, Gtk, Pango, Gio

from GTG.core.dirs import UI_DIR
from GTG.core.plugins.api import PluginAPI
from GTG.core.plugins.engine import PluginEngine
from GTG.core.task import Task
from GTG.core.translations import _, ngettext
from GTG.gtk.editor import GnomeConfig
from GTG.gtk.editor.calendar import GTGCalendar
from GTG.gtk.editor.taskview import TaskView
from GTG.gtk.tag_completion import tag_filter
from GTG.core.dates import Date
from GTG.tools.logger import log
"""
TODO (jakubbrindza): re-factor tag_filter into a separate module
"""


class TaskEditor():

    EDITOR_UI_FILE = os.path.join(UI_DIR, "taskeditor.ui")

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
        self.req = requester
        self.app = app
        self.browser_config = self.req.get_config('browser')
        self.config = self.req.get_task_config(task.get_id())
        self.time = None
        self.clipboard = clipboard
        self.builder = Gtk.Builder()
        self.builder.add_from_file(self.EDITOR_UI_FILE)
        self.donebutton = self.builder.get_object("mark_as_done")
        self.undonebutton = self.builder.get_object("mark_as_undone")
        self.dismissbutton = self.builder.get_object("dismiss")
        self.undismissbutton = self.builder.get_object("undismiss")
        self.add_subtask = self.builder.get_object("add_subtask")
        self.tag_store = self.builder.get_object("tag_store")
        self.parent_button = self.builder.get_object("parent")

        # Closed date
        self.closed_popover = self.builder.get_object("closed_popover")
        self.closed_entry = self.builder.get_object("closeddate_entry")
        self.closed_calendar = self.builder.get_object("calendar_closed")

        # Start date
        self.start_popover = self.builder.get_object("start_popover")
        self.start_entry = self.builder.get_object("startdate_entry")
        self.start_calendar = self.builder.get_object("calendar_start")

        # Due date
        self.due_popover = self.builder.get_object("due_popover")
        self.due_entry = self.builder.get_object("duedate_entry")
        self.due_calendar = self.builder.get_object("calendar_due")


        # Create our dictionary and connect it
        dic = {
            "on_tags_popover": self.open_tags_popover,
            "on_tag_toggled": self.on_tag_toggled,

            "on_move": self.on_move,

            "show_popover_start": self.show_popover_start,
            "startdate_selected": lambda c: self.on_date_selected(
                c, GTGCalendar.DATE_KIND_START),
            "startingdate_changed": lambda w: self.date_changed(
                w, GTGCalendar.DATE_KIND_START),
            "startdate_cleared": lambda w: self.on_date_cleared(
                w, GTGCalendar.DATE_KIND_START),
            "startdate_focus_out": lambda w, e: self.date_focus_out(
                w, e, GTGCalendar.DATE_KIND_START),

            "show_popover_due": self.show_popover_due,
            "duedate_selected": lambda c: self.on_date_selected(
                c, GTGCalendar.DATE_KIND_DUE),
            "duedate_changed": lambda w: self.date_changed(
                w, GTGCalendar.DATE_KIND_DUE),
            "duedate_now_selected": lambda w: self.on_duedate_fuzzy(
                w, Date.now()),
            "duedate_soon_selected": lambda w: self.on_duedate_fuzzy(
                w, Date.soon()),
            "duedate_someday_selected": lambda w: self.on_duedate_fuzzy(
                w, Date.someday()),
            "duedate_cleared": lambda w: self.on_date_cleared(
                w, GTGCalendar.DATE_KIND_DUE),
            "duedate_focus_out": lambda w, e: self.date_focus_out(
                w, e, GTGCalendar.DATE_KIND_DUE),

            "show_popover_closed": self.show_popover_closed,
            "closeddate_changed": lambda w: self.date_changed(
                w, GTGCalendar.DATE_KIND_CLOSED),
            "closeddate_selected": lambda c: self.on_date_selected(
                c, GTGCalendar.DATE_KIND_CLOSED),
            "closeddate_focus_out": lambda w, e: self.date_focus_out(
                w, e, GTGCalendar.DATE_KIND_CLOSED),
        }

        self.builder.connect_signals(dic)
        self.window = self.builder.get_object("TaskEditor")
        self.window.set_application(app)

        # Removing the Normal textview to replace it by our own
        # So don't try to change anything with glade, this is a home-made
        # widget
        textview = self.builder.get_object("textview")
        scrolled = self.builder.get_object("scrolledtask")
        scrolled.remove(textview)
        self.textview = TaskView(self.req, self.clipboard)
        self.textview.show()
        self.textview.set_subtask_callback(self.new_subtask)
        self.textview.open_task_callback(self.app.open_task)
        self.textview.set_left_margin(7)
        self.textview.set_right_margin(5)
        scrolled.add(self.textview)
        conf_font_value = self.browser_config.get("font_name")
        if conf_font_value != "":
            self.textview.override_font(Pango.FontDescription(conf_font_value))
        # Voila! it's done

        """
        TODO(jakubbrindza): Once all the functionality in editor is back and
        working, bring back also the accelerators! Dayleft_label needs to be
        brought back, however its position is unsure.
        """
        # self.dayleft_label = self.builder.get_object("dayleft")

        self.task = task
        tags = task.get_tags()
        self.textview.subtasks_callback(task.get_children)
        self.textview.removesubtask_callback(task.remove_child)
        self.textview.set_get_tagslist_callback(task.get_tags_name)
        self.textview.set_add_tag_callback(task.add_tag)
        self.textview.set_remove_tag_callback(task.remove_tag)
        self.textview.save_task_callback(self.light_save)

        texte = self.task.get_text()
        title = self.task.get_title()
        # the first line is the title
        self.textview.set_text(f"{title}\n")
        # we insert the rest of the task
        if texte:
            self.textview.insert(f"{texte}")
        else:
            # If not text, we insert tags
            if tags:
                for t in tags:
                    self.textview.insert_text("%s, " % t.get_name())
                self.textview.insert_text("\n")
            # If we don't have text, we still need to insert subtasks if any
            subtasks = task.get_children()
            if subtasks:
                self.textview.insert_subtasks(subtasks)
        # We select the title if it's a new task
        if thisisnew:
            self.textview.select_title()
        else:
            self.task.set_to_keep()
        self.textview.modified(full=True)
        self.window.connect("destroy", self.destruction)

        # Connect search field to tags popup
        self.tags_entry = self.builder.get_object("tags_entry")
        self.tags_tree = self.builder.get_object("tags_tree")

        self.tags_tree.set_search_entry(self.tags_entry)
        self.tags_tree.set_search_equal_func(self.search_function, None)

        # plugins
        self.pengine = PluginEngine()
        self.plugin_api = PluginAPI(self.req, self.app, self)
        self.pengine.register_api(self.plugin_api)
        self.pengine.onTaskLoad(self.plugin_api)

        # Putting the refresh callback at the end make the start a lot faster
        self.textview.refresh_callback(self.refresh_editor)
        self.refresh_editor()
        self.textview.grab_focus()

        self.init_dimensions()

        self.window.insert_action_group('app', app)
        self.window.insert_action_group('win', app.browser)
        self._set_actions()

        self.textview.set_editable(True)
        self.window.show()

    def _set_actions(self):
        """Setup actions."""

        action_entries = [
            ('editor.close', self.close,
             ('app.editor.close', ['Escape', '<ctrl>w'])),
            ('editor.show_parent', self.on_parent_select, None),
            ('editor.delete', self.delete_task, None),
            ('editor.open_tags_popup', self.open_tags_popover, None),
        ]

        for action, callback, accel in action_entries:
            simple_action = Gio.SimpleAction.new(action, None)
            simple_action.connect('activate', callback)
            simple_action.set_enabled(True)

            self.app.add_action(simple_action)

            if accel is not None:
                self.app.set_accels_for_action(*accel)

    def show_popover_start(self, widget, event):
        """Open the start date calendar popup."""

        self.start_popover.popup()

    def show_popover_due(self, widget, popover):
        """Open the due date calendar popup."""

        self.due_popover.popup()

    def show_popover_closed(self, widget, popover):
        """Open the closed date calendar popup."""

        self.closed_popover.popup()

    def open_tags_popover(self, action, param):
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

    def search_function(self, model, column, key, iter, *search_data):
        """Callback when searching in the tags popup."""

        if not key.startswith('@'):
            key = f'@{key}'

        # The return value is reversed. False if it matches, True
        # otherwise.
        return not model.get(iter, column)[0].startswith(key)

    def init_dimensions(self):
        """ Restores position and size of task if possible """
        position = self.config.get('position')
        if position and len(position) == 2:
            try:
                self.window.move(int(position[0]), int(position[1]))
            except ValueError:
                log.warning(
                    'Invalid position configuration for task %s: %s',
                    self.task.get_id(), position)

        size = self.config.get('size')
        if size and len(size) == 2:
            try:
                self.window.resize(int(size[0]), int(size[1]))
            except ValueError:
                log.warning(
                    'Invalid size configuration for task %s: %s',
                    self.task.get_id(), size)

    # Can be called at any time to reflect the status of the Task
    # Refresh should never interfere with the TaskView.
    # If a title is passed as a parameter, it will become
    # the new window title. If not, we will look for the task title.
    # Refreshtext is whether or not we should refresh the TaskView
    # (doing it all the time is dangerous if the task is empty)
    def refresh_editor(self, title=None, refreshtext=False):
        if self.window is None:
            return
        to_save = False
        # title of the window
        if title:
            self.window.set_title(title)
            to_save = True
        else:
            self.window.set_title(self.task.get_title())

        status = self.task.get_status()
        if status == Task.STA_DISMISSED:
            self.donebutton.show()
            self.undonebutton.hide()
            self.dismissbutton.hide()
            self.undismissbutton.show()
        elif status == Task.STA_DONE:
            self.donebutton.hide()
            self.undonebutton.show()
            self.dismissbutton.show()
            self.undismissbutton.hide
        else:
            self.donebutton.show()
            self.undonebutton.hide()
            self.dismissbutton.show()
            self.undismissbutton.hide()

        # Refreshing the the parent button
        has_parents = len(self.task.get_parents()) > 0
        self.parent_button.set_sensitive(has_parents)

        # Refreshing the status bar labels and date boxes
        if status in [Task.STA_DISMISSED, Task.STA_DONE]:
            self.builder.get_object("start_box").hide()
            self.builder.get_object("closed_box").show()
        else:
            self.builder.get_object("closed_box").hide()
            self.builder.get_object("start_box").show()

        # refreshing the start date field
        startdate = self.task.get_start_date()
        try:
            prevdate = Date.parse(self.start_entry.get_text())
            update_date = startdate != prevdate
        except ValueError:
            update_date = True

        if update_date:
            self.start_entry.set_text(str(startdate))

        # refreshing the due date field
        duedate = self.task.get_due_date()
        try:
            prevdate = Date.parse(self.due_entry.get_text())
            update_date = duedate != prevdate
        except ValueError:
            update_date = True

        if update_date:
            self.due_entry.set_text(str(duedate))

        # refreshing the closed date field
        closeddate = self.task.get_closed_date()
        prevcldate = Date.parse(self.closed_entry.get_text())
        if closeddate != prevcldate:
            self.closed_entry.set_text(str(closeddate))

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

        style_context = self.window.get_style_context()
        color = style_context.get_color(Gtk.StateFlags.INSENSITIVE).to_color()
        self.dayleft_label.set_markup(
            f"<span color='{color.to_string()}'>{txt}</span>")

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
            # If the date is valid, we write with default color in the widget
            # "none" will set the default color.
            widget.override_color(Gtk.StateType.NORMAL, None)
            widget.override_background_color(Gtk.StateType.NORMAL, None)
        else:
            # We should write in red in the entry if the date is not valid
            text_color = Gdk.RGBA()
            text_color.parse("#F00")
            widget.override_color(Gtk.StateType.NORMAL, text_color)

            bg_color = Gdk.RGBA()
            bg_color.parse("#F88")
            widget.override_background_color(Gtk.StateType.NORMAL, bg_color)

    def date_focus_out(self, widget, event, date_kind):
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
        Gtk.Calendar uses a 0-based convention for counting months.
        The rest of the world, including the datetime module, starts from 1.
        This is a converter between the two. GTG follows the datetime
        convention.
        """

        year, month, day = calendar.get_date()
        return datetime.date(year, month + 1, day)

    def on_duedate_fuzzy(self, widget, date):
        """ Callback when a fuzzy date is selected through the popup. """

        self.task.set_due_date(date)
        self.due_entry.set_text(str(date))

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
            self.start_entry.set_text(str(Date(date)))

        elif kind == GTGCalendar.DATE_KIND_DUE:
            self.task.set_due_date(Date(date))
            self.due_entry.set_text(str(Date(date)))

        elif kind == GTGCalendar.DATE_KIND_CLOSED:
            self.task.set_closed_date(Date(date))
            self.closed_entry.set_text(str(Date(date)))



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

    def delete_task(self, action, param):
        # this triggers the closing of the window in the view manager
        if self.task.is_new():
            self.app.close_task(self.task.get_id(), self.window)
        else:
            self.app.ask_delete_tasks([self.task.get_id()], self.window)

    # Take the title as argument and return the subtask ID
    def new_subtask(self, title=None, tid=None):
        if tid:
            self.task.add_child(tid)
        elif title:
            subt = self.task.new_subtask()
            subt.set_title(title)
            tid = subt.get_id()
        return tid

    def insert_subtask(self, action=None, param=None):
        self.textview.insert_newtask()
        self.textview.grab_focus()

    def inserttag_clicked(self, widget):
        itera = self.textview.get_insert()
        if itera.starts_line():
            self.textview.insert_text("@", itera)
        else:
            self.textview.insert_text(" @", itera)

    def on_parent_select(self, action, param):
        parents = self.task.get_parents()

        if len(parents) == 1:
            self.app.open_task(parents[0])
        elif len(parents) > 1:
            self.show_multiple_parent_popover(parents)

    def show_multiple_parent_popover(self, parent_ids):
        parent_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        for parent in parent_ids:
            parent_name = self.req.get_task(parent).get_title()
            button = Gtk.ToolButton.new(None, parent_name)
            button.connect("clicked", self.on_parent_item_clicked, parent)
            parent_box.add(button)

        self.parent_popover = Gtk.Popover.new(self.parent_button)
        self.parent_popover.add(parent_box)
        self.parent_popover.set_property("border-width", 0)
        self.parent_popover.set_position(Gtk.PositionType.BOTTOM)
        self.parent_popover.set_transitions_enabled(True)
        self.parent_popover.show_all()

    # On click handler for open_parent_button's menu items
    def on_parent_item_clicked(self, widget, parent_id):
        self.app.open_task(parent_id)
        if self.parent_popover.get_visible():
            self.parent_popover.hide()

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

    # This will bring the Task Editor to front
    def present(self):
        self.window.present()

    def get_position(self):
        return self.window.get_position()

    def on_move(self, widget, event):
        """ Save position and size of window """
        self.config.set('position', self.window.get_position())
        self.config.set('size', self.window.get_size())

    # We define dummy variable for when close is called from a callback
    def close(self, action=None, param=None):

        # We should also destroy the whole taskeditor object.
        if self.window:
            self.window.destroy()
            self.window = None

    # The destroy signal is linked to the "close" button. So if we call
    # destroy in the close function, this will cause the close to be called
    # twice
    # To solve that, close will just call "destroy" and the destroy signal
    # Will be linked to this destruction method that will save the task
    def destruction(self, a=None):
        # Save should be also called when buffer is modified
        self.pengine.onTaskClose(self.plugin_api)
        self.pengine.remove_api(self.plugin_api)
        tid = self.task.get_id()
        if self.task.is_new():
            self.req.delete_task(tid)
        else:
            self.save()
            for i in self.task.get_subtasks():
                if i:
                    i.set_to_keep()
        self.app.close_task(tid)

    def get_builder(self):
        return self.builder

    def get_task(self):
        return self.task

    def get_textview(self):
        return self.textview

    def get_window(self):
        return self.window
# -----------------------------------------------------------------------------
