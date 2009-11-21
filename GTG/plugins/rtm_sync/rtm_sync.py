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
import gobject
#import gobject
#import logging
from GTG import _
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

    def purgeDialog(self):
        self.showDialog(None)

    def showDialog(self, dialog = None):
        if hasattr(self, 'dialog') and self.dialog != None:
            self.dialog.destroy()
        self.dialog = dialog

    def __init__(self):
        #Icons!
        self.plugin_path = os.path.dirname(os.path.abspath(__file__))
        icons_subpath = "icons/hicolor/16x16/rtm_image.png"
        rtm_image_path = os.path.join(self.plugin_path, icons_subpath)
        pixbug_rtm_toolbar = gtk.gdk.\
            pixbuf_new_from_file_at_size(rtm_image_path, 16, 16)
        pixbug_rtm_menu = gtk.gdk.\
            pixbuf_new_from_file_at_size(rtm_image_path, 16, 16)
        rtm_toolbar_image = gtk.Image()
        rtm_menu_image = gtk.Image()
        rtm_toolbar_image.set_from_pixbuf(pixbug_rtm_toolbar)
        rtm_menu_image.set_from_pixbuf(pixbug_rtm_menu)
        rtm_toolbar_image.show()
        rtm_menu_image.show()

        #drop down menu
        self.menu_item = gtk.ImageMenuItem(_("Synchronize with RTM"))
        self.menu_item.connect('activate', self.onTesteMenu)
        self.menu_item.set_image(rtm_menu_image)

        #toolbar button
        self.tb_button = gtk.ToolButton(rtm_toolbar_image)
        self.tb_button.set_label(_("Synchronize with RTM"))
        self.tb_button.connect('clicked', self.onTbButton)
        self.separator = gtk.SeparatorToolItem()

        # plugin engine methods
    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        self.sync_engine = syncengine.SyncEngine(self)
        # add a menu item to the menu bar
        plugin_api.add_menu_item(self.menu_item)

        # saves the separator's index to later remove it
        plugin_api.add_toolbar_item(self.separator)
        # add a item(button) to the ToolBar
        plugin_api.add_toolbar_item(self.tb_button)

    def deactivate(self, plugin_api):
        plugin_api.remove_menu_item(self.menu_item)
        plugin_api.remove_toolbar_item(self.tb_button)
        plugin_api.remove_toolbar_item(self.separator)

    #load a dialog with a String
    def loadDialogToken(self, msg):
        path = os.path.dirname(os.path.abspath(__file__))
        glade_file = os.path.join(path, "gtk.glade")
        wTree = gtk.glade.XML(glade_file, "dialogtoken")
        self.showDialog(wTree.get_widget("dialogtoken"))
        self.btn_ok = wTree.get_widget("btn_ok")
        self.lbl_dialog = wTree.get_widget("lbl_dialog")
        self.lbl_dialog.set_markup(msg)
        self.dialog.connect("delete_event", self.close_dialog)
        self.btn_ok.connect("clicked", self.callback)
        self.dialog.show_all()

    def loadDialogSync(self, msg):
        path = os.path.dirname(os.path.abspath(__file__))
        glade_file = os.path.join(path, "gtk.glade")
        wTree = gtk.glade.XML(glade_file, "dialogsync")
        self.showDialog(wTree.get_widget("dialogsync"))
        self.btn_ok = wTree.get_widget("btn_ok")
        self.btn_ok.set_sensitive(False)
        self.lbl_dialog = wTree.get_widget("lbl_dialog")
        self.lbl_dialog.set_text(msg)
        self.progressbar = wTree.get_widget("progressbar")
        self.dialog.connect("delete_event", self.close_dialog)
        self.btn_ok.connect("clicked", self.close_dialog)
        self.dialog.show_all()

    def loadDialogNotification(self, msg):
        path = os.path.dirname(os.path.abspath(__file__))
        glade_file = os.path.join(path, "gtk.glade")
        wTree = gtk.glade.XML(glade_file, "notification")
        self.showDialog(wTree.get_widget("notification"))
        self.lbl_dialog = wTree.get_widget("lbl_dialog")
        self.lbl_dialog.set_text(msg)
        self.dialog.show_all()

    def close_dialog(self, widget, data=None):
        self.showDialog(None)

    def set_progressbar(self):
        self.progressbar.set_fraction(self.progressbar_percent)
        if self.progressbar_percent == 1.0:
            self.btn_ok.set_sensitive(True)

    def set_status(self):
        self.lbl_dialog.set_text(self.status)

    def set_substatus(self):
        self.progressbar.set_text(self.substatus)

    def onTesteMenu(self, widget):
        self.onTbButton(widget)

    def lauchSynchronization(self):
        self.loadDialogSync(_("Synchronization started"))
        self.worker_thread = Thread(target = \
                                self.sync_engine.synchronize).start()

    def onTbButton(self, widget):
        self.checkLogin()

    def checkLoginBtn(self, widget):
        self.showDialog(None)
        self.checkLogin(False)

    def checkLogin(self, firstime = True):
        self.firstime = firstime
        self.loadDialogNotification(_("Trying to access, please stand by..."))
        Thread(target = self.checkLoginThreadWatchdog).start()

    def checkLoginThreadWatchdog(self):
        login_thread = Thread(target = self.checkLoginThread)
        try:
            login_thread.start()
            login_thread.join(10)
        except:
            pass
        if login_thread.isAlive():
            #Can't connect to RTM server
            gobject.idle_add(self.loginHasFailed)
        else:
            gobject.idle_add(self.checkHasLogon)

    def loginHasFailed(self):
        self.callback = self.close_dialog
        self.loadDialogToken(_("Couldn't connect to Remember The Milk"))

    def checkLoginThread(self):
        try:
            self.sync_engine.rtmLogin()
        except:
            pass

    def checkHasLogon(self):
        login = self.sync_engine.rtmHasLogon()
        self.showDialog(None)
        if login == False:
            if not self.firstime:
                self.callback = self.close_dialog
                self.loadDialogToken(_("<b>Authentication failed</b>.\
Please retry."))
            else:
                self.callback = self.close_dialog
                self.callback = self.checkLoginBtn
                self.loadDialogToken(_("Please authenticate to Remember \
The Milk in the browser that is being opened now. \
When done, press OK"))
        else:
            self.lauchSynchronization()

    def onTaskOpened(self, plugin_api):
        pass
