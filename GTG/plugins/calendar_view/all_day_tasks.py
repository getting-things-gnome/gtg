from gi.repository import Gtk, Gdk
import cairo

from GTG.plugins.calendar_view.utils import convert_grid_to_screen_coord
from GTG.plugins.calendar_view.background import Background


class AllDayTasks(Gtk.DrawingArea):
    def __init__(self, parent, rows=1, cols=7):
        super(Gtk.DrawingArea, self).__init__()

        self.par = parent
        self.num_rows = rows
        self.num_columns = cols
        self.background = Background(rows, cols)

        self.today_cell = (None, None)
        self.selected_task = None
        self.faded_cells = []
        self.cells = []
        self.labels = None
        self.overflow_links = []

        self.connect("draw", self.draw)

        # drag-and-drop signals and events
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK
                        | Gdk.EventMask.BUTTON_RELEASE_MASK
                        | Gdk.EventMask.BUTTON1_MOTION_MASK
                        | Gdk.EventMask.POINTER_MOTION_MASK)

    def add_configurations(self, config):
        self.config = config

    def get_label_height(self):
        if self.labels:
            return self.config.label_height
        return 0

    def set_labels(self, labels):
        self.labels = labels

    def set_num_rows(self, rows):
        self.num_rows = rows
        self.background.set_num_rows(rows)

    def set_line_color(self, color):
        self.background.set_line_color(color)

    def set_background_color(self, color):
        self.background.set_background_color(color)

    def get_day_width(self):
        return self.get_allocation().width / float(self.num_columns)

    def get_week_height(self):
        return self.get_allocation().height / float(self.num_rows)

    def set_tasks_to_draw(self, drawtasks):
        self.drawtasks = drawtasks

    def highlight_cells(self, ctx, cells, color):
        alloc = self.get_allocation()
        for cell in cells:
            row, col = cell
            if 0 <= row < self.num_rows and 0 <= col < self.num_columns:
                ctx.save()
                self.background.highlight_cell(ctx, row, col, alloc, color)
                ctx.restore()

    def set_today_cell(self, row, col):
        if 0 <= row < self.num_rows and 0 <= col < self.num_columns:
            self.today_cell = (row, col)
        else:
            self.today_cell = (None, None)

    def draw(self, widget, ctx):
        ctx.set_line_width(self.config.line_width)
        ctx.set_font_size(self.config.font_size)
        ctx.select_font_face(self.config.font, cairo.FONT_SLANT_NORMAL,
                             cairo.FONT_WEIGHT_NORMAL)

        # first draw background
        ctx.save()
        alloc = self.get_allocation()
        self.set_line_color(self.config.line_color)
        row, col = self.today_cell
        self.set_background_color(self.config.bg_color)
        self.background.draw(ctx, alloc, self.config.vgrid, self.config.hgrid)
        if row is not None and col is not None and row >= 0 and col >= 0:
            self.background.highlight_cell(ctx, row, col, alloc,
                                           self.config.today_cell_color)
        ctx.restore()

        # then draw labels, if any (used only on month_view)
        if self.labels:
            ctx.save()
            color = self.config.font_color
            ctx.set_source_rgb(color[0], color[1], color[2])
            for j, week in enumerate(self.labels):
                for i, day in enumerate(week):
                    base_x = i * self.get_day_width() + self.config.padding
                    base_y = j * self.get_week_height()
                    base_y += self.get_label_height() - 2*self.config.padding
                    ctx.move_to(base_x, base_y)
                    ctx.text_path(day)
                    ctx.stroke()
            ctx.restore()

        # fade days not in current month
        if self.faded_cells:
            self.highlight_cells(ctx, self.faded_cells,
                                 self.config.faded_cells_color)

        # then draw links when there is overflowing tasks (only in month_view)
        if self.overflow_links:
            ctx.save()
            for link in self.overflow_links:
                link.draw(ctx, self.get_day_width(), self.get_week_height(),
                          self.config)
            ctx.restore()

        # then draw all tasks
        for dtask in self.drawtasks:
            selected = self.selected_task and \
                (dtask.get_id() == self.selected_task)
            ctx.save()
            dtask.draw(ctx, self.get_day_width(), self.config.task_height,
                       self.config, selected, self.get_week_height())
            ctx.restore()

        # if dragging cells to create new task, highlight them now
        if self.cells:
            self.highlight_cells(ctx, self.cells,
                                 self.config.highlight_cells_color)

    def identify_pointed_object(self, event, clicked=False):
        """
        Identify the object inside drawing area that is being pointed by the
        mouse. Also points out which mouse cursor should be used in result.

        @param event: a Gdk event
        @param clicked: bool, indicates whether or not the user clicked on the
        object being pointed
        """
        expand_border = 10
        cursor = Gdk.Cursor.new(Gdk.CursorType.ARROW)
        drag_action = None

        if clicked:
            cursor = Gdk.Cursor.new(Gdk.CursorType.HAND1)

        if self.overflow_links:
            for link in self.overflow_links:
                base_x, base_y, w, h = link.get_position()
                if base_x <= event.x <= base_x + w and \
                   base_y - h <= event.y <= base_y:
                    drag_action = "click_link"
                    cursor = Gdk.Cursor.new(Gdk.CursorType.HAND1)

        for task in self.drawtasks:
            (x, y, w, h) = convert_grid_to_screen_coord(
                self.get_day_width(), self.config.task_height,
                *task.get_position(), padding=self.config.padding)

            # calculating week position when in month view
            if task.get_week_num() is not None:
                y += task.get_week_num() * self.get_week_height() + \
                    self.get_label_height()

            if not y < event.y < (y + h):
                continue
            if x <= event.x <= x + expand_border:
                drag_action = "expand_left"
                cursor = Gdk.Cursor.new(Gdk.CursorType.LEFT_SIDE)
            elif (x + w) - expand_border <= event.x <= (x + w):
                drag_action = "expand_right"
                cursor = Gdk.Cursor.new(Gdk.CursorType.RIGHT_SIDE)
            elif x <= event.x <= (x + w):
                drag_action = "move"
                if clicked:
                    cursor = Gdk.Cursor.new(Gdk.CursorType.FLEUR)
            else:
                continue
            return task.get_id(), drag_action, cursor
        return None, drag_action, cursor
