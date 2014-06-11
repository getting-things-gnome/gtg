#!/usr/bin/python3
from gi.repository import Gtk, Gdk, GObject
import datetime
import random

from tasks import Task
from datastore import DataStore
from requester import Requester
from utils import random_color
from view import ViewBase
from week_view import WeekView, TwoWeeksView, MonthView
from controller import Controller

tests = True


class TaskView(Gtk.Dialog):
    """
    This class is a dialog for creating/editing a task.
    It receives a task as parameter, and has four editable entries:
    title, start and due dates, and a checkbox to mark the task as done.
    """
    def __init__(self, parent, task=None):
        Gtk.Dialog.__init__(self, "Edit Task", parent, 0,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                             Gtk.STOCK_OK, Gtk.ResponseType.OK))
        # makes the OK button be the default, and the "Enter" key activates it
        self.get_widget_for_response(Gtk.ResponseType.OK).grab_focus()

        box = self.get_content_area()
        vbox = Gtk.VBox(False, 4)
        box.add(vbox)

        box.pack_start(Gtk.Label("Title"), False, False, 0)
        self.title = Gtk.Entry()
        box.pack_start(self.title, True, True, 0)

        box.pack_start(Gtk.Label("Start Date"), False, False, 0)
        self.start_date = Gtk.Entry()
        box.pack_start(self.start_date, True, True, 0)

        box.pack_start(Gtk.Label("Due Date"), False, False, 0)
        self.due_date = Gtk.Entry()
        box.pack_start(self.due_date, True, True, 0)

        self.done = Gtk.CheckButton("Mark as done")
        box.pack_start(self.done, True, True, 0)

        if task:
            self.title.set_text(task.get_title())
            start = task.get_start_date().to_readable_string()
            self.start_date.set_text(start)
            self.due_date.set_text(task.get_due_date().to_readable_string())
            if(task.get_status() == Task.STA_DONE):
                self.done.set_active(True)
        else:
            self.set_title("New Task")
            self.done.set_sensitive(False)

        self.show_all()


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
            "on_statusbar_text_pushed": self.on_statusbar_text_pushed
        }
        builder.connect_signals(handlers)

        self.window = builder.get_object("window")
        self.window.__init__()
        self.window.set_title("GTG - Calendar View")
        self.window.connect("destroy", Gtk.main_quit)

        # Scrolled Window
        self.scroll = builder.get_object("scrolledwindow")
        self.scroll.add_events(Gdk.EventMask.SCROLL_MASK)
        self.scroll.connect("scroll-event", self.on_scroll)

        # hard coded tasks to populate calendar view
        # (title, start_date, due_date, done?, color)
        today = datetime.date.today()
        ex_tasks = [("task1", today, today, True, random_color()),
                    ("task2", today + datetime.timedelta(days=5),
                    today + datetime.timedelta(days=5), False, random_color()),
                    ("task3", today + datetime.timedelta(days=1),
                    today + datetime.timedelta(days=3), False, random_color()),
                    ("task4", today + datetime.timedelta(days=3),
                    today + datetime.timedelta(days=4), True, random_color()),
                    ("task5", today - datetime.timedelta(days=1),
                    today + datetime.timedelta(days=8), False, random_color()),
                    ("task6: very long title",
                    today + datetime.timedelta(days=2),
                    today + datetime.timedelta(days=3), False, random_color()),
                    ("task7", today + datetime.timedelta(days=5),
                    today + datetime.timedelta(days=15), False, random_color())
                    ]

        # DataStore object
        self.ds = DataStore()
        self.req = Requester(self.ds)
        self.ds.populate(ex_tasks)  # hard-coded tasks

        # FIXME: controller drawing content is not working
        # self.controller = Controller(self, self.req)
        # using weekview object instead for now:
        self.controller = WeekView(self, self.req)

        self.today_button = builder.get_object("today")
        self.header = builder.get_object("header")
        self.combobox = builder.get_object("combobox")
        self.combobox.set_active(0)

        self.statusbar = builder.get_object("statusbar")
        self.label = builder.get_object("label")

        self.scroll.add_with_viewport(self.controller)

        self.window.show_all()

    def on_scroll(self, widget, event):
        """
        Callback function to deal with scrolling the drawing area window.
        If scroll right or left, change the days displayed in the calendar
        view. If scroll up or down, propagates the signal to scroll window
        normally.
        """
        # scroll right
        if event.get_scroll_deltas()[1] > 0:
            self.on_next_clicked(widget, days=1)
        # scroll left
        elif event.get_scroll_deltas()[1] < 0:
            self.on_previous_clicked(widget, days=1)
        # scroll up or down
        else:
            return False  # propagates signal to scroll window normally
        return True

    def on_statusbar_text_pushed(self, text):
        """ Adds the @text to the statusbar """
        self.label.set_text(text)
        # self.statusbar.push(0, text)

    def on_add_clicked(self, button=None):
        """
        Adds a new task, with the help of a pop-up dialog
        for entering the task title, start and due dates.
        Redraw the calendar view after the changes.
        """
        # only to make testing easier
        if tests:
            new_task = self.req.new_task()
            today = datetime.date.today()
            start = random.choice(range(today.day, 31))
            end = random.choice(range(start, 31))
            new_task.set_start_date(str(today.year) + "-" + str(today.month) +
                                    "-" + str(start))
            new_task.set_due_date(str(today.year) + "-" + str(today.month) +
                                  "-" + str(end))
            new_task.set_color(random_color())
            dialog = TaskView(self.window, new_task)
        else:
            dialog = TaskView(self.window)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            if not tests:
                new_task = self.req.new_task()
            self.on_statusbar_text_pushed("Added task: %s" %
                                          new_task.get_title())
            new_task.set_title(dialog.title.get_text())
            new_task.set_start_date(dialog.start_date.get_text())
            new_task.set_due_date(dialog.due_date.get_text())
            color = random_color()
            new_task.set_color(color)
            self.content_update()
        else:
            if tests:
                self.req.delete_task(new_task.get_id())
            self.on_statusbar_text_pushed("...")
        dialog.hide()

    def on_edit_clicked(self, button=None):
        """
        Edits the selected task, with the help of a pop-up dialog
        for modifying the task title, start and due dates.
        Redraw the calendar view after the changes.
        """
        task = self.controller.get_selected_task()
        if task:
            dialog = TaskView(self.window, task)
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                self.on_statusbar_text_pushed("Edited task: %s" %
                                              task.get_title())
                task.set_title(dialog.title.get_text())
                task.set_start_date(dialog.start_date.get_text())
                task.set_due_date(dialog.due_date.get_text())
                if dialog.done.get_active():
                    task.set_status(Task.STA_DONE)
                else:
                    task.set_status(Task.STA_ACTIVE)
                self.content_update()
            else:
                self.on_statusbar_text_pushed("...")
            dialog.hide()

    def on_remove_clicked(self, button=None):
        """
        Removes the selected task from the datastore and redraw the
        calendar view.
        """
        task = self.controller.get_selected_task()
        if task:
            self.on_statusbar_text_pushed("Deleted task: %s" %
                                          task.get_title())
            self.req.delete_task(task.get_id())
            self.controller.unselect_task()
            self.content_update()
        else:
            self.on_statusbar_text_pushed("...")

    def on_next_clicked(self, button, days=None):
        """ Advances the dates being displayed by a given number of @days """
        self.controller.next(days)
        self.content_update()

    def on_previous_clicked(self, button, days=None):
        """ Regresses the dates being displayed by a given number of @days """
        self.controller.previous(days)
        self.content_update()

    def on_today_clicked(self, button):
        """ Show the day corresponding to today """
        self.controller.show_today()
        self.content_update()

    def on_combobox_changed(self, combo):
        """
        User chose a combobox entry: change the view_type according to it
        """
        view_type = combo.get_active_text()
        # FIXME: view switch is not working, even thought objects exist
        # try Gtk.Stack for this -> needs Gnome 3.10
        # self.controller.on_view_changed(view_type)
        print("Ignoring view change for now")
        self.content_update()

    def content_update(self):
        """ Performs all that is needed to update the content displayed """
        self.header.set_text(self.controller.get_current_year())
        self.today_button.set_sensitive(
            not self.controller.is_today_being_shown())
        self.controller.update()

CalendarPlugin()
Gtk.main()
