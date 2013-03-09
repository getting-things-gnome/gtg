# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
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
from GTG.tools.shortcut import get_saved_binding, \
                               check_invalidity, \
                               save_new_binding

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

        # If the path is a symlink and is broken, remove it
        if os.path.islink(AUTOSTART_PATH) and \
                not os.path.exists(os.path.realpath(AUTOSTART_PATH)):
            os.unlink(AUTOSTART_PATH)

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
        self.hbox1 = builder.get_object("hbox1")
        self.shortcut_button = builder.get_object("shortcut_button")

        self.shortcut = ShortcutWidget(self.dialog, self.hbox1,
                                       self.shortcut_button)

        self.fontbutton = builder.get_object("fontbutton")
        editor_font = self.config.get("font_name")
        if editor_font == "":
            style = self.dialog.get_style()
            editor_font = str(style.font_desc)
        self.fontbutton.set_font_name(editor_font)

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
                                'on_shortcut_button_toggled':
                                self.shortcut.on_shortcut_toggled,
                                })

    def _refresh_preferences_store(self):
        """ Sets the correct value in the preferences checkboxes """
        has_autostart = os.path.isfile(AUTOSTART_PATH)
        self.pref_autostart.set_active(has_autostart)

        self.shortcut.refresh_accel()

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

    def on_close(self, widget, data=None):
        """ Close the preferences dialog."""
        self.dialog.hide()
        return True

    @classmethod
    def on_help(cls, widget):
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

    def on_font_change(self, widget):
        """ Set a new font for editor """
        self.config.set("font_name", self.fontbutton.get_font_name())


class ShortcutWidget:
    """ Show Shortcut Accelerator Widget """

    def __init__(self, dialog, hbox1, button1):
        self.dialog = dialog
        self.hbox1 = hbox1
        self.button = button1
        self.new_task_default_binding = "<Primary>F12"

        self.liststore = gtk.ListStore(str, str)
        self.liststore.append(["", ""])
        treeview = gtk.TreeView(self.liststore)
        column_accel = gtk.TreeViewColumn()
        treeview.append_column(column_accel)
        treeview.set_headers_visible(False)

        cell = gtk.CellRendererAccel()
        cell.set_alignment(0.0, 1.0)
        cell.set_fixed_size(-1, 18)
        cell.set_property("accel-mode", gtk.CELL_RENDERER_ACCEL_MODE_OTHER)
        cell.connect("accel-edited", self._cellAccelEdit, self.liststore)
        cell.connect("accel-cleared", self._accel_cleared, self.liststore)
        self.cell = cell
        column_accel.pack_start(cell, True)
        column_accel.add_attribute(cell, "text", 1)
        self.hbox1.add(treeview)

    def refresh_accel(self):
        """ Refreshes the accelerator """
        iter1 = self.liststore.get_iter_first()
        self.new_task_binding = get_saved_binding()
        self.binding_backup = self.new_task_binding
        if self.new_task_binding == "":
            # User had set a shortcut, but has now disabled it
            self.button.set_active(False)
            self.liststore.set_value(iter1, 1, "Disabled")
            return
        elif self.new_task_binding is None:
            # User hasn't set a shortcut ever
            self.button.set_active(False)
            self.new_task_binding = self.new_task_default_binding
            self.binding_backup = self.new_task_binding
        else:
            # There exists a shortcut
            self.button.set_active(True)
        (accel_key, accel_mods) = gtk.accelerator_parse(self.new_task_binding)
        self.show_input = gtk.accelerator_get_label(accel_key, accel_mods)
        self.liststore.set_value(iter1, 1, self.show_input)

    def on_shortcut_toggled(self, widget):
        """ New task shortcut checkbox is toggled """
        if widget.get_active():
            self.new_task_binding = self.binding_backup
            save_new_binding(self.new_task_binding, True)
            self.cell.set_property("editable", True)
        else:
            self.new_task_binding = ""
            save_new_binding(self.new_task_binding, True)
            self.cell.set_property("editable", False)

    def _cellAccelEdit(self, cell, path, accel_key, accel_mods, code, model):
        """ Accelerator is modified """
        self.show_input = gtk.accelerator_get_label(accel_key, accel_mods)
        self.new_task_binding = gtk.accelerator_name(accel_key, accel_mods)
        if check_invalidity(self.new_task_binding, accel_key, accel_mods):
            self._show_warning(gtk.Button(_("Warning")), self.show_input)
            return
        self.binding_backup = self.new_task_binding
        iter = model.get_iter(path)
        model.set_value(iter, 1, self.show_input)
        save_new_binding(self.new_task_binding, self.button.get_active())

    def _accel_cleared(self, widget, path, model):
        """ Clear the accelerator """
        iter = model.get_iter(path)
        model.set_value(iter, 1, None)

    def _show_warning(self, widget, input_str):
        """ Show warning when user enters inappropriate accelerator """
        show = _("The shortcut \"%s\" cannot be used because "
               "it will become impossible to type using this key.\n"
               "Please try with a key such as "
               "Control, Alt or Shift at the same time.") % input_str
        dialog = gtk.MessageDialog(self.dialog, gtk.DIALOG_DESTROY_WITH_PARENT,
                                   gtk.MESSAGE_WARNING, gtk.BUTTONS_CANCEL,
                                   show)
        dialog.run()
        dialog.hide()
