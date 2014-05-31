#!/usr/bin/python3
from gi.repository import Gtk, Gdk, GObject
import cairo
import datetime
from calendar import monthrange
from tasks import Task
from drawtask import DrawTask
from datastore import DataStore
from dates import Date
from requester import Requester
from utils import date_generator

class Background:
    """
    A simple background that draws a white rectangle the size of the area.
    """
    def draw(self, ctx, area):
        ctx.rectangle(area.x, area.y,
                      area.width, area.height)
        #ctx.set_source_rgb(1, 1, 1) # white
        #ctx.fill()
    
class Header:
    def __init__(self, days=None, day_width=None):
        self.days = days
        self.header_size = 40
        self.day_width = day_width

    def set_day_width(self, day_width):
        self.day_width = day_width

    def set_days(self, days):
        self.days = days
    
    def draw(self, ctx):
        """
        Draws the header of the calendar view (days and weekdays).

        @param ctx: a Cairo context
        """
        ctx.set_source_rgb(0.35, 0.31, 0.24) 
        for i in range(0, len(self.days)+1):
            ctx.move_to(i*self.day_width, 5)
            ctx.line_to(i*self.day_width, 35)
            ctx.stroke()

        for i in range(0, len(self.days)):
            (x, y, w, h, dx, dy) = ctx.text_extents(self.days[i][1])
            ctx.move_to(i*self.day_width - (w-self.day_width)/2.0, 15)
            ctx.text_path(self.days[i][1])
            ctx.stroke()

            (x, y, w, h, dx, dy) = ctx.text_extents(self.days[i][0])
            ctx.move_to(i*self.day_width - (w-self.day_width)/2.0, 30)
            ctx.text_path(self.days[i][0])
            ctx.stroke()

class Drawing(Gtk.DrawingArea):
    """
    This class creates a visualization for all the tasks in a 
    datastore, given a period of time.
    """
    FONT = "Courier"

    def __init__(self, parent, tasks):
        """
        Initializes a Drawing, given a datastore containing the
        tasks to be visualized, and a view_type to indicate the view
        to be displayed.

        @param datastore: a DataStore object, contains the tasks that
        can be visualized
        """
        self.par = parent
        super(Drawing, self).__init__()

        self.header = Header()
        self.background = Background()

        #self.ds = datastore
        #self.req = datastore.get_requester()

        #task_ids = self.req.get_tasks_tree()
        #tasks = [self.req.get_task(t) for t in task_ids]
        #self.view_start_day = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
        #self.view_end_day = datetime.date.today() + datetime.timedelta(days=14)

        self.set_tasks_to_show(tasks)

        #self.view_start_day = self.view_end_day = self.numdays = None
        #self.set_view_type(view_type)
        #self.view_start_day = start
        #self.view_end_day = end
 
        self.header_size = 40
        self.task_height = 30

        # help on the control of resizing the main window (parent)
        #FIXME: hard-coded
        #self.resize_main = True

        self.connect("draw", self.draw)

        # drag-and-drop support
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK
                        | Gdk.EventMask.BUTTON_RELEASE_MASK
                        | Gdk.EventMask.BUTTON1_MOTION_MASK
                        | Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect("button-press-event", self.dnd_start)
        self.connect("motion-notify-event", self.motion_notify)
        self.connect("button-release-event", self.dnd_stop)
        self.selected_task = None
        self.drag_offset = None
        self.drag_action = None
        self.drag = None

    def set_day_width(self, day_width):
        self.day_width = day_width

    def set_view_days(self, start, numdays):
        self.view_start_day = start
        self.numdays = numdays
        self.view_end_day = start + datetime.timedelta(days=numdays-1)

    def set_days(self, days):
        self.days = days
        self.header.set_days(days)

    def set_tasks_to_show(self, tasks):
        tasks = [DrawTask(t) for t in tasks]
        self.tasks = tasks

    def compute_size(self):#, ctx):
        """
        Compute and request right size for the drawing area.

        @param ctx: a Cairo context
        """
        sidebar = 25

        #num_tasks = len(self.req.get_tasks_tree())
        num_tasks = len(self.tasks)

        width = self.numdays * self.day_width
        height = num_tasks * self.task_height + self.header_size

        self.set_size_request(width, height)


    def identify_pointed_object(self, event, clicked=False):
        """
        Identify the object inside drawing area that is being pointed by the mouse.
        Also points out which mouse cursor should be used in result.

        @param event: a Gdk event
        @param clicked: bool, indicates whether or not the user clicked on the
        object being pointed
        """
        const = 10
        cursor = Gdk.Cursor.new(Gdk.CursorType.ARROW)
        for task in self.tasks:
          (x, y, w, h) = task.get_position()
          if not y < event.y < (y + h):
            continue
          if x <= event.x <= x + const:
            self.drag_action = "expand_left"
            cursor = Gdk.Cursor.new(Gdk.CursorType.LEFT_SIDE)
          elif (x + w) - const <= event.x <= (x + w):
            self.drag_action = "expand_right"
            cursor = Gdk.Cursor.new(Gdk.CursorType.RIGHT_SIDE)
          elif x <= event.x <= (x + w):
            self.drag_action = "move"
            if clicked:
              cursor = Gdk.Cursor.new(Gdk.CursorType.FLEUR)
          else:
            continue
          return task, cursor
        return None, cursor

    def dnd_start(self, widget, event):
        """ User clicked the mouse button, starting drag and drop """
        # find which task was clicked, if any
        (self.selected_task, cursor) = self.identify_pointed_object(event, clicked=True)

        if self.selected_task:
          # double-click
          if event.type == Gdk.EventType._2BUTTON_PRESS:
            print(event.type)
          self.drag = True
          widget.get_window().set_cursor(cursor)
          task = self.selected_task.task
          #task.set_selected(True)
          #task = self.req.get_task(self.selected_task)
          start = (task.get_start_date().date() - self.view_start_day).days
          end = (task.get_due_date().date() - self.view_start_day).days + 1
          duration = end - start

          offset = (start * self.day_width) - event.x
          #offset_y = self.header_size + pos * self.task_height - event.y
          if self.drag_action == "expand_right":
            offset += duration * self.day_width
          self.drag_offset = offset

          self.queue_draw()


    def motion_notify(self, widget, event):
        """ User moved mouse over widget """
        if self.selected_task and self.drag: # a task was clicked
          task = self.selected_task.task
          #task.set_selected(True)
          #task = self.req.get_task(self.selected_task)
          start_date = task.get_start_date().date()
          end_date = task.get_due_date().date()
          duration = (end_date - start_date).days

          offset = self.drag_offset
          event_x = event.x + offset
          event_y = event.y

          weekday = int(event_x / self.day_width)
          day = self.view_start_day + datetime.timedelta(weekday)

          if self.drag_action == "expand_left":
            diff = start_date - day
            new_start_day = start_date - diff
            if new_start_day <= end_date:
              task.set_start_date(new_start_day)
            pass

          elif self.drag_action == "expand_right":
            diff = end_date - day
            new_due_day = end_date - diff
            if new_due_day >= start_date:
              task.set_due_date(new_due_day)
            pass

          else:
            new_start_day = self.view_start_day + datetime.timedelta(days = weekday)
            new_due_day = new_start_day + datetime.timedelta(days = duration)
            task.set_start_date(new_start_day)
            task.set_due_date(new_due_day)

          self.queue_draw()

        else: # mouse hover
          (t_id, cursor) = self.identify_pointed_object(event)
          widget.get_window().set_cursor(cursor)


    def dnd_stop(self, widget, event):
        """
        User released a button, stopping drag and drop.
        Selected task, if any, will still have the focus.
        """
        # user didn't click on a task - redraw to 'unselect' task
        if not self.selected_task:
          self.drag = None
          self.queue_draw()
          return

        rect = self.get_allocation()
        if not self.header_size < event.y < rect.height:
          # do something in the future
          pass
        else:
          event_x = event.x + self.drag_offset
          event_y = event.y
          weekday = int(event_x / self.day_width)

          #task = self.req.get_task(self.selected_task)
          task = self.selected_task.task
          #task.set_selected(True)
          start = task.get_start_date().date()
          end = task.get_due_date().date()
          duration = (end - start).days

          new_start_day = self.view_start_day + datetime.timedelta(days = weekday)
          if self.drag_action == "expand_right":
            new_start_day = task.get_start_date().date()
          new_due_day = new_start_day + datetime.timedelta(days = duration)

          if not self.drag_action == "expand_right" and new_start_day <= end:
              task.set_start_date(new_start_day)
          if not self.drag_action == "expand_left" and new_due_day >= start:
              task.set_due_date(new_due_day)

        widget.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.ARROW))
        self.drag_offset = None
        self.drag = None
        #self.selected_task = None
        self.queue_draw()

    def draw(self, widget, ctx, event=None):
        """ Draws everything inside the DrawingArea """
        ctx.set_line_width(0.8)
        ctx.select_font_face(self.FONT, cairo.FONT_SLANT_NORMAL,
                             cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(12)
        if event:
          ctx.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
          ctx.clip()

        # resize drawing area
        self.compute_size()#ctx)

        self.background.draw(ctx, self.get_allocation())
        # printing header
        #self.print_header(ctx)
        self.header.set_day_width(self.day_width)
        #self.header.set_days(self.days)
        self.header.draw(ctx)

        # drawing all tasks
        #task_ids = self.req.get_tasks_tree()
        #tasks = [self.req.get_task(t) for t in task_ids]
        #for pos, task in enumerate(self.tasks):
        for pos, drawtask in enumerate(self.tasks):
            if self.selected_task \
            and self.selected_task.get_id() == drawtask.get_id():
              selected = True
            else:
              selected = False
            drawtask.set_day_width(self.day_width)
            drawtask.draw(ctx, pos, self.view_start_day, self.view_end_day, selected)
            #self.draw_task(ctx, task, pos)
