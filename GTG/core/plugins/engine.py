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
        
        try:
            for loader, name, ispkg in pkgutil.iter_modules(plugin_dirs):
                file, pathname, desc = imp.find_module(name, plugin_dirs)
                plugins[name] = imp.load_module(name, file, pathname, desc)
        except Exception, e:
            print "Error: %s" % e
            
        for name, plugin in plugins.items():
            self.Plugins.append(self.loadPlugin(plugin))
			
        return self.Plugins
		
    # checks if the module loaded is a plugin and gets the main class
    def loadPlugin(self, plugin):
        plugin_locals = plugin.__dict__
        is_plugin = False
        loaded_plugin = {}
        
        # find the plugin class
        for key in plugin_locals.keys():
            try:
                is_plugin = getattr(plugin_locals[key], 'PLUGIN_NAME', None)
            except TypeError:
                continue
            
            # loads the plugin info
            if is_plugin:
                try:
                    loaded_plugin['plugin'] = plugin.__name__
                    loaded_plugin['class_name'] = key
                    loaded_plugin['class'] = plugin_locals[key]
                    loaded_plugin['name'] = plugin_locals[key].PLUGIN_NAME
                    loaded_plugin['version'] = plugin_locals[key].PLUGIN_VERSION
                    loaded_plugin['authors'] = plugin_locals[key].PLUGIN_AUTHORS
                    loaded_plugin['description'] = plugin_locals[key].PLUGIN_DESCRIPTION
                    loaded_plugin['state'] = plugin_locals[key].PLUGIN_ENABLED
                    loaded_plugin['instance'] = None
                except:
                    continue
				
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
				
    # loads the plug-in features for a task
    def onTaskLoad(self, plugins, plugin_api):
        for plgin in plugins:
            if plgin['state']:
                plgin['instance'].onTaskOpened(plugin_api)
                
	# rechecks the plug-ins to see if any changes where done to the state
    def recheckPlugins(self, plugins, plugin_api):
        for plgin in plugins:
            if plgin['instance'] != None and plgin['state'] == False:
                print "deactivating plugin: " + plgin['name']
                plgin['instance'].deactivate(plugin_api)
                plgin['instance'] = None
			
            if plgin['instance'] == None and plgin['state'] == True:
                print "activating plugin: " + plgin['name']
                plgin['instance'] = plgin['class']()
                plgin['instance'].activate(plugin_api)
                
                
#
# extends GTK actions
#
class PluginAPI:
    def __init__(self, plugin_engine, window, wTree, requester, task=None, textview=None):
        # private vars
        global  __wTree, __window, __plugin_engine, __requester
        
        __plugin_engine = plugin_engine
        __window = window
        __wTree = wTree
        __requester = requester
        
        if task:
            self.task = task
                 
        if textview:
            self.textview = textview
            
		
    # adds items to the MenuBar of the Main Window (TaskBrowser)
    def AddMenuItem(self, item):
        __wTree.get_widget('menu_plugin').get_submenu().append(item)
        item.show()
	
    # removes the item from the MenuBar		
    def RemoveMenuItem(self, item):
        try:
            __wTree.get_widget('menu_plugin').get_submenu().remove(item)
        except Exception, e:
            print "Error removing menu item: %s" % e
		
    def AddToolbarItem(self, item):
        # calculates the number of items on the ToolBar and adds the item 
        # on the end
        try:
            i = 0
            while __wTree.get_widget('task_tb').get_nth_item(i) is not None:
                i = i + 1
            __wTree.get_widget('task_tb').insert(item, i)
            item.show()
        except Exception, e:
            print "Error adding a toolbar item: %s" % e
	
    def RemoveToolbarItem(self, item):
        try:
            __wTree.get_widget('task_tb').remove(item)
        except Exception, e:
            print "Error removing a toolbar item: %s" % e
    
    # adds items to the Task Menu 
    def AddTaskToolbarItem(self, item):
        try:
            i = 0
            while __wTree.get_widget('task_tb1').get_nth_item(i) is not None:
                i = i + 1
            __wTree.get_widget('task_tb1').insert(item, i)
            item.show()
        except Exception, e:
            print "Error adding a toolbar item in to the TaskEditor: %s" % e
			
	# passes the requester to the plugin
    def getRequester(self):
        return __requester
			
	# changes the tasks TreeStore
    def changeTaskTreeStore(self, treestore):
        task_tview = __wTree.get_widget("task_tview")
        task_tview.set_model(treestore)
        
    # adds a tag, updated the text buffer, inserting the tag at the end of
    # the task
    def add_tag(self, tag):
        self.task.add_tag("@" + tag)
        #self.textview.insert_text("@" + tag)
        self.textview.insert_tag("@" + tag)
        
    # adds a attribute to a tag
    def add_tag_attribute(self, tag, attrib_name, attrib_value):
        try:
            tags = self.task.get_tags()
            for t in tags:
                if t.get_name() == tag:
                    t.set_attribute(attrib_name, attrib_value)
                    return True
        except:
            return False
    
    # pass all the tags to the plug-in
    def get_tags(self):
        return self.task.get_tags()
        
    # this will allow plugins to use the textview properties
    def get_textview(self):
        return self.textview
