from GTG.core.task import Task
from GTG.plugins.calendar_view.utils import convert_grid_to_screen_coord, \
    rounded_edges_or_pointed_ends_rectangle, create_vertical_gradient, \
    center_text_on_rect


class DrawTask:
    """
    This class is a wrap around a Task object, and is responsible for drawing
    that task inside the View. Each DrawTask has a corresponding Task object,
    with some extra information, such as the position the task will be drawn,
    the color, etc. It is important to note, however, that the same Task can
    have more than one DrawTask object associate with it (which is actually the
    case in the MonthView, if a single task needs to be displayed in more
    than one week).
    """
    def __init__(self, task):
        """
        Initializates a DrawTask object, given a @task.

        @param task: a Task object, the task this class will correspond to.
        """
        self.task = task
        self.position = (None, None, None, None)
        self.overflow_R = False
        self.overflow_L = False
        self.week_num = None

    def get_id(self):
        """
        Returns the id of the Task this class corresponds to.

        @return task_id: string, the id of the Task being respresented.
        """
        return self.task.get_id()

    def get_label(self):
        """
        Returns the title of the Task this class corresponds to.
        This will be the text used to draw the Task, and will appear inside the
        rectangle corresponding to the Task.

        @return title: string, the title of the Task being respresented.
        """
        return self.task.get_title()

    def get_color(self):
        """
        Returns the color that will be used to draw the task.

        @return color: triple of float, color in the format (red, green, blue).
        """
        return self.task.get_color()

    def set_position(self, x, y, w, h):
        """
        Sets the position given by the rectangle (@x, @y, @w, @h) that this
        task has inside a grid.

        OBS: Since each row in a View has its own Grid, the DrawTask position
        is relative to that specific grid. That's why in a MonthView object
        the week_num is needed.
        However, the DrawTask object has no notion of any of that.

        @param x: integer, the initial row inside a grid.
        @param y: integer, the initial col inside a grid.
        @param w: integer, the width in grid cells.
        @param h: integer, the height in grid cells.
        """
        self.position = (x, y, w, h)

    def get_position(self):
        """
        Returns the position of this object.
        See set_position for more details.

        @return position: 4-tuple of ints, the position of the task should be
                          drawn in the correspoding grid.
        """
        return self.position

    def set_week_num(self, week_num):
        """
        Sets the corresponding week inside a month this task should appear.
        Only used for MonthView.

        @param week_num: int, the number of the week this task should appear
                         inside a month.
        """
        self.week_num = week_num

    def get_week_num(self):
        """
        Gets the number of the month week this task should be drawn.
        See set_week_num for more details.

        @return week_num: int, the number of the week this task should appear
                          inside a month.
        """
        return self.week_num

    def is_overflowing_R(self):
        """
        Returns whether or not the task is overflowing to the right.
        See set_overflowing_R for more details.

        @return: bool, whether or not the task is overflowing to the right.
        """
        return self.overflow_R

    def is_overflowing_L(self):
        """
        Returns whether or not the task is overflowing to the left.
        See set_overflowing_L for more details.

        @return: bool, whether or not the task is overflowing to the left.
        """
        return self.overflow_L

    def set_overflowing_R(self, last_day):
        """
        Sets whether or not the task is overflowing to the right, i.e., the
        task's due date is after @last_day. This is usually the last day
        being displayed in the current view - or at the object's corresponding
        week, if in MonthView - that this object will be drawn.

        @param last_day: a datetime object, the last day being showed in the
                         area where the object will be drawn.
        """
        self.overflow_R = self.task.get_due_date().date() > last_day

    def set_overflowing_L(self, first_day):
        """
        Sets whether or not the task is overflowing to the left, i.e., the
        task's start date is before @first_day. This is usually the first day
        being displayed in the current view - or at the object's corresponding
        week, if in MonthView - that this object will be drawn.

        @param first_day: a datetime object, the first day being showed in the
                          area where the object will be drawn.
        """
        self.overflow_L = self.task.get_start_date().date() < first_day

    def is_done(self):
        """
        Returns whether or not the task is done (Task.status == STA_DONE).

        @return: bool, whether or not the task is done.
        """
        return self.task.get_status() == Task.STA_DONE

    def draw(self, ctx, grid_width, config, selected=False, week_height=None):
        """
        Draws a DrawTask object on the screen.

        @param ctx: a Cairo context.
        @param grid_width: float, the width of each column of the View.
        @param config: a ViewConfig object, contains configurations for the
                       drawing, such as: task height, font color, etc.
        @param selected: bool, whether or not this task is selected (i.e. the
                         task the user clicked on). Default = False.
        @param week_heigh: float, the height of each week in the View.
                           Only used for drawing on MonthView. Default = None.
        """
        task_x, task_y, task_w, task_h = self.get_position()

        base_x, base_y, width, height = convert_grid_to_screen_coord(
            grid_width, config.task_height, task_x, task_y, task_w, task_h,
            config.padding)

        # calculating week position when in month view
        if self.week_num is not None:
            base_y += self.week_num * week_height + config.label_height

        # restrict drawing to exposed area: no unnecessary drawing is done
        ctx.rectangle(base_x, base_y, width, height)
        ctx.clip()

        # create path to draw task
        rounded_edges_or_pointed_ends_rectangle(ctx, base_x, base_y,
                                                width, height,
                                                self.overflow_R,
                                                self.overflow_L)

        # task color
        color = config.selected_task_color if selected else self.get_color()
        alpha = 0.5 if self.is_done() else 1

        # background
        grad = create_vertical_gradient(base_x, base_y, height, color, alpha)
        ctx.set_source(grad)
        ctx.fill()

        # task label
        label = self.get_label()
        pos = (base_x, base_y, width, height)
        label, base_x, base_y = center_text_on_rect(ctx, label, *pos,
                                                    crop=True)
        ctx.move_to(base_x, base_y)
        c = config.task_font_color
        ctx.set_source_rgba(c[0], c[1], c[2], alpha)
        ctx.text_path(label)
        ctx.stroke()
