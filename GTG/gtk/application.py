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

from gi.repository import Gtk, Gdk, Gio, GLib, Xdp
import configparser
import os
import sys
import logging
import urllib.parse  # GLibs URI functions not available for some reason


from GTG.core.dirs import DATA_DIR
from GTG.core.datastore import Datastore
from GTG.core.tasks import Filter

from GTG.gtk.browser.delete_task import DeletionUI
from GTG.gtk.browser.main_window import MainWindow
from GTG.gtk.editor.editor import TaskEditor
from GTG.gtk.editor import text_tags
from GTG.gtk.preferences import Preferences
from GTG.gtk.plugins import PluginsDialog
from GTG.core import clipboard
from GTG.core.config import CoreConfig
from GTG.core.plugins.engine import PluginEngine
from GTG.core.plugins.api import PluginAPI
from GTG.backends import BackendFactory
from GTG.core.dirs import CSS_DIR
from GTG.core.dates import Date
from GTG.gtk.backends import BackendsDialog
from GTG.gtk.browser.tag_editor import TagEditor
from GTG.gtk.browser.search_editor import SearchEditor
from GTG.core.timer import Timer
from GTG.gtk.errorhandler import do_error_dialog

log = logging.getLogger(__name__)


class Application(Gtk.Application):

    portal: Xdp.Portal | None = None
    settings: Xdp.Settings | None = None
    ds: Datastore = Datastore()
    """Datastore loaded with the default data file"""

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

        self._exception = None
        """Exception that occurred in startup, None otherwise"""

        self._exception_dialog_timeout_id = None
        """
        Gio Source ID of an timer used to automatically kill GTG on
        startup error.
        """

        super().__init__(application_id=app_id,
                         flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.set_option_context_parameter_string("[gtg://TASK-ID…]")

        self.portal = Xdp.Portal.initable_new()
        if self.portal:
            self.settings = self.portal.get_settings()

    # --------------------------------------------------------------------------
    # INIT
    # --------------------------------------------------------------------------

    def do_startup(self):
        """Callback when primary instance should initialize"""
        try:
            Gtk.Application.do_startup(self)
            Gtk.Window.set_default_icon_name(self.props.application_id)

            # Load default file
            data_file = os.path.join(DATA_DIR, 'gtg_data.xml')
            self.ds.find_and_load_file(data_file)

            for backend_dic in BackendFactory().get_saved_backends_list():
                self.ds.register_backend(backend_dic)

            self.config_core = CoreConfig()
            self.config = self.config_core.get_subconfig('browser')
            self.config_plugins = self.config_core.get_subconfig('plugins')

            self.clipboard = clipboard.TaskClipboard(self.ds)

            self.timer = Timer(self.config)
            self.timer.connect('refresh', self.autoclean)

            self.preferences_dialog = Preferences(self)
            self.plugins_dialog = PluginsDialog(self.config_plugins)

            if self.portal:
                self.settings.connect("changed", self.update_theme)

                namespace = "org.gnome.desktop.interface"
                key = "color-scheme"
                state = self.settings.read_string(namespace, key) == "prefer-dark"
            else:
                state = self.config.get('dark_mode')

            self.toggle_darkmode(state)

            self.init_style()
        except Exception as e:
            self._exception = e
            log.exception("Exception during startup")
            self._exception_dialog_timeout_id = GLib.timeout_add(
                # priority is a kwarg for some reason not reflected in the docs
                5000, self._startup_exception_timeout, None)
             # Don't re-raise to not trigger the global exception hook

    def do_activate(self):
        """Callback when launched from the desktop."""

        if self._check_exception():
            return

        try:
            self.init_shared()
            self.browser.present()
            self.browser.restore_editor_windows()

            log.debug("Application activation finished")
        except Exception:
            log.exception("Exception during activation")
            dialog = do_error_dialog(self._exception, "Activation", ignorable=False)
            dialog.set_application(self)  # Keep application alive to show it

    def do_open(self, files, n_files, hint):
        """Callback when opening files/tasks"""

        if self._check_exception():
            return

        try:
            self.init_shared()
            len_files = len(files)
            log.debug("Received %d Task URIs", len_files)
            if len_files != n_files:
                log.warning("Length of files %d != supposed length %d", len_files, n_files)

            for file in files:
                if file.get_uri_scheme() == 'gtg':
                    uri = file.get_uri()
                    if uri[4:6] != '//':
                        log.info("Malformed URI, needs gtg://:%s", uri)
                    else:
                        parsed = urllib.parse.urlparse(uri)
                        task_id = parsed.netloc
                        log.debug("Opening task %s", task_id)
                        self.open_task(task_id)
                else:
                    log.info("Unknown task to open: %s", file.get_uri())

            log.debug("Application opening finished")
        except Exception:
            log.exception("Exception during opening")
            dialog = do_error_dialog(self._exception, "Opening", ignorable=False)
            dialog.set_application(self)  # Keep application alive to show it

    def _check_exception(self) -> bool:
        """
        Checks whenever an error occured before at startup, and shows an dialog.
        Returns True whenever such error occurred, False otherwise.
        """
        if self._exception is not None:
            GLib.Source.remove(self._exception_dialog_timeout_id)
            self._exception_dialog_timeout_id = None
            dialog = do_error_dialog(self._exception, "Startup", ignorable=False)
            dialog.set_application(self)  # Keep application alive, for now
        return self._exception is not None

    def _startup_exception_timeout(self, user_data):
        """
        Called when an exception in startup occurred, but didn't go over
        activation/opening a "file" within a specified amount of time.
        This can be caused by for example trying to call an DBus service,
        get an error during startup.

        It also means GTG was started in the background, so showing the user
        suddenly an error message isn't great, and thus this will just exit
        the application.

        Since this is an error case, the normal shutdown procedure isn't used
        but rather a python exit.
        """
        log.info("Exiting because of startup exception timeout")
        GLib.Source.remove(self._exception_dialog_timeout_id)
        self._exception_dialog_timeout_id = None
        sys.exit(1)

    def init_shared(self):
        """
        Initialize stuff that can't be done in the startup signal,
        but in the open or activate signals, otherwise GTK will segfault
        when creating windows in the startup signal
        """
        if not self.browser:  # Prevent multiple inits
            self.init_browser()
            self.init_actions()
            self.init_plugin_engine()
            self.browser.present()

    def init_browser(self):
        # Browser (still hidden)
        if not self.browser:
            self.browser = MainWindow(self)
            self.browser.restore_tag_selection()

            if self.props.application_id == 'org.gnome.GTG.Devel':
                self.browser.add_css_class('devel')

    def init_plugin_engine(self):
        """Setup the plugin engine."""

        self.plugin_engine = PluginEngine()
        plugin_api = PluginAPI(self)
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

        display = Gdk.Display.get_default()
        provider = Gtk.CssProvider()
        add_provider = Gtk.StyleContext.add_provider_for_display
        css_path = os.path.join(CSS_DIR, 'style.css')

        provider.load_from_path(css_path)
        add_provider(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def toggle_darkmode(self, state=True):
        """Use dark mode theme."""

        settings = Gtk.Settings.get_default()
        settings.set_property("gtk-application-prefer-dark-theme", state)

        # Toggle dark mode for preferences and editors
        if state:
            self.preferences_dialog.add_css_class('dark')
            text_tags.use_dark_mode()
        else:
            self.preferences_dialog.remove_css_class('dark')
            text_tags.use_light_mode()

    def init_actions(self):
        """Setup actions."""

        action_entries = [
            ('quit', lambda a, p: self.quit(), ('app.quit', ['<ctrl>Q'])),
            ('open_about', self.open_about, None),
            ('open_plugins', self.open_plugins_manager, None),
            ('new_task', self.new_task, ('app.new_task', ['<ctrl>N'])),
            ('new_subtask', self.new_subtask, ('app.new_subtask', ['<ctrl><shift>N'])),
            ('add_parent', self.add_parent, ('app.add_parent', ['<ctrl><shift>P'])),
            ('edit_task', self.edit_task, ('app.edit_task', ['<ctrl>E'])),
            ('mark_as_done', self.mark_as_done, ('app.mark_as_done', ['<ctrl>D'])),
            ('dismiss', self.dismiss, ('app.dismiss', ['<ctrl><shift>D'])),
            ('reopen', self.reopen, ('app.reopen', ['<ctrl>O'])),
            ('open_backends', self.open_backends_manager, None),
            ('open_help', self.open_help, ('app.open_help', ['F1'])),
            ('open_preferences', self.open_preferences, ('app.open_preferences', ['<ctrl>comma'])),
            ('close', self.close_context, ('app.close', ['Escape'])),
            ('editor.close', self.close_focused_task, ('app.editor.close', ['<ctrl>w'])),
            ('editor.show_parent', self.open_parent_task, None),
            ('editor.delete', self.delete_editor_task, None)
        ]

        for action, callback, accel in action_entries:
            simple_action = Gio.SimpleAction.new(action, None)
            simple_action.connect('activate', callback)
            simple_action.set_enabled(True)

            self.add_action(simple_action)

            if accel is not None:
                self.set_accels_for_action(*accel)

        self.plugins_dialog.insert_action_group('app', self)

    # --------------------------------------------------------------------------
    # ACTIONS
    # --------------------------------------------------------------------------

    def update_theme(self, _settings, namespace, key, value, *args):
        """
        Callback to set color theme according to the user's
        color-scheme preference.
        """

        if namespace == "org.gnome.desktop.interface" and key == "color-scheme":
            state = self.settings.read_string(namespace, key) == "prefer-dark"
            self.toggle_darkmode(state)

    def new_task(self, param=None, action=None):
        """Callback to add a new task."""

        self.browser.on_add_task()

    def new_subtask(self, param, action):
        """Callback to add a new subtask."""

        try:
            self.get_active_editor().insert_subtask()
        except AttributeError:
            self.browser.on_add_subtask()

    def add_parent(self, param, action):
        """Callback to add a parent to a task"""

        self.browser.on_add_parent()


    def edit_task(self, param, action):
        """Callback to edit a task."""

        self.browser.on_edit_active_task()

    def mark_as_done(self, param, action):
        """Callback to mark a task as done."""

        try:
            self.get_active_editor().change_status()
        except AttributeError:
            self.browser.on_mark_as_done()
        finally:
            self.browser.get_pane().refresh()

    def dismiss(self, param, action):
        """Callback to mark a task as done."""

        try:
            self.get_active_editor().toggle_dismiss()
        except AttributeError:
            self.browser.on_dismiss_task()
        finally:
            self.browser.get_pane().refresh()

    def reopen(self, param, action):
        """Callback to mark task as open."""

        try:
            self.get_active_editor().reopen()
        except AttributeError:
            self.browser.on_reopen_task()
        finally:
            self.browser.get_pane().refresh()

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
        self.preferences_dialog.set_transient_for(self.browser)

    def open_about(self, action, param):
        """Callback to open the about dialog."""

        self.browser.about.show()

    def open_plugins_manager(self, action, params):
        """Callback to open the plugins manager dialog."""

        self.plugins_dialog.activate()
        self.plugins_dialog.set_transient_for(self.browser)


    def close_context(self, action, params):
        """Callback to close based on the focus widget."""

        editor = self.get_active_editor()
        search = self.browser.search_entry.is_focus()

        if editor:
            self.close_task(editor.task.id)
        elif search:
            self.browser.toggle_search(action, params)

    def close_focused_task(self, action, params):
        """Callback to close currently focused task editor."""

        editor = self.get_active_editor()

        if editor:
            self.close_task(editor.task.id)

    def delete_editor_task(self, action, params):
        """Callback to delete the task currently open."""

        editor = self.get_active_editor()
        task = editor.task

        if editor.is_new():
            self.close_task(task)
        else:
            self.delete_tasks([task], editor)

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
        closed_tasks = self.ds.tasks.filter(Filter.CLOSED)

        to_remove = [t for t in closed_tasks
                     if (today - t.date_closed).days > max_days]

        for t in to_remove:
            self.ds.tasks.remove(t.id)


    def autoclean(self, timer):
        """Run Automatic cleanup of old tasks."""

        if self.config.get('autoclean'):
            self.purge_old_tasks()

    # --------------------------------------------------------------------------
    # TASK BROWSER API
    # --------------------------------------------------------------------------

    def open_edit_backends(self, sender=None, backend_id=None):
        """Open the backends dialog."""

        self.backends_dialog = BackendsDialog(self.ds)
        self.backends_dialog.dialog.insert_action_group('app', self)

        self.backends_dialog.activate()

        if backend_id:
            self.backends_dialog.show_config_for_backend(backend_id)

    def delete_tasks(self, tasks, window):
        """Present the delete task confirmation dialog."""

        if not self.delete_task_dialog:
            self.delete_task_dialog = DeletionUI(window, self.ds)

        def on_show_async_callback(tasks_to_delete):
            [self.close_task(task.id) for task in tasks_to_delete
            if task.id in self.open_tasks]

        self.delete_task_dialog.show_async(tasks, on_show_async_callback)

    def open_tag_editor(self, tag):
        """Open Tag editor dialog."""

        self.edit_tag_dialog = TagEditor(self, tag)
        self.edit_tag_dialog.set_transient_for(self.browser)
        self.edit_tag_dialog.insert_action_group('app', self)


    def open_search_editor(self, search):
        """Open Saved search editor dialog."""

        self.edit_search_dialog = SearchEditor(self, search)
        self.edit_search_dialog.set_transient_for(self.browser)
        self.edit_search_dialog.insert_action_group('app', self)

    def close_search_editor(self):
        """Close search editor dialog."""

        self.edit_search_dialog = None

    def close_tag_editor(self):
        """Close tag editor dialog."""

        self.edit_tag_dialog = None

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

    def open_task(self, task, new=False):
        """Open the task identified by 'uid'.

            If a Task editor is already opened for a given task, we present it.
            Otherwise, we create a new one.
        """

        if task.id in self.open_tasks:
            editor = self.open_tasks[task.id]
            editor.present()

        else:
            editor = TaskEditor(app=self, task=task)
            editor.present()

            self.open_tasks[task.id] = editor

            # Save open tasks to config
            config_open_tasks = self.config.get("opened_tasks")

            if task.id not in config_open_tasks:
                config_open_tasks.append(task.id)

            self.config.set("opened_tasks", config_open_tasks)

        return editor


    def get_active_editor(self):
        """Get focused task editor window."""

        for editor in self.open_tasks.values():
            if editor.is_active():
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
            log.debug('Tried to close tid %s but it is not open', tid)

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
            return  # Can't save when none has been loaded

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
        self.ds.save()

        Gtk.Application.do_shutdown(self)

    # --------------------------------------------------------------------------
    # MISC
    # --------------------------------------------------------------------------

    @staticmethod
    def set_logging(debug: bool = False):
        """Set whenever it should activate debug stuff like logging or not"""
        level = logging.DEBUG if debug else logging.INFO
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - "
                                      "%(module)s:%(funcName)s:%(lineno)d - "
                                      "%(message)s")
        handler.setFormatter(formatter)
        logger_ = logging.getLogger('GTG')
        handler.setLevel(level)
        logger_.addHandler(handler)
        logger_.setLevel(level)
        if debug:
            logger_.debug("Debug output enabled.")
