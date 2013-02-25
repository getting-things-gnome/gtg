# -*- coding: utf-8 -*-
# Copyright (c) 2009 - Luca Invernizzi <invernizzi.l@gmail.com>
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
import sys
import os

try:
    import pygtk
    pygtk.require("2.0")
except:
    sys.exit(1)

try:
    import gtk
except:
    sys.exit(1)

from threading import Timer

from GTG.tools.logger import Log
from GTG.tools.dates import Date


class pluginReaper:

    DEFAULT_PREFERENCES = {'max_days': 30,
                           'is_automatic': False,
                           'show_menu_item': True}

    PLUGIN_NAME = "task-reaper"

    # In case of automatic removing tasks, the time
    # between two runs of the cleaner function
    TIME_BETWEEN_PURGES = 60 * 60

    def __init__(self):
        self.path = os.path.dirname(os.path.abspath(__file__))
        # GUI initialization
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(
                                   os.path.dirname(os.path.abspath(__file__)) +
                                   "/reaper.ui"))
        self.preferences_dialog = self.builder.get_object("preferences_dialog")
        self.pref_chbox_show_menu_item = \
            self.builder.get_object("pref_chbox_show_menu_item")
        self.pref_chbox_is_automatic = \
            self.builder.get_object("pref_chbox_is_automatic")
        self.pref_spinbtn_max_days = \
            self.builder.get_object("pref_spinbtn_max_days")
        SIGNAL_CONNECTIONS_DIC = {
            "on_preferences_dialog_delete_event":
            self.on_preferences_cancel,
            "on_btn_preferences_cancel_clicked":
            self.on_preferences_cancel,
            "on_btn_preferences_ok_clicked":
            self.on_preferences_ok,
        }
        self.builder.connect_signals(SIGNAL_CONNECTIONS_DIC)
        self.menu_item = gtk.MenuItem("Delete old closed tasks")
        self.menu_item.connect('activate', self.delete_old_closed_tasks)

    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        # preferences initialization
        self.menu_item_is_shown = False
        self.is_automatic = False
        self.timer = None
        self.preferences_load()
        self.preferences_apply()

    def onTaskClosed(self, plugin_api):
        pass

    def onTaskOpened(self, plugin_api):
        pass

    def onQuit(self, plugin_api):
        if self.is_automatic is True:
            self.cancel_autopurge()

    def deactivate(self, plugin_api):
        if self.is_automatic is True:
            self.cancel_autopurge()
        if self.menu_item_is_shown is True:
            plugin_api.remove_menu_item(self.menu_item)

## HELPER FUNCTIONS ###########################################################
    def __log(self, message):
        Log.debug(message)

## CORE FUNCTIONS #############################################################
    def schedule_autopurge(self):
        self.timer = Timer(self.TIME_BETWEEN_PURGES,
                           self.delete_old_closed_tasks)
        self.timer.setDaemon(True)
        self.timer.start()
        self.__log("Automatic deletion of old tasks scheduled")

    def cancel_autopurge(self):
        if self.timer:
            self.__log("Automatic deletion of old tasks cancelled")
            self.timer.cancel()

    def delete_old_closed_tasks(self, widget=None):
        self.__log("Starting deletion of old tasks")
        today = Date.today()
        max_days = self.preferences["max_days"]
        requester = self.plugin_api.get_requester()
        closed_tree = requester.get_tasks_tree(name='inactive')
        closed_tasks = [requester.get_task(tid) for tid in
                        closed_tree.get_all_nodes()]
        to_remove = [t for t in closed_tasks
                     if (today - t.get_closed_date()).days > max_days]

        for task in to_remove:
            if requester.has_task(task.get_id()):
                requester.delete_task(task.get_id())

        # If automatic purging is on, schedule another run
        if self.is_automatic:
            self.schedule_autopurge()

## Preferences methods ########################################################
    def is_configurable(self):
        """A configurable plugin should have this method and return True"""
        return True

    def configure_dialog(self, manager_dialog):
        self.preferences_load()
        self.preferences_dialog.set_transient_for(manager_dialog)
        self.pref_chbox_is_automatic.set_active(
            self.preferences["is_automatic"])
        self.pref_chbox_show_menu_item.set_active(
            self.preferences["show_menu_item"])
        self.pref_spinbtn_max_days.set_value(
            self.preferences["max_days"])
        self.preferences_dialog.show_all()

    def on_preferences_cancel(self, widget=None, data=None):
        self.preferences_dialog.hide()
        return True

    def on_preferences_ok(self, widget=None, data=None):
        self.preferences["is_automatic"] = \
            self.pref_chbox_is_automatic.get_active()
        self.preferences["show_menu_item"] = \
            self.pref_chbox_show_menu_item.get_active()
        self.preferences["max_days"] = \
            self.pref_spinbtn_max_days.get_value()
        self.preferences_apply()
        self.preferences_store()
        self.preferences_dialog.hide()

    def preferences_load(self):
        self.preferences = self.plugin_api.load_configuration_object(
            self.PLUGIN_NAME, "preferences",
            default_values=self.DEFAULT_PREFERENCES)

    def preferences_store(self):
        self.plugin_api.save_configuration_object(self.PLUGIN_NAME,
                                                  "preferences",
                                                  self.preferences)

    def preferences_apply(self):
        # Showing the GUI
        if self.preferences['show_menu_item'] is True and \
                self.menu_item_is_shown is False:
            self.plugin_api.add_menu_item(self.menu_item)
            self.menu_item_is_shown = True
        elif self.preferences['show_menu_item'] is False and \
                self.menu_item_is_shown is True:
            self.plugin_api.remove_menu_item(self.menu_item)
            self.menu_item_is_shown = False
        # Auto-purge
        if self.preferences['is_automatic'] is True and \
                self.is_automatic is False:
            self.is_automatic = True
            # Run the first iteration immediately and schedule next iteration
            self.delete_old_closed_tasks()
        elif self.preferences['is_automatic'] is False and \
                self.is_automatic is True:
            self.cancel_autopurge()
            self.is_automatic = False
