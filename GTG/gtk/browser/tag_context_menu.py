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
import gtk

from GTG import _


class TagContextMenu(gtk.Menu):

    def __init__(self, req, vmanager, tag=None):
        self.__gobject_init__()
        self.req = req
        self.vmanager = vmanager
        self.tag = tag
        # Build up the menu
        self.__build_menu()
        self.set_tag(tag)
        # Make it visible
        self.show_all()

    def __build_menu(self):
        # Color chooser FIXME: SHOULD BECOME A COLOR PICKER
        self.mi_cc = gtk.MenuItem()
        self.mi_cc.set_label(_("Edit Tag..."))
        self.append(self.mi_cc)
        # Set the callbacks
        self.mi_cc.connect('activate', self.on_mi_cc_activate)

    ### PUBLIC API ###

    def set_tag(self, tag):
        """Update the context menu items using the tag attributes."""
        self.tag = tag

    ### CALLBACKS ###

    def on_mi_cc_activate(self, widget):
        self.vmanager.open_tag_editor(self.tag)

