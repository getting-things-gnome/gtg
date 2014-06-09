#!/usr/bin/python3
from gi.repository import Gtk, Gdk
import cairo
import datetime
from calendar import monthrange

HEADER_SIZE = 40

from drawtask import DrawTask, TASK_HEIGHT
from utils import date_generator


def convert_coordinates_to_grid(pos_x, pos_y, width, height,
                                header_x=0.0, header_y=0.0):
    grid_x = (pos_x - header_x) / width
    grid_y = (pos_y - header_y) / height
    return int(grid_x), int(grid_y)


class Background(Gtk.DrawingArea):
    """
    A class to draw everything regarding the background, such as
    the color, the grid, highlighted portion, etc.
    """
    def __init__(self):
        self.draw_grid = True
        self.column_width = None

    def set_column_width(self, column_width):
        self.column_width = column_width

    def draw(self, ctx, area, highlight_col=None):
        # ctx.rectangle(area.x, area.y, area.width, area.height)
        # ctx.set_source_rgb(1, 1, 1) # white
        # ctx.fill()

        # column to be highlighted has a different color
        if highlight_col is not None:
            ctx.set_source_rgba(1, 1, 1, 0.5)  # white
            ctx.rectangle(self.column_width*highlight_col,
                          area.y, self.column_width, area.height)
            ctx.fill()

        if self.draw_grid:
            ctx.set_source_rgb(0.35, 0.31, 0.24)
            ctx.move_to(0, HEADER_SIZE)
            ctx.line_to(area.width, HEADER_SIZE)
            ctx.stroke()

            ctx.move_to(0, 0)
            ctx.line_to(area.width, 0)
            ctx.stroke()

            ctx.set_source_rgba(0.35, 0.31, 0.24, 0.15)
            for i in range(0, int(area.width/self.column_width)):
                ctx.move_to(i*self.column_width, HEADER_SIZE)
                ctx.line_to(i*self.column_width, area.width)
                ctx.stroke()


class Header(Gtk.DrawingArea):
    def __init__(self, days=None, day_width=None):
        super(Header, self).__init__()
        self.days = days
        self.day_width = day_width
        self.connect("draw", self.draw)

    def set_day_width(self, day_width):
        self.day_width = day_width

    def set_days(self, days):
        self.days = days

    def draw(self, ctx):
        """
        Draws the header of the calendar view (days and weekdays).

        @param ctx: a Cairo context
        """
        ctx.set_source_rgba(0.35, 0.31, 0.24)
        for i in range(0, len(self.days)+1):
            ctx.move_to(i*self.day_width, 0)
            ctx.line_to(i*self.day_width, HEADER_SIZE)
            ctx.stroke()

        ctx.set_source_rgb(0.35, 0.31, 0.24)
        for i in range(0, len(self.days)):
            (x, y, w, h, dx, dy) = ctx.text_extents(self.days[i][1])
            ctx.move_to(i*self.day_width - (w-self.day_width)/2.0, 15)
            ctx.text_path(self.days[i][1])
            ctx.stroke()

            (x, y, w, h, dx, dy) = ctx.text_extents(self.days[i][0])
            ctx.move_to(i*self.day_width - (w-self.day_width)/2.0, 30)
            ctx.text_path(self.days[i][0])
            ctx.stroke()
