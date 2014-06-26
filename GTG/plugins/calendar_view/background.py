from gi.repository import Gtk


class Background(Gtk.DrawingArea):
    def __init__(self, rows=1, cols=7):
        super(Background, self).__init__()
        self.num_rows = rows
        self.num_columns = cols
        self.bg_color = None
        self.line_color = (0.35, 0.31, 0.24, 1)
        self.connect("draw", self.draw)

    def get_row_height(self, area):
        return area.height / float(self.num_rows)

    def get_col_width(self, area):
        if self.num_columns > 0:
            return area.width / float(self.num_columns)
        return 0

    def set_line_color(self, color):
        self.line_color = color

    def set_background_color(self, color):
        self.bg_color = color

    def draw(self, ctx, area, vgrid=False, hgrid=False):
        # print 'backgr', area.x, area.y, area.width, area.height
        if self.bg_color:
            color = self.bg_color
            ctx.rectangle(area.x, area.y, area.width, area.height)
            ctx.set_source_rgb(color[0], color[1], color[2])
            ctx.fill()

        if vgrid:
            col_width = self.get_col_width(area)
            color = self.line_color
            ctx.set_source_rgba(color[0], color[1], color[2], color[3])
            for i in range(0, self.num_columns+1):
                ctx.move_to(i*col_width, area.y)
                ctx.line_to(i*col_width, area.height)
                ctx.stroke()

        if hgrid:
            row_height = self.get_row_height(area)
            color = self.line_color
            ctx.set_source_rgba(color[0], color[1], color[2], color[3])
            for i in range(0, self.num_rows+1):
                ctx.move_to(area.x, i*row_height)
                ctx.line_to(area.width, i*row_height)
                ctx.stroke()

    def highlight_cell(self, ctx, row, col, area, color=(1, 1, 1), alpha=0.5):
        # print "highlt", area.x, area.y, area.width, area.height
        if row >= self.num_rows or row < 0 or \
           col >= self.num_columns or col < 0:
            raise ValueError("Cell is out of index!")
        col_width = self.get_col_width(area)
        row_height = self.get_row_height(area)
        ctx.set_source_rgba(color[0], color[1], color[2], alpha)
        ctx.rectangle(col * col_width,
                      row * row_height,
                      col_width,
                      row_height)
        ctx.fill()
