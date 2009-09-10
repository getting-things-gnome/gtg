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
#import pygtk
import os
import sys
from threading import Thread
#import gobject
#import logging
# IMPORTANT This add's the plugin's path to python sys path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+'/pyrtm')
import syncengine


class RtmSync:
    plugin_api = None
    worker_thread = None
    sync_engine = None
    progressbar = None
    progressbar_percent =0
    status = None
    lbl_dialog = None

    def __init__(self):
        self.menu_item = gtk.MenuItem("Synchronize with RTM")
        self.menu_item.connect('activate', self.onTesteMenu)
        self.tb_button = gtk.ToolButton(gtk.STOCK_INFO)
        self.tb_button.set_label("Synchronize RTM")
        self.tb_button.connect('clicked', self.onTbButton)

        # plugin engine methods
    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        # add a menu item to the menu bar
        plugin_api.add_menu_item(self.menu_item)

        # saves the separator's index to later remove it
        self.separator = plugin_api.add_toolbar_item(gtk.SeparatorToolItem())
        # add a item(button) to the ToolBar
        plugin_api.add_toolbar_item(self.tb_button)

    def deactivate(self, plugin_api):
        plugin_api.remove_menu_item(self.menu_item)
        plugin_api.remove_toolbar_item(self.tb_button)
        plugin_api.remove_toolbar_item(None, self.separator)

    #load a dialog with a String
    def loadDialogToken(self, msg):
        path = os.path.dirname(os.path.abspath(__file__))
        glade_file = os.path.join(path, "gtk.glade")
        wTree = gtk.glade.XML(glade_file, "dialogtoken")
        self.dialog = wTree.get_widget("dialogtoken")
        btn_ok = wTree.get_widget("btn_ok")
        self.lbl_dialog = wTree.get_widget("lbl_dialog")
        self.lbl_dialog.set_text(msg)
        self.dialog.connect("delete_event", self.close_dialog)
        btn_ok.connect("clicked", self.checkLogin)
        self.dialog.show_all()

    def loadDialogSync(self, msg):
        path = os.path.dirname(os.path.abspath(__file__))
        glade_file = os.path.join(path, "gtk.glade")
        wTree = gtk.glade.XML(glade_file, "dialogsync")
        self.dialog = wTree.get_widget("dialogsync")
        btn_ok = wTree.get_widget("btn_ok")
        self.lbl_dialog = wTree.get_widget("lbl_dialog")
        self.lbl_dialog.set_text(msg)
        self.progressbar = wTree.get_widget("progressbar")
        self.dialog.connect("delete_event", self.close_dialog)
        btn_ok.connect("clicked", self.close_dialog)
        self.dialog.show_all()

    def close_dialog(self, widget, data=None):
        self.dialog.destroy()
        return True

    def set_progressbar(self):
        self.progressbar.set_fraction(self.progressbar_percent)

    def set_status(self):
        self.lbl_dialog.set_text(self.status)

    def onTesteMenu(self, widget):
        self.onTbButton(widget)

    def lauchSynchronization(self):
        self.loadDialogSync("Synchronization started")
        self.worker_thread = Thread(target = \
                                self.sync_engine.synchronize).start()

    def onTbButton(self, widget):
        self.sync_engine=syncengine.SyncEngine(self)
        self.checkLogin(widget)

    def checkLogin(self, widget):
        if hasattr(self, 'dialog'):
            self.dialog.destroy()
        if self.sync_engine.rtmLogin() == False:
            self.loadDialogToken("Please authenticate to Remember \
                The Milk in the browser that is being opened now. \
                When done, press OK")
        else:
            self.lauchSynchronization()
