# -*- coding: utf-8 -*-
# Copyright (c) 2012 - Tom Kadwill <tomkadwill@gmail.com>
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

import os
import gtk
import datetime

from GTG.tools.logger import Log
from threading import Timer


###################################


class pluginUntouchedTasks:

    DEFAULT_PREFERENCES = {'max_days': 30,
                           'is_automatic': False,
                           'default_tag': '@untouched'}

    PLUGIN_NAME = "untouched-tasks"

    # In case of automatic removing tasks, the time
    # between two runs of the cleaner function
    TIME_BETWEEN_PURGES = 60 * 60

    def __init__(self):
        self.path = os.path.dirname(os.path.abspath(__file__))
        # GUI initialization
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(
                                   os.path.dirname(os.path.abspath(__file__)) +
                                   "/untouchedTasks.ui"))
        self.preferences_dialog = self.builder.get_object("preferences_dialog")
        self.pref_chbox_is_automatic = \
            self.builder.get_object("pref_chbox_is_automatic")
        self.pref_spinbtn_max_days = \
            self.builder.get_object("pref_spinbtn_max_days")
        self.pref_tag_name = \
            self.builder.get_object("pref_tag_name")
        SIGNAL_CONNECTIONS_DIC = {
            "on_preferences_dialog_delete_event":
            self.on_preferences_cancel,
            "on_btn_preferences_cancel_clicked":
            self.on_preferences_cancel,
            "on_btn_preferences_ok_clicked":
            self.on_preferences_ok,
        }
        self.builder.connect_signals(SIGNAL_CONNECTIONS_DIC)
        self.menu_item = gtk.MenuItem("Add @untouched tag")
        self.menu_item.connect('activate', self.add_untouched_tag)

    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        # preferences initialization
        self.is_automatic = False
        self.timer = None
        self.preferences_load()
        self.preferences_apply()
        # add menu item
        self.plugin_api.add_menu_item(self.menu_item)

    def deactivate(self, plugin_api):
        """
        Deactivates the plugin.
        """
        plugin_api.remove_menu_item(self.menu_item)
        # everything should be removed, in case a task is currently opened
        try:
            self.plugin_api.remove_task_toolbar_item(self.tb_Taskbutton)
        except:
            pass

## HELPER FUNCTIONS ###########################################################
    def __log(self, message):
        Log.debug(message)

## CORE FUNCTIONS #############################################################
    def schedule_autopurge(self):
        self.timer = Timer(self.TIME_BETWEEN_PURGES,
                           self.add_untouched_tag)
        self.timer.setDaemon(True)
        self.timer.start()
        self.__log("Automatic untouched tasks check scheduled")

    def cancel_autopurge(self):
        if self.timer:
            self.__log("Automatic untouched tasks check cancelled")
            self.timer.cancel()

    def add_untouched_tag(self, widget=None):
        # If no tag is picked up from preferences
        tag_name = self.pref_tag_name.get_text()
        if not tag_name:
            tag_name = self.preferences['default_tag']

        # Add @ if user has not entered it
        if tag_name.find('@') != 0:
            tag_name = '@' + tag_name

        self.__log("Starting process for adding " + tag_name)
        today = datetime.datetime.now()
        max_days = self.preferences["max_days"]
        requester = self.plugin_api.get_requester()
        closed_tree = requester.get_tasks_tree(name='inactive')
        closed_tasks = [requester.get_task(tid) for tid in
                        closed_tree.get_all_nodes()]

        # Add untouched tag to all tasks where new_date < time now
        for task in closed_tasks:
            modified_time = task.get_modified()
            new_time = modified_time + datetime.timedelta(days=max_days)
            if new_time < today:
                self.__log('Adding ' + tag_name + ' tag to: "' + task.title +
                           '" as last time it was modified was ' +
                           str(modified_time))
                task.add_tag(tag_name)

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
        self.pref_spinbtn_max_days.set_value(
            self.preferences["max_days"])
        self.pref_tag_name.set_text(
            self.preferences["default_tag"])
        self.preferences_dialog.show_all()

    def on_preferences_cancel(self, widget=None, data=None):
        self.preferences_dialog.hide()
        return True

    def on_preferences_ok(self, widget=None, data=None):
        self.preferences["is_automatic"] = \
            self.pref_chbox_is_automatic.get_active()
        self.preferences["max_days"] = \
            self.pref_spinbtn_max_days.get_value()
        self.preferences['default_tag'] = \
            self.pref_tag_name.get_text()
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
        # Auto-purge
        if self.preferences['is_automatic'] is True and \
                self.is_automatic is False:
            self.is_automatic = True
            # Run the first iteration immediately and schedule next iteration
            self.add_untouched_tag()
        elif self.preferences['is_automatic'] is False and \
                self.is_automatic is True:
            self.cancel_autopurge()
            self.is_automatic = False
