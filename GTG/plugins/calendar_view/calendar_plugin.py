#!/usr/bin/python3
from gi.repository import Gtk, GObject
import datetime
import random

from datastore import DataStore
from requester import Requester
from utils import random_color
from controller import Controller
from taskview import TaskView

tests = True


class CalendarPlugin(GObject.GObject):
    """
    This class is a plugin to display tasks into a dedicated view, where tasks
    can be selected, edited, moved around by dragging and dropping, etc.
    """
    def __init__(self):
        super(CalendarPlugin, self).__init__()
        self.first_day = self.last_day = self.numdays = None

        builder = Gtk.Builder()
        builder.add_from_file("calendar_view.glade")
        handlers = {
            "on_window_destroy": Gtk.main_quit,
            "on_today_clicked": self.on_today_clicked,
            "on_combobox_changed": self.on_combobox_changed,
            "on_add_clicked": self.on_add_clicked,
            "on_edit_clicked": self.on_edit_clicked,
            "on_remove_clicked": self.on_remove_clicked,
            "on_next_clicked": self.on_next_clicked,
            "on_previous_clicked": self.on_previous_clicked,
        }
        builder.connect_signals(handlers)

        self.window = builder.get_object("window")
        self.window.__init__()
        self.window.set_title("GTG - Calendar View")
        self.window.connect("destroy", Gtk.main_quit)

        # DataStore object
        self.ds = DataStore()
        self.req = Requester(self.ds)
        self.ds.populate()  # hard-coded tasks

        self.today_button = builder.get_object("today")
        self.header = builder.get_object("header")

        self.controller = Controller(self, self.req)
        vbox = builder.get_object("vbox")
        vbox.add(self.controller)
        vbox.reorder_child(self.controller, 1)

        self.combobox = builder.get_object("combobox")
        self.combobox.set_active(0)

        self.statusbar = builder.get_object("statusbar")

        self.window.show_all()

    def on_add_clicked(self, button=None, start_date=None, due_date=None):
        """
        Adds a new task, with the help of a pop-up dialog
        for entering the task title, start and due dates.
        Redraw the calendar view after the changes.
        """
        # only to make testing easier
        if tests and not start_date and not due_date:
            today = datetime.date.today()
            start = random.choice(range(today.day, 31))
            end = random.choice(range(start, 31))
            start_date = str(today.year) + "-" + str(today.month) + "-" + str(start)
            due_date = str(today.year) + "-" + str(today.month) + "-" + str(end)
        ####
        dialog = TaskView(self.window, new=True)
        dialog.set_task_title("My New Task")
        if start_date:
            dialog.set_start_date(start_date)
        if due_date:
            dialog.set_due_date(due_date)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            title = dialog.get_title()
            start_date = dialog.get_start_date()
            due_date = dialog.get_due_date()
            color = random_color()
            self.controller.add_new_task(title, start_date, due_date, color)
            self.statusbar.push(0, "Added task: %s" % title)
        else:
            self.statusbar.pop(0)
        dialog.hide()

    def on_edit_clicked(self, button=None, task_id=None):
        """
        Edits the selected task, with the help of a pop-up dialog
        for modifying the task title, start and due dates.
        Redraw the calendar view after the changes.
        """
        if not task_id:
            task_id = self.controller.get_selected_task()
        task = self.req.get_task(task_id)
        if task:
            dialog = TaskView(self.window, task)
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                title = dialog.get_title()
                start_date = dialog.get_start_date()
                due_date = dialog.get_due_date()
                is_done = dialog.get_active()
                self.controller.edit_task(task.get_id(), title,
                                          start_date, due_date, is_done)
                self.statusbar.push(0, "Edited task: %s" % title)
            else:
                self.statusbar.pop(0)
            dialog.hide()

    def on_remove_clicked(self, button=None):
        """
        Removes the selected task from the datastore and redraw the
        calendar view.
        """
        task = self.req.get_task(self.controller.get_selected_task())
        if task:
            self.controller.delete_task(task.get_id())
            self.statusbar.push(0, "Deleted task: %s" % task.get_title())
        else:
            self.statusbar.pop(0)

    def on_next_clicked(self, button, days=None):
        """ Advances the dates being displayed by a given number of @days """
        self.controller.next(days)
        self.content_update()
        self.controller.update()

    def on_previous_clicked(self, button, days=None):
        """ Regresses the dates being displayed by a given number of @days """
        self.controller.previous(days)
        self.content_update()
        self.controller.update()

    def on_today_clicked(self, button):
        """ Show the day corresponding to today """
        self.controller.show_today()
        self.content_update()

    def on_combobox_changed(self, combo):
        """
        User chose a combobox entry: change the view_type according to it
        """
        view_type = combo.get_active_text()
        self.controller.on_view_changed(view_type)
        # connect new view signals
        # FIXME: it seems that signals are being emitted multiple times
        # when change views back and forth and try to edit a task, multiple
        # TaskView editors appear
        self.controller.get_visible_view().connect("on_edit_task",
                                                   self.on_edit_clicked)
        self.controller.get_visible_view().connect("on_add_task",
                                                   self.on_add_clicked)
        self.controller.get_visible_view().connect("dates-changed",
                                                   self.on_dates_changed)
        self.content_update()

    def on_dates_changed(self, widget=None):
        """ Callback to update date-related objects in main window """
        self.header.set_text(self.controller.get_current_year())
        self.today_button.set_sensitive(
            not self.controller.is_today_being_shown())

    def content_update(self):
        """ Performs all that is needed to update the content displayed """
        self.on_dates_changed()
        self.controller.update()

CalendarPlugin()
Gtk.main()
