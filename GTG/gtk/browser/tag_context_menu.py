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

from GTG import _
from GTG.gtk.browser import GnomeConfig

class TagContextMenu(gtk.Menu):

    def __init__(self, req, tag=None):
        self.__gobject_init__()
        self.req = req
        self.tag = tag
        # Build up the menu
        self.__build_menu()
        self.set_tag(tag)
        # Make it visible
        self.show_all()

    def __build_menu(self):
        # Color chooser FIXME: SHOULD BECOME A COLOR PICKER
        self.mi_cc = gtk.MenuItem()
        self.mi_cc.set_label(_("Set color..."))
        self.append(self.mi_cc)
        # Don't display in work view mode
        self.mi_wv = gtk.CheckMenuItem()
        self.mi_wv.set_label(GnomeConfig.TAG_IN_WORKVIEW_TOGG)
        self.append(self.mi_wv)
        # Set the callbacks
        self.mi_cc.connect('activate', self.on_mi_cc_activate)
        self.mi_wv_toggle_hid = self.mi_wv.connect('activate', self.on_mi_wv_activate)

    def __set_default_values(self):
        # Don't set "Hide in workview" as active
        self.mi_wv.set_active(False)

    def __disable_all(self):
        pass

    def __enable_all(self):
        pass

    ### PUBLIC API ###

    def set_tag(self, tag):
        """Update the context menu items using the tag attributes."""
        # set_active emit the 'toggle' signal, so we have to disable the handler
        # when we update programmatically
        self.mi_wv.handler_block(self.mi_wv_toggle_hid)
        if tag is None:
            self.tag = None
            self.__set_default_values()
            self.__disable_all()
        else:
            self.tag = tag
            self.__enable_all()
            is_hidden_in_wv = (self.tag.get_attribute("nonworkview") == "True")
            self.mi_wv.set_active(is_hidden_in_wv)
        self.mi_wv.handler_unblock(self.mi_wv_toggle_hid)

    ### CALLBACKS ###

    def on_mi_wv_activate(self, widget):
        """Toggle the nonworkview attribute of the tag, update the view"""
        is_hidden_in_wv = not (self.tag.get_attribute("nonworkview") == "True")
        self.tag.set_attribute("nonworkview", str(is_hidden_in_wv))

    def on_mi_cc_activate(self, widget):
        color_dialog = gtk.ColorSelectionDialog('Choose color')
        colorsel = color_dialog.colorsel

        # Get previous color
        color = self.tag.get_attribute("color")
        if color is not None:
            colorspec = gtk.gdk.color_parse(color)
            colorsel.set_previous_color(colorspec)
            colorsel.set_current_color(colorspec)
        response = color_dialog.run()
        new_color = colorsel.get_current_color()
        
        # Check response_id and set color if required
        if response == gtk.RESPONSE_OK and new_color:
            strcolor = gtk.color_selection_palette_to_string([new_color])
            self.tag.set_attribute("color", strcolor)
        color_dialog.destroy()
