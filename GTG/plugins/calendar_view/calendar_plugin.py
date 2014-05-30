#!/usr/bin/python3
from gi.repository import Gtk, Gdk, GObject
import cairo
import datetime
from calendar import monthrange
import random
from tasks import Task
from datastore import DataStore
from dates import Date
from requester import Requester

from utils import random_color, date_generator
from drawing import Drawing

tests = True
        
class TaskView(Gtk.Dialog):
    """
    This class is a dialog for creating/editing a task.
    It receives a task as parameter, and has four editable entries:
    title, start and due dates, and a checkbox to mark the task as done.
    """
    def __init__(self, parent, task = None):
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
            self.start_date.set_text(task.get_start_date().to_readable_string())
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
    def __init__(self, view_type="2weeks"):
        super(CalendarPlugin, self).__init__()

        builder = Gtk.Builder()
        builder.add_from_file("calendar_view.glade")
        handlers = {
            "on_window_destroy": Gtk.main_quit,
            "on_today_clicked": self.on_today_clicked,
            "on_week_clicked": self.on_week_clicked,
            "on_2weeks_clicked": self.on_2weeks_clicked,
            "on_month_clicked": self.on_month_clicked,
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
                    ("task2", today + datetime.timedelta(days=5), today + datetime.timedelta(days=5), False, random_color()),
                    ("task3", today + datetime.timedelta(days=1), today + datetime.timedelta(days=3), False, random_color()),
                    ("task4", today + datetime.timedelta(days=3), today + datetime.timedelta(days=4), True, random_color()),
                    ("task5", today - datetime.timedelta(days=1), today + datetime.timedelta(days=8), False, random_color()),
                    ("task6: very long title", today + datetime.timedelta(days=2), today + datetime.timedelta(days=3), False, random_color()),
                    ("task7", today + datetime.timedelta(days=5), today + datetime.timedelta(days=15), False, random_color())
                   ]

        # DataStore object
        self.ds = DataStore()
        self.req = Requester(self.ds)
        self.ds.populate(ex_tasks) #hard-coded tasks

        # Pack the Drawing object inside the scrolled window
        tasks = [self.req.get_task(t) for t in self.req.get_tasks_tree()]
        self.drawing = Drawing(self, tasks)
        #self.drawing.set_view_days(self.view_start_day, self.view_end_day)
        #self.drawing = Drawing(self, self.ds, view_type)

        self.view_start_day = self.view_end_day = self.numdays = None
        self.set_view_type(view_type)

        self.scroll.add_with_viewport(self.drawing)

        self.header = builder.get_object("header")
        self.header.set_text(self.get_current_year())

        self.statusbar = builder.get_object("statusbar")
        self.label = builder.get_object("label")

        self.window.show_all()

    def get_current_year(self):
        """ Gets the correspondent year of the days being displayed in the calendar view """
        if self.view_start_day.year != self.view_end_day.year:
          return ("%s / %s" % (self.view_start_day.year, self.view_end_day.year))
        return str(self.view_start_day.year)

    def set_numdays(self, numdays):
        """ Sets the number of days to be displayed in the calendar view """
        self.numdays = numdays

    def update_tasks_to_show(self):
        tasks = [self.req.get_task(t) for t in self.req.get_tasks_tree()]
        tasks = [t for t in tasks if self.is_in_this_view_range(t)]
        self.drawing.set_tasks_to_show(tasks)

    def set_view_days(self, start_day, numdays=None):
        """
        Sets the first and the last day the calendar view will show.

        @param start_day: must be a datetime object, first day to be 
        shown in the calendar view
        @param numdays: integer, number of days to be shown. If none is given,
        the default self.numdays will be used.
        """
        if not numdays:
          numdays = self.numdays
        assert(isinstance(start_day, datetime.date))
        self.view_start_day = start_day
        self.days = date_generator(start_day, numdays)
        self.view_end_day = start_day + datetime.timedelta(days=self.numdays-1)

        self.update_tasks_to_show()

        self.drawing.set_days(self.days)
        self.drawing.set_view_days(self.view_start_day, self.numdays)

    def is_in_this_view_range(self, task):
        """
        Returns true if the given @task should be drawn in the current view
        (i.e. either the start or due days are between the start and end day views)

        @ param task: a Task object
        """
        return (task.get_due_date().date() >= self.view_start_day) \
           and (task.get_start_date().date() <= self.view_end_day)

    def set_view_type(self, view_type):
        """
        Set what kind of view will be displayed. This will determine the number of
        days to show, as well as the minimum width of each day to be drawn.

        @param view_type: string, indicates the view to be displayed.
        It can be either "week", "2weeks" or "month"
        """
        self.view_type = view_type
        if not self.view_start_day:
          start_day = datetime.date.today()
        else:
          start_day = self.view_start_day

        if view_type == "week":
          start_day -= datetime.timedelta(days=start_day.weekday())
          self.set_numdays(7)
          self.min_day_width = 60
        elif view_type == "2weeks":
          start_day -= datetime.timedelta(days=start_day.weekday())
          self.set_numdays(14)
          self.min_day_width = 50
        elif view_type == "month":
          self.set_numdays(monthrange(start_day.year, start_day.month)[1])
          start_day -= datetime.timedelta(days=start_day.day-1)
          self.min_day_width = 40
        else: # error check
          exit(-1)
        self.resize_main = True #FIXME: allow resize back
        self.set_view_days(start_day, self.numdays)

        rect = self.window.get_allocation()
        sidebar = 25
        rect.width -= sidebar
        self.day_width = self.min_day_width
        if self.min_day_width * self.numdays < rect.width:
          self.day_width = rect.width / float(self.numdays)
        self.drawing.set_day_width(self.day_width)

    def on_scroll(self, widget, event):
        """
        Callback function to deal with scrolling the drawing area window.
        If scroll right or left, change the days displayed in the calendar view.
        If scroll up or down, propagates the signal to scroll window normally.
        """
        # scroll right
        if event.get_scroll_deltas()[1] > 0:
          self.on_next_clicked(widget, days=1)
        # scroll left
        elif event.get_scroll_deltas()[1] < 0:
          self.on_previous_clicked(widget, days=1)
        # scroll up or down
        else:
          return False # propagates signal to scroll window normally
        return True

    def on_statusbar_text_pushed(self, text):
        """ Adds the @text to the statusbar """
        self.label.set_text(text)
        #self.statusbar.push(0, text)

    def on_add_clicked(self, button):
        """ 
        Adds a new task, with the help of a pop-up dialog
        for entering the task title, start and due dates.
        Redraw the calendar view after the changes.
        """
        # only to make testing easier
        if tests: 
            new_task = self.req.new_task() 
            today = datetime.date.today()
            start = random.choice(range(today.day,30))
            end = random.choice([start,30])
            new_task.set_start_date(str(today.year)+"-"+str(today.month)+"-"+str(start))
            new_task.set_due_date(str(today.year)+"-"+str(today.month)+"-"+str(end))
            new_task.set_color(random_color())
            dialog = TaskView(self.window, new_task)
        else: 
            dialog = TaskView(self.window)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            if not tests:
                new_task = self.req.new_task() 
            self.on_statusbar_text_pushed("Added task: %s" % new_task.get_title())
            new_task.set_title(dialog.title.get_text())
            new_task.set_start_date(dialog.start_date.get_text())
            new_task.set_due_date(dialog.due_date.get_text())
            color = random_color()
            new_task.set_color(color)
            self.update_tasks_to_show()
            self.drawing.queue_draw()
        else:
            if tests:
                self.req.delete_task(new_task.get_id()) 
            self.on_statusbar_text_pushed("...")
        dialog.hide()

    def on_edit_clicked(self, button):
        """ 
        Edits the selected task, with the help of a pop-up dialog
        for modifying the task title, start and due dates.
        Redraw the calendar view after the changes.
        """
        task = self.drawing.selected_task.task
        if task:
            #task = self.req.get_task(task_id)

            dialog = TaskView(self.window, task)
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                self.on_statusbar_text_pushed("Edited task: %s" % task.get_title())
                task.set_title(dialog.title.get_text())
                task.set_start_date(dialog.start_date.get_text())
                task.set_due_date(dialog.due_date.get_text())
                if dialog.done.get_active():
                    task.set_status(Task.STA_DONE)
                else:
                    task.set_status(Task.STA_ACTIVE)
                self.drawing.queue_draw()
            else:
                self.on_statusbar_text_pushed("...")
            dialog.hide()

    def on_remove_clicked(self, button):
        """ 
        Removes the selected task from the datastore and redraw the
        calendar view.
        """
        task = self.drawing.selected_task.task
        if task:
            self.on_statusbar_text_pushed("Deleted task: %s" % task.get_title())
            self.req.delete_task(task.get_id())
            self.drawing.selected_task = None
            self.update_tasks_to_show()
            self.drawing.queue_draw()
        else:
            self.on_statusbar_text_pushed("...")

    def on_next_clicked(self, button, days=None):
        """ Advances the dates being displayed by a given number of @days """
        start = self.view_start_day
        if not days:
          days = self.numdays

          # if the current first view day is not Monday, advances to the
          # beginning of next week instead of advancing @numdays
          # FIXME: do the same for month view
          if start.weekday() != 0:
            days = self.numdays - start.weekday()
        self.set_view_days(start + datetime.timedelta(days=days))
        self.header.set_text(self.get_current_year())
        self.drawing.queue_draw()

    def on_previous_clicked(self, button, days=None):
        """ Regresses the dates being displayed by a given number of @days """
        start = self.view_start_day
        if not days:
          days = self.numdays
          # if the current first view day is not Monday, goes back to the
          # beginning of the current week one instead of regressing @numdays
          # FIXME: do the same for month view
          if start.weekday() != 0:
            days = start.weekday()

        #tasks = [self.req.get_task(t) for t in self.req.get_tasks_tree()]
        #tasks = [t for t in tasks if self.is_in_this_view_range(t)]
        #self.drawing.set_tasks_to_show(tasks)
        self.set_view_days(start - datetime.timedelta(days=days))
        self.header.set_text(self.get_current_year())
        self.drawing.queue_draw()

    def on_today_clicked(self, button):
        #button.set_sensitive(False)
        start_day = datetime.date.today()
        if self.view_type == "month":
          start_day -= datetime.timedelta(days=start_day.day-1)
        else:
          start_day -= datetime.timedelta(days=start_day.weekday())
        self.set_view_days(start_day)
        self.drawing.queue_draw()

    def on_week_clicked(self, button):
        self.set_view_type("week")
        self.header.set_text(self.get_current_year())
        self.drawing.queue_draw()

    def on_2weeks_clicked(self, button):
        self.set_view_type("2weeks")
        self.header.set_text(self.get_current_year())
        self.drawing.queue_draw()

    def on_month_clicked(self, button):
        self.set_view_type("month")
        self.header.set_text(self.get_current_year())
        self.drawing.queue_draw()

CalendarPlugin()
Gtk.main()
