# -*- coding: utf-8 -*-
# Copyright (c) 2014 - Sara Ribeiro <sara.rmgr@gmail.com>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk


class Background(Gtk.DrawingArea):
    """
    This class is responsible for drawing everything related to the background
    of an area, such as the filling color of each cell and the grid lines.
    The class assumes the area we are working with is a grid, and receives
    the number of rows and columns as parameter.
    It also can highlighting a single cell using a different color.
    """
    def __init__(self, rows=1, cols=7):
        """
        Creates a new Background object that will simulate a grid with
        @rows and @cols.

        @param rows: int, the number of rows the background will have.
        @param cols: int, the number of cols the background will have.
        """
        super(Background, self).__init__()
        self.num_rows = rows
        self.num_columns = cols
        self.bg_color = None
        self.line_color = None
        self.connect("draw", self.draw)

    def set_num_rows(self, rows):
        """
        Sets the number of rows the background area will be divided into.

        @param rows: int, the number of rows the background will have.
        """
        self.num_rows = rows

    def get_row_height(self, area):
        """
        Gets the height of each row.

        @return row_heigh: float, the height of each row in the background.
        """
        try:
            row_height = area.height / float(self.num_rows)
        except ZeroDivisionError:
            print("Background object doesn't have any rows.")
            raise
        else:
            return row_height

    def get_col_width(self, area):
        """
        Gets the width of each column.

        @return col_width: float, the width of each column in the background.
        """
        try:
            col_width = area.width / float(self.num_columns)
        except ZeroDivisionError:
            print("Background object doesn't have any columns.")
            raise
        else:
            return col_width

    def set_line_color(self, color):
        """
        Sets the @color of the grid lines.

        @param color: a 4-tuple of floats, a color in the format (red, green,
                      blue, alpha).
        """
        self.line_color = color

    def set_background_color(self, color):
        """
        Sets the color the background of all cells should be painted.

        @param color: triple of floats, color in the format (red, green, blue).
        """
        self.bg_color = color

    def draw(self, ctx, area, vgrid=False, hgrid=False):
        """
        Draws the content of the Background: the background color and the
        vertical and horizontal lines between the cells, if applicable.

        @param ctx: a Cairo context.
        @param area: a GtkAllocation object, representing the whole area being
                     considered for the drawing.
        @param vgrid: bool, wheter or not the vertical lines of the grid
                      will be drawn. Default = False.
        @param hgrid: bool, wheter or not the horizontal lines of the grid
                      will be drawn. Default = False.
        """
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

    def highlight_cell(self, ctx, row, col, area, color):
        """
        Highlights the background of a grid cell given by @row, @col using
        @color. The grid total area is given by @area.

        @param ctx: a Cairo context.
        @param row: integer, the row index of the cell to be highlighted.
        @param col: integer, the col index of the cell to be highlighted.
        @param area: a GtkAllocation object, representing the whole area being
                     considered for the drawing (not only this cell).
        @param color: a 4-tuple of floats, a color in the format (red, green,
                      blue, alpha).
        """
        if row >= self.num_rows or row < 0 or \
           col >= self.num_columns or col < 0:
            raise ValueError("Cell is out of index!")
        col_width = self.get_col_width(area)
        row_height = self.get_row_height(area)
        ctx.set_source_rgba(color[0], color[1], color[2], color[3])
        ctx.rectangle(col * col_width, row * row_height, col_width, row_height)
        ctx.fill()
