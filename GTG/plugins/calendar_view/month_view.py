from gi.repository import Gtk, Gdk
import datetime
import calendar

from GTG.plugins.calendar_view.week import WeekSpan
from GTG.plugins.calendar_view.drawtask import DrawTask
from GTG.plugins.calendar_view.grid import Grid
from GTG.plugins.calendar_view.utils import convert_coordinates_to_grid, \
    date_to_col_coord, date_to_row_coord, \
    convert_coordinates_to_col, convert_coordinates_to_row
from GTG.plugins.calendar_view.view import ViewBase
from GTG.plugins.calendar_view.day_cell import DayCell
from GTG.plugins.calendar_view.link_label import LinkLabel


class MonthView(ViewBase):

    def __init__(self, parent, requester, numdays=7):
        super(MonthView, self).__init__(parent, requester, numdays)

        self.config.min_day_width = 60
        self.config.min_week_height = 80
        self.config.task_height = 15
        self.update_config()

        self.weeks = []

        # Scrolled Window options
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)

        self.connect("size-allocate", self.on_size_allocate)

    def update_config(self):
        self.all_day_tasks.add_configurations(self.config)
        self.header.add_configurations(self.config)

    def on_size_allocate(self, widget=None, event=None):
        """ Refreshes content when window is resized """
        self.refresh()

    def init_weeks(self, numweeks):
        """
        Initializates the structure needed to manage dates, tasks and task
        positions for each one of the @numweeks weeks of the month.
        Structure self.weeks is a list of size @numweeks, where each position
        manages the dates corresponding to a week, being actually a dictionary
        with entries:
            'grid': contains Grid object.
            'dates': contains WeekSpan object.
            'tasks': is an empty list, will keep track of list of DrawTask.

        @param numweeks: integer, the number of weeks
        """
        self.weeks = []
        for w in range(numweeks):
            week = {}
            week['grid'] = Grid(1, self.numdays)
            week['dates'] = WeekSpan()
            week['tasks'] = []
            self.weeks.append(week)
        self.all_day_tasks.set_num_rows(numweeks)

    def first_day(self):
        """ Returns the first day of the view being displayed """
        return self.weeks[0]['dates'].start_date

    def last_day(self):
        """ Returns the last day of the view being displayed """
        return self.weeks[-1]['dates'].end_date

    def get_week_height(self):
        """ Returns the week/row height in pixels """
        return self.all_day_tasks.get_week_height()

    def show_today(self):
        """
        Shows the range of dates in the current view with the date
        corresponding to today among it.
        """
        today = datetime.date.today()
        self.update_weeks(today.year, today.month)
        self.refresh()

    def total_rows_needed_in_calendar_cell(self, row, col):
        """
        Gets the total number of rows needed to display the content in a
        specific calendar cell given by @row and @col.

        @param row: integer, the row index of the cell, corresponding to the
                    week we are looking at.
        @param col: integer, the col index of the cell.
        @return: integer, the total number of rows needed in order to display
                 all the content in this specific cell.
        """
        grid = self.weeks[row]['grid']  # grid correspondent to this week/row
        last_row_index = grid.last_occupied_row_in_col(col)
        return last_row_index + 1

    def compute_size(self):
        """ Computes and requests the size needed to draw everything. """
        width = self.config.min_day_width * self.numdays
        height = self.config.min_week_height * self.numweeks
        self.all_day_tasks.set_size_request(width, height)

    def calculate_number_of_weeks(self, year, month):
        """
        Calculates the number of weeks the given @month of a @year has.

        @param year: integer, a valid year in the format YYYY.
        @param month: integer, a month (should be between 1 and 12).
        @return total_weeks: integer, the number of weeks @month has.
        """
        num_days_in_month = calendar.monthrange(year, month)[1]
        first_day = datetime.date(year, month, 1)
        last_day = datetime.date(year, month, num_days_in_month)
        total_weeks = date_to_row_coord(last_day, first_day) + 1
        return total_weeks

    def update_weeks(self, year, month):
        """
        Updates the dates of the weeks of a a specific @month of a @year.
        This will erase the whole self.weeks structure, and then fill the entry
        week['dates'] of each week with the right dates.

        @param year: integer, a valid year in the format YYYY.
        @param month: integer, a month (should be between 1 and 12)
        """
        self.year = year
        self.month = month
        self.numweeks = self.calculate_number_of_weeks(year, month)
        self.init_weeks(self.numweeks)
        first_day = datetime.date(year, month, 1)
        for i, week in enumerate(self.weeks):
            new_week = WeekSpan()
            day = first_day + datetime.timedelta(days=i*7)
            new_week.week_containing_day(day)
            week['dates'] = new_week

    def update_header(self, format="%A"):
        """
        Updates the header label of the days to be drawn given a specific
        strftime @format, and then redraws the header. If more than one line is
        wanted to display each labels, the format must separate the content
        inteded for each line by a space.

        @param format: string, must follow the strftime convention.
         Default: "%A" - weekday as locale's full name.
        """
        days = self.weeks[0]['dates'].label(format)
        days = [d.split() for d in days]
        self.header.set_labels(days)
        self.header.queue_draw()
        self.emit('dates-changed')

    def update_days_label(self, format="%d"):
        """
        Updates the label of the days of the month to be drawn given a specific
        strftime @format.

        @param format: string, must follow the strftime convention.
         Default: "%d" - day of month as a zero-padded decimal number.
        """
        days = []
        for week in self.weeks:
            days.append(week['dates'].label(format))
        self.all_day_tasks.set_labels(days)

    def set_task_drawing_position(self, dtask, week, grid, num_week=None):
        """
        Calculates and sets the position of a @dtask inside a specific @week
        using @grid as guidance.

        @param dtask: a DrawingTask object.
        @param week: a WeekSpan object.
        @param grid: a Grid object.
        @param num_week: integer, the number of the week the task should be
                         drawn.
        """
        task = self.req.get_task(dtask.get_id())

        start = max(task.get_start_date().date(), week.start_date)
        end = min(task.get_due_date().date(), week.end_date)
        duration = (end - start).days + 1

        x = date_to_col_coord(start, week.start_date)
        w = duration
        x, y, w, h = grid.add_to_grid(x, w, id=dtask.get_id())

        dtask.set_position(x, y, w, h)  # position inside this grid
        dtask.set_week_num(num_week)  # which week this task is in
        dtask.set_overflowing_L(week.start_date)
        dtask.set_overflowing_R(week.end_date)

    def date_range_to_string(self):
        """
        Returns the string correspoding to the days being displayed in this
        view.
        """
        date_this_month = datetime.date(self.year, self.month, 1)
        return date_this_month.strftime("%B / %Y")

    def is_in_week_range(self, task, week):
        """
        Returns true if the given @task have either the start or due days
        between the start and end day of @week.

        @param task: a Task object.
        @param week: a WeekSpan object.
        """
        return (task.get_due_date().date() >= week.start_date) and \
               (task.get_start_date().date() <= week.end_date)

    def get_maximum_tasks_per_week(self):
        """ Returns the maximum number of tasks a single cell can hold. """
        tasks_available_area = (self.get_week_height() -
                                self.all_day_tasks.get_label_height())
        return int(tasks_available_area // self.config.task_height)

    def on_show_more_tasks(self, day):
        """
        Callback function to show the hidden tasks from a @day cell. This
        function is called after a label '+x more' is clicked.
        It will display a popup dialog containing all the tasks for a
        specific @day (including the hidden ones).

        @param day: a datetime object, corresponds to the clicked day.
        """
        appears_in_day = lambda t: \
            (t.task.get_due_date().date() >= day) and \
            (t.task.get_start_date().date() <= day)

        row = date_to_row_coord(day, datetime.date(self.year, self.month, 1))
        week = self.weeks[row]
        tasks = [t.task for t in week['tasks'] if
                 appears_in_day(t)]

        # FIXME: create popover also (check if GNOME >= 3.12)
        popup = DayCell(self.get_toplevel(), day, tasks, self.edit_task)
        popup.run()
        popup.destroy()

    def create_link(self, row, col, count):
        """
        Creates a link to the hidden tasks inside a day cell given by (@row,
        @col) with @count overflowing tasks.

        @param row: integer, the row corresponding to the cell.
        @param col: integer, the col corresponding to the cell.
        @param count: integer, the number of tasks hidden in this cell.
        @return link: a LinkLabel object.
        """
        link = LinkLabel(count, row, col)
        return link

    def tasks_to_hide(self, row, col, visible_rows, needed_rows):
        """
        Returns the tasks that should be hidden inside a day cell given
        by (@row, @col). It receives the number of @visible_rows the cell
        can hold, and the total of @needed_rows that would be necessary to
        display all tasks in this cell (without hiding any).

        @param row: integer, the row corresponding to the cell.
        @param col: integer, the col corresponding to the cell.
        @param visible_rows: integer, the number of rows a cell can hold.
        @param needed_rows: integer, the number of rows needed to display all
                            the tasks inside the given cell.
        @return to_hide: list of strings, contains the ids of the tasks that
                         will be hidden in this cell.
        """
        grid = self.weeks[row]['grid']
        to_hide = []
        if needed_rows >= visible_rows:
            for i in range(visible_rows, needed_rows):
                cell = grid[i][col]
                if not cell.is_free():
                    to_hide.append(str(cell))
        return to_hide

    def solve_overflowing_tasks_problem(self):
        """
        Solves the case where we have more tasks than available space to draw
        in a single cell/day. If a cell has overflowing tasks, they will be
        hidden and a label indicating so will be created where the user will
        be able to click and see the hidden tasks.
        """
        overflow_links = []
        visible_rows = self.get_maximum_tasks_per_week()
        for row, week in enumerate(self.weeks):
            if week['grid'].num_rows > visible_rows:
                for col in range(self.numdays):
                    needed_rows = self.total_rows_needed_in_calendar_cell(
                        row, col)
                    # not enough space to draw all tasks in this day
                    if needed_rows > visible_rows:
                        to_hide = self.tasks_to_hide(row, col, visible_rows,
                                                     needed_rows)
                        num_hidden_tasks = len(to_hide)

                        # hide overflowing tasks from cell
                        for dtask in week['tasks']:
                            if dtask.get_id() in to_hide:
                                dtask.set_position(-1, -1, -1, -1)

                        # create link to hidden tasks
                        link = self.create_link(row, col, num_hidden_tasks)
                        overflow_links.append(link)
        self.all_day_tasks.overflow_links = overflow_links

    def update_drawtasks(self, tasks=None):
        """
        Updates the drawtasks and calculates the position of where each one of
        them should be drawn.

        @param tasks: a Task list, containing the tasks to be drawn.
         If none is given, the tasks will be retrieved from the requester.
        """
        def duration(task):
            return (task.get_due_date() - task.get_start_date()).days

        if not tasks:
            tasks = [self.req.get_task(t) for t in
                     self.tasktree.get_all_nodes()]
        self.tasks = [t for t in tasks if t is not None and
                      self.is_in_days_range(t)]
        self.tasks.sort(key=lambda t: duration(t), reverse=True)

        dtasks = []
        for i, week in enumerate(self.weeks):
            week['tasks'] = [DrawTask(t) for t in self.tasks if
                             self.is_in_week_range(t, week['dates'])]
            dtasks += week['tasks']

            week['grid'].clear_rows()
            for t in week['tasks']:
                self.set_task_drawing_position(t, week['dates'],
                                               week['grid'], i)
        self.all_day_tasks.set_tasks_to_draw(dtasks)

        # solve case where there is not enough space to draw all tasks in a day
        self.solve_overflowing_tasks_problem()

        # clears selected_task if it is not being showed
        if self.selected_task:
            if self.req.has_task(self.selected_task):
                task = self.req.get_task(self.selected_task)
                if not self.is_in_days_range(task):
                    self.unselect_task()
            else:
                self.unselect_task()

    def fade_days_not_in_this_month(self):
        """
        Fade the days at beginnig and/or the end of the view that do not belong
        to the current month being displayed.
        """
        cells = []

        # cells to fade from days in previous month
        row = 0
        col = 0
        for day in self.weeks[0]['dates'].days:
            if day.month != self.month:
                cells.append((row, col))
                col += 1
            else:
                break

        # cells to fade from days in next month
        row = self.numweeks - 1
        col = self.numdays - 1
        for day in reversed(self.weeks[-1]['dates'].days):
            if day.month != self.month:
                cells.append((row, col))
                col -= 1
            else:
                break
        self.all_day_tasks.faded_cells = cells

    def highlight_today_cell(self):
        """ Highlights the cell equivalent to today."""
        if self.is_today_being_shown():
            today = datetime.date.today()
            row = date_to_row_coord(
                today, datetime.date(self.year, self.month, 1))
            if row == -1:
                row = self.numweeks
            col = datetime.date.today().weekday()
        else:
            row = -1
            col = -1
        self.all_day_tasks.set_today_cell(row, col)
        # self.header.set_highlight_cell(0, col)

    def refresh(self):
        """
        Updates the header, the content to be drawn (tasks), recalculates the
        size needed and then redraws everything.
        """
        self.update_drawtasks()
        self.compute_size()
        self.highlight_today_cell()
        self.fade_days_not_in_this_month()
        self.update_header()
        self.update_days_label()
        self.all_day_tasks.queue_draw()

    def next(self, months=1):
        """
        Advances the dates being displayed by a given number of @months.

        @param days: integer, the number of months to advance. Default = 1.
        """
        day_in_next_month = self.last_day() + datetime.timedelta(days=1)
        self.update_weeks(day_in_next_month.year, day_in_next_month.month)
        self.refresh()

    def previous(self, months=1):
        """
        Regresses the dates being displayed by a given number of @months.

        @param months: integer, the number of months to go back. Default = 1.
        """
        day_in_prev_month = self.first_day() - datetime.timedelta(days=1)
        self.update_weeks(day_in_prev_month.year, day_in_prev_month.month)
        self.refresh()

    def total_days_between_cells(self, cell_a, cell_b):
        """
        Returns the total of days elapsed between two grid cells of a month
        calendar. If the dates are the same, it returns 0.

        @param cell_a: tuple (int, int), contains (row, col) of first cell.
        @param cell_b: tuple (int, int), contains (row, col) of sencond cell.
        @return total_days: integer, the number of days between the two cells,
        returning 0 if they are the same.
        """
        # get dates correspoding for each cell
        start = self.weeks[cell_a[0]]['dates'].days[cell_a[1]]
        end = self.weeks[cell_b[0]]['dates'].days[cell_b[1]]
        return (end - start).days

    def get_right_order(self, start_row, start_col, end_row, end_col):
        """
        Gets the right order two cells (@start_row, @start_col) and
        (@end_row, @end_col) should have, inverting them in case the @end cell
        starts before the @start. The result will always return the one most
        at the most top-left as @start, and the other as @end.

        @param start_row: integer, the row where the user started dragging
        @param start_col: integer, the col where the user started dragging
        @param end_row: integer, the row where the user finished dragging
        @param end_col: integer, the col where the user finished dragging

        @return start_row, start_col, end_row, end_col: a 4-tuple of integers,
                containing the row and col for the cell at the most top-left,
                and then the row and col of the other one.
        """
        if end_row < start_row:  # multiple rows
            end_row, start_row = start_row, end_row
            end_col, start_col = start_col, end_col
        elif end_row == start_row and end_col < start_col:  # single row
            end_col, start_col = start_col, end_col
        return start_row, start_col, end_row, end_col

    def calculate_offset(self, task_id, event):
        """
        Calculates the vertical and horizontal offsets, so a user can drag not
        only from the beggining of a task (in case it spans multiple rows
        and/or columns). The offsets will be calculated using the task
        represented by @task_id as reference.

        @param task_id: string, the id of the Task object we want to use as
                        reference.
        @param event: GdkEvent object, contains the pointer coordinates.
        @return offset_x: float, horizontal offset.
        @return offset_y: float, vertical offset.
        """
        task = self.req.get_task(task_id)

        # calculate vertical offset
        week_height = self.get_week_height()
        clicked_row = convert_coordinates_to_row(event.y, week_height)
        # start_row points to row where task starts, or to first row if
        # it starts in date previous to what is being shown at this view
        start_row = clicked_row
        while (start_row > 0 and task.get_start_date().date() <
               self.weeks[start_row]['dates'].start_date):
            start_row -= 1
        offset_y = (start_row - clicked_row) * week_height

        # calculate horizontal offset
        day_width = self.get_day_width()
        clicked_col = convert_coordinates_to_col(event.x, day_width)
        start_col_in_clicked_row = max(
            task.get_start_date().date(),
            self.weeks[clicked_row]['dates'].start_date
            ).weekday()
        col_diff = clicked_col - start_col_in_clicked_row

        offset_x = (start_col_in_clicked_row - clicked_col) * day_width
        if self.drag_action == "expand_right":
            offset_x += col_diff * day_width
            offset_y = 0
        elif self.drag_action == "move":
            offset_x = clicked_col * day_width
            offset_y = clicked_row * week_height

        return offset_x, offset_y

    def track_cells_to_create_new_task(self, event):
        """
        Keeps track of the range of cells between the start of the dragging
        (mouse click) and where the mouse is at the moment, in order to create
        a new task when the mouse button is released. In the meantime, the
        cells will be highlighted to show where the task will be created.

        @param event: GdkEvent object, contains the pointer coordinates.
        """
        day_width = self.get_day_width()
        week_height = self.get_week_height()
        curr_row, curr_col = convert_coordinates_to_grid(
            event.x, event.y, day_width, week_height)
        start_row, start_col = convert_coordinates_to_grid(
            self.drag_offset[0], self.drag_offset[1],
            day_width, week_height)

        # invert cols/rows in case user started dragging from the end date
        start_row, start_col, curr_row, curr_col = self.get_right_order(
            start_row, start_col, curr_row, curr_col)

        total_days = self.total_days_between_cells((start_row, start_col),
                                                   (curr_row, curr_col))+1

        # highlight cells while moving mouse
        cells = []
        for i in range((curr_row - start_row + 1) + 1):
            for col in range(start_col,
                             min(start_col+total_days, self.numdays)):
                cells.append((start_row + i, col))
            total_days -= (self.numdays - start_col)
            start_col = 0

        self.all_day_tasks.cells = cells
        self.all_day_tasks.queue_draw()

    def modify_task_using_dnd(self, task_id, event):
        """
        Modifies a @task using drag and drop according to the pointer
        corrdinates given by @event. The task can be moved, expanded or shrunk
        depending on the dragging action.

        @param task_id: string, the id of the Task object we want to modify.
        @param event: GdkEvent object, contains the pointer coordinates.
        """
        task = self.req.get_task(task_id)
        start_date = task.get_start_date().date()
        end_date = task.get_due_date().date()
        duration = (end_date - start_date).days

        day_width = self.get_day_width()
        week_height = self.get_week_height()

        row = convert_coordinates_to_row(event.y, week_height)
        col = convert_coordinates_to_col(event.x, day_width)
        if row < 0 or row >= self.numweeks or col < 0 or col >= self.numdays:
            return

        if self.drag_action == "expand_left":
            new_start_day = self.weeks[row]['dates'].days[col]
            if new_start_day <= end_date:
                task.set_start_date(new_start_day)

        elif self.drag_action == "expand_right":
            new_due_day = self.weeks[row]['dates'].days[col]
            if new_due_day >= start_date:
                task.set_due_date(new_due_day)

        else:
            offset_x = self.drag_offset[0]
            offset_y = self.drag_offset[1]
            previous_row, previous_col = convert_coordinates_to_grid(
                offset_x, offset_y, day_width, week_height)
            diff = self.total_days_between_cells(
                (previous_row, previous_col), (row, col))

            if diff != 0:  # new_start_day != start_date:
                new_start_day = start_date + datetime.timedelta(diff)
                new_due_day = new_start_day + datetime.timedelta(duration)
                task.set_start_date(new_start_day)
                task.set_due_date(new_due_day)
                self.drag_offset = self.calculate_offset(
                    self.selected_task, event)

    def dnd_start(self, widget, event):
        """ User clicked the mouse button, starting drag and drop """
        # find which task was clicked, if any
        task_id, self.drag_action, cursor = \
            self.all_day_tasks.identify_pointed_object(event, clicked=True)
        self.set_selected_task(task_id)
        self.all_day_tasks.queue_draw()

        if self.selected_task:
            # double-click opens task to edit
            if event.type == Gdk.EventType._2BUTTON_PRESS:
                self.ask_edit_task(self.selected_task)
                self.is_dragging = False
                self.drag_offset = None
                return

            self.drag_offset = self.calculate_offset(self.selected_task, event)
        # if no task is selected, save mouse location in case the user wants
        # to create a new task using DnD
        else:
            self.drag_offset = (event.x, event.y)

        widget.get_window().set_cursor(cursor)

    def motion_notify(self, widget, event):
        """ User moved mouse over widget """
        # don't do any action beyond delimited area
        alloc = self.get_allocation()
        if (event.x < 0 or event.x > alloc.width or
                event.y < 0 or event.y > alloc.height):
            return

        # dragging with no task selected: new task will be created
        if not self.selected_task and self.drag_offset is not None:
            self.is_dragging = True
            self.drag_action = None  # in case action was 'click_link'
            self.track_cells_to_create_new_task(event)
            return

        # a task was clicked
        if self.selected_task and self.drag_offset is not None:
            self.is_dragging = True
            self.modify_task_using_dnd(self.selected_task, event)

        else:  # mouse hover
            t_id, self.drag_action, cursor = \
                self.all_day_tasks.identify_pointed_object(event)
            widget.get_window().set_cursor(cursor)

    def dnd_stop(self, widget, event):
        """ User released a button, stopping drag and drop. """
        # dragging with no task selected: new task will be created
        if not self.selected_task and self.is_dragging:
            day_width = self.get_day_width()
            week_height = self.get_week_height()
            start_row, start_col = convert_coordinates_to_grid(
                self.drag_offset[0], self.drag_offset[1],
                day_width, week_height)

            event = self.fit_event_in_boundaries(event)
            end_row, end_col = convert_coordinates_to_grid(
                event.x, event.y, day_width, week_height)

            # invert cols/rows in case user started dragging from the end date
            start_row, start_col, end_row, end_col = self.get_right_order(
                start_row, start_col, end_row, end_col)

            total_days = self.total_days_between_cells(
                (start_row, start_col), (end_row, end_col))
            start_date = self.weeks[start_row]['dates'].days[start_col]
            due_date = start_date + datetime.timedelta(days=total_days)

            self.ask_add_new_task(start_date, due_date)
            self.all_day_tasks.cells = []

        # user didn't click on a task or just finished dragging task
        # in both cases, redraw to 'unselect' task
        elif not self.selected_task or self.is_dragging:
            self.unselect_task()
            self.all_day_tasks.queue_draw()

        # clicked on link to show hidden tasks
        if self.drag_action == 'click_link':
            row, col = convert_coordinates_to_grid(event.x, event.y,
                                                   self.get_day_width(),
                                                   self.get_week_height())
            day = self.weeks[row]['dates'].days[col]
            self.on_show_more_tasks(day)
            self.drag_action = None

        widget.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.ARROW))
        self.drag_offset = None
        self.is_dragging = False
        self.drag_action = None
