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
import urllib.parse # GLibs URI functions not available for some reason

from GTG.gtk.browser.delete_task import DeletionUI
from GTG.gtk.browser.main_window import MainWindow
from GTG.gtk.editor.editor import TaskEditor
from GTG.gtk.editor import text_tags
from GTG.gtk.preferences import Preferences
from GTG.gtk.plugins import PluginsDialog
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

    def __init__(self, app_id):
        """Setup Application."""

        super().__init__(application_id=app_id,
                         flags=Gio.ApplicationFlags.HANDLES_OPEN)

    # --------------------------------------------------------------------------
    # INIT
    # --------------------------------------------------------------------------

    def do_startup(self):
        """Callback when primary instance should initialize"""
        Gtk.Application.do_startup(self)

        # Register backends
        datastore = DataStore()

        for backend_dic in BackendFactory().get_saved_backends_list():
            datastore.register_backend(backend_dic)

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

        if self.config.get('dark_mode'):
            self.toggle_darkmode()

        self.init_style()

    def do_activate(self):
        """Callback when launched from the desktop."""

        self.init_shared()
        self.browser.present()

        log.debug("Application activation finished")

    def do_open(self, files, n_files, hint):
        """Callback when opening files/tasks"""

        self.init_shared()

        log.debug(f'Received {len(files)} Task URIs')
        if len(files) != n_files:
            log.warning(f"Length of files {len(files)} != supposed length {n_files}")

        for file in files:
            if file.get_uri_scheme() == 'gtg':
                uri = file.get_uri()
                if uri[4:6] != '//':
                    log.info(f"Malformed URI, needs gtg://: {uri}")
                else:
                    parsed = urllib.parse.urlparse(uri)
                    task_id = parsed.netloc
                    log.debug(f'Opening task {task_id}')
                    self.open_task(task_id)
            else:
                log.info(f"Unknown task to open: {file.get_uri()}")

        log.debug("Application opening finished")

    def init_shared(self):
        """
        Initialize stuff that can't be done in the startup signal,
        but in the open or activate signals, otherwise GTK will segfault
        when creating windows in the startup signal
        """
        if not self.browser: # Prevent multiple inits
            self.init_browser()
            self.init_actions()
            self.init_plugin_engine()
            self.browser.present()

    def init_browser(self):
        # Browser (still hidden)
        if not self.browser:
            self.browser = MainWindow(self.req, self)

            if self.props.application_id == 'org.gnome.GTGDevel':
                self.browser.get_style_context().add_class('devel')

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

    def toggle_darkmode(self, state=True):
        """Use dark mode theme."""

        settings = Gtk.Settings.get_default()
        prefs_css = self.preferences_dialog.window.get_style_context()
        settings.set_property("gtk-application-prefer-dark-theme", state)

        # Toggle dark mode for preferences and editors
        if state:
            prefs_css.add_class('dark')
            text_tags.use_dark_mode()
        else:
            prefs_css.remove_class('dark')
            text_tags.use_light_mode()

    def init_actions(self):
        """Setup actions."""

        action_entries = [
            ('quit', lambda a, p: self.quit(), ('app.quit', ['<ctrl>Q'])),
            ('open_about', self.open_about, None),
            ('open_plugins', self.open_plugins_manager, None),
            ('new_task', self.new_task, ('app.new_task', ['<ctrl>N'])),
            ('new_subtask', self.new_subtask, ('app.new_subtask', ['<ctrl><shift>N'])),
            ('edit_task', self.edit_task, ('app.edit_task', ['<ctrl>E'])),
            ('mark_as_done', self.mark_as_done, ('app.mark_as_done', ['<ctrl>D'])),
            ('dismiss', self.dismiss, ('app.dismiss', ['<ctrl>I'])),
            ('open_backends', self.open_backends_manager, None),
            ('open_help', self.open_help, ('app.open_help', ['F1'])),
            ('open_preferences', self.open_preferences, ('app.open_preferences', ['<ctrl>comma'])),
            ('close', self.close_context, ('app.close', ['Escape'])),
            ('editor.close', self.close_focused_task, ('app.editor.close', ['<ctrl>w'])),
            ('editor.show_parent', self.open_parent_task, None),
            ('editor.delete', self.delete_editor_task, None),
            ('editor.open_tags_popup', self.open_tags_popup_in_editor, None),
        ]

        for action, callback, accel in action_entries:
            simple_action = Gio.SimpleAction.new(action, None)
            simple_action.connect('activate', callback)
            simple_action.set_enabled(True)

            self.add_action(simple_action)

            if accel is not None:
                self.set_accels_for_action(*accel)

        self.plugins_dialog.dialog.insert_action_group('app', self)

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

        try:
            Gtk.show_uri(None, "help:gtg", Gdk.CURRENT_TIME)
        except GLib.Error:
            log.error('Could not open help')

    def open_backends_manager(self, action, param):
        """Callback to open the backends manager dialog."""

        self.open_edit_backends()

    def open_preferences(self, action, param):
        """Callback to open the preferences dialog."""

        self.preferences_dialog.activate()
        self.preferences_dialog.window.set_transient_for(self.browser)

    def open_about(self, action, param):
        """Callback to open the about dialog."""

        self.browser.about.show()

    def open_plugins_manager(self, action, params):
        """Callback to open the plugins manager dialog."""

        self.plugins_dialog.activate()
        self.plugins_dialog.dialog.set_transient_for(self.browser)


    def close_context(self, action, params):
        """Callback to close based on the focus widget."""

        editor = self.get_active_editor()
        search = self.browser.search_entry.is_focus()

        if editor:
            self.close_task(editor.task.get_id())
        elif search:
            self.browser.toggle_search(action, params)

    def close_focused_task(self, action, params):
        """Callback to close currently focused task editor."""

        editor = self.get_active_editor()

        if editor:
            self.close_task(editor.task.get_id())

    def delete_editor_task(self, action, params):
        """Callback to delete the task currently open."""

        editor = self.get_active_editor()
        task = editor.task

        if task.is_new():
            self.close_task(task.get_id())
        else:
            self.delete_tasks([task.get_id()], editor.window)

    def open_tags_popup_in_editor(self, action, params):
        """Callback to open the tags popup in the focused task editor."""

        editor = self.get_active_editor()
        editor.open_tags_popover()

    def open_parent_task(self, action, params):
        """Callback to open the parent of the currently open task."""

        editor = self.get_active_editor()
        editor.open_parent()

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

        tasks_to_delete = self.delete_task_dialog.show(tids)

        [self.close_task(task.get_id()) for task in tasks_to_delete
         if task.get_id() in self.open_tasks]

    def open_tag_editor(self, tag):
        """Open Tag editor dialog."""

        if not self.edit_tag_dialog:
            self.edit_tag_dialog = TagEditor(self.req, self, tag)
            self.edit_tag_dialog.set_transient_for(self.browser)
            self.edit_tag_dialog.insert_action_group('app', self)
        else:
            self.edit_tag_dialog.set_tag(tag)

        self.edit_tag_dialog.present()

    def close_tag_editor(self):
        """Close tag editor dialog."""

        self.edit_tag_dialog.hide()

    def select_tag(self, tag):
        """Select a tag in the browser."""

        self.browser.select_on_sidebar(tag)

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

        try:
            editor = self.open_tasks[tid]
            editor.close()

            open_tasks = self.config.get("opened_tasks")

            if tid in open_tasks:
                open_tasks.remove(tid)

            self.config.set("opened_tasks", open_tasks)

        except KeyError:
            log.debug(f'Tried to close tid {tid} but it is not open')

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

        if self.plugin_engine is None:
            return # Can't save when none has been loaded

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

        if self.req is not None:
            # Save data and shutdown datastore backends
            self.req.save_datastore(quit=True)

        Gtk.Application.do_shutdown(self)

    # --------------------------------------------------------------------------
    # MISC
    # --------------------------------------------------------------------------

    def set_debug_flag(self, debug):
        """Set whenever it should activate debug stuff like logging or not"""
        if debug:
            log.setLevel(logging.DEBUG)
            log.debug("Debug output enabled.")
        else:
            log.setLevel(logging.INFO)

