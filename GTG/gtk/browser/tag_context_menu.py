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

"""
tag_context_menu:
Implements a context (pop-up) menu for the tag item in the sidebar.
Right now it is just a void shell It is supposed to become a more generic 
sidebar context for all kind of item displayed there.
Also, it is supposed to handle more complex menus (with non-std widgets,
like a color picker)
"""

import pygtk
pygtk.require('2.0')
import gtk

from GTG import _

class TagContextMenu(gtk.Menu): # pylint: disable-msg=R0904
    """Context menu fo the tag i the sidebar"""

    def __init__(self, req, vmanager, tag=None):
        self.__gobject_init__()
        gtk.Menu.__init__(self)
        self.req = req
        self.vmanager = vmanager
        self.tag = tag
        # Build up the menu
        self.__build_menu()
        self.set_tag(tag)
        # Make it visible
        self.show_all()

    def __build_menu(self):
        """Build up the widget"""
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

    def on_mi_cc_activate(self, widget): # pylint: disable-msg=W0613
        """Callback: show the tag editor upon request"""
        self.vmanager.open_tag_editor(self.tag)
