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

"""
simple_color_selector: a module defining a widget allowing to pick a color
from a palette. The widget also allows to define and add new colors.
"""

import pygtk
pygtk.require('2.0')
import gobject
import gtk
import math

from GTG import _

DEFAULT_PALETTE = [
    "#EF2929", "#AD7FA8", "#729FCF", "#8AE234", "#E9B96E",
    "#FCAF3E", "#FCE94F", "#EEEEEC", "#888A85",
    "#CC0000", "#75507B", "#3465A4", "#73D216", "#C17D11",
    "#F57900", "#EDD400", "#D3D7CF", "#555753",
    "#A40000", "#5C3566", "#204A87", "#4E9A06", "#8F5902",
    "#CE5C00", "#C4A000", "#BABDB6", "#2E3436",
]

BUTTON_WIDTH = 36
BUTTON_HEIGHT = 24


class SimpleColorSelectorPaletteItem(gtk.DrawingArea):
    """An item of the color selecctor palette"""

    def __init__(self, color=None):
        gtk.DrawingArea.__init__(self)
        self.__gobject_init__()
        self.color = color
        self.selected = False
        self.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        # Connect callbacks
        self.connect("expose_event", self.on_expose)
        self.connect("configure_event", self.on_configure)

    def __draw(self):
        """Draws the widget"""
        alloc = self.get_allocation()
        alloc_w, alloc_h = alloc[2], alloc[3]
        # Drawing context
        cr_ctxt = self.window.cairo_create()
        gdkcontext = gtk.gdk.CairoContext(cr_ctxt)

        # Draw rectangle
        if self.color is not None:
            my_color = gtk.gdk.color_parse(self.color)
            gdkcontext.set_source_color(my_color)
        else:
            gdkcontext.set_source_rgba(0, 0, 0, 0)
        gdkcontext.rectangle(0, 0, alloc_w, alloc_h)
        gdkcontext.fill()

        # Outer line
        gdkcontext.set_source_rgba(0, 0, 0, 0.30)
        gdkcontext.set_line_width(2.0)
        gdkcontext.rectangle(0, 0, alloc_w, alloc_h)
        gdkcontext.stroke()

          # If selected draw a symbol
        if(self.selected):
            size = alloc_h * 0.50 - 3
            pos_x = math.floor((alloc_w - size) / 2)
            pos_y = math.floor((alloc_h - size) / 2)
            gdkcontext.set_source_rgba(255, 255, 255, 0.80)
            gdkcontext.arc(
                alloc_w / 2, alloc_h / 2, size / 2 + 3, 0, 2 * math.pi)
            gdkcontext.fill()
            gdkcontext.set_line_width(1.0)
            gdkcontext.set_source_rgba(0, 0, 0, 0.20)
            gdkcontext.arc(
                alloc_w / 2, alloc_h / 2, size / 2 + 3, 0, 2 * math.pi)
            gdkcontext.stroke()
            gdkcontext.set_source_rgba(0, 0, 0, 0.50)
            gdkcontext.set_line_width(3.0)
            gdkcontext.move_to(pos_x, pos_y + size / 2)
            gdkcontext.line_to(pos_x + size / 2, pos_y + size)
            gdkcontext.line_to(pos_x + size, pos_y)
            gdkcontext.stroke()

    ### callbacks ###
    def on_expose(self, widget, params):
        """Callback: redraws the widget when it is exposed"""
        self.__draw()

    def on_configure(self, widget, params):
        """Callback: redraws the widget when it is exposed"""
        self.__draw()

    ### PUBLIC IF ###
    def set_color(self, color):
        """Defines the widget color"""
        self.color = color

    def set_selected(self, sel):
        """Toggle the selected state of the widget"""
        self.selected = sel
        self.queue_draw()

    def get_selected(self):
        """Returns the selected state of the widget"""
        return self.selected


class SimpleColorSelector(gtk.VBox):
    """Widget displaying a palette of colors, possibly with a button allowing
     to define new colors."""

    def __init__(self, width=9, colors=None, custom_colors=None):
        gtk.VBox.__init__(self)
        self.__gobject_init__()
        self.width = width
        # widget model
        if colors is None:
            self.colors = DEFAULT_PALETTE
        else:
            self.colors = colors
        if custom_colors is None:
            self.custom_colors = []
        else:
            self.custom_colors = custom_colors
        self.buttons = []
        self.cc_buttons = []
        self.buttons_lookup = {}
        self.selected_col = None
        # Build up the widget
        self.palette = None
        self.custom_palette = None
        self.__build_palette()
        self.__build_custom_palette()
        # Show toplevel
        self.show()

    def __reset_palette(self):
        """Destroy existing widget and reset model for base palette color"""
        if self.palette is not None:
            if self.selected_col is not None and  \
                    self.selected_col.color in self.colors:
                self.selected_col = None
            for button in self.buttons:
                self.buttons_lookup.pop(button.color)
            self.buttons = []
            self.palette.destroy()

    def __build_palette(self):
        """Draws the palette of colors"""
        self.__reset_palette()
        # (re-)create the palette widget
        self.palette = gtk.Alignment()
        self.pack_start(self.palette)
        # Draw the palette
        vbox = gtk.VBox()
        self.palette.add(vbox)
        vbox.set_spacing(4)
        for i in xrange(len(self.colors)):
            if i % self.width == 0:
                cur_hbox = gtk.HBox()
                vbox.pack_start(cur_hbox)
            # add the color box
            img = SimpleColorSelectorPaletteItem()
            img.set_size_request(
                BUTTON_WIDTH, BUTTON_HEIGHT)
            img.connect("button-press-event", self.on_color_clicked)
            img.set_color(self.colors[i])
            self.buttons_lookup[self.colors[i]] = img
            self.buttons.append(img)
            cur_hbox.pack_start(img, expand=False, fill=False)
            cur_hbox.set_spacing(4)
        # make palette visible
        self.palette.show_all()

    def __reset_custom_palette(self):
        """Destroy existing widget and reset model for custom colors"""
        if self.custom_palette is not None:
            if self.selected_col is not None and \
                    self.selected_col.color in self.custom_colors:
                self.selected_col = None
            for button in self.cc_buttons:
                if button.color is not None:
                    self.buttons_lookup.pop(button.color)
            self.cc_buttons = []
            self.custom_palette.destroy()

    def __build_custom_palette(self):
        """Draws the palette of custom colors"""
        self.__reset_custom_palette()
        # (re-)create the palette widget
        self.custom_palette = gtk.Alignment(xscale=1.0)
        self.custom_palette.set_padding(10, 0, 0, 0)
        self.pack_start(self.custom_palette)
        # Draw the previous color palette: only one line
        cc_vbox = gtk.VBox()
        self.custom_palette.add(cc_vbox)
        cc_vbox.set_spacing(4)
        cc_hbox = gtk.HBox()
        cc_vbox.pack_start(cc_hbox)
        for i in xrange(len(self.custom_colors)):
            # add the color box
            img = SimpleColorSelectorPaletteItem()
            img.set_size_request(
                BUTTON_WIDTH, BUTTON_HEIGHT)
            img.connect("button-press-event", self.on_color_clicked)
            if i < len(self.custom_colors):
                img.set_color(self.custom_colors[i])
                self.buttons_lookup[self.custom_colors[i]] = img
            cc_hbox.pack_start(img, expand=False, fill=False)
            cc_hbox.set_spacing(4)
            self.cc_buttons.append(img)
        # Draw the add button
        img = gtk.Image()
        img.set_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_BUTTON)
        self.add_button = gtk.Button()
        self.add_button.set_image(img)
        self.add_button.set_label(_("Add custom color"))
        cc_vbox.pack_start(self.add_button, expand=True, fill=True)
        self.add_button.connect("clicked", self.on_color_add)
        # hide the custom palette if no custom color is defined
        if len(self.custom_colors) == 0:
            self.custom_palette.hide()
        else:
            self.custom_palette.show_all()

    # Handlers
    def on_color_clicked(self, widget, event):
        """Callback: when a color is clicked, update the model and
        notify the parent"""
        # if re-click: unselect
        if self.selected_col == widget:
            self.selected_col.set_selected(False)
            self.selected_col = None
        else:
            # if previous selection: unselect
            if self.selected_col is not None:
                self.selected_col.set_selected(False)
            self.selected_col = widget
            self.selected_col.set_selected(True)
        self.emit("color-changed")

    def on_color_add(self, widget):
        """Callback: when adding a new color, show the color definition
        window, update the model, notifies the parent."""
        color_dialog = gtk.ColorSelectionDialog(_('Choose a color'))
        colorsel = color_dialog.colorsel
        if self.selected_col is not None:
            color = gtk.gdk.color_parse(self.selected_col.color)
            colorsel.set_current_color(color)
        response = color_dialog.run()
        new_color = colorsel.get_current_color()
        # Check response_id and set color if required
        if response == gtk.RESPONSE_OK and new_color:
            strcolor = gtk.color_selection_palette_to_string([new_color])
            # Add the color to the palette and notify
            if strcolor not in self.colors:
                self.add_custom_color(strcolor)
            # Select the new color and notify
            self.set_selected_color(strcolor)
            self.emit("color-changed")
        # Clean up
        color_dialog.destroy()

    # public IF
    def has_color(self, col):
        """Returns True if the color is already present"""
        return col in self.colors or col in self.custom_colors

    def get_custom_colors(self):
        """Return the list of custom-defined colors"""
        return self.custom_colors

    def set_custom_colors(self, custom_colors):
        """Defines the list of custom-defined colors"""
        self.custom_colors = []
        for col in custom_colors:
            if col not in self.colors:
                self.custom_colors.append(col)
        # Update the custom palette
        self.__build_custom_palette()
        # hide the custom palette if no custom color is defined
        if len(self.custom_colors) == 0:
            self.custom_palette.hide()

    def add_custom_color(self, col):
        """Add a color to the palette, at the first position"""
        if col not in self.custom_colors:
            self.custom_colors.insert(0, col)
        if len(self.custom_colors) > self.width:
            self.custom_colors.pop()
        self.__build_custom_palette()
        self.emit("color-added")

    def get_selected_color(self):
        """Return the selected state of a particular color"""
        if self.selected_col is None:
            return None
        else:
            return self.selected_col.color

    def set_selected_color(self, col):
        """Defines the selected state of a displayed color"""
        self.unselect_color()
        if self.has_color(col):
            self.buttons_lookup[col].set_selected(True)
            self.selected_col = self.buttons_lookup[col]

    def unselect_color(self):
        """Deselect all colors"""
        if self.selected_col is not None:
            self.selected_col.set_selected(False)
            self.selected_col = None


gobject.type_register(SimpleColorSelector)
gobject.signal_new("color-changed", SimpleColorSelector,
                   gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
gobject.signal_new("color-added", SimpleColorSelector,
                   gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
