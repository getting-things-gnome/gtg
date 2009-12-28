# -*- coding: utf-8 -*-
# Copyright (c) 2009 - Paulo Cabido <paulo.cabido@gmail.com>
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
import sys
import os

from GTG.tools import openurl


class NotificationArea:


    DEFAULT_PREFERENCES = {"start_minimized": False}
    PLUGIN_NAME = "notification_area"
    
    def __init__(self):
        self.minimized = False
    
    def activate(self, plugin_api):
        data_dir = plugin_api.get_data_dir()
        self.plugin_api = plugin_api
        icon = gtk.gdk.pixbuf_new_from_file_at_size(data_dir + "/icons/hicolor/16x16/apps/gtg.png", 16, 16)
        if not hasattr(self,"statusicon"):
            self.statusicon = gtk.status_icon_new_from_pixbuf(icon)
            self.statusicon.set_tooltip("Getting Things Gnome!")
            self.statusicon.connect('activate', self.minimize, plugin_api)
        self.statusicon.set_visible(True)
        menu = gtk.Menu()
        
        #path_image_new_task = data_dir + "/icons/hicolor/16x16/actions/gtg-task-new.png"
        #pixbug_new_task = gtk.gdk.pixbuf_new_from_file_at_size(path_image_new_task,\
        #                                                       16, 16)
        #image_new_task = gtk.Image()
        #image_new_task.set_from_pixbuf(pixbug_new_task)
        #image_new_task.show()
        #menuItem = gtk.ImageMenuItem("_New Task")
        #menuItem.set_image(image_new_task)
        ##menuItem.connect('activate', self.new_task)
        #menu.append(menuItem)
        self.view_main_window = gtk.CheckMenuItem("_View Main Window")
        self.view_main_window.set_active(True)
        self.view_main_window.connect('activate', self.minimize, plugin_api)
        menu.append(self.view_main_window)
        
        menu.append(gtk.SeparatorMenuItem())
        
        
        menuItem = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        menuItem.connect('activate', self.about, plugin_api)
        menu.append(menuItem)
        
        menu.append(gtk.SeparatorMenuItem())
        
        menuItem = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        menuItem.connect('activate', self.exit, self.statusicon)
        menu.append(menuItem)
        
        self.statusicon.connect('popup-menu', self.on_icon_popup, menu)

        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.dirname(os.path.abspath(__file__)) +\
                                   "/notification_area.ui")
        self.preferences_dialog = self.builder.get_object("preferences_dialog")
        self.chbox_miminized    = self.builder.get_object("pref_chbox_minimized")
        SIGNAL_CONNECTIONS_DIC = {
            "on_preferences_dialog_delete_event":
                self.on_preferences_cancel,
            "on_btn_preferences_cancel_clicked":
                self.on_preferences_cancel,
            "on_btn_preferences_ok_clicked":
                self.on_preferences_ok
        }
        self.builder.connect_signals(SIGNAL_CONNECTIONS_DIC)
        self.preferences_load()
        self.preferences_apply()
        
    def deactivate(self, plugin_api):
        self.statusicon.set_visible(False)
        self.plugin_api.get_browser().start_minimized = False
    
    def onTaskOpened(self, plugin_api):
        pass
    
    def minimize(self, widget, plugin_api):
        if self.minimized:
            self.view_main_window.set_active(True)
            plugin_api.show_window()
            self.minimized = not self.minimized
        else:
            self.view_main_window.set_active(False)
            plugin_api.hide_window()
            self.minimized = not self.minimized
        
    def on_icon_popup(self, icon, button, timestamp, menu=None):
        if menu:
            menu.show_all()
            menu.popup(None, None, gtk.status_icon_position_menu, button, timestamp, icon)
    
    def about(self, widget, plugin_api, data=None):
        sys.path.insert(0,plugin_api.get_data_dir())
        from GTG import info
        
        about = plugin_api.get_about_dialog()

        gtk.about_dialog_set_url_hook(lambda dialog, url: openurl.openurl(url))
        about.set_website(info.URL)
        about.set_website_label(info.URL)
        about.set_version(info.VERSION)
        about.set_authors(info.AUTHORS)
        about.set_artists(info.ARTISTS)
        about.set_translator_credits(info.TRANSLATORS)
        about.show_all()
    
    def exit(self, widget, data=None):
        gtk.main_quit()

## Preferences methods #########################################################

    def is_configurable(self):
        """A configurable plugin should have this method and return True"""
        return True

    def configure_dialog(self, plugin_apis, manager_dialog):
        self.preferences_load()
        self.preferences_dialog.set_transient_for(manager_dialog)
        self.chbox_miminized.set_active(self.preferences["start_minimized"])
        self.preferences_dialog.show_all()

    def on_preferences_cancel(self, widget = None, data = None):
        self.preferences_dialog.hide()
        return True

    def on_preferences_ok(self, widget = None, data = None):
        self.preferences["start_minimized"] = self.chbox_miminized.get_active()
        self.preferences_apply()
        self.preferences_store()
        self.preferences_dialog.hide()

    def preferences_load(self):
        data = self.plugin_api.load_configuration_object(self.PLUGIN_NAME,\
                                                         "preferences")
        if data == None or type(data) != type (dict()):
            self.preferences = self.DEFAULT_PREFERENCES
        else:
            self.preferences = data

    def preferences_store(self):
        self.plugin_api.save_configuration_object(self.PLUGIN_NAME,\
                                                  "preferences", \
                                                  self.preferences)

    def preferences_apply(self):
        if self.plugin_api.is_browser():
            if self.preferences["start_minimized"]:
                self.plugin_api.get_browser().start_minimized = True
            else:
                self.plugin_api.get_browser().start_minimized = False
