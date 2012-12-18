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

class notToday:

    def __init__(self):
        self.plugin_api = None
        self.menu_entry = None
        self.tb_button = None

    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        self._init_gtk()
        self.plugin_api.set_active_selection_changed_callback(self.selection_changed)

    def deactivate(self, plugin_api): # pylint: disable-msg=W0613
        """ Removes the gtk widgets before quitting """
        self._gtk_deactivate()
        
        
    def mark_not_today(self,button):
        print "now we need to select tasks:"
        print self.plugin_api.get_selected()
        
    def selection_changed(self,selection):
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
        self.tb_button.set_label("Do it tomorrow")
        self.tb_button.connect('clicked', self.mark_not_today)
        self.tb_button.show()
        self.plugin_api.add_toolbar_item(self.tb_button)

      

    def _gtk_deactivate(self):
        """ Remove Toolbar Button and Menu item for this plugin """
        if self.menu_entry:
            self.plugin_api.remove_menu_item(self.menu_item)
            self.menu_entry = False

        if self.toolbar_entry:
            self.plugin_api.remove_toolbar_item(self.tb_button)
            self.toolbar_entry = False
