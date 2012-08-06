# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
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

""" The Preferences Dialog for configuring GTG """
import os
import shutil

import gtk
from xdg.BaseDirectory import xdg_config_home

from GTG import _
from GTG import info
from GTG.gtk import ViewConfig

AUTOSTART_DIRECTORY = os.path.join(xdg_config_home, "autostart")
AUTOSTART_FILE = "gtg.desktop"
AUTOSTART_PATH = os.path.join(AUTOSTART_DIRECTORY, AUTOSTART_FILE)


def enable_gtg_autostart():
    """ Enable autostart

    Firstly, locate gtg.desktop file. Then link it in AUTOSTART_FILE.
    On Windows, there is no os.symlink, just copy the file. """
    desktop_file_path = None
    this_directory = os.path.dirname(os.path.abspath(__file__))
    for path in ["../..", "../../../applications",
                "../../../../../share/applications"]:
        fullpath = os.path.join(this_directory, path, AUTOSTART_FILE)
        fullpath = os.path.normpath(fullpath)
        if os.path.isfile(fullpath):
            desktop_file_path = fullpath
            break

    if desktop_file_path:
        if not os.path.exists(AUTOSTART_DIRECTORY):
            os.mkdir(AUTOSTART_DIRECTORY)

        if os.path.isdir(AUTOSTART_DIRECTORY) and \
           not os.path.exists(AUTOSTART_PATH):
            if hasattr(os, "symlink"):
                os.symlink(desktop_file_path, AUTOSTART_PATH)
            else:
                shutil.copyfile(desktop_file_path, AUTOSTART_PATH)


def disable_gtg_autostart():
    """ Disable autostart, removing the file in autostart_path """
    if os.path.isfile(AUTOSTART_PATH):
        os.remove(AUTOSTART_PATH)


class PreferencesDialog:
    """ Show preference dialog """

    def __init__(self, req):
        self.req = req
        self.config = self.req.get_config('browser')
        builder = gtk.Builder()
        builder.add_from_file(ViewConfig.PREFERENCES_GLADE_FILE)

        self.dialog = builder.get_object("PreferencesDialog")
        self.dialog.set_title(_("Preferences - %s" % info.NAME))
        self.pref_autostart = builder.get_object("pref_autostart")
        self.pref_show_preview = builder.get_object("pref_show_preview")
        self.bg_color_enable = builder.get_object("bg_color_enable")
        self.fontbutton = builder.get_object("fontbutton")
	self.fontbutton.set_font_name(self.config.get("font_name")) 
        builder.connect_signals({
          'on_pref_autostart_toggled':
            self.on_autostart_toggled,
          'on_pref_show_preview_toggled':
            self.toggle_preview,
          'on_bg_color_toggled':
            self.on_bg_color_toggled,
          'on_prefs_help':
            self.on_help,
          'on_prefs_close':
            self.on_close,
          'on_PreferencesDialog_delete_event':
            self.on_close,
          'on_fontbutton_font_set':
            self.on_font_change,  
        })

    def  _refresh_preferences_store(self):
        """ Sets the correct value in the preferences checkboxes """
        has_autostart = os.path.isfile(AUTOSTART_PATH)
        self.pref_autostart.set_active(has_autostart)

        show_preview = self.config.get("contents_preview_enable")
        self.pref_show_preview.set_active(show_preview)

        bg_color = self.config.get("bg_color_enable")
        self.bg_color_enable.set_active(bg_color)

    def _refresh_task_browser(self):
        """ Refresh tasks in task browser """
        task_tree = self.req.get_tasks_tree(refresh=False).get_basetree()
        task_tree.refresh_all()

    def activate(self):
        """ Activate the preferences dialog."""
        self._refresh_preferences_store()
        self.dialog.show_all()

    def on_close(self, widget, data=None): # pylint: disable-msg=W0613
        """ Close the preferences dialog."""
        self.dialog.hide()
        return True

    @classmethod
    def on_help(cls, widget): # pylint: disable-msg=W0613
        """ In future, this will open help for preferences """
        return True

    @classmethod
    def on_autostart_toggled(cls, widget):
        """ Toggle GTG autostarting with the GNOME desktop """
        if widget.get_active():
            enable_gtg_autostart()
        else:
            disable_gtg_autostart()

    def toggle_preview(self, widget):
        """ Toggle previews in the task view on or off."""
        curstate = self.config.get("contents_preview_enable")
        if curstate != widget.get_active():
            self.config.set("contents_preview_enable", not curstate)
            self._refresh_task_browser()

    def on_bg_color_toggled(self, widget):
        """ Save configuration and refresh nodes to apply the change """
        curstate = self.config.get("bg_color_enable")
        if curstate != widget.get_active():
            self.config.set("bg_color_enable", not curstate)
            self._refresh_task_browser()
    def on_font_change(self,widget):
	self.config.set("font_name", self.fontbutton.get_font_name())     
        self.fontbutton.set_font_name(self.fontbutton.get_font_name())
