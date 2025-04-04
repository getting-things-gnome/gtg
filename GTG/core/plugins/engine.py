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

import importlib
import inspect
import os
import logging
from typing import List, Tuple
from gi.repository import GLib # type: ignore[import-untyped]

from GTG.core.dirs import PLUGIN_DIRS
from GTG.core.borg import Borg

log = logging.getLogger(__name__)


class Plugin():
    """A class to represent a plugin."""

    # A reference to an instance of the plugin class
    instance = None
    # True if the plugin has been enabled by the user.
    enabled = False
    # True if some error prevents the plugin from being activated.
    error = False
    # True if the plugin is actually loaded and running.
    _active = False
    missing_modules: List[str] = []
    missing_dbus: List[Tuple[str, ...]] = []

    def __init__(self, info, module_paths):
        """Initialize the Plugin using a ConfigParser."""
        info_fields = {
            'module_name': 'module',
            'full_name': 'name',
            'version': 'version',
            'authors': 'authors',
            'short_description': 'short-description',
            'description': 'description',
            'module_depends': 'dependencies',
            'dbus_depends': 'dbus-dependencies',
        }
        for attr, field in info_fields.items():
            try:
                setattr(self, attr, info[field])
            except KeyError:
                setattr(self, attr, [])
        # turn the enabled attribute into a bool
        self.enabled = info['enabled'].lower() == "true"
        # ensure the module dependencies are a list
        if isinstance(self.module_depends, str):
            self.module_depends = self.module_depends.split(',')
            if not self.module_depends[-1]:
                self.module_depends = self.module_depends[:-1]
        # ensure the dbus dependencies are a list
        if isinstance(self.dbus_depends, str):
            self.dbus_depends = [self.dbus_depends]
        self._load_module(module_paths)

    # 'active' property
    def _get_active(self):
        return self._active

    def _set_active(self, value):
        if value:
            self.instance = self.plugin_class()
        else:
            self.instance = None
        self._active = value

    active = property(_get_active, _set_active)

    def _check_module_depends(self):
        """Check the availability of modules this plugin depends on."""
        self.missing_modules = []
        for mod_name in self.module_depends:
            try:
                __import__(mod_name)
            except Exception:
                self.missing_modules.append(mod_name)
                self.error = True

    def is_configurable(self):
        """Since some plugins don't have a is_configurable() method."""
        return self.instance and hasattr(self.instance, 'is_configurable') and\
            self.instance.is_configurable()

    def _load_module(self, module_paths):
        """Load the module containing this plugin."""
        try:
            # import the module containing the plugin
            spec = importlib.machinery.PathFinder().find_spec(self.module_name, module_paths)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            classes = inspect.getmembers(mod, inspect.isclass)

            self.class_name = classes[0][0]
            self.plugin_class = classes[0][1]

        except ImportError as e:
            print(e)
            # load_module() failed, probably because of a module dependency
            if len(self.module_depends) > 0:
                self._check_module_depends()
            else:
                # no dependencies in info file; use the ImportError instead
                self.missing_modules.append(str(e).split(" ")[3])
            self.error = True
        except Exception:
            log.exception("load_module() failed for some other reason:")
            self.error = True

    def reload(self, module_paths):
        if not self.active:
            self._load_module(module_paths)


class PluginEngine(Borg):
    """
    A class to manage plugins. Only one can exist.
    """

    def __init__(self):
        """Initialize the plugin engine.
        """
        super().__init__()
        if hasattr(self, "plugins"):
            # Borg has already been initialized, skip
            return

        self.initialized_plugins = []
        self.plugins = {}
        self.plugin_apis = []

        # find all plugin info files (*.gtg-plugin)
        for path in PLUGIN_DIRS:
            for f in os.listdir(path):
                info_file = os.path.join(path, f)
                if os.path.isfile(info_file) and f.endswith('.gtg-plugin'):
                    parser = GLib.KeyFile.new()
                    parser.load_from_file(info_file, GLib.KeyFileFlags.NONE)
                    keys = parser.get_keys("GTG Plugin")[0]  # The list of keys
                    info = {key: parser.get_locale_string("GTG Plugin", key, None) for key in keys}
                    p = Plugin(info, PLUGIN_DIRS)
                    self.plugins[p.module_name] = p

    def get_plugin(self, module_name):
        return self.plugins[module_name]

    def get_plugins(self, kind_of_plugins="all"):
        """
        Returns a list of plugins
        filtering only a kind of plugin
        @param kind_of_plugins: one of "active",
                                       "inactive",
                                       "enabled",
                                       "disabled",
                                       "all"
        """
        all_plugins = iter(self.plugins.values())
        if kind_of_plugins == "all":
            return all_plugins

        def filter_fun(plugin):
            return (kind_of_plugins == "active" and plugin.active) or \
                (kind_of_plugins == "inactive" and not plugin.active) or \
                (kind_of_plugins == "enabled" and plugin.enabled) or \
                (kind_of_plugins == "disabled" and not plugin.enabled)

        return list(filter(filter_fun, all_plugins))

    def register_api(self, api):
        """Adds a plugin api to the list of currently loaded apis"""
        self.plugin_apis.append(api)

    def remove_api(self, api):
        self.plugin_apis.remove(api)

    def activate_plugins(self, plugins=[]):
        """Activate plugins."""
        assert(isinstance(plugins, list))
        if not plugins:
            plugins = self.get_plugins("inactive")
        for plugin in plugins:
            # activate enabled plugins without errors
            if plugin.enabled and not plugin.error:
                # activate the plugin
                plugin.active = True
                for api in self.plugin_apis:
                    if hasattr(plugin.instance, "activate"):
                        plugin.instance.activate(api)
                    if api.is_editor():
                        if hasattr(plugin.instance, "onTaskOpened"):
                            plugin.instance.onTaskOpened(api)
                        # also refresh the content of the task
                        tv = api.get_ui().get_textview()
                        if tv:
                            tv.on_modified(None)

    def deactivate_plugins(self, plugins=[]):
        """Deactivate plugins."""
        assert(isinstance(plugins, list))
        if not plugins:
            plugins = self.get_plugins("active")
        for plugin in plugins:
            # deactivate disabled plugins
            if not plugin.enabled:
                for api in self.plugin_apis:
                    if hasattr(plugin.instance, "deactivate"):
                        plugin.instance.deactivate(api)
                        classname = plugin.instance.deactivate.__class__
                        api.remove_active_selection_changed_callback(classname)
                    if api.is_editor():
                        if hasattr(plugin.instance, "onTaskClosed"):
                            plugin.instance.onTaskClosed(api)
                        # also refresh the content of the task
                        tv = api.get_ui().get_textview()
                        if tv:
                            tv.on_modified(None)
                plugin.active = False
            # if plugin is enabled and has onQuit member, execute it
            else:
                for api in self.plugin_apis:
                    if hasattr(plugin.instance, "onQuit"):
                        plugin.instance.onQuit(api)

    def onTaskLoad(self, plugin_api):
        """Pass the onTaskLoad signal to all active plugins."""
        for plugin in self.get_plugins("active"):
            if hasattr(plugin.instance, "onTaskOpened"):
                plugin.instance.onTaskOpened(plugin_api)

    def onTaskClose(self, plugin_api):
        """Pass the onTaskClose signal to all active plugins."""
        for plugin in self.get_plugins("active"):
            if hasattr(plugin.instance, 'onTaskClosed'):
                plugin.instance.onTaskClosed(plugin_api)

# FIXME: What are these for? must check someday! (invernizzi)
    def recheck_plugins(self, plugin_apis):
        """Check plugins to make sure their states are consistent.

        TODO: somehow make this unnecessary?
        """
        for plugin in self.get_plugins():
            try:
                if plugin.instance and plugin.enabled and plugin.active:
                    self.deactivate_plugins(self.plugin_apis, [plugin])
                elif plugin.instance is None and plugin.enabled and \
                        (not plugin.active):
                    if plugin.error:
                        plugin.enabled = False
                    else:
                        self.activate_plugins(self.plugin_apis, [plugin])
                elif plugin.instance and plugin.enabled and not plugin.active:
                    if plugin.error:
                        plugin.enabled = False
                    else:
                        self.activate_plguins(self.plugin_apis, [plugin])
            except Exception as e:
                print(f"Error: {e}")

    def recheck_plugin_errors(self, check_all=False):
        """Attempt a reload of plugins with errors, or all plugins."""
        for plugin in self.get_plugins():
            if check_all or plugin.error:
                plugin.reload(PLUGIN_DIRS)
