# -*- coding: utf-8 -*-
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

import os

from gi.repository import Gtk

from GTG.core.dirs import UI_DIR
from GTG.gtk.general_preferences import GeneralPreferences


class Preferences(object):
    """Preferences is a framework for diplaying and switching
    between indivitual parts of preferences: general, plugins
    and synchronisation. These will be accessed via get_ui() method"""

    PREFERENCES_UI_FILE = os.path.join(UI_DIR, "preferences.ui")

    def __init__(self, req, vmanager):
        self.req = req
        self.config = self.req.get_config('browser')
        builder = Gtk.Builder()
        builder.add_from_file(self.PREFERENCES_UI_FILE)

        self.window = builder.get_object("Preferences")

        builder.connect_signals(self)

        self.headerbar = builder.get_object("right_header_bar")
        self.stack = builder.get_object("stack")

        self.pages = {}
        self.add_page(GeneralPreferences(req, vmanager))

        self.on_sidebar_change(self.stack)

    def activate(self):
        """ Activate the preferences window."""
        self.pages['general'].activate()
        self.window.show()

    def on_close(self, widget, data=None):
        """ Close the preferences dialog."""
        self.window.hide()
        return True

    def add_page(self, page):
        '''add_page adds a titled child to the main stack.
        All children are added using this function from __init__'''
        page_name = page.get_name()
        self.pages[page_name] = page
        self.stack.add_titled(page.get_ui(), page_name, page.get_title())

    def on_sidebar_change(self, widget, data=None):
        '''Setting the correct headerbar title based on
        visible child of stack'''
        visible_page = self.pages[self.stack.get_visible_child_name()]
        self.headerbar.set_title(visible_page.get_title())
