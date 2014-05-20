from gi.repository import Gtk, Gdk, GObject
import cairo
import datetime
import random
from tasks import Task
from datastore import DataStore
from dates import Date
from requester import Requester

tests = True

def date_generator(start, end = None, numdays = None):
    """ 
    Generates a list of tuples (day, weekday), such that day is a string in
    the format ' %m/%d', and weekday is a string in the format '%a'.
    The list has a specific size, so that it represents the days starting
    from @start.
    The list will either end on a given @end date, or will have size @numdays.
    If the end date is specified, the @numdays parameter is ignored.
    If neither parameter is specified, the list will have size 7 (a week).

    @param start: must be a datetime object, first date to be included in the list
    @param end: must be a datetime object and greater than start, last date in the list. Default = None
    @param numdays: integer, size of the list. Only considered if @end is not given. Default = 7 days
    @return days: list of tuples, each containing a date in the format '%m/%d', and also an
    abbreviated weekday for the given date
    """
    if end: 
        assert(end > start)
        numdays = (end - start).days + 1
    elif not numdays:
        numdays = 7
    date_list = [start + datetime.timedelta(days=x) for x in range(numdays)]
    days = [(x.strftime("%m/%d"), x.strftime("%a")) for x in date_list]
    return days
    
class Calendar(Gtk.DrawingArea):
    """
    This class creates a visualization for all the tasks in a 
    datastore, given a period of time.
    """
    def __init__(self, parent, datastore): 
        """
        Initializes a Calendar, given a datastore containing the
        tasks to be visualized.

        @param datastore: a DataStore object, contains the tasks that
        can be visualized
        """
        self.par = parent
        super(Calendar, self).__init__()

        self.ds = datastore
        self.req = datastore.get_requester()

        task_ids = self.req.get_tasks_tree()
        tasks = [self.req.get_task(t) for t in task_ids]

        self.task_positions = {}
        self.moved_task = None
        self.selected_task = None

        self.view_start_day = self.view_end_day = self.numdays = None
        start_day = min([t.get_start_date().date() for t in tasks])
        #end_day = max([t.get_due_date().date() for t in tasks])
        self.set_view_days(start_day) #, end_day)

        #test:
        #self.set_view_days(self.view_start_day - datetime.timedelta(days=2), self.view_end_day + datetime.timedelta(days=1)) #test
 
        self.connect("draw", self.draw)

        # drag-and-drop support
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.BUTTON1_MOTION_MASK)
        self.connect("button-press-event", self.dnd_start)
        self.connect("motion-notify-event", self.motion_notify)
        self.connect("button-release-event", self.dnd_stop)

    def get_clicked_task_id(self, event):
        for task_id, (x, y, w, h) in self.task_positions.items():
          if x <= event.x <= (x + w) and y <= event.y <= (y + h):
            return task_id
        return None

    def dnd_start(self, widget, event):
        """ User clicked the mouse button, starting drag and drop """
        # find which task was clicked, if any
        self.selected_task = self.get_clicked_task_id(event)

        if self.selected_task:
          task = self.req.get_task(self.selected_task)
          start = (task.get_start_date().date() - self.view_start_day).days
          end = (task.get_due_date().date() - self.view_start_day).days + 1
          offset = start * self.step - event.x
          #offset_y = self.header_size + pos * self.task_height - event.y
          self.moved_task = [event.x, event.y, end-start, offset]
          self.queue_draw()

    def motion_notify(self, widget, event):
        """ User moved mouse over widget """
        if self.moved_task:
          self.moved_task[0] = event.x
          self.moved_task[1] = event.y
          self.queue_draw()

    def dnd_stop(self, widget, event):
        """ User released a button, stopping drag and drop """
        self.moved_task = None
        self.selected_task = None
        self.queue_draw()

    def set_view_days(self, start_day, end_day = None):
        """
        Set the first and the last day the calendar view will show.

        @param start_day: must be a datetime object, first day to be 
        shown in the calendar view
        @param end_day: must be a datetime object, last day to be 
        shown in the calendar view
        """
        assert(isinstance(start_day, datetime.date))
        self.view_start_day = start_day
        if end_day:
            assert(isinstance(end_day, datetime.date))
            self.view_end_day = end_day
        self.days = date_generator(start_day, end_day) #, self.numdays)
        self.numdays = len(self.days)
        if not end_day:
            self.view_end_day = self.view_start_day + datetime.timedelta(days=self.numdays)
    
    def print_header(self, ctx):
        """
        Draws the header of the calendar view (days and weekdays).

        @param ctx: a Cairo context
        """
        ctx.set_source_rgb(0.35, 0.31, 0.24) 
        for i in range(0, len(self.days)+1):
            ctx.move_to(i*self.step, 5)
            ctx.line_to(i*self.step, 35)
            ctx.stroke()

        for i in range(0, len(self.days)):
            (x, y, w, h, dx, dy) = ctx.text_extents(self.days[i][1])
            ctx.move_to(i*self.step - (w-self.step)/2.0, 15) 
            ctx.text_path(self.days[i][1])
            ctx.stroke()

            (x, y, w, h, dx, dy) = ctx.text_extents(self.days[i][0])
            ctx.move_to(i*self.step - (w-self.step)/2.0, 30) 
            ctx.text_path(self.days[i][0])
            ctx.stroke()
        
    def draw_task(self, ctx, task, pos):
        """
        Draws a given @task in a relative postion @pos.

        @param ctx: a Cairo context
        @param task: a Task object to be drawn
        @param pos: the relative order the task should appear (starting from 0)
        """
        label = task.get_title()
        start = (task.get_start_date().date() - self.view_start_day).days
        end = (task.get_due_date().date() - self.view_start_day).days + 1
        complete = task.get_status()
        duration = end - start

        if len(label) > duration * self.step/10 + 2:
            crop_at = int(duration*(self.step/10))
            label = label[:crop_at] + "..."

        if complete == Task.STA_DONE:
            alpha = 0.5
        else:
            alpha = 1

        # drawing rectangle for task duration 
        base_x = start * self.step
        base_y = self.header_size + pos * self.task_height
        width = duration * self.step
        height = self.task_height
        height -= self.padding

        ctx.save()
        ctx.rectangle(base_x, base_y, width, height)
        ctx.clip()

        # keep record of positions for discovering task when using drag and drop
        self.task_positions[task.get_id()] = (base_x, base_y, width, height)

        color = [0.5, start/6.0, end/6.0]

        # selected task in yellow
        if self.selected_task == task.get_id():
          color = [0.8, 0.8, 0]

        # solid color
        ctx.set_source_rgba(color[0], color[1], color[2], alpha)
        ctx.fill()

        # printing task label
        ctx.set_source_rgba(1, 1, 1, alpha)
        (x, y, w, h, dx, dy) = ctx.text_extents(label)
        base_x = (start+duration/2.0) * self.step - w/2.0
        base_y = self.header_size + (pos+1)*self.task_height - h/2.0
        base_y -= self.padding
        ctx.move_to(base_x, base_y)
        ctx.text_path(label)
        ctx.stroke()

        # restore old context
        ctx.restore()

    def draw(self, widget, ctx, event=None):
        ctx.set_line_width(0.8)
        ctx.select_font_face("Courier", cairo.FONT_SLANT_NORMAL, 
                             cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(11)
        if event:
          ctx.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
          ctx.clip()
        self._draw(ctx)

    def _draw_moved_event(self, ctx):
        if not self.moved_task:
          return

        event_x, event_y, event_w, offset = self.moved_task

        # don't draw on header
        rect = self.get_allocation()
        #if event_y < self.header_size:
        if not self.header_size < event_y < rect.height:
          return

        event_x += offset

        num_tasks = len(self.req.get_tasks_tree())
        x = int(event_x / self.step) * self.step
        y = self.header_size + int( (event_y - self.header_size)/ self.task_height) * self.task_height
        h = self.task_height
        w = event_w * self.step
        h -= self.padding

        ctx.set_source_rgba(0, 0, 0, 1)
        ctx.rectangle(x, y, w, h)
        ctx.fill()


    def _draw(self, ctx):
        alloc = self.get_allocation()
        self.step = round(alloc.width / float(self.numdays))
        self.header_size = 40
        self.task_height = 25
        self.padding = 5
        self.footer = 10

        task_ids = self.req.get_tasks_tree()
        tasks = [self.req.get_task(t) for t in task_ids]

        # resizes vertical area according to number of tasks
        self.set_size_request(350, len(tasks) * self.task_height + self.header_size + self.footer)

        # printing header
        self.print_header(ctx)

        # drawing all tasks
        for pos, task in enumerate(tasks):
            self.draw_task(ctx, task, pos)

        self._draw_moved_event(ctx)
        
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

    def __init__(self):
        super(CalendarPlugin, self).__init__()

        builder = Gtk.Builder()
        builder.add_from_file("calendar_view.glade")
        handlers = {
            "on_window_destroy": Gtk.main_quit,
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
        self.window.set_title("Gantt Chart View")
        self.window.connect("destroy", Gtk.main_quit)

        self.statusbar = builder.get_object("statusbar")

        # Scrolled Window
        self.scroll = builder.get_object("scrolledwindow")

        # hard coded tasks to populate calendar view
        # (title, start_date, due_date, done?)
        ex_tasks = [("task1", "2014-03-17", "2014-03-17", True), 
                    ("task2", "2014-03-22", "2014-03-22", False), 
                    ("task3", "2014-03-18", "2014-03-20", False),
                    ("task4", "2014-03-20", "2014-03-21", True),
                    ("task5", "2014-03-17", "2014-03-23", False),
                    ("task6: very very long task", "2014-03-19", "2014-03-20", False),
                    ("task7", "2014-03-22", "2014-03-24", False)
                   ]

        # DataStore object
        self.ds = DataStore()
        self.req = Requester(self.ds)
        self.ds.populate(ex_tasks) #hard-coded tasks

        # Pack the Calendar object inside the scrolled window
        self.calendar = Calendar(self, self.ds) 
        self.scroll.add_with_viewport(self.calendar)

        self.label = builder.get_object("label")
        self.window.show_all()


    def on_statusbar_text_pushed(self, text):
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
            start = random.choice(range(1,30))
            end = random.choice([start,30])
            new_task.set_start_date("2014-03-"+str(start))
            new_task.set_due_date("2014-03-"+str(end))
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
            self.calendar.queue_draw()
        else:
            if tests:
                self.req.delete_task(new_task.get_id()) 
            self.on_statusbar_text_pushed("...")
        dialog.hide()

    def on_edit_clicked(self, button):
        """ 
        Edits a random task, with the help of a pop-up dialog
        for modifying the task title, start and due dates.
        Redraw the calendar view after the changes.
        """
        task_id = self.req.get_random_task()
        if task_id:
            task = self.req.get_task(task_id)

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
                self.calendar.queue_draw()
            else:
                self.on_statusbar_text_pushed("...")
            dialog.hide()

    def on_remove_clicked(self, button):
        """ 
        Removes a random task from the datastore and redraw the 
        calendar view.
        """
        task_id = self.req.get_random_task()
        if task_id:
            self.on_statusbar_text_pushed("Deleted task: %s" % self.req.get_task(task_id).get_title())
            self.req.delete_task(task_id)
            self.calendar.queue_draw()
        else:
            self.on_statusbar_text_pushed("...")

    def on_next_clicked(self, button):
        self.calendar.set_view_days(self.calendar.view_start_day + datetime.timedelta(days=7))
        self.calendar.queue_draw()

    def on_previous_clicked(self, button):
        self.calendar.set_view_days(self.calendar.view_start_day - datetime.timedelta(days=7))
        self.calendar.queue_draw()

CalendarPlugin()
Gtk.main()
