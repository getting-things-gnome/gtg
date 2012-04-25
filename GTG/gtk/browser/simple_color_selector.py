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

DEFAULT_PALETTE = [
  ["#EF2929", "#AD7FA8", "#729FCF", "#8AE234", "#E9B96E", "#FCAF3E", "#FCE94F"],
  ["#CC0000", "#75507B", "#3465A4", "#73D216", "#C17D11", "#F57900", "#EDD400"],
  ["#A40000", "#5C3566", "#204A87", "#4E9A06", "#8F5902", "#CE5C00", "#C4A000"],
  ["#FFFFFF", "#D3D7CF", "#BABDB6", "#888A85", "#555753", "#2E3436", "#000000"],
]

class SimpleColorSelectorPaletteItem(gtk.DrawingArea):

    def __init__(self, color="#FFFFFF"):
        self.__gobject_init__()
        self.color = color
        self.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        # Connect callbacks
        self.connect("expose_event", self.on_expose)
        self.connect("configure_event", self.on_configure)

    def __draw(self):
        alloc_x, alloc_y, alloc_w, alloc_h = self.get_allocation()
        # Drawing context
        cr         = self.window.cairo_create()
        gdkcontext = gtk.gdk.CairoContext(cr)
        gdkcontext.set_antialias(cairo.ANTIALIAS_NONE)

        # Draw rounded rectangle
        my_color = gtk.gdk.color_parse(self.color)
        gdkcontext.set_source_color(my_color)
        gdkcontext.rectangle(0, 0, alloc_w, alloc_h)
        gdkcontext.fill()

        # Outer line
        gdkcontext.set_source_rgba(0, 0, 0, 0.20)
        gdkcontext.set_line_width(2.0)
        gdkcontext.rectangle(0, 0, alloc_w, alloc_h)
        gdkcontext.stroke()

    def on_expose(self, widget, params):
        self.__draw()

    def on_configure(self, widget, params):
        self.__draw()

    def set_color(self, color):
        self.color = color


class SimpleColorSelectorPalette(gtk.VBox):

    BUTTON_WIDTH  = 32
    BUTTON_HEIGHT = 28

    def __init__(self, width=7, height=4):
        self.__gobject_init__()
        self.width = width
        self.height = height
        self.palette = DEFAULT_PALETTE
        self.buttons = []
        # Build up the menu
        self.set_size_request( \
            self.width*self.BUTTON_WIDTH, self.height*self.BUTTON_HEIGHT)
        self.__build_widget()
        # Connect callbacks

        # Make it visible
        self.show_all()

    def __build_widget(self):
        # Draw the palette
        self.set_spacing(4)
        for i in xrange(self.height):
            cur_hbox = gtk.HBox()
            cur_hbox.set_spacing(4)
            self.buttons.append([])
            for j in xrange(self.width):
                img = SimpleColorSelectorPaletteItem()
                img.set_color(self.palette[i][j])
                img.connect("button-press-event", self.on_color_clicked)
                self.buttons[i].append(img)
                cur_hbox.pack_start(img, expand=True, fill=True)
            self.pack_start(cur_hbox)

    def on_color_clicked(self, widget, event):
        self.emit("color-clicked", widget.color)

gobject.type_register(SimpleColorSelectorPalette)
gobject.signal_new("color-clicked", SimpleColorSelectorPalette,
                   gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_STRING,))


class SimpleColorSelector(gtk.VBox):

    def __init__(self):
        self.__gobject_init__()
        self.sel_color = None
        # Build up the menu
        self.__build_widget()
        self.__set_default_values()
        # Make it visible
        self.show_all()

    def __build_widget(self):
        self.colsel_pal = SimpleColorSelectorPalette()
        self.colsel_pal.connect("color-clicked", self.on_color_selected)
        self.add(self.colsel_pal)
        # Draw the palette
        
        # Connect the callbacks

    def __set_default_values(self):
        pass

    ### handlers ###
    def on_color_selected(self, widget, color):
        self.sel_color = color
        self.emit("color-selected", self.sel_color)

    ### public API ###

    def set_palette(self, pal):
        self.palette = pal


gobject.type_register(SimpleColorSelector)
gobject.signal_new("color-selected", SimpleColorSelector,
                   gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_STRING,))
