#!/usr/bin/python3
from gi.repository import Gtk, Gdk, GObject
import cairo
import datetime
from calendar import monthrange
from tasks import Task
from datastore import DataStore
from dates import Date
from requester import Requester
from utils import date_generator

HEADER_SIZE = 40

from drawtask import DrawTask, TASK_HEIGHT

def convert_coordinates_to_grid(pos_x, pos_y, width, height, header_x=0.0, header_y=0.0):
  grid_x = (pos_x - header_x) / width
  grid_y = (pos_y - header_y) / height
  return int(grid_x), int(grid_y)

class Background:
    """
    A class to draw everything regarding the background, such as
    the color, the grid, highlighted portion, etc.
    """
    def __init__(self):
        self.draw_grid = True
        self.column_width = None

    def set_column_width(self, column_width):
        self.column_width = column_width

    def draw(self, ctx, area, highlight_col=None):
        #ctx.rectangle(area.x, area.y, area.width, area.height)
        #ctx.set_source_rgb(1, 1, 1) # white
        #ctx.fill()

        # column to be highlighted has a different color
        if highlight_col is not None:
          ctx.set_source_rgba(1, 1, 1, 0.5) # white
          ctx.rectangle(self.column_width*highlight_col, area.y, self.column_width, area.height)
          ctx.fill()

        if self.draw_grid:

          ctx.set_source_rgb(0.35, 0.31, 0.24)
          ctx.move_to(0, HEADER_SIZE)
          ctx.line_to(area.width, HEADER_SIZE)
          ctx.stroke()

          ctx.move_to(0, 0)
          ctx.line_to(area.width, 0)
          ctx.stroke()

          ctx.set_source_rgba(0.35, 0.31, 0.24, 0.15)
          for i in range(0, int(area.width/self.column_width)):
              ctx.move_to(i*self.column_width, HEADER_SIZE)
              ctx.line_to(i*self.column_width, area.width)
              ctx.stroke()
    
class Header:
    def __init__(self, days=None, day_width=None):
        self.days = days
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
        ctx.set_source_rgba(0.35, 0.31, 0.24)
        for i in range(0, len(self.days)+1):
            ctx.move_to(i*self.day_width, 0)
            ctx.line_to(i*self.day_width, HEADER_SIZE)
            ctx.stroke()

        ctx.set_source_rgb(0.35, 0.31, 0.24)
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
        Initializes a Drawing, given the tasks to be visualized.
        @param tasks: a Task list, contains the tasks that
        will be drawn
        """
        self.par = parent
        super(Drawing, self).__init__()

        self.header = Header()
        self.background = Background()

        self.today_column = None
        self.day_width = None
        self.first_day = None
        self.numdays = None
        self.last_day = None
        self.tasks = None

        self.set_tasks_to_show(tasks)

        self.connect("draw", self.draw)
        self.connect("size-allocate", self.on_size_allocate)

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

    def set_view_type(self, view_type):
        if view_type == "Week":
          self.min_day_width = 60
        elif view_type == "2 Weeks":
          self.min_day_width = 50
        elif view_type == "Month":
          self.min_day_width = 40
        width = self.min_day_width*self.numdays
        height = TASK_HEIGHT*len(self.tasks)+HEADER_SIZE
        self.set_size_request(width, height)

    def set_day_width(self, day_width):
        self.day_width = day_width

    def set_view_days(self, start, numdays):
        self.first_day = start
        self.numdays = numdays
        self.last_day = start + datetime.timedelta(days=numdays-1)
        self.today_column = (datetime.date.today() - self.first_day).days


    def set_days(self, days):
        self.days = days
        self.header.set_days(days)

    def set_tasks_to_show(self, tasks):
        tasks = [DrawTask(t) for t in tasks]
        self.tasks = tasks

    def on_size_allocate(self, widget=None, event=None):
        """
        Calculates new day_width and area for drawingarea
        when window is resized
        """
        rect = self.get_allocation()
        self.day_width = self.min_day_width
        if self.min_day_width * self.numdays < rect.width:
          self.day_width = rect.width / float(self.numdays)

        num_tasks = len(self.tasks)
        width = self.numdays * self.day_width
        height = num_tasks * TASK_HEIGHT + HEADER_SIZE

        self.set_day_width(self.day_width)
        #return(rect.x, rect.y, width, height)


    def identify_pointed_object(self, event, clicked=False):
        """
        Identify the object inside drawing area that is being pointed by the mouse.
        Also points out which mouse cursor should be used in result.

        @param event: a Gdk event
        @param clicked: bool, indicates whether or not the user clicked on the
        object being pointed
        """
        #print(event.x, event.y, convert_coordinates_to_grid(event.x, event.y, self.day_width, TASK_HEIGHT, header_y=HEADER_SIZE))
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
            pass # open task to edit in future
          self.drag = True
          widget.get_window().set_cursor(cursor)
          task = self.selected_task.task
          start = (task.get_start_date().date() - self.first_day).days
          end = (task.get_due_date().date() - self.first_day).days + 1
          duration = end - start

          offset = (start * self.day_width) - event.x
          #offset_y = HEADER_SIZE + pos * TASK_HEIGHT - event.y
          if self.drag_action == "expand_right":
            offset += duration * self.day_width
          self.drag_offset = offset

          self.queue_draw()


    def motion_notify(self, widget, event):
        """ User moved mouse over widget """
        if self.selected_task and self.drag: # a task was clicked
          task = self.selected_task.task
          start_date = task.get_start_date().date()
          end_date = task.get_due_date().date()
          duration = (end_date - start_date).days

          offset = self.drag_offset
          event_x = event.x + offset
          event_y = event.y

          weekday = int(event_x / self.day_width)
          day = self.first_day + datetime.timedelta(weekday)

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
            new_start_day = self.first_day + datetime.timedelta(days = weekday)
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
        if not HEADER_SIZE < event.y < rect.height:
          # do something in the future
          pass
        else:
          event_x = event.x + self.drag_offset
          event_y = event.y
          weekday = int(event_x / self.day_width)

          task = self.selected_task.task
          start = task.get_start_date().date()
          end = task.get_due_date().date()
          duration = (end - start).days

          new_start_day = self.first_day + datetime.timedelta(days = weekday)
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

    def draw(self, widget, ctx):
        """ Draws everything inside the DrawingArea """
        ctx.set_line_width(0.8)
        ctx.select_font_face(self.FONT, cairo.FONT_SLANT_NORMAL,
                             cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(12)

        self.background.set_column_width(self.day_width)
        self.background.draw(ctx, self.get_allocation(), highlight_col=self.today_column)

        # printing header
        self.header.set_day_width(self.day_width)
        self.header.draw(ctx)

        # drawing all tasks
        for pos, drawtask in enumerate(self.tasks):
            if self.selected_task \
            and self.selected_task.get_id() == drawtask.get_id():
              selected = True
            else:
              selected = False
            drawtask.set_day_width(self.day_width)
            drawtask.draw(ctx, pos, self.first_day, self.last_day, selected)
