import cairo
import datetime
import random

random.seed(7)  # to generate same colors/dates every time


def random_color(mix=(0, 0.5, 0.5)):
    """
    Generates a random color based on the color @mix given as parameter.
    If the @mix color is the same every time, all the colors generated
    will be as from the same color pallete.

    param @mix: triple of floats, a color in the format (red, green, blue)
    """
    red = (random.random() + mix[0])/2
    green = (random.random() + mix[1])/2
    blue = (random.random() + mix[2])/2
    return (red, green, blue)


def date_generator(start, numdays):
    """
    Generates a list of dates (datetime objects) with a specific size @numdays,
    so that it represents the days starting from @start.

    @param start: a datetime object, first date to be included in the list
    @param numdays: integer, size of the list
    @return days: list of datetime objects, each containing a date
    """
    date_list = [start + datetime.timedelta(days=x) for x in range(numdays)]
    return date_list


def create_vertical_gradient(x, y, h, color, alpha):
    grad = cairo.LinearGradient(x, y, x, y+h)
    c = [c + 0.1 for c in color]
    grad.add_color_stop_rgba(0, c[0], c[1], c[2], alpha)
    grad.add_color_stop_rgba(0.2, color[0], color[1], color[2], alpha)
    grad.add_color_stop_rgba(0.8, color[0], color[1], color[2], alpha)
    grad.add_color_stop_rgba(1, c[0], c[1], c[2], alpha)
    return grad


def convert_coordinates_to_col(pos_x, width, header_x=0):
    grid_x = (pos_x - header_x) / width
    return int(grid_x)


def convert_coordinates_to_row(pos_y, height, header_y=0):
    grid_y = (pos_y - header_y) / height
    return int(grid_y)


def convert_coordinates_to_grid(pos_x, pos_y, width, height,
                                header_x=0.0, header_y=0.0):
    grid_x = convert_coordinates_to_col(pos_x, width, header_x)
    grid_y = convert_coordinates_to_col(pos_y, height, header_y)
    return grid_x, grid_y


def convert_grid_to_screen_coord(col_width, line_height, x, y, w, h,
                                 padding=0, header_x=0, header_y=0):
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
    day = date.day
    week = 0
    while(day - 7 > 0):
        day -= 7
        week += 1
    if day > date.weekday() + 1:
        week += 1
    return week


def date_to_col_coord(date, start):
    return (date - start).days


def date_to_grid_coord(date, start):
    row = date_to_row_coord(date, start)
    col = date_to_col_coord(date, start)
    return (row, col)


def center_text_on_rect(ctx, text, base_x, base_y, width, height, crop=False):
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
