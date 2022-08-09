# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) - The GTG Team
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
# -----------------------------------------------------------------------------

"""Tag colors widget"""

from gi.repository import Gtk, Gdk, GObject


class TagPill(Gtk.DrawingArea):
    """Color pill widget for tags."""
    
    __gtype_name__ = 'TagPill'

    def __init__(self, radius: int = 5):

        super(TagPill, self).__init__()
        self.colors = [Gdk.RGBA()]
        self.colors_str = ''
        self.radius = radius
        self.set_draw_func(self.do_draw_function)


    @GObject.Property(type=str)
    def color_list(self) -> str:
        return self.colors_str


    @color_list.setter
    def set_colors(self, value) -> None:

        try:
            self.colors = []

            for color in value.split(','):
                rgba = Gdk.RGBA()
                rgba.parse(color)
                self.colors.append(rgba)

            self.set_size_request((16 + 6) * len(self.colors), 16)
            self.queue_draw()
        except AttributeError:
            self.colors = [Gdk.RGBA()]


    def draw_rect(self, context, x: int, w: int, h: int, 
                  color: Gdk.RGBA = None) -> None:
        """Draw a single color rectangle."""
        
        y = 0   # No change in Y axis
        r = self.radius
        
        if color:
            context.set_source_rgba(color.red, color.green, color.blue)
        else:
            context.set_source_rgba(0, 0, 0, 0.5)

        #   A  *  BQ
        #  H       C
        #  *       *
        #  G       D
        #   F  *  E

        context.move_to(x + r, y)          # Move to A
        context.line_to(x + w - r, y)      # Line to B

        context.curve_to(
            x + w, y,
            x + w, y,
            x + w, y + r
        )  # Curve to C
        context.line_to(x + w, y + h - r)  # Line to D

        context.curve_to(
            x + w, y + h,
            x + w, y + h,
            x + w - r, y + h
        )  # Curve to E
        context.line_to(x + r, y + h)      # Line to F

        context.curve_to(
            x, y + h,
            x, y + h,
            x, y + h - r
        )  # Curve to G
        context.line_to(x, y + r)          # Line to H

        context.curve_to(
            x, y,
            x, y,
            x + r, y
        )  # Curve to A


    def do_draw_function(self, area, context, w, h, user_data=None):
        """Drawing callback."""
        
        for i, color in enumerate(self.colors):
            x = i * (16 + 6)
            self.draw_rect(context, x, 16, h, color)
            context.fill()
