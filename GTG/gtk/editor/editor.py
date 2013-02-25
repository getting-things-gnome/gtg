# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 - Lionel Dricot & Bertrand Rousseau
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

import pango
import gtk

from GTG import _, ngettext
from GTG.gtk.editor import GnomeConfig
from GTG.gtk.editor.taskview import TaskView
from GTG.core.plugins.engine import PluginEngine
from GTG.core.plugins.api import PluginAPI
from GTG.core.task import Task
from GTG.tools.dates import Date
from GTG.gtk.editor.calendar import GTGCalendar


class TaskEditor:

    def __init__(self,
                 requester,
                 vmanager,
                 task,
                 taskconfig=None,
                 thisisnew=False,
                 clipboard=None):
        '''
        req is the requester
        vmanager is the view manager
        taskconfig is a ConfigObj dic to save infos about tasks
        thisisnew is True when a new task is created and opened
        '''
        self.req = requester
        self.browser_config = self.req.get_config('browser')
        self.vmanager = vmanager
        self.config = taskconfig
        self.time = None
        self.clipboard = clipboard
        self.builder = gtk.Builder()
        self.builder.add_from_file(GnomeConfig.GLADE_FILE)
        self.donebutton = self.builder.get_object("mark_as_done_editor")
        self.dismissbutton = self.builder.get_object("dismiss_editor")
        self.deletebutton = self.builder.get_object("delete_editor")
        self.deletebutton.set_tooltip_text(GnomeConfig.DELETE_TOOLTIP)
        self.subtask_button = self.builder.get_object("insert_subtask")
        self.subtask_button.set_tooltip_text(GnomeConfig.SUBTASK_TOOLTIP)
        self.inserttag_button = self.builder.get_object("inserttag")
        self.inserttag_button.set_tooltip_text(GnomeConfig.TAG_TOOLTIP)

        # Create our dictionary and connect it
        dic = {
            "mark_as_done_clicked": self.change_status,
            "on_dismiss": self.dismiss,
            "delete_clicked": self.delete_task,
            "on_duedate_pressed": (self.on_date_pressed,
                                   GTGCalendar.DATE_KIND_DUE),
            "on_startdate_pressed": (self.on_date_pressed,
                                     GTGCalendar.DATE_KIND_START),
            "on_closeddate_pressed": (self.on_date_pressed,
                                      GTGCalendar.DATE_KIND_CLOSED),
            "close_clicked": self.close,
            "duedate_changed": (self.date_changed,
                                GTGCalendar.DATE_KIND_DUE),
            "duedate_focus_out": (self.date_focus_out,
                                  GTGCalendar.DATE_KIND_DUE),
            "startingdate_changed": (self.date_changed,
                                     GTGCalendar.DATE_KIND_START),
            "startdate_focus_out": (self.date_focus_out,
                                    GTGCalendar.DATE_KIND_START),
            "closeddate_changed": (self.date_changed,
                                   GTGCalendar.DATE_KIND_CLOSED),
            "closeddate_focus_out": (self.date_focus_out,
                                     GTGCalendar.DATE_KIND_CLOSED),
            "on_insert_subtask_clicked": self.insert_subtask,
            "on_inserttag_clicked": self.inserttag_clicked,
            "on_move": self.on_move,
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
            self.textview.modify_font(pango.FontDescription(conf_font_value))
        # Voila! it's done
        self.calendar = GTGCalendar(self.builder)
        self.duedate_widget = self.builder.get_object("duedate_entry")
        self.startdate_widget = self.builder.get_object("startdate_entry")
        self.closeddate_widget = self.builder.get_object("closeddate_entry")
        self.dayleft_label = self.builder.get_object("dayleft")
        self.tasksidebar = self.builder.get_object("tasksidebar")
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
        self.calendar.connect("date-changed", self.on_date_changed)

        # plugins
        self.pengine = PluginEngine()
        self.plugin_api = PluginAPI(self.req, self.vmanager, self)
        self.pengine.register_api(self.plugin_api)
        self.pengine.onTaskLoad(self.plugin_api)

        # Putting the refresh callback at the end make the start a lot faster
        self.textview.refresh_callback(self.refresh_editor)
        self.refresh_editor()
        self.textview.grab_focus()

        # restoring size and position, spatial tasks
        if self.config:
            tid = self.task.get_id()
            if tid in self.config:
                if "position" in self.config[tid]:
                    pos_x, pos_y = self.config[tid]["position"]
                    self.move(int(pos_x), int(pos_y))
                if "size" in self.config[tid]:
                    width, height = self.config[tid]["size"]
                    self.window.resize(int(width), int(height))

        self.textview.set_editable(True)
        self.window.show()

    # Define accelerator-keys for this dialog
    # TODO: undo/redo
    def init_accelerators(self):
        agr = gtk.AccelGroup()
        self.window.add_accel_group(agr)

        # Escape and Ctrl-W close the dialog. It's faster to call close
        # directly, rather than use the close button widget
        key, modifier = gtk.accelerator_parse('Escape')
        agr.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.close)

        key, modifier = gtk.accelerator_parse('<Control>w')
        agr.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.close)

        # Ctrl-N creates a new task
        key, modifier = gtk.accelerator_parse('<Control>n')
        agr.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.new_task)

        # Ctrl-Shift-N creates a new subtask
        insert_subtask = self.builder.get_object("insert_subtask")
        key, mod = gtk.accelerator_parse("<Control><Shift>n")
        insert_subtask.add_accelerator('clicked', agr, key, mod,
                                       gtk.ACCEL_VISIBLE)

        # Ctrl-D marks task as done
        mark_as_done_editor = self.builder.get_object('mark_as_done_editor')
        key, mod = gtk.accelerator_parse('<Control>d')
        mark_as_done_editor.add_accelerator('clicked', agr, key, mod,
                                            gtk.ACCEL_VISIBLE)

        # Ctrl-I marks task as dismissed
        dismiss_editor = self.builder.get_object('dismiss_editor')
        key, mod = gtk.accelerator_parse('<Control>i')
        dismiss_editor.add_accelerator('clicked', agr, key, mod,
                                       gtk.ACCEL_VISIBLE)

    # Can be called at any time to reflect the status of the Task
    # Refresh should never interfere with the TaskView.
    # If a title is passed as a parameter, it will become
    # the new window title. If not, we will look for the task title.
    # Refreshtext is whether or not we should refresh the TaskView
    #(doing it all the time is dangerous if the task is empty)
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
        dismiss_tooltip = GnomeConfig.MARK_UNDISMISS_TOOLTIP
        if status == Task.STA_DISMISSED:
            self.donebutton.set_label(GnomeConfig.MARK_DONE)
            self.donebutton.set_tooltip_text(GnomeConfig.MARK_DONE_TOOLTIP)
            self.donebutton.set_icon_name("gtg-task-done")
            self.dismissbutton.set_label(GnomeConfig.MARK_UNDISMISS)
            self.dismissbutton.set_tooltip_text(dismiss_tooltip)
            self.dismissbutton.set_icon_name("gtg-task-undismiss")
        elif status == Task.STA_DONE:
            self.donebutton.set_label(GnomeConfig.MARK_UNDONE)
            self.donebutton.set_tooltip_text(GnomeConfig.MARK_UNDONE_TOOLTIP)
            self.donebutton.set_icon_name("gtg-task-undone")
            self.dismissbutton.set_label(GnomeConfig.MARK_DISMISS)
            self.dismissbutton.set_tooltip_text(dismiss_tooltip)
            self.dismissbutton.set_icon_name("gtg-task-dismiss")
        else:
            self.donebutton.set_label(GnomeConfig.MARK_DONE)
            self.donebutton.set_tooltip_text(GnomeConfig.MARK_DONE_TOOLTIP)
            self.donebutton.set_icon_name("gtg-task-done")
            self.dismissbutton.set_label(GnomeConfig.MARK_DISMISS)
            self.dismissbutton.set_tooltip_text(dismiss_tooltip)
            self.dismissbutton.set_icon_name("gtg-task-dismiss")
        self.donebutton.show()
        self.tasksidebar.show()

        # Refreshing the status bar labels and date boxes
        if status in [Task.STA_DISMISSED, Task.STA_DONE]:
            self.builder.get_object("label2").hide()
            self.builder.get_object("hbox1").hide()
            self.builder.get_object("label4").show()
            self.builder.get_object("hbox4").show()
        else:
            self.builder.get_object("label4").hide()
            self.builder.get_object("hbox4").hide()
            self.builder.get_object("label2").show()
            self.builder.get_object("hbox1").show()

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
        # If the task is marked as done, we display the delay between the
        # due date and the actual closing date. If the task isn't marked
        # as done, we display the number of days left.
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
                txt = ngettext("Due tomorrow!", "%(days)d days left", result) \
                    % {'days': result}
            elif result == 0:
                txt = _("Due today!")
            elif result < 0:
                abs_result = abs(result)
                txt = ngettext("Due yesterday!", "Was %(days)d days ago",
                               abs_result) % {'days': abs_result}
        window_style = self.window.get_style()
        color = str(window_style.text[gtk.STATE_INSENSITIVE])
        self.dayleft_label.set_markup(
            "<span color='" + color + "'>" + txt + "</span>")

        # Refreshing the tag list in the insert tag button
        taglist = self.req.get_used_tags()
        menu = gtk.Menu()
        tag_count = 0
        for tagname in taglist:
            tag_object = self.req.get_tag(tagname)
            if not tag_object.is_special() and \
                    not self.task.has_tags(tag_list=[tagname]):
                tag_count += 1
                mi = gtk.MenuItem(label=tagname, use_underline=False)
                mi.connect("activate", self.inserttag, tagname)
                mi.show()
                menu.append(mi)
        if tag_count > 0:
            self.inserttag_button.set_menu(menu)

        if refreshtext:
            self.textview.modified(refresheditor=False)
        if to_save:
            self.light_save()

    def date_changed(self, widget, data):
        try:
            Date.parse(widget.get_text())
            valid = True
        except ValueError:
            valid = False

        if valid:
            # If the date is valid, we write with default color in the widget
            # "none" will set the default color.
            widget.modify_text(gtk.STATE_NORMAL, None)
            widget.modify_base(gtk.STATE_NORMAL, None)
        else:
            # We should write in red in the entry if the date is not valid
            widget.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse("#F00"))
            widget.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#F88"))

    def date_focus_out(self, widget, event, data):
        try:
            datetoset = Date.parse(widget.get_text())
        except ValueError:
            datetoset = None

        if datetoset is not None:
            if data == "start":
                self.task.set_start_date(datetoset)
            elif data == "due":
                self.task.set_due_date(datetoset)
            elif data == "closed":
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
        x, y = widget.window.get_origin()
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
        if stat == "Dismiss":
            self.task.set_status("Active")
            self.refresh_editor()
        else:
            self.task.set_status("Dismiss")
            self.close_all_subtasks()
            self.close(None)

    def change_status(self, widget):
        stat = self.task.get_status()
        if stat == "Done":
            self.task.set_status("Active")
            self.refresh_editor()
        else:
            self.task.set_status("Done")
            self.close_all_subtasks()
            self.close(None)

    def delete_task(self, widget):
        # this triggers the closing of the window in the view manager
        if self.task.is_new():
#            self.req.delete_task(self.task.get_id())
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
        self.textview.grab_focus()

    def inserttag(self, widget, tag):
        self.textview.insert_tags([tag])
        self.textview.grab_focus()

    def save(self):
        self.task.set_title(self.textview.get_title())
        self.task.set_text(self.textview.get_text())
        self.task.sync()
        if self.config is not None:
            self.config.write()
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

    def move(self, x, y):
        try:
            xx = int(x)
            yy = int(y)
            self.window.move(xx, yy)
        except:
            pass

    def get_position(self):
        return self.window.get_position()

    def on_move(self, widget, event):
        # saving the position
        if self.config is not None:
            tid = self.task.get_id()
            if not tid in self.config:
                self.config[tid] = dict()
            self.config[tid]["position"] = self.get_position()
            self.config[tid]["size"] = self.window.get_size()

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
