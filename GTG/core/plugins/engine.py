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
from configobj import ConfigObj

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
        # find all the plugin config files (only!)
        plugin_configs = []
        for f in os.listdir(self.plugin_path[0]):
            try:
                if not os.path.isdir(os.path.join(self.plugin_path[0], f)):
                    if len(os.path.splitext(f)) > 1:
                        if os.path.splitext(f)[1] == ".gtg-plugin":
                            plugin_configs.append(os.path.join(self.plugin_path[0], f))
            except Exception, e:
                continue
                   
        # for each plugin (config) we load the info
        for config in plugin_configs:
            error = False
            missing = []
            configobj = ConfigObj(config)
            if configobj.has_key("GTG Plugin"):
                name = configobj["GTG Plugin"]["Module"]
                try:
                    file, pathname, desc = imp.find_module(name, self.plugin_path)
                    tmp_load = imp.load_module(name, file, pathname, desc)
                except Exception, e:
                    #print e
                    missing.append(str(e).split(" ")[3])
                    error = True
                                
                
                # find the class object
                if not error:
                    for key, item in tmp_load.__dict__.items():
                        if "classobj" in str(type(item)):
                            c = item
                            break
                
                plugin = {}             
                plugin['plugin'] = configobj["GTG Plugin"]["Name"]
                #plugin['plugin'] = tmp_load.__name__
                
                if not error:
                    plugin['class_name'] = c.__dict__["__module__"].split(".")[1]
                    plugin['class'] = c
                    plugin['state'] = eval(configobj["GTG Plugin"]["Enabled"])
                else:
                    plugin['class'] = None
                    plugin['state'] = False
                    
                plugin['name'] = configobj["GTG Plugin"]["Name"]
                plugin['version'] = configobj["GTG Plugin"]["Version"]
                plugin['authors'] = configobj["GTG Plugin"]["Authors"]
                plugin['description'] = configobj["GTG Plugin"]["Description"]
                plugin['instance'] = None
                plugin['missing_modules'] = missing
                
                self.Plugins.append(plugin)
                
        return self.Plugins
	
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
            if plgin['state'] and not plgin['missing_modules']:
                plgin['instance'] = plgin['class']()
                plgin['instance'].activate(plugin_api)
                
    # deactivate the enabled plugins
    def deactivatePlugins(self, plugins, plugin_api):
        for plgin in plugins:
            if plgin['state'] and not plgin['missing_modules']:
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
                    #print "deactivating plugin: " + plgin['name']
                    plgin['instance'].deactivate(plugin_api)
                    plgin['instance'] = None
                except Exception, e:
                    print "Error: %s" % e
            elif plgin['instance'] == None and plgin['state'] == True:
                try:    
                    #print "activating plugin: " + plgin['name']
                    if not plgin['missing_modules']:
                        plgin['instance'] = plgin['class']()
                        plgin['instance'].activate(plugin_api)
                    else:
                        plgin['state'] = False
                except Exception, e:
                    print "Error: %s" % e
