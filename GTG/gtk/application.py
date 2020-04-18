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

"""Main class of GTG."""

from gi.repository import Gtk, Gdk, Gio
import configparser
import os
import logging

from GTG.gtk.browser.delete_task import DeletionUI
from GTG.gtk.browser.main_window import MainWindow
from GTG.gtk.editor.editor import TaskEditor
from GTG.gtk.preferences import Preferences
from GTG.gtk.plugins import PluginsDialog
from webbrowser import open as openurl
from GTG.core import info
from GTG.gtk.dbus import DBusTaskWrapper
from GTG.core import clipboard
from GTG.core.plugins.engine import PluginEngine
from GTG.core.plugins.api import PluginAPI
from GTG.backends import BackendFactory
from GTG.core.datastore import DataStore
from GTG.core.dirs import CSS_DIR
from GTG.core.logger import log
from GTG.core.dates import Date
from GTG.gtk.backends import BackendsDialog
from GTG.gtk.browser.tag_editor import TagEditor
from GTG.core.timer import Timer


class Application(Gtk.Application):

    # Requester
    req = None

    # List of Task URIs to open
    uri_list = None

    # List of opened tasks (task editor windows). Task IDs are keys,
    # while the editors are their values.
    open_tasks = {}

    # The main window (AKA Task Browser)
    browser = None

    # Configuration sections
    config = None
    config_plugins = None

    # Shared clipboard
    clipboard = None

    # Timer to refresh views and purge tasks
    timer = None

    # Plugin Engine instance
    plugin_engine = None

    # Dialogs
    preferences_dialog = None
    plugins_dialog = None
    backends_dialog = None
    delete_task_dialog = None
    edit_tag_dialog = None


    def __init__(self, debug):
        """Setup Application."""

        app_id = f'org.gnome.GTG{"devel" if debug else ""}'
        super().__init__(application_id=app_id)

        if debug:
            log.setLevel(logging.DEBUG)
            log.debug("Debug output enabled.")
        else:
            log.setLevel(logging.INFO)

        # Register backends
        datastore = DataStore()

        [datastore.register_backend(backend_dic)
         for backend_dic in BackendFactory().get_saved_backends_list()]

        # Save the backends directly to be sure projects.xml is written
        datastore.save(quit=False)

        self.req = datastore.get_requester()

        self.config = self.req.get_config("browser")
        self.config_plugins = self.req.get_config("plugins")

        self.clipboard = clipboard.TaskClipboard(self.req)

        self.timer = Timer(self.config)
        self.timer.connect('refresh', self.autoclean)

        self.preferences_dialog = Preferences(self.req, self)
        self.plugins_dialog = PluginsDialog(self.req)

        self.init_style()

        DBusTaskWrapper(self.req, self)

    # --------------------------------------------------------------------------
    # INIT
    # --------------------------------------------------------------------------

    def do_activate(self):
        """Callback when launched from the desktop."""

        # Browser (still hidden)
        if not self.browser:
            self.browser = MainWindow(self.req, self)

        if log.isEnabledFor(logging.DEBUG):
            self.browser.get_style_context().add_class('devel')

        self.init_actions()
        self.init_plugin_engine()
        self.browser.present()
        self.open_uri_list()

        log.debug("Application activation finished")

    def init_plugin_engine(self):
        """Setup the plugin engine."""

        self.plugin_engine = PluginEngine()

        plugin_api = PluginAPI(self.req, self)
        self.plugin_engine.register_api(plugin_api)

        try:
            enabled_plugins = self.config_plugins.get("enabled")
        except configparser.Error:
            enabled_plugins = []

        for plugin in self.plugin_engine.get_plugins():
            plugin.enabled = plugin.module_name in enabled_plugins

        self.plugin_engine.activate_plugins()

    def init_style(self):
        """Load the application's CSS file."""

        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider()
        add_provider = Gtk.StyleContext.add_provider_for_screen
        css_path = os.path.join(CSS_DIR, 'style.css')

        provider.load_from_path(css_path)
        add_provider(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def init_actions(self):
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
                ('app.open_preferences', ['<ctrl>comma'])),
        ]

        for action, callback, accel in action_entries:
            simple_action = Gio.SimpleAction.new(action, None)
            simple_action.connect('activate', callback)
            simple_action.set_enabled(True)

            self.add_action(simple_action)

            if accel is not None:
                self.set_accels_for_action(*accel)

        self.plugins_dialog.dialog.insert_action_group('app', self)

    def open_uri_list(self):
        """Open the Editor windows of the tasks associated with the uris given.
           Uris are of the form gtg://<taskid>
        """

        log.debug(f'Received {len(self.uri_list)} Task URIs')

        for uri in self.uri_list:
            if uri.startswith('gtg://'):
                log.debug(f'Opening task {uri[6:]}')
                self.open_task(uri[6:])

        # if no window was opened, we just quit
        if not self.browser.is_visible() and not self.open_tasks:
            self.quit()

    # --------------------------------------------------------------------------
    # ACTIONS
    # --------------------------------------------------------------------------

    def new_task(self, param=None, action=None):
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

    def open_help(self, action, param):
        """Open help callback."""

        openurl(info.HELP_URI)

    def open_backends_manager(self, action, param):
        """Callback to open the backends manager dialog."""

        self.open_edit_backends()

    def open_preferences(self, action, param):
        """Callback to open the preferences dialog."""

        self.preferences.activate()

    def open_about(self, action, param):
        """Callback to open the about dialog."""

        self.browser.about.show()

    def open_plugins_manager(self, action, params):
        """Callback to open the plugins manager dialog."""

        self.plugins_dialog.activate()

    # --------------------------------------------------------------------------
    # TASKS AUTOCLEANING
    # --------------------------------------------------------------------------

    def purge_old_tasks(self, widget=None):
        """Remove closed tasks older than N days."""

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

    def autoclean(self, timer):
        """Run Automatic cleanup of old tasks."""

        if self.config.get('autoclean'):
            self.purge_old_tasks()

    # --------------------------------------------------------------------------
    # TASK BROWSER API
    # --------------------------------------------------------------------------

    def open_edit_backends(self, sender=None, backend_id=None):
        """Open the backends dialog."""

        self.backends_dialog = BackendsDialog(self.req)
        self.backends_dialog.dialog.insert_action_group('app', self)

        self.backends_dialog.activate()

        if backend_id:
            self.backends_dialog.show_config_for_backend(backend_id)


    def delete_tasks(self, tids, window):
        """Present the delete task confirmation dialog."""

        if not self.delete_task_dialog:
            self.delete_task_dialog = DeletionUI(self.req, window)

        tags_to_delete = self.delete_task_dialog.show(tids)

        [self.close_task(task.get_id()) for task in tags_to_delete
         if task.get_id() in self.open_tasks]

    def open_tag_editor(self, tag):
        """Open Tag editor dialog."""

        if not self.edit_tag_dialog:
            self.edit_tag_dialog = TagEditor(self.req, self, tag)
        else:
            self.edit_tag_dialog.set_tag(tag)

        self.edit_tag_dialog.present()

    def close_tag_editor(self):
        """Close tag editor dialog."""

        self.edit_tag_dialog.hide()

    # --------------------------------------------------------------------------
    # TASK EDITOR API
    # --------------------------------------------------------------------------

    def reload_opened_editors(self, task_uid_list=None):
        """Reloads all the opened editors passed in the list 'task_uid_list'.

        If 'task_uid_list' is not passed or None, we reload all the opened
        editors.
        """

        if task_uid_list:
            [self.open_tasks[tid].reload_editor() for tid in self.open_tasks
             if tid in task_uid_list]
        else:
            [task.reload_editor() for task in self.open_tasks]

    def open_task(self, uid, new=False):
        """Open the task identified by 'uid'.

            If a Task editor is already opened for a given task, we present it.
            Otherwise, we create a new one.
        """

        if uid in self.open_tasks:
            editor = self.open_tasks[uid]
            editor.present()

        else:
            task = self.req.get_task(uid)
            editor = None

            if task:
                editor = TaskEditor(requester=self.req, app=self, task=task,
                                    thisisnew=new, clipboard=self.clipboard)

                editor.present()
                self.open_tasks[uid] = editor

                # Save open tasks to config
                open_tasks = self.config.get("opened_tasks")

                if uid not in open_tasks:
                    open_tasks.append(uid)

                self.config.set("opened_tasks", open_tasks)

            else:
                log.error(f'Task {uid} could not be found!')

        return editor

    def get_active_editor(self):
        """Get focused task editor window."""

        for editor in self.open_tasks.values():
            if editor.window.is_active():
                return editor

    def close_task(self, tid):
        """Close a task editor window."""

        if tid in self.open_tasks:
            editor = self.open_tasks[tid]

            # We have to remove the tid first, otherwise
            # close_task would be called once again
            # by editor.close
            del self.open_tasks[tid]

            editor.close()

        open_tasks = self.config.get("opened_tasks")

        if tid in open_tasks:
            open_tasks.remove(tid)

        self.config.set("opened_tasks", open_tasks)

    # --------------------------------------------------------------------------
    # SHUTDOWN
    # --------------------------------------------------------------------------

    def save_tasks(self):
        """Save opened tasks and their positions."""

        open_task = []

        for otid in list(self.open_tasks.keys()):
            open_task.append(otid)
            self.open_tasks[otid].close()

        self.config.set("opened_tasks", open_task)

    def save_plugin_settings(self):
        """Save plugin settings to configuration."""

        if self.plugin_engine.plugins:
            self.config_plugins.set(
                'disabled',
                [p.module_name
                 for p in self.plugin_engine.get_plugins('disabled')])

            self.config_plugins.set(
                'enabled',
                [p.module_name
                 for p in self.plugin_engine.get_plugins('enabled')])

        self.plugin_engine.deactivate_plugins()

    def quit(self):
        """Quit the application."""

        # This is needed to avoid warnings when closing the browser
        # with editor windows open, because of the "win"
        # group of actions.

        self.save_tasks()
        Gtk.Application.quit(self)

    def do_shutdown(self):
        """Callback when GTG is closed."""

        self.save_plugin_settings()

        # Save data and shutdown datastore backends
        self.req.save_datastore(quit=True)

        Gtk.Application.do_shutdown(self)
