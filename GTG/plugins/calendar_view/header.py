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
import cairo

from GTG.plugins.calendar_view.background import Background
from GTG.plugins.calendar_view.utils import center_text_on_rect


class Header(Gtk.DrawingArea):
    """ This class represents a header to display the dates of a View. """
    def __init__(self, cols=7):
        super(Header, self).__init__()
        self.labels = []
        self.background = Background(1, cols)
        self.sidebar = 0
        self.highlight_cell = (None, None)

        self.connect("draw", self.draw)

    def add_configurations(self, config):
        """
        Adds the configurations to be used while drawing in this class, such as
        the colors to be used for each component, the font, etc.

        @param config: a ViewConfig object.
        """
        self.config = config

    def set_sidebar_size(self, size):
        """
        Sets the space that a sidebar would need if it was drawn.
        This is needed when the Header is above an object inside a
        ScrolledWindow and the scrollbar appears in that widget, making things
        appear disaligned if the Header does not count the sidebar space as
        well.

        @param size: int, the size of the sidebar in pixels.
        """
        self.sidebar = size

    def set_labels(self, labels):
        """
        Sets the label of each column in the header, given by @labels.
        Since each cell in header can have multiple lines of text, @labels
        should have one list corresponding to each line of content, and thus
        have the length equals the number of lines to be displayed. So @labels
        should be a list of list of strings.
        For each list that corresponds to a line of content, there is a list
        of size #cols that will correspond to the content of each column in
        that line. All the labels with the same internal index will be drawn
        in the same col.

        Ex:    labels[0][0] = 'Mon'  ...  label[0][6] = 'Sun'
               labels[1][0] = '1/1'  ...  label[1][6] = '1/7'

        will be drawn as:

               labels[x][0]  ...  labels[x][6]
                    __v_________________v__
                   |     |     |     |     |
        labels[0]  | Mon | Tue | ... | Sun |
        labels[1]  | 1/1 | 1/2 | ... | 1/7 |
                   |_____|_____|_____|_____|

        @param labels: list of list of strings, containing the content of the
                       header, being that labels[R] contains the content of a
                       row R, and labels[0..x][C] contain the content of the
                       column C (each cell will have x rows).
        """
        self.labels = labels

    def set_line_color(self, color):
        """
        Sets the @color the grid lines should be drawn in the background.

        @param color: a 4-tuple of floats, a color in the format (red, green,
                      blue, alpha).
        """
        self.background.set_line_color(color)

    def set_background_color(self, color):
        """
        Sets the color the background of all cells should be painted.

        @param color: triple of floats, color in the format (red, green, blue).
        """
        self.background.set_background_color(color)

    def get_height(self):
        """
        Gets the height of each printable line in header. This depends directly
        on the labels list passed in set_labels.

        @return line_height: float, the height of each printable line.
        """
        try:
            line_height = self.get_allocation().height / len(self.labels[0])
        except ZeroDivisionError:
            print("List of labels in object Header not initialized!")
            raise
        else:
            return line_height

    def get_col_width(self):
        """
        Gets the width of each column.

        @return col_width: float, the width of each column in the header.
        """
        try:
            col_width = (self.get_allocation().width - self.sidebar) \
                / float(len(self.labels))
        except ZeroDivisionError:
            print("List of labels in object Header not initialized!")
            raise
        else:
            return col_width

    def set_highlight_cell(self, row, col):
        """
        Sets a cell given by @row, @col to be highlighted. Only one cell of the
        Header can be highlighted at a time.

        @param row: integer, the row index of the cell to be highlighted.
        @param col: integer, the col index of the cell to be highlighted.
        """
        if row == 0 and 0 <= col < self.background.num_columns:
            self.highlight_cell = (row, col)
        else:
            self.highlight_cell = (None, None)

    def draw(self, widget, ctx):
        """
        Draws the header according to the labels.

        @param ctx: a Cairo context.
        """
        alloc = self.get_allocation()
        alloc.width -= self.sidebar
        # FIXME: look deeper into why x and y are not starting at 0.
        # This has to do with spacing in vbox (glade file). Temporary fix:
        alloc.x = 0
        alloc.y = 0

        ctx.set_line_width(self.config.line_width)
        self.set_line_color(self.config.line_color)
        self.set_background_color(self.config.bg_color)
        self.background.draw(ctx, alloc, vgrid=False, hgrid=True)

        row, col = self.highlight_cell
        if row is not None and col is not None:
            self.background.highlight_cell(ctx, row, col, alloc,
                                           self.config.today_cell_color)

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
