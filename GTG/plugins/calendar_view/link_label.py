class LinkLabel:
    """
    This class is a label that simulates a link, in order to display the hidden
    tasks in a specific day. It is used by the MonthView, when there are more
    tasks to be displayed than it fits on the cell height.
    """
    def __init__(self, count, row, col):
        """
        Initializes a LinkLabel object, that will be used to link to the
        hidden tasks inside a day cell given by (@row, @col) with @count
        overflowing tasks.

        @param count: integer, the number of tasks hidden in the corresponding
                      cell for this object.
        @param row: integer, the row of the cell this object corresponds to.
        @param col: integer, the col of the cell this object corresponds to.
        """
        self.text = self.create_label(count)
        self.row = row
        self.col = col
        self.position = None

    def create_label(self, count):
        """
        Creates a label that will be printed when this object is drawn.

        @param count: integer, the number of tasks hidden in the corresponding
                      cell for this object.
        @return label: string, the label that will be used for drawing.
        """
        return '+%d more' % count

    def set_position(self, x, y, w, h):
        """
        Sets the bounding box of this object in the parent widget coordinates
        given by the rectangle (@x, @y, @w, @h).

        @param x: float, the leftmost x coordinate of the bounding box.
        @param y: float, the topmost y coordinate of the bounding box.
        @param w: float, the width of the bounding box.
        @param h: float, the height of the bounding box.
        """
        self.position = (x, y, w, h)

    def get_position(self):
        """
        Returns the position of this object.
        See set_position for more details.

        @return position: 4-tuple of floats, the position the link should be
                          drawn in the screen.
        """
        return self.position

    def get_corresponding_cell(self):
        """
        Gets the corresponding cell that this LinkLabel object is related to.

        @return row: integer, the row of the cell this object corresponds to.
        @return col: integer, the col of the cell this object corresponds to.
        """
        return self.row, self.col

    def draw(self, ctx, day_width, week_height, config):
        """
        Draws a LinkLabel object on the screen.

        @param ctx: a Cairo context.
        @param day_width: float, the width of each day of the View.
        @param week_heigh: float, the height of each week in the View.
        @param config: a ViewConfig object, contains configurations for the
                       drawing, such as: label height, font color, etc.
        """
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
