# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
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

from gi.repository import GObject, GLib, Gtk, Gdk, Graphene
from gi.repository import Pango
import gi
import cairo
gi.require_version('PangoCairo', '1.0')
# XXX: disable PEP8 checking on this line to prevent an E402 error due to
#      require_version needing to be called before the PangoCairo import


class CellRendererTags(Gtk.CellRenderer):

    SYMBOLIC_ICONS = (
        'emblem-documents-symbolic',
        'task-past-due-symbolic',
        'system-search-symbolic',
    )

    __gproperties__ = {
        'tag_list': (GObject.TYPE_PYOBJECT,
                     "Tag list", "A list of tags", GObject.ParamFlags.READWRITE),
        'tag': (GObject.TYPE_PYOBJECT, "Tag",
                "Tag", GObject.ParamFlags.READWRITE),
    }

    # Private methods
    def __roundedrec(self, context, x, y, w, h, r=10):
        "Draw a rounded rectangle"
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
    def __init__(self, config):
        super().__init__()
        self.tag_list = None
        self.tag = None
        self.xpad = 1
        self.ypad = 1
        self.PADDING = 1
        self.config = config
        self._ignore_icon_error_for = set()

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

    def do_snapshot(self, snapshot, widget, background_area, cell_area, flags):

        vw_tags = self.__count_viewable_tags()
        count = 0

        # Select source
        if self.tag_list is not None:
            tags = self.tag_list
        elif self.tag is not None:
            tags = [self.tag]
        else:
            return

        if self.config.get('dark_mode'):
            symbolic_color = Gdk.RGBA()
            symbolic_color.red = 1
            symbolic_color.green = 1
            symbolic_color.blue = 1
            symbolic_color.alpha = 0.9
        else:
            symbolic_color = Gdk.RGBA()
            symbolic_color.alpha = 1

        # Drawing context
        cell_area_graphrect = Graphene.Rect.alloc().init(
            cell_area.x, cell_area.y, cell_area.width + 64, cell_area.height
        )
        gdkcontext = snapshot.append_cairo(cell_area_graphrect)
        scale_factor = widget.get_scale_factor()
        # Don't blur border on lodpi
        if scale_factor == 1:
            gdkcontext.set_antialias(cairo.ANTIALIAS_NONE)

        # Coordinates of the origin point
        x_align = self.get_property("xalign")
        y_align = self.get_property("yalign")
        padding = self.PADDING
        orig_x = cell_area.x + int(
            (cell_area.width - 16 * vw_tags - padding * 2 * (vw_tags - 1)) * x_align)
        orig_y = cell_area.y + int(
            (cell_area.height - 16) * y_align)

        # We draw the icons & squares
        for my_tag in tags:

            my_tag_icon = my_tag.get_attribute("icon")
            my_tag_color = my_tag.get_attribute("color")

            rect_x = orig_x + self.PADDING * 2 * count + 16 * count
            rect_y = orig_y

            if my_tag_icon:
                if my_tag_icon in self.SYMBOLIC_ICONS:
                    icon_theme = Gtk.IconTheme.get_for_display(widget.get_display())

                    snapshot.save()
                    point = Graphene.Point.alloc().init(rect_x, rect_y)
                    snapshot.translate(point)

                    gicon = icon_theme.lookup_icon(
                        my_tag_icon, None, 16, scale_factor, 0, 0
                    )
                    gicon.snapshot_symbolic(snapshot, 16, 16, [symbolic_color])
                    snapshot.restore()

                    count += 1

                else:
                    layout = Pango.Layout(widget.get_pango_context())
                    layout.set_markup(my_tag_icon)

                    snapshot.save()
                    point = Graphene.Point.alloc().init(rect_x - 2, rect_y - 1)
                    snapshot.translate(point)

                    snapshot.append_layout(layout, widget.get_style_context().get_color())
                    snapshot.restore()

                    count += 1

            elif my_tag_color:

                # Draw rounded rectangle
                my_color = Gdk.RGBA()
                my_color.parse(my_tag_color)
                Gdk.cairo_set_source_rgba(gdkcontext, my_color)

                self.__roundedrec(gdkcontext, rect_x, rect_y, 16, 16, 8)
                gdkcontext.fill()
                count += 1

                # Outer line
                color = Gdk.RGBA()
                color.red, color.green, color.blue, color.alpha = 0, 0, 0, 0.20
                Gdk.cairo_set_source_rgba(gdkcontext, color)
                gdkcontext.set_line_width(1.0)
                self.__roundedrec(gdkcontext, rect_x, rect_y, 16, 16, 8)
                gdkcontext.stroke()

        if self.tag and my_tag:

            my_tag_icon = my_tag.get_attribute("icon")
            my_tag_color = my_tag.get_attribute("color")

            if not my_tag_icon and not my_tag_color:
                # Draw rounded rectangle
                color = Gdk.RGBA()
                color.red, color.blue, color.green, color.alpha = 0.95, 0.95, 0.95, 1
                Gdk.cairo_set_source_rgba(gdkcontext,color)
                self.__roundedrec(gdkcontext, rect_x, rect_y, 16, 16, 8)
                gdkcontext.fill()

                # Outer line
                color = Gdk.RGBA()
                color.alpha = 0.20
                Gdk.cairo_set_source_rgba(gdkcontext, color)
                gdkcontext.set_line_width(1.0)
                self.__roundedrec(gdkcontext, rect_x, rect_y, 16, 16, 8)
                gdkcontext.stroke()

    def do_get_preferred_width(self, widget):
        count = self.__count_viewable_tags()
        required_size = self.xpad * 2 + 16 * count + 2 * count * self.PADDING

        return required_size, required_size

    def do_get_preferred_height(self, widget):
        required_size = 16 + 2 * self.ypad
        return required_size, required_size


GObject.type_register(CellRendererTags)
