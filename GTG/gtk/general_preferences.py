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

from gi.repository import Gtk, GLib, GObject

from GTG.core.dirs import UI_DIR
from GTG.gtk.action_row import ActionRow
from gettext import gettext as _

import logging

log = logging.getLogger(__name__)


@Gtk.Template(filename=os.path.join(UI_DIR, "general_preferences.ui"))
class GeneralPreferences(Gtk.ScrolledWindow):
    __gtype_name__ = 'GeneralPreferences'

    _preview_button = Gtk.Template.Child()
    _bg_color_button = Gtk.Template.Child()
    _font_button = Gtk.Template.Child()

    _refresh_time_entry = Gtk.Template.Child()
    _autoclean_switch = Gtk.Template.Child()
    _autoclean_days_spin = Gtk.Template.Child()
    _dark_mode_switch = Gtk.Template.Child()

    is_portal_initiated = GObject.Property(type=bool, default=False)

    def __init__(self, app):
        super().__init__()
        self.config = app.config

        self.app = app
        self.timer = app.timer

        time_entry_focus_controller = Gtk.EventControllerFocus()
        time_entry_focus_controller.connect("leave", self.on_leave_time_entry)
        self._refresh_time_entry.add_controller(time_entry_focus_controller)
        # setting preference values should not block,
        # as setting certain preferences depends on the complete initialization
        # of the app.
        GLib.idle_add(self._refresh_preferences_store)
        self.is_portal_initiated = bool(self.app.portal)

    # Following 3 methods: get_name, get_title, get_ui are
    # required for all children of stack in Preferences class.
    # Plugins and Synchronisation must have them, too!
    # They are used for easier, more abstract adding of the
    # children and setting the headerbar title.
    def get_name(self):
        return 'general'

    def get_title(self):
        return _('General')

    def activate(self):
        pass

    def get_default_editor_font(self):
        if not self.config.get("font_name") or not self.config.get("font_size"):
            editor_font = Gtk.Settings.get_default().get_property("gtk-font-name")
        else:
            editor_font = self.config.get("font_name") + " " + str(self.config.get("font_size"))
        return editor_font

    def _refresh_preferences_store(self):
        """ Sets the correct value in the preferences checkboxes """

        show_preview = self.config.get("contents_preview_enable")
        self._preview_button.set_active(show_preview)

        bg_color = self.config.get("bg_color_enable")
        self._bg_color_button.set_active(bg_color)

        self._refresh_time_entry.set_text(self.timer.get_formatted_time())

        self._font_button.set_font(self.get_default_editor_font())

        enable_autoclean = self.config.get("autoclean")
        self._autoclean_switch.set_active(enable_autoclean)

        autoclean_days = self.config.get("autoclean_days")
        self._autoclean_days_spin.set_value(autoclean_days)

    @Gtk.Template.Callback()
    def on_valid_time_check(self, widget):
        """
        This function checks for validity of the user input with
        every new key-stroke from the user by parsing the input.
        """
        try:
            input_time = self._refresh_time_entry.get_text()
            self.timer.parse_time(input_time)
            self._refresh_time_entry.remove_css_class("error")
        except ValueError:
            self._refresh_time_entry.add_css_class("error")

    def on_leave_time_entry(self, widget, data=None):
        """
        This function not only parses the user input, but is
        called only when the time entry is focused out. It also
        sets the time value for the widget.
        """
        try:
            input_time = self._refresh_time_entry.get_text()
            correct_time = self.timer.parse_time(input_time)
            self.timer.set_configuration(correct_time)
        except ValueError:
            pass

        self._refresh_preferences_store()

    @Gtk.Template.Callback()
    def on_preview_toggled(self, widget, state):
        """ Toggle previews in the task view on or off."""
        curstate = self.config.get("contents_preview_enable")
        if curstate != self._preview_button.get_active():
            self.config.set("contents_preview_enable", not curstate)

    @Gtk.Template.Callback()
    def on_bg_color_toggled(self, widget, state):
        """ Save configuration and refresh nodes to apply the change """
        curstate = self.config.get("bg_color_enable")
        if curstate != self._bg_color_button.get_active():
            self.config.set("bg_color_enable", not curstate)

            for task in self.app.ds.tasks.lookup.values():
                task.notify('row_css')

    @Gtk.Template.Callback()
    def on_font_change(self, widget):
        """ Set a new font for editor """
        self.config.set("font_name", self._font_button.get_font_family().get_name())
        self.config.set("font_size", int(self._font_button.get_font_size()/1000))

    @Gtk.Template.Callback()
    def on_autoclean_toggled(self, widget, state):
        """Toggle automatic deletion of old closed tasks."""

        self.config.set("autoclean", self._autoclean_switch.get_active())

    @Gtk.Template.Callback()
    def on_autoclean_days_changed(self, widget):
        """Update value for maximum days before removing a task."""

        self.config.set("autoclean_days", int(widget.get_value()))

    @Gtk.Template.Callback()
    def on_purge_clicked(self, widget):
        """Purge old tasks immediately."""

        self.app.purge_old_tasks(widget)

    @Gtk.Template.Callback()
    def on_dark_mode_toggled(self, widget, state):
        """Toggle darkmode."""

        self.config.set("dark_mode", self._dark_mode_switch.get_active())
        self.app.toggle_darkmode(self._dark_mode_switch.get_active())
