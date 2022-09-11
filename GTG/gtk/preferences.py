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


@Gtk.Template(filename=os.path.join(UI_DIR, "preferences.ui"))
class Preferences(Gtk.Window):
    """Preferences  a framework for diplaying and switching
    between indivitual parts of preferences: general, plugins
    and synchronisation."""
    __gtype_name__ = 'Preferences'

    _page_stack = Gtk.Template.Child()

    def __init__(self, app):
        super().__init__()
        self.config = app.config

        self.pages = {}
        self.add_page(GeneralPreferences(app))

    def activate(self):
        """ Activate the preferences window."""
        self.pages['general'].activate()
        self.show()

    @Gtk.Template.Callback()
    def on_close(self, widget, data=None):
        """ Close the preferences dialog."""
        self.hide()
        return True

    def add_page(self, page):
        """add_page adds a titled child to the main stack.
        All children are added using this function from __init__"""
        page_name = page.get_name()
        self.pages[page_name] = page
        self._page_stack.add_titled(page, page_name, page.get_title())
