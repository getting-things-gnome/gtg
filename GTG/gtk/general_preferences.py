# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2015 - Jakub Brindza
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

"""General Preferences represents one of the children
in Preferences window. It is viewed in its stack.
It enables user to set the most general settings of GTG."""

import os

from gi.repository import Gtk, Gdk

from GTG.core.dirs import UI_DIR
from GTG.core.translations import _
from GTG.tools import autostart
from GTG.tools import shortcut


class GeneralPreferences(object):

    GENERAL_PREFERENCES_UI = os.path.join(UI_DIR, "general_preferences.ui")
    INVALID_COLOR = Gdk.Color(50000, 0, 0)

    def __init__(self, req, vmanager):
        self.req = req
        self.config = self.req.get_config('browser')
        builder = Gtk.Builder()
        builder.add_from_file(self.GENERAL_PREFERENCES_UI)

        self.ui_widget = builder.get_object("general_pref_window")
        self.autostart_button = builder.get_object("autostart_button")
        self.preview_button = builder.get_object("preview_button")
        self.bg_color_button = builder.get_object("bg_color_button")
        self.shortcut_button = builder.get_object("shortcut_button")
        self.font_button = builder.get_object("font_button")
        self.shortcut_popover = builder.get_object("shortcut_popover")
        self.set_shortcut = builder.get_object("set_shortcut")

        self.shortcut = ShortcutWidget(builder)

        self.timer = vmanager.timer
        self.refresh_time = builder.get_object("time_entry")

        builder.connect_signals(self)

    # Following 3 methods: get_name, get_title, get_ui are
    # required for all children of stack in Preferences class.
    # Plugins and Synchronisation must have them, too!
    # They are used for easier, more abstract adding of the
    # children and setting the headerbar title.
    def get_name(self):
        return 'general'

    def get_title(self):
        return _('General Preferences')

    def get_ui(self):
        '''
        This method returns widget displayed in Preferences window.
        '''
        return self.ui_widget

    def activate(self):
        self._refresh_preferences_store()

    def on_shortcut_popover(self, widget):
        self.shortcut_popover.show()

    def get_default_editor_font(self):
        editor_font = self.config.get("font_name")
        if editor_font == "":
            font = self.ui_widget.get_style_context().get_font(
                Gtk.StateFlags.NORMAL)
            editor_font = font.to_string()
        return editor_font

    def _refresh_preferences_store(self):
        """ Sets the correct value in the preferences checkboxes """
        self.autostart_button.set_active(autostart.is_enabled())

        self.shortcut.refresh_accel()

        show_preview = self.config.get("contents_preview_enable")
        self.preview_button.set_active(show_preview)

        bg_color = self.config.get("bg_color_enable")
        self.bg_color_button.set_active(bg_color)

        self.refresh_time.set_text(self.timer.get_formatted_time())
        self.refresh_time.modify_fg(Gtk.StateFlags.NORMAL, None)

        self.font_button.set_font_name(self.get_default_editor_font())

    def _refresh_task_browser(self):
        """ Refresh tasks in task browser """
        task_tree = self.req.get_tasks_tree(refresh=False).get_basetree()
        task_tree.refresh_all()

    def on_valid_time_check(self, widget):
        '''
        This function checks for validity of the user input with
        every new key-stroke from the user by parsing the input.
        '''
        try:
            input_time = self.refresh_time.get_text()
            self.timer.parse_time(input_time)
            color = None
        except ValueError:
            color = self.INVALID_COLOR

        self.refresh_time.modify_fg(Gtk.StateFlags.NORMAL, color)

    def on_leave_time_entry(self, widget, data=None):
        '''
        This function not only parses the user input, but is
        called only when the time entry is focused out. It also
        sets the time value for the widget.
        '''
        try:
            input_time = self.refresh_time.get_text()
            correct_time = self.timer.parse_time(input_time)
            self.timer.set_configuration(correct_time)
        except ValueError:
            pass

        self._refresh_preferences_store()

    def on_autostart_toggled(self, widget, state):
        """ Toggle GTG autostarting with the GNOME desktop """
        if self.autostart_button.get_active():
            autostart.enable()
        else:
            autostart.disable()

    def on_shortcut_toggled(self, widget, state):
        self.shortcut.on_shortcut_toggled(widget, state)

    def on_preview_toggled(self, widget, state):
        """ Toggle previews in the task view on or off."""
        curstate = self.config.get("contents_preview_enable")
        if curstate != self.preview_button.get_active():
            self.config.set("contents_preview_enable", not curstate)
            self._refresh_task_browser()

    def on_bg_color_toggled(self, widget, state):
        """ Save configuration and refresh nodes to apply the change """
        curstate = self.config.get("bg_color_enable")
        if curstate != self.bg_color_button.get_active():
            self.config.set("bg_color_enable", not curstate)
            self._refresh_task_browser()

    def on_font_change(self, widget):
        """ Set a new font for editor """
        self.config.set("font_name", self.font_button.get_font_name())


class ShortcutWidget(object):
    """ Show Shortcut Accelerator Widget """

    def __init__(self, builder):
        self.builder = builder
        self.ui_widget = builder.get_object("general_pref_window")
        self.button = builder.get_object("shortcut_button")
        self.new_task_default_binding = "<Primary>F12"
        self.gsettings_install_label_shown = True

        self.liststore = Gtk.ListStore(str, str)
        self.liststore.append(["", ""])
        treeview = Gtk.TreeView(self.liststore)
        column_accel = Gtk.TreeViewColumn()
        treeview.append_column(column_accel)
        treeview.set_headers_visible(False)

    def refresh_accel(self):
        """ Refreshes the accelerator """

        if not shortcut.is_gsettings_present():
            self.button.set_sensitive(False)
            iter1 = self.liststore.get_iter_first()
            self.liststore.set_value(iter1, 1, "Disabled")
            self.cell.set_sensitive(False)

            if not self.gsettings_install_label_shown:
                self._show_gsettings_install_label()
                self.gsettings_install_label_shown = True
            return

        iter1 = self.liststore.get_iter_first()
        self.new_task_binding = shortcut.get_saved_binding()
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
        (accel_key, accel_mods) = Gtk.accelerator_parse(self.new_task_binding)
        self.show_input = Gtk.accelerator_get_label(accel_key, accel_mods)
        self.liststore.set_value(iter1, 1, self.show_input)

    def on_shortcut_toggled(self, widget, state):
        """ New task shortcut checkbox is toggled """
        if widget.get_active():
            self.new_task_binding = self.binding_backup
            shortcut.save_new_binding(self.new_task_binding, True)
            self.cell.set_property("editable", True)
        else:
            self.new_task_binding = ""
            shortcut.save_new_binding(self.new_task_binding, True)
            self.cell.set_property("editable", False)

    def _cellAccelEdit(self, cell, path, accel_key, accel_mods, code, model):
        """ Accelerator is modified """
        self.show_input = Gtk.accelerator_get_label(accel_key, accel_mods)
        self.new_task_binding = Gtk.accelerator_name(accel_key, accel_mods)
        if shortcut.check_invalidity(self.new_task_binding, accel_key,
                                     accel_mods):
            self._show_warning(self.show_input)
            return
        self.binding_backup = self.new_task_binding
        iter = model.get_iter(path)
        model.set_value(iter, 1, self.show_input)
        shortcut.save_new_binding(self.new_task_binding,
                                  self.button.get_active())

    def _accel_cleared(self, widget, path, model):
        """ Clear the accelerator """
        iter = model.get_iter(path)
        model.set_value(iter, 1, None)

    def _show_gsettings_install_label(self):
        vbox = self.builder.get_object("prefs-vbox7")
        label = Gtk.Label()
        label.set_markup(_("<small>Please install <i><b>gsettings</b></i> "
                           "to enable New task shortcut</small>"))
        vbox.add(label)

    def _show_warning(self, input_str):
        """ Show warning when user enters inappropriate accelerator """
        show = _("The shortcut \"%s\" cannot be used because "
                 "it will become impossible to type using this key.\n"
                 "Please try with a key such as "
                 "Control, Alt or Shift at the same time.") % input_str
        dialog = Gtk.MessageDialog(self.ui_widget,
                                   Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                   Gtk.MessageType.WARNING,
                                   Gtk.ButtonsType.OK,
                                   show)
        dialog.run()
        dialog.hide()
