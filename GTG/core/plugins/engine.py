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
import dbus
from configobj import ConfigObj


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
            missing_dbus = []
            configobj = ConfigObj(config)
            if configobj.has_key("GTG Plugin"):
                name = configobj["GTG Plugin"]["Module"]
                try:
                    file, pathname, desc = imp.find_module(name, self.plugin_path)
                    tmp_load = imp.load_module(name, file, pathname, desc)
                except ImportError, e:      
                	if configobj["GTG Plugin"].has_key("Dependencies"):
                		for module in configobj["GTG Plugin"]["Dependencies"]:
                			try:
                				__import__(module)
                			except:
                				missing.append(module)
                	else:
                		missing.append(str(e).split(" ")[3])
                	error = True
                except Exception, e:
                	error = True
                
                # check DBus dependencies
                if configobj["GTG Plugin"].has_key("Dbus-dependencies"):
                    if "str" in str(type(configobj["GTG Plugin"]["Dbus-dependencies"])):
                        dbobj = configobj["GTG Plugin"]["Dbus-dependencies"]
                        if len(dbobj.split(":")) > 1 and len(dbobj.split(":")) < 3:
                            try:
                                tmp_dbus = dbobj.split(":")
                                self.hamster=dbus.SessionBus().get_object(tmp_dbus[0], tmp_dbus[1])
                            except Exception, e:
                                error = True
                                missing_dbus.append((dbobj.split(":")[0],dbobj.split(":")[1]))
                        else:
                            if dbobj:
                                missing_dbus.append((dbobj))
                                error = True    
                    elif "list" in str(type(configobj["GTG Plugin"]["Dbus-dependencies"])):
                        for dbobj in configobj["GTG Plugin"]["Dbus-dependencies"]:
                            if len(dbobj.split(":")) > 1 and len(dbobj.split(":")) < 3:
                                try:
                                    tmp_dbus = dbobj.split(":")
                                    self.hamster=dbus.SessionBus().get_object(tmp_dbus[0], tmp_dbus[1])
                                except Exception, e:
                                    error = True
                                    missing_dbus.append((dbobj.split(":")[0],dbobj.split(":")[1]))
                            else:
                                if dbobj:
                                    missing_dbus.append((dbobj))
                                    error = True
                
                # find the class object
                if not error:
                    for key, item in tmp_load.__dict__.items():
                        if "classobj" in str(type(item)):
                            c = item
                            break
                
                plugin = {}             
                plugin['plugin'] = configobj["GTG Plugin"]["Module"]
                #plugin['plugin'] = tmp_load.__name__
                
                if not error:
                    plugin['class_name'] = c.__dict__["__module__"].split(".")[1]
                    plugin['class'] = c
                    plugin['state'] = eval(configobj["GTG Plugin"]["Enabled"])
                    plugin['error'] = False
                    plugin['missing_modules'] = []
                    plugin['missing_dbus'] = []
                else:
                    plugin['class_name'] = ""
                    plugin['class'] = None
                    plugin['state'] = False
                    plugin['error'] = True
                    plugin['missing_modules'] = missing
                    plugin['missing_dbus'] = missing_dbus
                    
                if configobj["GTG Plugin"].has_key("Dependencies"):
                	plugin['dependencies'] = configobj["GTG Plugin"]["Dependencies"]
                else: 
                    plugin['dependencies'] = None
                    
                if configobj["GTG Plugin"].has_key("Dbus-dependencies"):
                	plugin['dbus-dependencies'] = configobj["GTG Plugin"]["Dbus-dependencies"]
                else: 
                    plugin['dbus-dependencies'] = None
                    
                plugin['name'] = configobj["GTG Plugin"]["Name"]
                plugin['version'] = configobj["GTG Plugin"]["Version"]
                plugin['authors'] = configobj["GTG Plugin"]["Authors"]
                plugin['description'] = configobj["GTG Plugin"]["Description"]
                plugin['instance'] = None
                
                
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
            if plgin['state'] and not plgin['error']:
                plgin['instance'] = plgin['class']()
                plgin['instance'].activate(plugin_api)
                
    # deactivate the enabled plugins
    def deactivatePlugins(self, plugins, plugin_api):
        for plgin in plugins:
            if plgin['state'] and not plgin['error']:
                plgin['instance'].deactivate(plugin_api)
				
    # loads the plug-in features for a task
    def onTaskLoad(self, plugins, plugin_api):
        for plgin in plugins:
            if plgin['state']:
                plgin['instance'].onTaskOpened(plugin_api)
     

    	           
	# rechecks the plug-ins to see if any changes where done to the state
    def recheckPlugins(self, plugins, plugin_api):
        for plugin in plugins:
            if plugin['instance'] != None and plugin['state'] == False:
                try:
                    #print "deactivating plugin: " + plgin['name']
                    plugin['instance'].deactivate(plugin_api)
                    plugin['instance'] = None
                except Exception, e:
                    print "Error: %s" % e
            elif plugin['instance'] == None and plugin['state'] == True:
                try:    
                    #print "activating plugin: " + plgin['name']
                    if not plugin['error']:
                        plugin['instance'] = plugin['class']()
                        plugin['instance'].activate(plugin_api)
                    else:
                        plugin['state'] = False
                except Exception, e:
                    print "Error: %s" % e

    # rechecks the plugins with errors
    def recheckPluginsErrors(self, plugins, plugin_api):
    	for plugin in plugins:
    		if plugin['error']:
    			error = False
    			missing = []
    			missing_dbus = []

    			try:
    				file, pathname, desc = imp.find_module(plugin['plugin'], self.plugin_path)
    				tmp_load = imp.load_module(name, file, pathname, desc)
    			except ImportError, e:
    				print e
    				if plugin["dependencies"]:
    					for module in plugin["dependencies"]:
    						try:
    							__import__(module)
    						except:
    							missing.append(module)
    				else:
    					missing.append(str(e).split(" ")[3])
    				error = True
    			except Exception, e:
    				error = True
    				
    			if plugin["dbus-dependencies"]:
    				if "str" in str(type(plugin["dbus-dependencies"])):
    					dbobj = plugin["dbus-dependencies"]
    					if len(dbobj.split(":")) > 1 and len(dbobj.split(":")) < 3:
    						try:
    							tmp_dbus = dbobj.split(":")
    							self.hamster=dbus.SessionBus().get_object(tmp_dbus[0], tmp_dbus[1])
    						except Exception, e:
    							error = True
    							missing_dbus.append((dbobj.split(":")[0],dbobj.split(":")[1]))
    					else:
    						if dbobj:
    							missing_dbus.append((dbobj))
    							error = True    
    				elif "list" in str(type(plugin["dbus-dependencies"])):
    					for dbobj in plugin["dbus-dependencies"]:
    						if len(dbobj.split(":")) > 1 and len(dbobj.split(":")) < 3:
    							try:
    								tmp_dbus = dbobj.split(":")
    								self.hamster=dbus.SessionBus().get_object(tmp_dbus[0], tmp_dbus[1])
    							except Exception, e:
    								error = True
    								missing_dbus.append((dbobj.split(":")[0],dbobj.split(":")[1]))
    						else:
    							if dbobj:
    								missing_dbus.append((dbobj))
    								error = True
        		
        		if not error:
        			#load the plugin
        			for key, item in tmp_load.__dict__.items():
        				if "classobj" in str(type(item)):
        					c = item
        					break
                           
        			plugin['class_name'] = c.__dict__["__module__"].split(".")[1]
        			plugin['class'] = c
        			plugin['state'] = False
        			plugin['error'] = False
        			plugin['missing_modules'] = []
        			plugin['missing_dbus'] = []
        		else:
        			if missing:
        				plugin['missing_modules'] = missing
        			if missing_dbus:
        				plugin['missing_dbus'] = missing_dbus
        		
        				