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


class TagContextMenu(gtk.Menu):
    """Context menu fo the tag i the sidebar"""

    def __init__(self, req, vmanager, tag=None):
        self.__gobject_init__()
        gtk.Menu.__init__(self)
        self.req = req
        self.vmanager = vmanager
        self.tag = tag
        # Build up the menu
        self.set_tag(tag)
        self.__build_menu()

    def __build_menu(self):
        """Build up the widget"""
        # Reset the widget
        for i in self:
            self.remove(i)
            i.destroy()
        if self.tag is not None:
            # Color chooser FIXME: SHOULD BECOME A COLOR PICKER
            self.mi_cc = gtk.MenuItem()
            self.mi_cc.set_label(_("Edit Tag..."))
            self.append(self.mi_cc)
            self.mi_cc.connect('activate', self.on_mi_cc_activate)
            if self.tag.is_search_tag():
                self.mi_del = gtk.MenuItem()
                self.mi_del.set_label(_("Delete"))
                self.append(self.mi_del)
                self.mi_del.connect('activate', self.on_mi_del_activate)
        # Make it visible
        self.show_all()

    ### PUBLIC API ############################################################
    def set_tag(self, tag):
        """Update the context menu items using the tag attributes."""
        self.tag = tag
        self.__build_menu()

    ### CALLBACKS #############################################################
    def on_mi_cc_activate(self, widget):
        """Callback: show the tag editor upon request"""
        self.vmanager.open_tag_editor(self.tag)

    def on_mi_del_activate(self, widget):
        """ delete a selected search """
        self.req.remove_tag(self.tag.get_name())
