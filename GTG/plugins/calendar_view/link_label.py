class LinkLabel:
    """
    This class is a label that simulates a link, in order to display the hidden
    tasks in a specific day. It is used by the MonthView, when there are more
    tasks to be displayed than it fits on the cell height.
    """
    def __init__(self, count, row, col):
        self.text = self.create_label(count)
        self.row = row
        self.col = col
        self.position = None

    def create_label(self, count):
        return '+%d more' % count

    def set_position(self, x, y, w, h):
        self.position = (x, y, w, h)

    def get_position(self):
        return self.position

    def get_corresponding_cell(self):
        return self.row, self.col

    def draw(self, ctx, day_width, week_height, config):
        w, h = ctx.text_extents(self.text)[2:4]
        base_x = (self.col+1) * day_width - w
        base_x -= 3*config.padding
        base_y = self.row * week_height
        base_y += config.label_height - 2*config.padding
        self.set_position(base_x, base_y, w, h)

        color = config.link_color
        ctx.set_source_rgba(color[0], color[1], color[2], color[3])

        ctx.move_to(base_x, base_y)
        ctx.text_path(self.text)

        # underline
        y = base_y + 2
        ctx.move_to(base_x, y)
        ctx.line_to(base_x + w, y)
        ctx.stroke()
