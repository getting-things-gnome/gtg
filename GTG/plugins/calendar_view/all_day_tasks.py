from gi.repository import Gtk, Gdk
import cairo
import utils

from drawtask import TASK_HEIGHT
from background import Background


class AllDayTasks(Gtk.DrawingArea):
    def __init__(self, parent, rows=1, cols=7):
        super(Gtk.DrawingArea, self).__init__()

        self.par = parent
        self.num_rows = rows
        self.num_columns = cols
        self.background = Background(rows, cols)

        self.padding = 1.5
        self.font = "Courier"
        self.font_size = 12
        self.font_color = (0.35, 0.31, 0.24)
        self.highlight_cell = (None, None)
        self.selected_task = None
        self.cells = []
        self.labels = None

        self.connect("draw", self.draw)

        # drag-and-drop signals and events
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK
                        | Gdk.EventMask.BUTTON_RELEASE_MASK
                        | Gdk.EventMask.BUTTON1_MOTION_MASK
                        | Gdk.EventMask.POINTER_MOTION_MASK)

    def set_labels(self, labels):
        self.labels = labels

    def set_num_rows(self, rows):
        self.num_rows = rows
        self.background.set_num_rows(rows)

    def set_font(self, font):
        self.font = font

    def set_font_size(self, size):
        self.font_size = size

    def set_font_color(self, color):
        self.font_color = color

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
                self.background.highlight_cell(ctx, row, col, alloc,
                                               color, alpha=0.5)
                ctx.restore()

    def set_highlight_cell(self, row, col):
        if 0 <= row < self.num_rows and 0 <= col < self.num_columns:
            self.highlight_cell = (row, col)
        else:
            self.highlight_cell = (None, None)

    def draw(self, widget, ctx):
        ctx.set_line_width(0.8)
        ctx.set_font_size(self.font_size)
        ctx.select_font_face(self.font, cairo.FONT_SLANT_NORMAL,
                             cairo.FONT_WEIGHT_NORMAL)

        # first draw background
        ctx.save()
        alloc = self.get_allocation()
        self.set_line_color(color=(0.35, 0.31, 0.24, 0.15))
        row, col = self.highlight_cell
        if row is not None and col is not None and row >= 0 and col >= 0:
            self.background.highlight_cell(ctx, row, col, alloc)
        self.background.draw(ctx, alloc, vgrid=True, hgrid=True)
        ctx.restore()

        # then draw labels, if any (used only on month_view)
        if self.labels:
            ctx.save()
            color = self.font_color
            ctx.set_source_rgb(color[0], color[1], color[2])
            for j, week in enumerate(self.labels):
                for i, day in enumerate(week):
                    base_x = i * self.get_day_width() + self.padding
                    base_y = j * self.get_week_height() + self.font_size
                    ctx.move_to(base_x, base_y)
                    ctx.text_path(day)
                    ctx.stroke()
            ctx.restore()

        # then draw all tasks
        for dtask in self.drawtasks:
            selected = self.selected_task and \
                (dtask.get_id() == self.selected_task)
            ctx.save()
            dtask.draw(ctx, self.get_day_width(), self.padding, selected,
                       self.get_week_height())
            ctx.restore()

        # FIXME: remove this from draw() and make function callable directly
        # need a ctx to draw the highlight cells
        self.highlight_cells(ctx, self.cells, color=(0.8, 0.8, 0.8))

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
        for task in self.drawtasks:
            (x, y, w, h) = utils.convert_grid_to_screen_coord(
                self.get_day_width(), TASK_HEIGHT, *task.get_position(),
                padding=self.padding)
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
        return None, None, cursor
