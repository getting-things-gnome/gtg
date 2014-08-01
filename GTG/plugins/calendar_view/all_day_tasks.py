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
        self.link_color = (0, 0, 255, 0.5)  # default blue link color
        self.today_cell = (None, None)
        self.selected_task = None
        self.faded_cells = []
        self.cells = []
        self.labels = None
        self.label_height = self.font_size
        self.overflow_links = []

        self.connect("draw", self.draw)

        # drag-and-drop signals and events
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK
                        | Gdk.EventMask.BUTTON_RELEASE_MASK
                        | Gdk.EventMask.BUTTON1_MOTION_MASK
                        | Gdk.EventMask.POINTER_MOTION_MASK)

    def get_label_height(self):
        if self.labels:
          return self.label_height
        return 0

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

    def highlight_cells(self, ctx, cells, color, alpha=0.5):
        alloc = self.get_allocation()
        for cell in cells:
            row, col = cell
            if 0 <= row < self.num_rows and 0 <= col < self.num_columns:
                ctx.save()
                self.background.highlight_cell(ctx, row, col, alloc,
                                               color, alpha)
                ctx.restore()

    def set_today_cell(self, row, col):
        if 0 <= row < self.num_rows and 0 <= col < self.num_columns:
            self.today_cell = (row, col)
        else:
            self.today_cell = (None, None)

    def draw(self, widget, ctx):
        ctx.set_line_width(0.8)
        ctx.set_font_size(self.font_size)
        ctx.select_font_face(self.font, cairo.FONT_SLANT_NORMAL,
                             cairo.FONT_WEIGHT_NORMAL)

        # first draw background
        ctx.save()
        alloc = self.get_allocation()
        self.set_line_color(color=(0.35, 0.31, 0.24, 0.15))
        row, col = self.today_cell
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
                    base_y = j * self.get_week_height() + self.label_height
                    ctx.move_to(base_x, base_y)
                    ctx.text_path(day)
                    ctx.stroke()
            ctx.restore()

        # fade days not in current month
        if self.faded_cells:
            self.highlight_cells(ctx, self.faded_cells, color=(0.8, 0.8, 0.8))

        # then draw links when there is overflowing tasks (only in month_view)
        if self.overflow_links:
            ctx.save()
            color = self.link_color
            ctx.set_source_rgba(color[0], color[1], color[2], color[3])
            for link in self.overflow_links:
                (text, row, col) = link
                w = ctx.text_extents(text)[2]
                base_x = (col+1) * self.get_day_width() - w - 3*self.padding
                base_y = row * self.get_week_height() + self.label_height
                ctx.move_to(base_x, base_y)
                ctx.text_path(text)
                # underline
                y = base_y + 2
                ctx.move_to(base_x, y)
                ctx.line_to(base_x + w, y)
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

        # if dragging cells to create new task, highlight them now
        if self.cells:
            self.highlight_cells(ctx, self.cells, color=(0.8, 0.8, 0),
                alpha=0.1)

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
                (text, row, col) = link
                # h, w = ctx.text_extents(text)[1:3]
                # FIXME: more generic values for h and w
                h = self.font_size
                w = self.font_size/2 * len(text)
                base_x = (col+1) * self.get_day_width() - w - 3*self.padding
                base_y = row * self.get_week_height() + self.label_height
                if base_x <= event.x <= base_x + w and \
                   base_y - h <= event.y <= base_y:
                    drag_action = "click_link"
                    cursor = Gdk.Cursor.new(Gdk.CursorType.HAND1)

        for task in self.drawtasks:
            (x, y, w, h) = utils.convert_grid_to_screen_coord(
                self.get_day_width(), TASK_HEIGHT, *task.get_position(),
                padding=self.padding)

            # calculating week position when in month view
            if task.get_week_num() is not None:
                y += task.get_week_num() * self.get_week_height() + 15

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
