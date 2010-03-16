# -*- coding: utf-8 -*-
# Copyright (c) 2009 - Luca Invernizzi <invernizzi.l@gmail.com>
#                    - Paulo Cabido <paulo.cabido@gmail.com> (example file)
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

import gtk
from threading import Thread

from GTG import _
from GTG.plugins.evolution_sync.syncEngine import SyncEngine

class EvolutionSync:

    def __init__(self):
        #drop down menu
        self.menu_item = gtk.MenuItem(_("Synchronize with Evolution"))
        self.menu_item.connect('activate', self.onTesteMenu)

    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        # add a menu item to the menu bar
        plugin_api.add_menu_item(self.menu_item)
        self.sync_engine = SyncEngine(self)

    def deactivate(self, plugin_api):
        plugin_api.remove_menu_item(self.menu_item)

    def onTesteMenu(self, widget):
        self.worker_thread = Thread(target = \
                                self.sync_engine.synchronize).start()

    def onTaskOpened(self, plugin_api):
        pass
