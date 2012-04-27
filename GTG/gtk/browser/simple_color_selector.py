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
  ["#EF2929", "#AD7FA8", "#729FCF", "#8AE234", "#E9B96E", "#FCAF3E", "#FCE94F", "#EEEEEC", "#888A85"],
  ["#CC0000", "#75507B", "#3465A4", "#73D216", "#C17D11", "#F57900", "#EDD400", "#D3D7CF", "#555753"],
  ["#A40000", "#5C3566", "#204A87", "#4E9A06", "#8F5902", "#CE5C00", "#C4A000", "#BABDB6", "#2E3436"],
]

BUTTON_WIDTH  = 36
BUTTON_HEIGHT = 24

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

    def get_selected(self):
        return self.selected

class SimpleColorSelectorPalette(gtk.VBox):

    def __init__(self, width=9, height=3):
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
                    BUTTON_WIDTH, BUTTON_HEIGHT)
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

    def get_color_selected(self, col):
        if self.has_color(col):
            return self.buttons[col].get_selected()
        else:
            return None

    def set_color_selected(self, col):
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


class SimpleColorSelectorPaletteCustom(gtk.VBox):

    def __init__(self, width=9, height=1):
        self.__gobject_init__()
        self.width = width
        self.height = height
        self.colors = []
        self.buttons = {}
        self.selected_col = None
        # Build up the widget
        self.__build_widget()
        # Make it visible
        self.show_all()

    def __build_widget(self):
        col_count = 0
        # Draw the palette
        self.set_spacing(4)
        for i in xrange(self.height):
            if col_count > len(self.colors)-1 or color_count > self.width:
                break
            cur_hbox = gtk.HBox()
            cur_hbox.set_spacing(4)
            for j in xrange(self.width):
                if col_count > len(self.colors)-1 or color_count > self.width:
                    break
                img = SimpleColorSelectorPaletteItem()
                img.set_size_request( \
                    BUTTON_WIDTH, BUTTON_HEIGHT)
                img.set_color(self.colors[col_count])
                img.connect("button-press-event", self.on_color_clicked)
                self.buttons[self.colors[col_count]] = img
                cur_hbox.pack_start(img, expand=False, fill=False)
                col_count = col_count + 1
            self.pack_start(cur_hbox)
        # Draw the add button
        self.add_button = gtk.Button(_('Add'))
        self.add_button.connect("clicked", self.on_color_add)
        self.pack_start(self.add_button)

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

    def on_color_add(self, widget):
        color_dialog = gtk.ColorSelectionDialog(_('Choose a color'))
        colorsel = color_dialog.colorsel
        response = color_dialog.run()
        new_color = colorsel.get_current_color()
        # Check response_id and set color if required
        if response == gtk.RESPONSE_OK and new_color:
            strcolor = gtk.color_selection_palette_to_string([new_color])
            # Add the color to the palette and notify
            print "FIXME: update custom palette"
            self.emit("color-added")
            # Select the new colro and notify
            print "FIXME: slect the color in the custom palette"
            self.selected_col = strcolor
            self.emit("color-clicked", self.selected_col)
        # Clean up
        color_dialog.destroy()

    # public IF

    def has_color(self, col):
        return col in self.buttons.keys()

    def get_color_selected(self, col):
        if self.has_color(col):
            return self.buttons[col].get_selected()
        else:
            return None

    def set_color_selected(self, col):
        if self.has_color(col):
            self.buttons[col].set_selected(True)
            self.selected_col = self.buttons[col]

    def unselect_color(self):
        if self.selected_col is not None:
            self.selected_col.set_selected(False)
            self.selected_col = None


gobject.type_register(SimpleColorSelectorPaletteCustom)
gobject.signal_new("color-clicked", SimpleColorSelectorPaletteCustom,
                   gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_STRING,))
gobject.signal_new("color-added", SimpleColorSelectorPaletteCustom,
                   gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())

class SimpleColorSelector(gtk.VBox):

    def __init__(self):
        self.__gobject_init__()
        self.sel_color = None
        self.custom_colors = []
        # Build up the menu
        self.__build_widget()
        # Make it visible
        self.show_all()

    def __build_widget(self):
        self.set_spacing(10)
        self.colsel_pal = SimpleColorSelectorPalette()
        self.colsel_pal.connect("color-clicked", self.on_colsel_pal_color_clicked)
        self.pack_start(self.colsel_pal)
        self.colsel_custcol = SimpleColorSelectorPaletteCustom()
        self.colsel_custcol.connect("color-clicked", self.on_colsel_custcol_color_clicked)
        self.colsel_custcol.connect("color-added", self.on_colsel_custcol_color_added)
        self.pack_start(self.colsel_custcol)

    ### handlers ###
    def on_colsel_pal_color_clicked(self, widget, color):
        # if we click on the palette, we can unselect a potentially slected
        # custom color
        self.colsel_custcol.unselect_color()
        # Determine if it's a selection or an de-selection
        if self.colsel_pal.get_color_selected(color) == True:
            self.sel_color = color
            self.emit("color-defined")
        else:
            self.sel_color = None
            self.emit("color-defined")

    def on_colsel_custcol_color_clicked(self, widget, color):
        # if we click on the custom colors, we can unselect a potentially slctd
        # palette color
        self.colsel_pal.unselect_color()
        # Determine if it's a selection or an de-selection
        if self.colsel_custcol.get_color_selected(color) == True:
            self.sel_color = color
        else:
            self.sel_color = None
            self.emit("color-defined")

    def on_colsel_custcol_color_added(self, widget):
        self.emit("color-added")

    ### public API ###

    def set_selected_color(self, col):
        self.sel_color = col
        if self.colsel_pal.has_color(col):
            self.colsel_pal.set_color_selected(col)
        else:
            # insert as custom color
            print "FIXME: add custom color to custom color palette"

    def get_selected_color(self):
        return self.sel_color

    def set_custom_colors(self, col_lst):
        print "FIXME: custom color definition not implement yet"

    def get_custom_colors(self):
        return self.custom_colors

gobject.type_register(SimpleColorSelector)
gobject.signal_new("color-defined", SimpleColorSelector,
                   gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
gobject.signal_new("color-added", SimpleColorSelector,
                   gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())

