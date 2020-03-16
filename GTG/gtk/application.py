# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2015 - Lionel Dricot & Bertrand Rousseau
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

from gi.repository import GObject, Gtk, Gdk, Gio
import configparser
import os
import logging

from GTG.gtk.delete_dialog import DeletionUI
from GTG.gtk.browser.main_window import MainWindow
from GTG.gtk.editor.editor import TaskEditor
from GTG.gtk.preferences import Preferences
from GTG.gtk.plugins import PluginsDialog
from webbrowser import open as openurl
from GTG import info
from GTG.gtk.dbuswrapper import DBusTaskWrapper
from GTG.tools import clipboard
from GTG.core.plugins.engine import PluginEngine
from GTG.core.plugins.api import PluginAPI
from GTG.backends import BackendFactory
from GTG.core.datastore import DataStore
from GTG.core.dirs import CSS_DIR
from GTG.tools.logger import log
from GTG.core.dates import Date
from GTG.gtk.backends_dialog import BackendsDialog
from GTG.backends.backendsignals import BackendSignals
from GTG.gtk.browser.tag_editor import TagEditor
from GTG.core.timer import Timer


class Application(Gtk.Application):

    # List of Task URIs to open
    uri_list = NotImplemented

    # init ##################################################################
    def __init__(self, debug):

        super().__init__(application_id='org.gnome.GTGDevel')

        if debug:
            log.setLevel(logging.DEBUG)
            log.debug("Debug output enabled.")
        else:
            log.setLevel(logging.INFO)

        self.ds = DataStore()

        # Register backends
        [self.ds.register_backend(backend_dic)
         for backend_dic in BackendFactory().get_saved_backends_list()]

        # Save the backends directly to be sure projects.xml is written
        self.ds.save(quit=False)

        self.req = self.ds.get_requester()

        self.browser_config = self.req.get_config("browser")
        self.plugins_config = self.req.get_config("plugins")

        # Editors
        # This is the list of tasks that are already opened in an editor
        # of course it's empty right now
        self.opened_task = {}

        self.browser = None
        self.gtk_terminate = False  # if true, the gtk main is not started

        # Shared clipboard
        self.clipboard = clipboard.TaskClipboard(self.req)

        # Initialize Timer
        self.config = self.req.get_config('browser')
        self.timer = Timer(self.config)
        self.timer.connect('refresh', self.autoclean)

        # Deletion UI
        self.delete_dialog = None

        # Tag Editor
        self.tag_editor_dialog = None

        # Backends Editor
        self.edit_backends_dialog = None

        # Preferences and Backends windows
        self.preferences = Preferences(self.req, self)

        # Initialize  dialogs
        self.plugins = PluginsDialog(self.req)

        # Load custom css
        self._init_style()

        DBusTaskWrapper(self.req, self)

    def __init_plugin_engine(self):
        self.pengine = PluginEngine()
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

    def _init_style(self):
        """Load the application's CSS file."""

        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider()
        css_path = os.path.join(CSS_DIR, 'style.css')

        provider.load_from_path(css_path)
        Gtk.StyleContext.add_provider_for_screen(screen, provider,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _set_actions(self):
        """Setup actions."""

        action_entries = [
            ('quit', lambda a, p: self.quit(), ('app.quit', ['<ctrl>Q'])),
            ('open_about', self.open_about, None),
            ('open_plugins', self.open_plugins_manager, None),
            ('new_task', self.new_task, ('app.new_task', ['<ctrl>N'])),
            ('new_subtask', self.new_subtask,
             ('app.new_subtask', ['<ctrl><shift>N'])),
            ('edit_task', self.edit_task, ('app.edit_task', ['<ctrl>E'])),
            ('mark_as_done', self.mark_as_done,
             ('app.mark_as_done', ['<ctrl>D'])),
            ('dismiss', self.dismiss, ('app.dismiss', ['<ctrl>I'])),
            ('open_backends', self.open_backends_manager, None),
            ('open_help', self.open_help, ('app.open_help', ['F1'])),
            ('open_preferences', self.open_preferences,
                ('app.open_preferences', ['<ctrl>P'])),
        ]

        for action, callback, accel in action_entries:
            simple_action = Gio.SimpleAction.new(action, None)
            simple_action.connect('activate', callback)
            simple_action.set_enabled(True)

            self.add_action(simple_action)

            if accel is not None:
                self.set_accels_for_action(*accel)

        self.plugins.dialog.insert_action_group('app', self)


    # Browser ##############################################################
    def open_browser(self):
        if not self.browser:
            self.browser = MainWindow(self.req, self)
        # notify user if backup was used
        backend_dic = self.req.get_all_backends()
        for backend in backend_dic:
            if backend.get_name() == "backend_localfile" and \
                    backend.used_backup():
                backend.notify_user_about_backup()
        log.debug("Browser is open")

    def hide_browser(self, sender=None):
        self.browser.hide()

    def iconify_browser(self, sender=None):
        self.browser.iconify()

    def show_browser(self, sender=None):
        self.browser.present()

    def is_browser_visible(self, sender=None):
        return self.browser.is_visible()

    def get_browser(self):
        # used by the plugin api to hook in the browser
        return self.browser

    def purge_old_tasks(self, widget=None):
        log.debug("Deleting old tasks")

        today = Date.today()
        max_days = self.config.get('autoclean_days')
        closed_tree = self.req.get_tasks_tree(name='inactive')

        closed_tasks = [self.req.get_task(tid) for tid in
                        closed_tree.get_all_nodes()]

        to_remove = [t for t in closed_tasks
                     if (today - t.get_closed_date()).days > max_days]

        [self.req.delete_task(task.get_id())
         for task in to_remove
         if self.req.has_task(task.get_id())]

    def get_active_editor(self):
        """Get focused task editor window."""

        for editor in self.opened_task.values():
            if editor.window.is_active():
                return editor

    def autoclean(self, timer):
        """Run Automatic cleanup of old tasks."""

        if self.config.get('autoclean'):
            self.purge_old_tasks()

    def new_task(self, param, action):
        """Callback to add a new task."""

        self.browser.on_add_task()

    def new_subtask(self, param, action):
        """Callback to add a new subtask."""

        try:
            self.get_active_editor().insert_subtask()
        except AttributeError:
            self.browser.on_add_subtask()

    def edit_task(self, param, action):
        """Callback to edit a task."""

        self.browser.on_edit_active_task()

    def mark_as_done(self, param, action):
        """Callback to mark a task as done."""
        try:
            self.get_active_editor().change_status()
        except AttributeError:
            self.browser.on_mark_as_done()

    def dismiss(self, param, action):
        """Callback to mark a task as done."""

        try:
            self.get_active_editor().dismiss()
        except AttributeError:
            self.browser.on_dismiss_task()


# Task Editor ############################################################
    def get_opened_editors(self):
        """
        Returns a dict of task_uid -> TaskEditor, one for each opened editor
        window
        """
        return self.opened_task

    def reload_opened_editors(self, task_uid_list=None):
        """Reloads all the opened editors passed in the list 'task_uid_list'.

        If 'task_uid_list' is not passed or None, we reload all the opened editors.
        Else, we reload the editors of tasks in 'task_uid_list' only.
        """
        opened_editors = self.get_opened_editors()
        for t in opened_editors:
            if not task_uid_list or t in task_uid_list:
                opened_editors[t].reload_editor()

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
                app=self,
                task=t,
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

# Others dialog ###########################################################
    def open_about(self, action, param):
        self.browser.about.show()

    def open_edit_backends(self, sender=None, backend_id=None):
        if not self.edit_backends_dialog:
            self.edit_backends_dialog = BackendsDialog(self.req)
            self.edit_backends_dialog.dialog.insert_action_group('app', self)

        self.edit_backends_dialog.activate()
        if backend_id is not None:
            self.edit_backends_dialog.show_config_for_backend(backend_id)

    def configure_backend(self, backend_id):
        self.open_edit_backends(None, backend_id)

    def open_backends_manager(self, action, param):
        """Callback to open the backends manager dialog."""

        self.open_edit_backends()

    def open_preferences(self, action, param):
        self.preferences.activate()

    def open_plugins_manager(self, action, params):
        """Callback to open the plugins manager dialog."""

        self.plugins.activate()

    def ask_delete_tasks(self, tids, window):
        if not self.delete_dialog:
            self.delete_dialog = DeletionUI(self.req, window)
        finallist = self.delete_dialog.show(tids)
        for t in finallist:
            if t.get_id() in self.opened_task:
                self.close_task(t.get_id())

    def open_tag_editor(self, tag):
        if not self.tag_editor_dialog:
            self.tag_editor_dialog = TagEditor(self.req, self, tag)
        else:
            self.tag_editor_dialog.set_tag(tag)
        self.tag_editor_dialog.show()
        self.tag_editor_dialog.present()

    def close_tag_editor(self):
        self.tag_editor_dialog.hide()

    def open_help(self, action, param):
        """Open help callback."""

        openurl(info.HELP_URI)

# URIS #####################################################################
    def open_uri_list(self):
        """
        Open the Editor windows of the tasks associated with the uris given.
        Uris are of the form gtg://<taskid>
        """

        log.debug(f'Received {len(self.uri_list)} Task URIs')

        for uri in self.uri_list:
            if uri.startswith('gtg://'):
                log.debug(f'Opening task {uri[6:]}')
                self.open_task(uri[6:])

        # if no window was opened, we just quit
        if not self.is_browser_visible() and not self.opened_task:
            self.quit()

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

    def do_activate(self):
        """Callback when launched from the desktop."""

        # Browser (still hidden)
        if not self.browser:
            self.browser = MainWindow(self.req, self)

        self._set_actions()
        self.__init_plugin_engine()
        self.show_browser()
        self.open_uri_list()

        log.debug("Application activation finished")

    def _save_tasks(self):
        """Save opened tasks and their positions."""

        open_task = []

        for otid in list(self.opened_task.keys()):
            open_task.append(otid)
            self.opened_task[otid].close()

        self.browser_config.set("opened_tasks", open_task)

    def _save_plugin_settings(self):
        """Save plugin settings to configuration."""

        if self.pengine.plugins:
            self.plugins_config.set(
                "disabled",
                [p.module_name for p in self.pengine.get_plugins("disabled")],
            )
            self.plugins_config.set(
                "enabled",
                [p.module_name for p in self.pengine.get_plugins("enabled")],
            )

        self.pengine.deactivate_plugins()

    def quit(self):
        """Quit the application."""

        # This is needed to avoid warnings when closing the browser
        # with editor windows open, because of the "win"
        # group of actions.

        self._save_tasks()
        Gtk.Application.quit(self)

    def do_shutdown(self):
        """Callback when GTG is closed."""

        self._save_plugin_settings()

        # Save data and shutdown datastore backends
        self.req.save_datastore(quit=True)

        Gtk.Application.do_shutdown(self)
