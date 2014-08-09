from gi.repository import Gtk
import cairo

from GTG.plugins.calendar_view.background import Background
from GTG.plugins.calendar_view.utils import center_text_on_rect


class Header(Gtk.DrawingArea):
    def __init__(self, cols=7):
        super(Header, self).__init__()
        self.labels = []
        self.background = Background(1, cols)
        self.sidebar = 0
        self.highlight_cell = (None, None)

        self.connect("draw", self.draw)

    def add_configurations(self, config):
        self.config = config

    def set_sidebar_size(self, size):
        self.sidebar = size

    def set_labels(self, labels):
        self.labels = labels

    def set_line_color(self, color):
        self.background.set_line_color(color)

    def set_background_color(self, color):
        self.background.set_background_color(color)

    def get_height(self):
        try:
            line_height = self.get_allocation().height / len(self.labels[0])
        except ZeroDivisionError:
            print("List of labels in object Header not initialized!")
            raise
        else:
            return line_height

    def get_col_width(self):
        try:
            col_width = (self.get_allocation().width - self.sidebar) \
                / float(len(self.labels))
        except ZeroDivisionError:
            print("List of labels in object Header not initialized!")
            raise
        else:
            return col_width

    def set_highlight_cell(self, row, col):
        if row == 0 and 0 <= col < len(self.labels):
            self.highlight_cell = (row, col)
        else:
            self.highlight_cell = (None, None)

    def draw(self, widget, ctx):
        """
        Draws the header according to the labels.

        @param ctx: a Cairo context
        """
        alloc = self.get_allocation()
        alloc.width -= self.sidebar
        # FIXME: look deeper into why x=5 and y=35 - both should start at 0
        # Whathever is happening has to do with spacing in vbox (glade file)
        # temporary fix:
        alloc.x = 0
        alloc.y = 0

        ctx.set_line_width(0.8)
        row, col = self.highlight_cell
        if row is not None and col is not None:
            # print "header", alloc.x, alloc.y, alloc.width, alloc.height
            self.background.highlight_cell(ctx, row, col, alloc,
                                           self.config.today_cell_color)

        self.set_line_color(self.config.line_color)
        self.background.draw(ctx, alloc, vgrid=False, hgrid=True)

        color = self.config.font_color
        ctx.set_source_rgb(color[0], color[1], color[2])

        ctx.set_font_size(self.config.font_size)
        ctx.select_font_face(self.config.font, cairo.FONT_SLANT_NORMAL,
                             cairo.FONT_WEIGHT_NORMAL)

        # print labels: use multiple lines if necessary
        col_width = self.get_col_width()
        line_height = self.get_height()
        for i in range(0, len(self.labels)):
            for j in range(0, len(self.labels[i])):
                label, base_x, base_y = center_text_on_rect(
                    ctx, self.labels[i][j],
                    (i * col_width), (j * line_height),
                    col_width, line_height)
                ctx.move_to(base_x, base_y)
                ctx.text_path(label)
                ctx.stroke()
