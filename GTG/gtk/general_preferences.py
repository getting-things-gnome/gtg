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
from gettext import gettext as _


class GeneralPreferences():

    GENERAL_PREFERENCES_UI = os.path.join(UI_DIR, "general_preferences.ui")
    INVALID_COLOR = Gdk.Color(50000, 0, 0)

    def __init__(self, req, app):
        self.req = req
        self.config = self.req.get_config('browser')
        builder = Gtk.Builder()
        builder.add_from_file(self.GENERAL_PREFERENCES_UI)

        self.ui_widget = builder.get_object("general_pref_window")
        self.preview_button = builder.get_object("preview_button")
        self.bg_color_button = builder.get_object("bg_color_button")
        self.font_button = builder.get_object("font_button")

        self.app = app
        self.timer = app.timer
        self.refresh_time = builder.get_object("time_entry")
        self.autoclean_enable = builder.get_object("autoclean_enable")
        self.autoclean_days = builder.get_object("autoclean_days")
        self.dark_mode = builder.get_object("darkmode_enable")

        self._refresh_preferences_store()
        builder.connect_signals(self)

    # Following 3 methods: get_name, get_title, get_ui are
    # required for all children of stack in Preferences class.
    # Plugins and Synchronisation must have them, too!
    # They are used for easier, more abstract adding of the
    # children and setting the headerbar title.
    def get_name(self):
        return 'general'

    def get_title(self):
        return _('General')

    def get_ui(self):
        """
        This method returns widget displayed in Preferences window.
        """
        return self.ui_widget

    def activate(self):
        pass

    def get_default_editor_font(self):
        editor_font = self.config.get("font_name")
        if editor_font == "":
            font = self.ui_widget.get_style_context().get_font(
                Gtk.StateFlags.NORMAL)
            editor_font = font.to_string()
        return editor_font

    def _refresh_preferences_store(self):
        """ Sets the correct value in the preferences checkboxes """

        show_preview = self.config.get("contents_preview_enable")
        self.preview_button.set_active(show_preview)

        bg_color = self.config.get("bg_color_enable")
        self.bg_color_button.set_active(bg_color)

        self.refresh_time.set_text(self.timer.get_formatted_time())
        self.refresh_time.modify_fg(Gtk.StateFlags.NORMAL, None)

        self.font_button.set_font_name(self.get_default_editor_font())

        enable_autoclean = self.config.get("autoclean")
        self.autoclean_enable.set_active(enable_autoclean)

        autoclean_days = self.config.get("autoclean_days")
        self.autoclean_days.set_value(autoclean_days)

        dark_mode = self.config.get("dark_mode")
        self.dark_mode.set_active(dark_mode)

    def _refresh_task_browser(self):
        """ Refresh tasks in task browser """

        collapsed = self.config.get("collapsed_tasks")
        task_tree = self.req.get_tasks_tree(refresh=False).get_basetree()
        task_tree.refresh_all()

        self.app.browser.restore_collapsed_tasks(collapsed)

    def on_valid_time_check(self, widget):
        """
        This function checks for validity of the user input with
        every new key-stroke from the user by parsing the input.
        """
        try:
            input_time = self.refresh_time.get_text()
            self.timer.parse_time(input_time)
            color = None
        except ValueError:
            color = self.INVALID_COLOR

        self.refresh_time.modify_fg(Gtk.StateFlags.NORMAL, color)

    def on_leave_time_entry(self, widget, data=None):
        """
        This function not only parses the user input, but is
        called only when the time entry is focused out. It also
        sets the time value for the widget.
        """
        try:
            input_time = self.refresh_time.get_text()
            correct_time = self.timer.parse_time(input_time)
            self.timer.set_configuration(correct_time)
        except ValueError:
            pass

        self._refresh_preferences_store()

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

    def on_autoclean_toggled(self, widget, state):
        """Toggle automatic deletion of old closed tasks."""

        self.config.set("autoclean", state)

    def on_autoclean_days_changed(self, widget):
        """Update value for maximum days before removing a task."""

        self.config.set("autoclean_days", int(widget.get_value()))

    def on_purge_clicked(self, widget):
        """Purge old tasks immediately."""

        self.app.purge_old_tasks(widget)

    def on_dark_mode_toggled(self, widget, state):
        """Toggle darkmode."""

        self.config.set("dark_mode", state)
        self.app.toggle_darkmode(state)
        collapsed = self.config.get("collapsed_tasks")

        # Refresh panes
        func = self.app.browser.tv_factory.get_task_bg_color

        for pane in self.app.browser.vtree_panes.values():
            pane.set_bg_color(func, 'bg_color')
            pane.basetree.get_basetree().refresh_all()

        self.app.browser.restore_collapsed_tasks(collapsed)
