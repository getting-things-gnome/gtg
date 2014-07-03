# -*- coding: utf-8 -*-
# Copyright (c) 2014 - Sara Ribeiro <sara.rmgr@gmail.com>

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

from gi.repository import Gtk
from GTG import _
from GTG.plugins.calendar_view.calendar_plugin import CalendarPlugin


class calendarView:

    def __init__(self):
        self.plugin_api = None
        self.tb_button = None

    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        self.req = self.plugin_api.get_requester()
        self._init_gtk()
        self.plugin_api.set_active_selection_changed_callback(
            self.selection_changed)

    def deactivate(self, plugin_api):
        """ Removes the gtk widgets before quitting """
        self._gtk_deactivate()

    def show_calendar(self, button):
        self.calendar = CalendarPlugin(self.req)

    def selection_changed(self, selection):
        pass
        # if selection.count_selected_rows() > 0:
        #     self.tb_button.set_sensitive(True)
        # else:
        #     self.tb_button.set_sensitive(False)

# GTK FUNCTIONS ##############################################################
    def _init_gtk(self):
        """ Initialize all the GTK widgets """

        self.tb_button = Gtk.ToolButton()
        self.tb_button.set_icon_name("x-office-calendar")  # -symbolic")
        self.tb_button.set_is_important(True)
        self.tb_button.set_label(_("View tasks in calendar"))
        self.tb_button.connect('clicked', self.show_calendar)
        self.tb_button.show()
        self.plugin_api.add_toolbar_item(self.tb_button)

    def _gtk_deactivate(self):
        """ Remove Toolbar Button """
        if self.tb_button:
            self.plugin_api.remove_toolbar_item(self.tb_button)
            self.tb_button = False
