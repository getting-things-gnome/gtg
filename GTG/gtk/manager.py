# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
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
"""
Manager loads the prefs and launches the gtk main loop
"""

from gi.repository import GObject, Gtk
import configparser

import GTG
from GTG.gtk.delete_dialog import DeletionUI
from GTG.gtk.browser.browser import TaskBrowser
from GTG.gtk.editor.editor import TaskEditor
from GTG.gtk.preferences import PreferencesDialog
from GTG.gtk.plugins import PluginsDialog
from GTG.gtk.dbuswrapper import DBusTaskWrapper
from GTG.tools import clipboard
from GTG.core.plugins.engine import PluginEngine
from GTG.core.plugins.api import PluginAPI
from GTG.tools.logger import Log
from GTG.gtk.backends_dialog import BackendsDialog
from GTG.backends.backendsignals import BackendSignals
from GTG.gtk.browser.tag_editor import TagEditor
from GTG.core.timer import Timer


class Manager(GObject.GObject):

    __object_signal__ = (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE,
                         (GObject.TYPE_PYOBJECT,))
    __object_string_signal__ = (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE,
                                (GObject.TYPE_PYOBJECT, GObject.TYPE_STRING, ))
    __gsignals__ = {'tasks-deleted': __object_signal__,
                    'task-status-changed': __object_string_signal__,
                    }

    # init ##################################################################
    def __init__(self, req):
        GObject.GObject.__init__(self)
        self.req = req
        self.config_obj = self.req.get_global_config()
        self.browser_config = self.config_obj.get_subconfig("browser")
        self.plugins_config = self.config_obj.get_subconfig("plugins")
        self.task_config = self.config_obj.get_taskconfig()

        # Editors
        # This is the list of tasks that are already opened in an editor
        # of course it's empty right now
        self.opened_task = {}

        self.browser = None
        self.__start_browser_hidden = False
        self.gtk_terminate = False  # if true, the gtk main is not started

        # if true, closing the last window doesn't quit GTG
        # (GTG lives somewhere else without GUI, e.g. notification area)
        self.daemon_mode = False

        # Shared clipboard
        self.clipboard = clipboard.TaskClipboard(self.req)

        # Initialize Timer
        self.config = self.req.get_config('browser')
        self.timer = Timer(self.config)

        # Browser (still hidden)
        self.browser = TaskBrowser(self.req, self)

        self.__init_plugin_engine()

        if not self.__start_browser_hidden:
            self.show_browser()

        # Deletion UI
        self.delete_dialog = None

        # Preferences and Backends windows
        # Initialize  dialogs
        self.preferences = PreferencesDialog(self.req, self)
        self.plugins = PluginsDialog(self.config_obj)
        self.edit_backends_dialog = None

        # Tag Editor
        self.tag_editor_dialog = None

        # DBus
        DBusTaskWrapper(self.req, self)
        Log.debug("Manager initialization finished")

    def __init_plugin_engine(self):
        self.pengine = PluginEngine(GTG.PLUGIN_DIR)
        # initializes the plugin api class
        self.plugin_api = PluginAPI(self.req, self)
        self.pengine.register_api(self.plugin_api)
        # checks the conf for user settings
        try:
            plugins_enabled = self.plugins_config.get("enabled")
        except configparser.Error:
            plugins_enabled = []
        for plugin in self.pengine.get_plugins():
            plugin.enabled = plugin.module_name in plugins_enabled
        # initializes and activates each plugin (that is enabled)
        self.pengine.activate_plugins()

    # Browser ##############################################################
    def open_browser(self):
        if not self.browser:
            self.browser = TaskBrowser(self.req, self)
        # notify user if backup was used
        backend_dic = self.req.get_all_backends()
        for backend in backend_dic:
            if backend.get_name() == "backend_localfile" and \
                    backend.used_backup():
                backend.notify_user_about_backup()
        Log.debug("Browser is open")

    # FIXME : the browser should not be the center of the universe.
    # In fact, we should build a system where view can register themselves
    # as "stay_alive" views. As long as at least one "stay_alive" view
    # is registered, gtg keeps running. It quit only when the last
    # "stay_alive view" is closed (and then unregistered).
    # Currently, the browser is our only "stay_alive" view.
    def close_browser(self, sender=None):
        self.hide_browser()
        # may take a while to quit
        self.quit()

    def hide_browser(self, sender=None):
        self.browser.hide()

    def iconify_browser(self, sender=None):
        self.browser.iconify()

    def show_browser(self, sender=None):
        self.browser.show()

    def is_browser_visible(self, sender=None):
        return self.browser.is_visible()

    def get_browser(self):
        # used by the plugin api to hook in the browser
        return self.browser

    def start_browser_hidden(self):
        self.__start_browser_hidden = True

    def set_daemon_mode(self, in_daemon_mode):
        """ Used by notification area plugin to override the behavior:
        last closed window quits GTG """
        self.daemon_mode = in_daemon_mode

# Task Editor ############################################################
    def get_opened_editors(self):
        '''
        Returns a dict of task_uid -> TaskEditor, one for each opened editor
        window
        '''
        return self.opened_task

    def open_task(self, uid, thisisnew=False):
        """Open the task identified by 'uid'.

        If a Task editor is already opened for a given task, we present it.
        Else, we create a new one.
        """
        t = self.req.get_task(uid)
        tv = None
        if uid in self.opened_task:
            tv = self.opened_task[uid]
            tv.present()
        elif t:
            tv = TaskEditor(
                requester=self.req,
                vmanager=self,
                task=t,
                taskconfig=self.task_config,
                thisisnew=thisisnew,
                clipboard=self.clipboard)
            tv.present()
            # registering as opened
            self.opened_task[uid] = tv
            # save that we opened this task
            opened_tasks = self.browser_config.get("opened_tasks")
            if uid not in opened_tasks:
                opened_tasks.append(uid)
            self.browser_config.set("opened_tasks", opened_tasks)
        return tv

    def close_task(self, tid):
        # When an editor is closed, it should de-register itself.
        if tid in self.opened_task:
            # the following line has the side effect of removing the
            # tid key in the opened_task dictionary.
            editor = self.opened_task[tid]
            if editor:
                del self.opened_task[tid]
                # we have to remove the tid from opened_task first
                # else, it close_task would be called once again
                # by editor.close
                editor.close()
            opened_tasks = self.browser_config.get("opened_tasks")
            if tid in opened_tasks:
                opened_tasks.remove(tid)
            self.browser_config.set("opened_tasks", opened_tasks)
        self.check_quit_condition()

    def check_quit_condition(self):
        '''
        checking if we need to shut down the whole GTG (if no window is open)
        '''
        if not self.daemon_mode and not self.is_browser_visible() and \
                not self.opened_task:
            # no need to live"
            self.quit()

# Others dialog ###########################################################
    def open_edit_backends(self, sender=None, backend_id=None):
        if not self.edit_backends_dialog:
            self.edit_backends_dialog = BackendsDialog(self.req)
        self.edit_backends_dialog.activate()
        if backend_id is not None:
            self.edit_backends_dialog.show_config_for_backend(backend_id)

    def configure_backend(self, backend_id):
        self.open_edit_backends(None, backend_id)

    def open_preferences(self, config_priv):
        self.preferences.activate()

    def configure_plugins(self):
        self.plugins.activate()

    def ask_delete_tasks(self, tids):
        if not self.delete_dialog:
            self.delete_dialog = DeletionUI(self.req)
        finallist = self.delete_dialog.delete_tasks(tids)
        for t in finallist:
            if t.get_id() in self.opened_task:
                self.close_task(t.get_id())
        GObject.idle_add(self.emit, "tasks-deleted", finallist)
        return finallist

    def open_tag_editor(self, tag):
        if not self.tag_editor_dialog:
            self.tag_editor_dialog = TagEditor(self.req, self, tag)
        else:
            self.tag_editor_dialog.set_tag(tag)
        self.tag_editor_dialog.show()
        self.tag_editor_dialog.present()

    def close_tag_editor(self):
        self.tag_editor_dialog.hide()

# STATUS #####################################################################
    def ask_set_task_status(self, task, new_status):
        '''
        Both browser and editor have to use this central method to set
        task status. It also emits a signal with the task instance as first
        and the new status as second parameter
        '''
        task.set_status(new_status)
        GObject.idle_add(self.emit, "task-status-changed", task, new_status)

# URIS #####################################################################
    def open_uri_list(self, unused, uri_list):
        '''
        Open the Editor windows of the tasks associated with the uris given.
        Uris are of the form gtg://<taskid>
        '''
        for uri in uri_list:
            if uri.startswith("gtg://"):
                self.open_task(uri[6:])
        # if no window was opened, we just quit
        self.check_quit_condition()

# MAIN #####################################################################
    def main(self, once_thru=False, uri_list=[]):
        if uri_list:
            # before opening the requested tasks, we make sure that all of them
            # are loaded.
            BackendSignals().connect('default-backend-loaded',
                                     self.open_uri_list,
                                     uri_list)
        else:
            self.open_browser()
        GObject.threads_init()
        if not self.gtk_terminate:
            if once_thru:
                Gtk.main_iteration()
            else:
                Gtk.main()
        return 0

    def quit(self, sender=None):
        Gtk.main_quit()
        # save opened tasks and their positions.
        open_task = []
        for otid in list(self.opened_task.keys()):
            open_task.append(otid)
            self.opened_task[otid].close()
        self.browser_config.set("opened_tasks", open_task)

        # adds the plugin settings to the conf
        # FIXME: this code is replicated in the preference window.
        if len(self.pengine.plugins) > 0:
            self.plugins_config.clear()
            self.plugins_config.set(
                "disabled",
                [p.module_name for p in self.pengine.get_plugins("disabled")],
            )
            self.plugins_config.set(
                "enabled",
                [p.module_name for p in self.pengine.get_plugins("enabled")],
            )
        # plugins are deactivated
        self.pengine.deactivate_plugins()
