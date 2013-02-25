# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 - Lionel Dricot & Bertrand Rousseau
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

#=== IMPORT ===================================================================

# system imports
import pygtk
pygtk.require('2.0')
import gobject
import glib
import gtk
import cairo
from GTG.tools.logger import Log

#=== MAIN CLASS ===============================================================


class CellRendererTags(gtk.GenericCellRenderer):
    __gproperties__ = {
        'tag_list': (gobject.TYPE_PYOBJECT,
                     "Tag list", "A list of tags", gobject.PARAM_READWRITE),
        'tag': (gobject.TYPE_PYOBJECT, "Tag",
                "Tag", gobject.PARAM_READWRITE),
    }

    # Private methods
    def __roundedrec(self, context, x, y, w, h, r=10):
        "Draw a rounded rectangle"
        #   A****BQ
        #  H      C
        #  *      *
        #  G      D
        #   F****E

        context.move_to(x + r, y)                          # Move to A
        context.line_to(
            x + w - r, y)                        # Straight line to B
        # Curve to C, Control points are both at Q
        context.curve_to(x + w, y, x + w, y, x + w, y + r)
        context.line_to(x + w, y + h - r)                      # Move to D
        context.curve_to(
            x + w, y + h, x + w, y + h, x + w - r, y + h)  # Curve to E
        context.line_to(x + r, y + h)                        # Line to F
        context.curve_to(x, y + h, x, y + h, x, y + h - r)       # Curve to G
        context.line_to(x, y + r)                          # Line to H
        context.curve_to(x, y, x, y, x + r, y)             # Curve to A
        return

    def __count_viewable_tags(self):

        count = 0

        if self.tag_list is not None:
            for my_tag in self.tag_list:
                my_tag_color = my_tag.get_attribute("color")
                my_tag_icon = my_tag.get_attribute("icon")
                if my_tag_color or my_tag_icon:
                    count = count + 1
        elif self.tag is not None:
            count = 1
        else:
            count = 0

        return count

    # Class methods
    def __init__(self):
        self.__gobject_init__()
        self.tag_list = None
        self.tag = None
        self.xpad = 1
        self.ypad = 1
        self.PADDING = 1

    def do_set_property(self, pspec, value):
        if pspec.name == "tag-list":
            self.tag_list = value
        else:
            setattr(self, pspec.name, value)

    def do_get_property(self, pspec):
        if pspec.name == "tag-list":
            return self.tag_list
        else:
            return getattr(self, pspec.name)

    def on_render(self, window, widget, background_area, cell_area,
                  expose_area, flags):

        vw_tags = self.__count_viewable_tags()
        count = 0

        # Select source
        if self.tag_list is not None:
            tags = self.tag_list
        elif self.tag is not None:
            tags = [self.tag]
        else:
            return

        # Drawing context
        cr = window.cairo_create()
        gdkcontext = gtk.gdk.CairoContext(cr)
        gdkcontext.set_antialias(cairo.ANTIALIAS_NONE)

        # Coordinates of the origin point
        x_align = self.get_property("xalign")
        y_align = self.get_property("yalign")
        padding = self.PADDING
        orig_x = cell_area.x + int((cell_area.width - 16 * vw_tags -
                                    padding * 2 * (vw_tags - 1)) * x_align)
        orig_y = cell_area.y + int((cell_area.height - 16) * y_align)

        # We draw the icons & squares
        for my_tag in tags:

            my_tag_icon = my_tag.get_attribute("icon")
            my_tag_color = my_tag.get_attribute("color")

            rect_x = orig_x + self.PADDING * 2 * count + 16 * count
            rect_y = orig_y

            if my_tag_icon:
                try:
                    pixbuf = gtk.icon_theme_get_default().load_icon(
                        my_tag_icon, 16, 0)
                    gdkcontext.set_source_pixbuf(pixbuf, rect_x, rect_y)
                    gdkcontext.paint()
                    count = count + 1
                except glib.GError:
                    # In some rare cases an icon could not be found
                    # (e.g. wrong set icon path, missing icon)
                    # Raising an exception breaks UI and signal catcher badly
                    Log.error("Can't load icon '%s'" % my_tag_icon)

            elif my_tag_color:

                # Draw rounded rectangle
                my_color = gtk.gdk.color_parse(my_tag_color)
                gdkcontext.set_source_color(my_color)
                self.__roundedrec(gdkcontext, rect_x, rect_y, 16, 16, 8)
                gdkcontext.fill()
                count = count + 1

                # Outer line
                gdkcontext.set_source_rgba(0, 0, 0, 0.20)
                gdkcontext.set_line_width(1.0)
                self.__roundedrec(gdkcontext, rect_x, rect_y, 16, 16, 8)
                gdkcontext.stroke()

        if self.tag and my_tag:

            my_tag_icon = my_tag.get_attribute("icon")
            my_tag_color = my_tag.get_attribute("color")

            if not my_tag_icon and not my_tag_color:
                # Draw rounded rectangle
                gdkcontext.set_source_rgba(0.95, 0.95, 0.95, 1)
                self.__roundedrec(gdkcontext, rect_x, rect_y, 16, 16, 8)
                gdkcontext.fill()

                # Outer line
                gdkcontext.set_source_rgba(0, 0, 0, 0.20)
                gdkcontext.set_line_width(1.0)
                self.__roundedrec(gdkcontext, rect_x, rect_y, 16, 16, 8)
                gdkcontext.stroke()

    def on_get_size(self, widget, cell_area=None):

        count = self.__count_viewable_tags()

        if count != 0:
            return (self.xpad, self.ypad,
                    self.xpad * 2 + 16 * count + 2 * count * self.PADDING,
                    16 + 2 * self.ypad)
        else:
            return (self.xpad, self.ypad, self.xpad * 2, self.ypad * 2)

gobject.type_register(CellRendererTags)
