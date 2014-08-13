import cairo
import datetime
import random

random.seed(7)  # to generate same colors/dates every time


def random_color(mix=(0, 0.5, 0.5)):
    """
    Generates a random color based on the color @mix given as parameter.
    If the @mix color is the same every time, all the colors generated
    will be as from the same color pallete.

    @param mix: triple of floats, a color in the format (red, green, blue).
    @return color: triple of floats, a newly generated color in the format RGB.
    """
    red = (random.random() + mix[0])/2
    green = (random.random() + mix[1])/2
    blue = (random.random() + mix[2])/2
    return (red, green, blue)


def date_generator(start, numdays):
    """
    Generates a list of dates (datetime objects) with a specific size @numdays,
    so that it represents the days starting from @start.

    @param start: a datetime object, first date to be included in the list.
    @param numdays: int, number of days from @start to generate. This will
                    ultimately be the size of the list.
    @return date_list: list of datetime objects, each containing a date
                       between @start and @start+@numdays.
    """
    date_list = [start + datetime.timedelta(days=x) for x in range(numdays)]
    return date_list


def create_vertical_gradient(x, y, h, color, alpha):
    """
    Creates a vertical gradient along the line given by (@x, @y), (@x, @y+@h).
    The gradient will have predominant color @color, with transparency @alpha.

    @param x: float, x coordinate of the first point.
    @param y: float, y coordinate of the first point.
    @param h: float, the height between the first and the second points.
    @param color: 3-tuple of floats, corresponding to the RGB code of the
                  main color the gradient will have.
    @param alpha: float between 0 and 1, the transparency of the color.
    @return grad: a cairo.LinearGradient object.
    """
    grad = cairo.LinearGradient(x, y, x, y+h)
    c = [c + 0.1 for c in color]
    grad.add_color_stop_rgba(0, c[0], c[1], c[2], alpha)
    grad.add_color_stop_rgba(0.2, color[0], color[1], color[2], alpha)
    grad.add_color_stop_rgba(0.8, color[0], color[1], color[2], alpha)
    grad.add_color_stop_rgba(1, c[0], c[1], c[2], alpha)
    return grad


def convert_coordinates_to_col(pos_x, width, header_x=0):
    """
    Converts the coordinate given by @pos_x into a col position in a grid,
    assuming that the grid starts at coordinate @header_x and each col has
    size @width.

    @param pos_x: float, the x coordinate.
    @param width: float, the width of each col.
    @param header_x: float, the x coord where the grid begins. Default = 0.
    @return col: integer, the corresponding col for the coordinate.
    """
    col = (pos_x - header_x) / width
    return int(col)


def convert_coordinates_to_row(pos_y, height, header_y=0):
    """
    Converts the coordinate given by @pos_y into a row position in a grid,
    assuming that the grid starts at coordinate @header_y and each row has
    size @height.

    @param pos_y: float, the y coordinate.
    @param height: float, the height of each row.
    @param header_y: float, the y coord where the grid begins. Default = 0.
    @return row: integer, the corresponding row for the coordinate.
    """
    row = (pos_y - header_y) / height
    return int(row)


def convert_coordinates_to_grid(pos_x, pos_y, width, height,
                                header_x=0.0, header_y=0.0):
    """
    Converts the coordinate given by @pos_x, @pos_y into a grid position.
    See convert_coordinates_to_col and convert_coordinates_to_row for more
    details.

    @param pos_x: float, the x coordinate.
    @param pos_y: float, the y coordinate.
    @param width: float, the width of each col.
    @param height: float, the height of each row.
    @param header_x: float, the x coord where the grid begins. Default = 0.
    @param header_y: float, the y coord where the grid begins. Default = 0.
    @return row: integer, the corresponding row for the coordinate.
    @return col: integer, the corresponding col for the coordinate.
    """
    col = convert_coordinates_to_col(pos_x, width, header_x)
    row = convert_coordinates_to_row(pos_y, height, header_y)
    return row, col


def convert_grid_to_screen_coord(col_width, line_height, x, y, w, h,
                                 padding=0, header_x=0, header_y=0):
    """
    Converts the grid rectangle given by (@x, @y, @w, @y) into a screen
    coordinate, assuming that the grid starts at point (@header_x, @header_y)
    and that each grid has size @col_width, @line_height.
    It also assumes a @padding around each grid cell.

    @param col_width: float, the width of each col.
    @param line_height: float, the height of each row.
    @param x: int, the column the rectangle starts in the grid.
    @param y: int, the row the rectangle starts in the grid.
    @param w: int, the number of columns the rectangle occupies in the grid.
    @param h: int, the number of rows the rectangle occupies in the grid.
    @param padding: float, the padding around each cell. Default = 0.
    @param header_x: float, the x coord where the grid begins. Default = 0.
    @param header_y: float, the y coord where the grid begins. Default = 0.

    @return base_x: float, the leftmost x coordinate of the rectangle
    @return base_y: float, the topmost y coordinate of the rectangle
    @return width: float, the width of the rectangle
    @return height: float, the height of the rectangle
    """
    base_x = x * col_width + header_x
    base_y = y * line_height + header_y
    width = w * col_width
    height = h * line_height
    if padding:
        base_x += padding
        base_y += padding
        width -= 2*padding
        height -= 2*padding
    return base_x, base_y, width, height


def date_to_row_coord(date, start):
    """
    Converts a @date to a row in a grid, given a reference @start date.
    This function basically returns the position of the date's week in the
    month view. It assumes that @start is in row 0, and that each row
    corresponds to a week, and that @date should be displayed in the same
    month as start, even if it appears in a different month.
    For example, consider the following cases, using as @start date Jul/01/14:

          @date   @row                            July 2014
          Jun/30 -> 0                        Mo Tu We Th Fr Sa Su
          Jul/07 -> 1                        30  1  2  3  4  5  6
          Jul/19 -> 2                         7  8  9 10 11 12 13
          Jul/31 -> 4                        14 15 16 17 18 19 20
          Aug/01 -> 4                        21 22 23 24 25 26 27
          Aub/03 -> 4                        28 29 30 31  1  2  3

    ATTENTION: Note that this does not check the validity of any of these
    assumptions, so it needs to be used carefully.
    For example, for the same @start date as above, the following results are
    obtained, even though the dates should not be shown in the month view:
        Jun/25 -> 0  # error!
        Aug/05 -> 4  # error!

    @param date: a datetime object, the date we want to convert to row.
    @param start: a datetime object, the date we want to use as reference,
                  usually it should be the first day of the month in question.
    @return row: int, the corresponding row for the date.
    """
    # date is in previous month than start
    if date.month + 1 == start.month:
        return 0
    # date is in next month than start
    elif date.month - 1 == start.month:
        return -1
    # two dates in same month
    elif date.month == start.month:
        day = date.day
        week = 0
        while(day - 7 > 0):
            day -= 7
            week += 1
        if day > date.weekday() + 1:
            week += 1
        return week
    raise ValueError("Dates %d and %d are not valid combinations." %
                     (date, start))


def date_to_col_coord(date, start):
    """
    Converts a @date to a column in a grid, given a reference @start date.
    This function assumes that @start is in column 0, and then the column
    corresponding to @date will be the difference between the two of them.

    @param date: a datetime object, the date we want to convert to col.
    @param start: a datetime object, the date we want to use as reference.
    @return col: int, the corresponding col for the date.
    """
    return (date - start).days


def date_to_grid_coord(date, start):
    """
    Converts a @date to a cell (row, col) in a grid, given a reference @start
    date. See date_to_row_coord and date_to col_coord for more details.

    @param date: a datetime object, the date we want to convert to col.
    @param start: a datetime object, the date we want to use as reference.
    @return col: int, the corresponding col for the date.
    @return row: int, the corresponding row for the date.
    """
    row = date_to_row_coord(date, start)
    col = date_to_col_coord(date, start)
    return (row, col)


def center_text_on_rect(ctx, text, base_x, base_y, width, height, crop=False):
    """
    Centers a @text inside a rectangle delimited by @base_x, @base_y, @width,
    @height. If @crop is set to True, the text will be cropped in case it
    overflows the rectangle delimited area ("..." will be added at the end).

    @param ctx: a Cairo context.
    @param base_x: float, the leftmost x coordinate of the rectangle.
    @param base_y: float, the topmost y coordinate of the rectangle.
    @param width: float, the width of the rectangle.
    @param height: float, the height of the rectangle.
    @param crop: bool, whether or not the text should be cropped if it is too
                 long to fit inside the rectangle. Default = False.
    @return text: string, the original text
                          OR if (crop=True and text is too long):
                          the string cropped to fit the rectangle and with
                          "..." added at the end.
    @return base_x: float, the leftmost x coordinate the text should be drawn.
    @return base_y: float, the topmost y coordinate the text should be drawn.
    """
    (x, y, w, h, dx, dy) = ctx.text_extents(text)
    if crop:
        letter_w = ctx.text_extents('m')[2]
        if len(text)*letter_w > width:
            crop_at = int(width/letter_w) - 3
            text = text[:crop_at] + "..."
            (x, y, w, h, dx, dy) = ctx.text_extents(text)
    base_x = base_x + width/2.0 - w/2.0
    base_y = base_y + height/2.0 + h/2.0
    return text, base_x, base_y


def rounded_edges_or_pointed_ends_rectangle(ctx, x, y, w, h,
                                            arrow_right=False,
                                            arrow_left=False, r=5):
    """
    Draws a rectangle with either rounded edges, or with right and/or left
    pointed ends. The non-pointed end, if any, will have rounded edges as
    well.

      x      w   @param ctx: a Cairo context
      v      v   @param x: the leftmost x coordinate of the bounding box
    y> A****BQ   @param y: the topmost y coordinate of the bounding box
      H      C   @param w: the width of the bounding box
      J      K   @param h: the height of the bounding box
      G      D   @param r: the radius of the rounded edges. Default = 8
    h> F****E    @param arrow_right: bool, whether there should be an arrow
                  to the right
                 @param arrow_left: bool, whether there should be an arrow to
                  the left
    """
    ctx.move_to(x+r, y)                               # Move to A
    ctx.line_to(x+w-r, y)                             # Straight line to B
    if arrow_right:
        ctx.line_to(x+w, y+h/2)                       # Straight line to K
        ctx.line_to(x+w-r, y+h)                       # Straight line to E
    else:
        ctx.curve_to(x+w, y, x+w, y, x+w, y+r)  # Curve to C: 2 ctrl pts at Q
        ctx.line_to(x+w, y+h-r)                       # Move to D
        ctx.curve_to(x+w, y+h, x+w, y+h, x+w-r, y+h)  # Curve to E
    ctx.line_to(x+r, y+h)                             # Line to F
    if arrow_left:
        ctx.line_to(x, y+h/2)                         # Straight line to J
        ctx.line_to(x+r, y)                           # Straight line to A
    else:
        ctx.curve_to(x, y+h, x, y+h, x, y+h-r)        # Curve to G
        ctx.line_to(x, y+r)                           # Line to H
        ctx.curve_to(x, y, x, y, x+r, y)              # Curve to A
