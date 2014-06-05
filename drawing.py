#!/usr/bin/python3
from gi.repository import Gtk, Gdk
import cairo
import datetime
from calendar import monthrange

HEADER_SIZE = 40

from drawtask import DrawTask, TASK_HEIGHT
from utils import date_generator


def convert_coordinates_to_grid(pos_x, pos_y, width, height,
                                header_x=0.0, header_y=0.0):
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
        # ctx.rectangle(area.x, area.y, area.width, area.height)
        # ctx.set_source_rgb(1, 1, 1) # white
        # ctx.fill()

        # column to be highlighted has a different color
        if highlight_col is not None:
            ctx.set_source_rgba(1, 1, 1, 0.5)  # white
            ctx.rectangle(self.column_width*highlight_col,
                          area.y, self.column_width, area.height)
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

    def __init__(self, parent, requester, view_type="Week"):
        """
        Initializes a Drawing, given a @requester containing the tasks to be
        visualized, and a @view_type to indicate the kind of view to be
        displayed. If no view_type is given, the default "Week" will be used.

        @param parent:
        @param requester: a Requester object, from
         where the tasks that will be drawn will be gotten
        @param view_type: string, indicates the view to be displayed.
         It can be either "Week", "2 Weeks" or "Month". Default = "Week".
        """
        super(Drawing, self).__init__()

        self.par = parent
        self.req = requester

        self.header = Header()
        self.background = Background()

        tasks = [DrawTask(self.req.get_task(t)) for
                 t in self.req.get_tasks_tree()]
        self.tasks = tasks

        self.view_type = None
        self.first_day = None
        self.last_day = None
        self.numdays = None
        self.day_width = None
        self.today_column = None

        self.set_view_type(view_type)

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

    def get_selected_task(self):
        """ Returns which task is being selected. """
        if self.selected_task:
            return self.selected_task.task

    def unselect_task(self):
        """ Unselects the task that was selected before. """
        self.self_task = None

    def set_day_width(self, day_width):
        """ Sets the width of the column that each day will be drawn. """
        self.day_width = day_width

    def set_view_type(self, view_type):
        """
        Set what kind of view that will be displayed.
        This will determine the number of days to show.

        @param view_type: string, indicates the view to be displayed.
         It can be either "Week", "2 Weeks" or "Month"
        """
        self.view_type = view_type
        if not self.first_day:
            start_day = datetime.date.today()
        else:
            start_day = self.first_day

        if view_type == "Week":
            start_day -= datetime.timedelta(days=start_day.weekday())
            self.numdays = 7
            self.min_day_width = 60
        elif view_type == "2 Weeks":
            start_day -= datetime.timedelta(days=start_day.weekday())
            self.numdays = 14
            self.min_day_width = 50
        elif view_type == "Month":
            self.numdays = 31
            start_day -= datetime.timedelta(days=start_day.day-1)
            self.min_day_width = 40
        else:  # error check
            exit(-1)
        self.set_days_range(start_day, self.numdays)
        self.compute_size()

    def set_days_range(self, start, numdays=None):
        """
        Sets the range of days to be shown, starting from @start and with
        size @numdays. If numdays is not given, the default self.numdays will
        be used.

        @param start: must be a datetime object, first day to be shown.
        @param numdays: integer, total number of days to be shown.
         If none is given, the default self.numdays will be used.
        """
        if not numdays:
            numdays = self.numdays
        self.first_day = start
        self.numdays = numdays
        self.last_day = start + datetime.timedelta(days=numdays-1)
        self.update_days()
        self.today_column = (datetime.date.today() - self.first_day).days

    def update_days(self, days=None):
        """
        Update the days to be drawn.

        @param days: list of tuples in the same format returned
         by utils.date_generator(). Each tuple contains a date in the
         format '%m/%d' and also an abbreviated weekday for the given date.
         If none is given, @days will be generated by utils.date_generator()
         having self.first_day and self.numdays as parameters.
        """
        if not days:
            days = date_generator(self.first_day, self.numdays)
        self.days = days
        self.header.set_days(days)

    def update_tasks(self, tasks=None):
        """
        Updates the tasks to be drawn

        @param tasks: a Task list, containing the tasks to be drawn.
         If none is given, the tasks will be retrieved from the requester.
        """
        if not tasks:
            tasks = [self.req.get_task(t) for t in self.req.get_tasks_tree()]
        self.tasks = [DrawTask(t) for t in tasks if self.is_in_days_range(t)]

    def update(self):
        """
        Updates the content to be drawn (tasks), recalculates the size needed
        and then redraws everything.
        """
        self.update_tasks()
        self.compute_size()
        self.queue_draw()

    def is_in_days_range(self, task):
        """
        Returns true if the given @task have either the start or due days
        between the current first and last day being displayed.
        Useful to know if @task should be drawn in the current screen.

        @ param task: a Task object
        """
        return (task.get_due_date().date() >= self.first_day) and \
               (task.get_start_date().date() <= self.last_day)

    def get_current_year(self):
        """
        Gets the correspondent year of the days
        being displayed in the calendar view
        """
        if self.first_day.year != self.last_day.year:
            return ("%s / %s" % (self.first_day.year, self.last_day.year))
        return str(self.first_day.year)

    def show_today(self):
        """
        Shows the range of dates in the current view with the date
        corresponding to today among it.
        """
        start_day = datetime.date.today()
        if self.view_type == "Month":
            start_day -= datetime.timedelta(days=start_day.day-1)
        else:
            start_day -= datetime.timedelta(days=start_day.weekday())
        self.set_days_range(start_day)
        self.update()

    def is_today_being_shown(self):
        """
        Returns true if the date for today is being
        shown in the current view
        """
        today = datetime.date.today()
        return today >= self.first_day and today <= self.last_day

    def next(self, days=None):
        """
        Advances the dates being displayed by a given number of @days.
        If none is given, the default self.numdays will be used. In this case,
        if the actual first_day being shown is not at the beginning of a
        week/month, it will advance to the beginning of the next one instead
        of advancing @numdays.

        @param days: integer, the number of days to advance.
         If none is given, the default self.numdays will be used.
        """
        start = self.first_day

        if not days:
            days = self.numdays

            if self.view_type == "Month":
                if start.day != 1:
                    # FIXME: months should have different numdays
                    numdays = monthrange(self.first_day.year,
                                         self.first_day.month)[1]
                    days = numdays - start.day + 1
            else:  # weeks
                if start.weekday() != 0:
                    days = self.numdays - start.weekday()

        self.set_days_range(start + datetime.timedelta(days=days))
        self.update()

    def previous(self, days=None):
        """
        Regresses the dates being displayed by a given number of @days.
        If none is given, the default self.numdays will be used. In this case,
        if the actual first_day being shown is not at the beginning of a
        week/month, it will go back to the beginning of it instead
        of going back @numdays.

        @param days: integer, the number of days to go back.
         If none is given, the default self.numdays will be used.
        """
        start = self.first_day

        if not days:
            days = self.numdays
            if self.view_type == "Month":
                # FIXME: months should have different numdays
                if start.day != 1:
                    days = start.day - 1
            else:  # weeks
                if start.weekday() != 0:
                    days = start.weekday()

        self.set_days_range(start - datetime.timedelta(days=days))
        self.update()

    def compute_size(self):
        """ Computes and requests the size needed to draw everything. """
        width = self.min_day_width*self.numdays
        height = TASK_HEIGHT*len(self.tasks)+HEADER_SIZE
        self.set_size_request(width, height)

    def on_size_allocate(self, widget=None, event=None):
        """ Calculates new day_width when window is resized """
        rect = self.get_allocation()
        self.day_width = self.min_day_width
        if self.min_day_width * self.numdays < rect.width:
            self.day_width = rect.width / float(self.numdays)
        self.set_day_width(self.day_width)

    def identify_pointed_object(self, event, clicked=False):
        """
        Identify the object inside drawing area that is being pointed by the
        mouse. Also points out which mouse cursor should be used in result.

        @param event: a Gdk event
        @param clicked: bool, indicates whether or not the user clicked on the
        object being pointed
        """
        # print(event.x, event.y,
        #       convert_coordinates_to_grid(event.x, event.y, self.day_width,
        #       TASK_HEIGHT, header_y=HEADER_SIZE))
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
        (self.selected_task, cursor) = self.identify_pointed_object(
            event, clicked=True)

        if self.selected_task:
            # double-click
            if event.type == Gdk.EventType._2BUTTON_PRESS:
                pass  # open task to edit in future
            self.drag = True
            widget.get_window().set_cursor(cursor)
            task = self.selected_task.task
            start = (task.get_start_date().date() - self.first_day).days
            end = (task.get_due_date().date() - self.first_day).days + 1
            duration = end - start

            offset = (start * self.day_width) - event.x
            # offset_y = HEADER_SIZE + pos * TASK_HEIGHT - event.y
            if self.drag_action == "expand_right":
                offset += duration * self.day_width
            self.drag_offset = offset

            self.queue_draw()

    def motion_notify(self, widget, event):
        """ User moved mouse over widget """
        if self.selected_task and self.drag:  # a task was clicked
            task = self.selected_task.task
            start_date = task.get_start_date().date()
            end_date = task.get_due_date().date()
            duration = (end_date - start_date).days

            offset = self.drag_offset
            event_x = event.x + offset
            # event_y = event.y

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
                new_start_day = self.first_day + \
                    datetime.timedelta(days=weekday)
                new_due_day = new_start_day + datetime.timedelta(days=duration)
                task.set_start_date(new_start_day)
                task.set_due_date(new_due_day)

            self.queue_draw()

        else:  # mouse hover
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
            # event_y = event.y
            weekday = int(event_x / self.day_width)

            task = self.selected_task.task
            start = task.get_start_date().date()
            end = task.get_due_date().date()
            duration = (end - start).days

            new_start_day = self.first_day + datetime.timedelta(days=weekday)
            if self.drag_action == "expand_right":
                new_start_day = task.get_start_date().date()
            new_due_day = new_start_day + datetime.timedelta(days=duration)

            if not self.drag_action == "expand_right" \
               and new_start_day <= end:
                task.set_start_date(new_start_day)
            if not self.drag_action == "expand_left" \
               and new_due_day >= start:
                task.set_due_date(new_due_day)

        widget.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.ARROW))
        self.drag_offset = None
        self.drag = None
        # self.selected_task = None
        self.queue_draw()

    def draw(self, widget, ctx):
        """ Draws everything inside the DrawingArea """
        ctx.set_line_width(0.8)
        ctx.select_font_face(self.FONT, cairo.FONT_SLANT_NORMAL,
                             cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(12)

        self.background.set_column_width(self.day_width)
        self.background.draw(ctx, self.get_allocation(),
                             highlight_col=self.today_column)

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
