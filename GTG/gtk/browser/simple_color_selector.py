# -*- coding: utf-8 -*-
# pylint: disable-msg=W0201
# -----------------------------------------------------------------------------
# Getting Things Gnome! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2009 - Lionel Dricot & Bertrand Rousseau
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

import pygtk
pygtk.require('2.0')
import gobject
import gtk
import math
import cairo

from GTG import _
from GTG.gtk.browser import GnomeConfig

#FIXME: rearrange colors by neighbouring tone
#FIXME: use a more saturated palette
DEFAULT_PALETTE = [
  ["#EF2929", "#AD7FA8", "#729FCF", "#8AE234", "#E9B96E", "#FCAF3E", "#FCE94F"],
#  ["#CC0000", "#75507B", "#3465A4", "#73D216", "#C17D11", "#F57900", "#EDD400"],
  ["#A40000", "#5C3566", "#204A87", "#4E9A06", "#8F5902", "#CE5C00", "#C4A000"],
  ["#FFFFFF", "#D3D7CF", "#BABDB6", "#888A85", "#555753", "#2E3436", "#000000"],
]

class SimpleColorSelectorPaletteItem(gtk.DrawingArea):

    def __init__(self, color="#FFFFFF"):
        self.__gobject_init__()
        self.color = color
        self.selected = False
        self.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        # Connect callbacks
        self.connect("expose_event", self.on_expose)
        self.connect("configure_event", self.on_configure)

    def __draw(self):
        alloc_x, alloc_y, alloc_w, alloc_h = self.get_allocation()
        # Drawing context
        cr         = self.window.cairo_create()
        gdkcontext = gtk.gdk.CairoContext(cr)

        # Draw rounded rectangle
        my_color = gtk.gdk.color_parse(self.color)
        gdkcontext.set_source_color(my_color)
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
            x = math.floor((alloc_w-size)/2)
            y = math.floor((alloc_h-size)/2)
            gdkcontext.set_source_rgba(255, 255, 255, 0.80)
            gdkcontext.arc(alloc_w/2, alloc_h/2, size/2 + 3, 0, 2*math.pi)
            gdkcontext.fill()
            gdkcontext.set_line_width(1.0)
            gdkcontext.set_source_rgba(0, 0, 0, 0.20)
            gdkcontext.arc(alloc_w/2, alloc_h/2, size/2 + 3, 0, 2*math.pi)
            gdkcontext.stroke()
            gdkcontext.set_source_rgba(0, 0, 0, 0.50)
            gdkcontext.set_line_width(3.0)
            gdkcontext.move_to(x       , y+size/2)
            gdkcontext.line_to(x+size/2, y+size)
            gdkcontext.line_to(x+size  , y)
            gdkcontext.stroke()

    def on_expose(self, widget, params):
        self.__draw()

    def on_configure(self, widget, params):
        self.__draw()

    def set_color(self, color):
        self.color = color

    def set_selected(self, sel):
        self.selected = sel
        self.queue_draw()


class SimpleColorSelectorPalette(gtk.VBox):

    BUTTON_WIDTH  = 36
    BUTTON_HEIGHT = 24

    def __init__(self, width=7, height=3):
        self.__gobject_init__()
        self.width = width
        self.height = height
        self.palette = DEFAULT_PALETTE
        self.buttons = {}
        self.selected_col = None
        # Build up the widget
        self.__build_widget()
        # Make it visible
        self.show_all()

    def __build_widget(self):
        # Draw the palette
        self.set_spacing(4)
        for i in xrange(self.height):
            cur_hbox = gtk.HBox()
            cur_hbox.set_spacing(4)
            for j in xrange(self.width):
                img = SimpleColorSelectorPaletteItem()
                img.set_size_request( \
                    self.BUTTON_WIDTH, self.BUTTON_HEIGHT)
                img.set_color(self.palette[i][j])
                img.connect("button-press-event", self.on_color_clicked)
                self.buttons[self.palette[i][j]] = img
                cur_hbox.pack_start(img, expand=False, fill=False)
            self.pack_start(cur_hbox)

    # Handlers
    def on_color_clicked(self, widget, event):
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
        self.emit("color-clicked", widget.color)

    # public IF

    def has_color(self, col):
        return col in self.buttons.keys()

    def set_selected_color(self, col):
        if self.has_color(col):
            self.buttons[col].set_selected(True)
            self.selected_col = self.buttons[col]

    def unselect_color(self):
        if self.selected_col is not None:
            self.selected_col.set_selected(False)
            self.selected_col = None


gobject.type_register(SimpleColorSelectorPalette)
gobject.signal_new("color-clicked", SimpleColorSelectorPalette,
                   gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_STRING,))


class SimpleColorSelector(gtk.VBox):

    def __init__(self):
        self.__gobject_init__()
        self.sel_color = None
        # Build up the menu
        self.__build_widget()
        # Make it visible
        self.show_all()

    def __build_widget(self):
        self.set_spacing(10)
        self.colsel_pal = SimpleColorSelectorPalette()
        self.colsel_pal.connect("color-clicked", self.on_pal_color_selected)
        self.pack_start(self.colsel_pal)
        self.colsel_cust = gtk.Button(_("Select A Custom Color"))
        self.colsel_cust.connect("clicked", self.on_cust_color_selected)
        self.pack_start(self.colsel_cust)

    ### handlers ###
    def on_pal_color_selected(self, widget, color):
        self.sel_color = color
        self.emit("color-selected", self.sel_color)

    def on_cust_color_selected(self, widget):
        self.colsel_pal.unselect_color()
        color_dialog = gtk.ColorSelectionDialog(_('Choose a color'))
        colorsel = color_dialog.colorsel
        # Get previous color
        color = self.sel_color
        if color is not None:
            colorspec = gtk.gdk.color_parse(color)
            colorsel.set_previous_color(colorspec)
            colorsel.set_current_color(colorspec)
        response = color_dialog.run()
        new_color = colorsel.get_current_color()
        # Check response_id and set color if required
        if response == gtk.RESPONSE_OK and new_color:
            strcolor = gtk.color_selection_palette_to_string([new_color])
            # Save the change and notify
            self.sel_color = strcolor
            self.emit("color-selected", self.sel_color)
        # Clean up
        color_dialog.destroy()

    ### public API ###

    def set_selected_color(self, col):
        self.sel_color = col
        if self.colsel_pal.has_color(col):
            self.colsel_pal.set_selected_color(col)
        else:
            # insert as custom color
            pass


gobject.type_register(SimpleColorSelector)
gobject.signal_new("color-selected", SimpleColorSelector,
                   gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_STRING,))
