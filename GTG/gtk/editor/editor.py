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
"""
This is the TaskEditor

It's the window you see when you double-click on a Task
The main text widget is a home-made TextView called TaskView (see taskview.py)
The rest is the logic of the widget: date changing widgets, buttons, ...
"""
import time
import os

from gi.repository import Gdk, Gtk, Pango

from GTG.core.dirs import UI_DIR
from GTG.core.plugins.api import PluginAPI
from GTG.core.plugins.engine import PluginEngine
from GTG.core.task import Task
from GTG.core.translations import _, ngettext
from GTG.gtk.editor import GnomeConfig
from GTG.gtk.editor.calendar import GTGCalendar
from GTG.gtk.editor.taskview import TaskView
from GTG.gtk.help import add_help_shortcut
from GTG.gtk.tag_completion import tag_filter
from GTG.tools.dates import Date
from GTG.tools.logger import Log
'''
TODO (jakubbrindza): re-factor tag_filter into a separate module
'''


class TaskEditor(object):

    EDITOR_UI_FILE = os.path.join(UI_DIR, "taskeditor.ui")

    def __init__(self,
                 requester,
                 vmanager,
                 task,
                 thisisnew=False,
                 clipboard=None):
        '''
        req is the requester
        vmanager is the view manager
        thisisnew is True when a new task is created and opened
        '''
        self.req = requester
        self.vmanager = vmanager
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

        # Create our dictionary and connect it
        dic = {
            "on_mark_as_done": self.change_status,
            "on_dismiss": self.dismiss,
            "delete_clicked": self.delete_task,
            "on_duedate_pressed": lambda w: self.on_date_pressed(
                w, GTGCalendar.DATE_KIND_DUE),
            "on_tags_popover": self.open_tags_popover,
            "on_startdate_pressed": lambda w: self.on_date_pressed(
                w, GTGCalendar.DATE_KIND_START),
            "on_closeddate_pressed": lambda w: self.on_date_pressed(
                w, GTGCalendar.DATE_KIND_CLOSED),
            "duedate_changed": lambda w: self.date_changed(
                w, GTGCalendar.DATE_KIND_DUE),
            "duedate_focus_out": lambda w, e: self.date_focus_out(
                w, e, GTGCalendar.DATE_KIND_DUE),
            "startingdate_changed": lambda w: self.date_changed(
                w, GTGCalendar.DATE_KIND_START),
            "startdate_focus_out": lambda w, e: self.date_focus_out(
                w, e, GTGCalendar.DATE_KIND_START),
            "closeddate_changed": lambda w: self.date_changed(
                w, GTGCalendar.DATE_KIND_CLOSED),
            "closeddate_focus_out": lambda w, e: self.date_focus_out(
                w, e, GTGCalendar.DATE_KIND_CLOSED),
            "on_insert_subtask_clicked": self.insert_subtask,
            "on_inserttag_clicked": self.inserttag_clicked,
            "on_parent_select": self.on_parent_select,
            "on_move": self.on_move,
            "show_popover_start": self.show_popover_start,
            "show_popover_due": self.show_popover_due,
            "show_popover_closed": self.show_popover_closed,
            "on_tag_toggled": self.on_tag_toggled,
        }
        self.builder.connect_signals(dic)
        self.window = self.builder.get_object("TaskEditor")
        # Removing the Normal textview to replace it by our own
        # So don't try to change anything with glade, this is a home-made
        # widget
        textview = self.builder.get_object("textview")
        scrolled = self.builder.get_object("scrolledtask")
        scrolled.remove(textview)
        self.textview = TaskView(self.req, self.clipboard)
        self.textview.show()
        self.textview.set_subtask_callback(self.new_subtask)
        self.textview.open_task_callback(self.vmanager.open_task)
        self.textview.set_left_margin(7)
        self.textview.set_right_margin(5)
        scrolled.add(self.textview)
        conf_font_value = self.browser_config.get("font_name")
        if conf_font_value != "":
            self.textview.override_font(Pango.FontDescription(conf_font_value))
        # Voila! it's done
        self.calendar = GTGCalendar()
        self.calendar.set_transient_for(self.window)
        self.calendar.set_decorated(False)
        self.duedate_widget = self.builder.get_object("duedate_entry")
        self.startdate_widget = self.builder.get_object("startdate_entry")
        self.closeddate_widget = self.builder.get_object("closeddate_entry")
        '''
        TODO(jakubbrindza): Once all the functionality in editor is back and
        working, bring back also the accelerators! Dayleft_label needs to be
        brought back, however its position is unsure.
        '''
        # self.dayleft_label = self.builder.get_object("dayleft")
        # Define accelerator keys
        self.init_accelerators()

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
        self.textview.set_text("%s\n" % title)
        # we insert the rest of the task
        if texte:
            self.textview.insert("%s" % texte)
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
        '''
        TODO(jakubbrindza): make on_date_changed work alongside
        the new popover calendar
        '''
        # self.calendar.connect("date-changed", self.on_date_changed)

        # plugins
        self.pengine = PluginEngine()
        self.plugin_api = PluginAPI(self.req, self.vmanager, self)
        self.pengine.register_api(self.plugin_api)
        self.pengine.onTaskLoad(self.plugin_api)

        # Putting the refresh callback at the end make the start a lot faster
        self.textview.refresh_callback(self.refresh_editor)
        self.refresh_editor()
        self.textview.grab_focus()

        self.init_dimensions()

        self.textview.set_editable(True)
        self.window.show()

    # Define accelerator-keys for this dialog
    '''
    TODO: undo/redo
    + RE-enable all the features so that they work properly.
    + new shortcuts for bold and italic once implemented.
    '''
    def init_accelerators(self):
        agr = Gtk.AccelGroup()
        self.window.add_accel_group(agr)

        # Escape and Ctrl-W close the dialog. It's faster to call close
        # directly, rather than use the close button widget
        key, modifier = Gtk.accelerator_parse('Escape')
        agr.connect(key, modifier, Gtk.AccelFlags.VISIBLE, self.close)

        key, modifier = Gtk.accelerator_parse('<Control>w')
        agr.connect(key, modifier, Gtk.AccelFlags.VISIBLE, self.close)

        # F1 shows help
        add_help_shortcut(self.window, "editor")

        # Ctrl-N creates a new task
        key, modifier = Gtk.accelerator_parse('<Control>n')
        agr.connect(key, modifier, Gtk.AccelFlags.VISIBLE, self.new_task)

        # Ctrl-Shift-N creates a new subtask
        key, mod = Gtk.accelerator_parse("<Control><Shift>n")
        self.add_subtask.add_accelerator('clicked', agr, key, mod,
                                         Gtk.AccelFlags.VISIBLE)

        # Ctrl-D marks task as done
        key, mod = Gtk.accelerator_parse('<Control>d')
        self.donebutton.add_accelerator('clicked', agr, key, mod,
                                        Gtk.AccelFlags.VISIBLE)

        # Ctrl-I marks task as dismissed
        key, mod = Gtk.accelerator_parse('<Control>i')
        self.dismissbutton.add_accelerator('clicked', agr, key, mod,
                                           Gtk.AccelFlags.VISIBLE)

        # Ctrl-Q quits GTG
        key, modifier = Gtk.accelerator_parse('<Control>q')
        agr.connect(key, modifier, Gtk.AccelFlags.VISIBLE, self.quit)

    '''
    TODO(jakubbrindza): Add the functionality to the existing calendar widgets.
    This will require ammending and re-factoring the entire calendar.py.
    '''

    def show_popover_start(self, widget, event):
        popover = self.builder.get_object("date_popover")
        popover.set_relative_to(self.startdate_widget)
        popover.set_modal(False)
        popover.show_all()

    def show_popover_due(self, widget, popover):
        popover = self.builder.get_object("date_popover")
        popover.set_relative_to(self.duedate_widget)
        popover.set_modal(False)
        popover.show_all()

    def show_popover_closed(self, widget, popover):
        closed_popover = self.builder.get_object("closed_popover")
        closed_popover.set_relative_to(self.closeddate_widget)
        closed_popover.set_modal(False)
        closed_popover.show_all()

    def open_tags_popover(self, widget):
        self.tag_store.clear()

        tags = self.req.get_tag_tree().get_all_nodes()

        used_tags = self.task.get_tags()

        for tagname in tags:
            tag = self.req.get_tag(tagname)
            if tag_filter(tag):
                is_used = tag in used_tags
                self.tag_store.append([is_used, tagname])
                '''
                TODO(jakubbrindza): add sorting of the tags based on
                True | False and within each sub-group arrange them
                alphabetically
                '''

    def on_tag_toggled(self, widget, path):
        """We toggle by tag_row variable. tag_row is
        meant to be a tuple (is_used, tagname)"""
        tag_row = self.tag_store[path]
        tag_row[0] = not tag_row[0]

        if tag_row[0]:
            self.textview.insert_tags([tag_row[1]])
        '''
        TODO(jakubbrindza): Add else case that will remove tag.
        '''

    def init_dimensions(self):
        """ Restores position and size of task if possible """
        position = self.config.get('position')
        if position and len(position) == 2:
            try:
                self.window.move(int(position[0]), int(position[1]))
            except ValueError:
                Log.warning(
                    'Invalid position configuration for task %s: %s',
                    self.task.get_id(), position)

        size = self.config.get('size')
        if size and len(size) == 2:
            try:
                self.window.resize(int(size[0]), int(size[1]))
            except ValueError:
                Log.warning(
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
            prevdate = Date.parse(self.startdate_widget.get_text())
            update_date = startdate != prevdate
        except ValueError:
            update_date = True

        if update_date:
            self.startdate_widget.set_text(str(startdate))

        # refreshing the due date field
        duedate = self.task.get_due_date()
        try:
            prevdate = Date.parse(self.duedate_widget.get_text())
            update_date = duedate != prevdate
        except ValueError:
            update_date = True

        if update_date:
            self.duedate_widget.set_text(str(duedate))

        # refreshing the closed date field
        closeddate = self.task.get_closed_date()
        prevcldate = Date.parse(self.closeddate_widget.get_text())
        if closeddate != prevcldate:
            self.closeddate_widget.set_text(str(closeddate))

        # refreshing the day left label
        '''
        TODO(jakubbrindza): re-enable refreshing the day left.
        We need to come up how and where this information is viewed
        in the editor window.
        '''
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
            "<span color='%s'>%s</span>" % (color.to_string(), txt))

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
            elif date_kind == GTGCalendar.DATE_KIND_DUE:
                self.task.set_due_date(datetoset)
            elif date_kind == GTGCalendar.DATE_KIND_CLOSED:
                self.task.set_closed_date(datetoset)
            self.refresh_editor()

    def on_date_pressed(self, widget, date_kind):
        """Called when a date-changing button is clicked."""
        if date_kind == GTGCalendar.DATE_KIND_DUE:
            if not self.task.get_due_date():
                date = self.task.get_start_date()
            else:
                date = self.task.get_due_date()
        elif date_kind == GTGCalendar.DATE_KIND_START:
            date = self.task.get_start_date()
        elif date_kind == GTGCalendar.DATE_KIND_CLOSED:
            date = self.task.get_closed_date()
        self.calendar.set_date(date, date_kind)
        # we show the calendar at the right position
        rect = widget.get_allocation()
        result, x, y = widget.get_window().get_origin()
        self.calendar.show_at_position(x + rect.x + rect.width,
                                       y + rect.y)

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
            self.vmanager.close_task(task.get_id())

    def dismiss(self, widget):
        stat = self.task.get_status()
        if stat == Task.STA_DISMISSED:
            self.task.set_status(Task.STA_ACTIVE)
            self.refresh_editor()
        else:
            self.task.set_status(Task.STA_DISMISSED)
            self.close_all_subtasks()
            self.close(None)

    def change_status(self, widget):
        stat = self.task.get_status()
        if stat == Task.STA_DONE:
            self.task.set_status(Task.STA_ACTIVE)
            self.refresh_editor()
        else:
            self.task.set_status(Task.STA_DONE)
            self.close_all_subtasks()
            self.close(None)

    def delete_task(self, widget):
        # this triggers the closing of the window in the view manager
        if self.task.is_new():
            self.vmanager.close_task(self.task.get_id())
        else:
            self.vmanager.ask_delete_tasks([self.task.get_id()])

    # Take the title as argument and return the subtask ID
    def new_subtask(self, title=None, tid=None):
        if tid:
            self.task.add_child(tid)
        elif title:
            subt = self.task.new_subtask()
            subt.set_title(title)
            tid = subt.get_id()
        return tid

    # Create a new task
    def new_task(self, *args):
        task = self.req.new_task(newtask=True)
        task_id = task.get_id()
        self.vmanager.open_task(task_id)

    def insert_subtask(self, widget):
        self.textview.insert_newtask()
        self.textview.grab_focus()

    def inserttag_clicked(self, widget):
        itera = self.textview.get_insert()
        if itera.starts_line():
            self.textview.insert_text("@", itera)
        else:
            self.textview.insert_text(" @", itera)

    def on_parent_select(self, widget):
        parents = self.task.get_parents()

        if len(parents) == 1:
            self.vmanager.open_task(parents[0])
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
        self.vmanager.open_task(parent_id)
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
    def close(self, window=None, a=None, b=None, c=None):

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
        self.vmanager.close_task(tid)

    def get_builder(self):
        return self.builder

    def get_task(self):
        return self.task

    def get_textview(self):
        return self.textview

    def get_window(self):
        return self.window

    def quit(self, accel_group=None, acceleratable=None, keyval=None,
             modifier=None):
        """Handles the accelerator for quitting GTG."""
        self.vmanager.quit()

# -----------------------------------------------------------------------------
