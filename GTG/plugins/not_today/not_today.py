# -*- coding: utf-8 -*-
# Copyright (c) 2012 - Lionel Dricot <lionel@ploum.net>

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

import gtk
from GTG.tools.dates import Date
from GTG import _


class notToday:

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

    def mark_not_today(self, button):
        start_date = Date.parse("tomorrow")
        for tid in self.plugin_api.get_selected():
            task = self.req.get_task(tid)
            task.set_start_date(start_date)

    def selection_changed(self, selection):
        if selection.count_selected_rows() > 0:
            self.tb_button.set_sensitive(True)
        else:
            self.tb_button.set_sensitive(False)

## GTK FUNCTIONS ##############################################################
    def _init_gtk(self):
        """ Initialize all the GTK widgets """

        self.tb_button = gtk.ToolButton()
        self.tb_button.set_sensitive(False)
        self.tb_button.set_icon_name("document-revert")
        self.tb_button.set_is_important(True)
        self.tb_button.set_label(_("Do it tomorrow"))
        self.tb_button.connect('clicked', self.mark_not_today)
        self.tb_button.show()
        self.plugin_api.add_toolbar_item(self.tb_button)

    def _gtk_deactivate(self):
        """ Remove Toolbar Button """
        if self.tb_button:
            self.plugin_api.remove_toolbar_item(self.tb_button)
            self.tb_button = False
