# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personnal organizer for the GNOME desktop
# Copyright (c) 2008-2009 - Lionel Dricot & Bertrand Rousseau
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

import pkgutil
import imp
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



# this class manages the plug-ins
class PluginEngine:
	
    # initializes the plug-in engine
    # NOTE: the path has to be a list of paths
    def __init__(self, plugin_path):
        self.Plugins = []
        self.plugin_path = plugin_path
        self.initialized_plugins = []
		
    # loads the plugins from the plugin dir
    def LoadPlugins(self):
        plugins = {}
        
        # find all the folders in the plugin dir
        plugin_dirs = []
        plugin_dirs.append(self.plugin_path[0])
        for f in os.listdir(self.plugin_path[0]):
            if os.path.isdir(os.path.join(self.plugin_path[0], f)):
                plugin_dirs.append(os.path.join(self.plugin_path[0], f))
        
        
            for loader, name, ispkg in pkgutil.iter_modules(plugin_dirs):
                try:
                    file, pathname, desc = imp.find_module(name, plugin_dirs)
                    #plugins[name] = imp.load_module(name, file, pathname, desc)
                    tmp_load = imp.load_module(name, file, pathname, desc)
                    is_plugin = False
                    for key in tmp_load.__dict__.keys():
                        try:
                            is_plugin = getattr(tmp_load.__dict__[key], 'PLUGIN_NAME', None)
                        except TypeError:
                            continue
                    
                        if is_plugin:
                            plugins[name] = [tmp_load, key]
                            break
                        
                except Exception, e:
                    print "Error while trying to load a python module: %s" % e
                    continue
            
        for name, plugin in plugins.items():
            tmp_plgin = self.loadPlugin(plugin)
            if tmp_plgin:
                self.Plugins.append(tmp_plgin)
			
        return self.Plugins
		
    # checks if the module loaded is a plugin and gets the main class
    def loadPlugin(self, plugin):
        plugin_locals = plugin[0].__dict__
        key = plugin[1]
        loaded_plugin = {}
         
        # loads the plugin info
        try:
            loaded_plugin['plugin'] = plugin[0].__name__
            loaded_plugin['class_name'] = key
            loaded_plugin['class'] = plugin_locals[key]
            loaded_plugin['name'] = plugin_locals[key].PLUGIN_NAME
            loaded_plugin['version'] = plugin_locals[key].PLUGIN_VERSION
            loaded_plugin['authors'] = plugin_locals[key].PLUGIN_AUTHORS
            loaded_plugin['description'] = plugin_locals[key].PLUGIN_DESCRIPTION
            loaded_plugin['state'] = plugin_locals[key].PLUGIN_ENABLED
            loaded_plugin['instance'] = None
        except Exception, e:
            print "Erro: %s" % e
		
        if not loaded_plugin:
            return None	
        return loaded_plugin
	
    def enabledPlugins(self, plugins):
        pe = []
        for p in plugins:
            if p['state']:
                pe.append(p['name'])
        return pe
    
    def disabledPlugins(self, plugins):
        pd = []
        for p in plugins:
            if not p['state']:
                pd.append(p['name'])
        return pd
    
    # activates the plugins
    def activatePlugins(self, plugins, plugin_api):
        for plgin in plugins:
            if plgin['state']:
                plgin['instance'] = plgin['class']()
                plgin['instance'].activate(plugin_api)
                
    # deactivate the enabled plugins
    def deactivatePlugins(self, plugins, plugin_api):
        for plgin in plugins:
            if plgin['state']:
                plgin['instance'].deactivate(plugin_api)
				
    # loads the plug-in features for a task
    def onTaskLoad(self, plugins, plugin_api):
        for plgin in plugins:
            if plgin['state']:
                plgin['instance'].onTaskOpened(plugin_api)
                
	# rechecks the plug-ins to see if any changes where done to the state
    def recheckPlugins(self, plugins, plugin_api):
        for plgin in plugins:
            if plgin['instance'] != None and plgin['state'] == False:
                try:
                    print "deactivating plugin: " + plgin['name']
                    plgin['instance'].deactivate(plugin_api)
                    plgin['instance'] = None
                except Exception, e:
                    print "Error: %s" % e
            elif plgin['instance'] == None and plgin['state'] == True:
                try:    
                    print "activating plugin: " + plgin['name']
                    plgin['instance'] = plgin['class']()
                    plgin['instance'].activate(plugin_api)
                except Exception, e:
                    print "Error: %s" % e
