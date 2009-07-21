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
import gtk

class PluginAPI:
    def __init__(self, window, wTree, requester, task=None, textview=None):
        # private vars       
        self.__window = window
        self.__wTree = wTree
        self.__requester = requester
        
        if task:
            self.task = task
                 
        if textview:
            self.textview = textview
        
    # adds items to the MenuBar of the Main Window (TaskBrowser)
    def AddMenuItem(self, item):
        self.__wTree.get_widget('menu_plugin').get_submenu().append(item)
        item.show()
    
    # removes the item from the MenuBar        
    def RemoveMenuItem(self, item):
        try:
            self.__wTree.get_widget('menu_plugin').get_submenu().remove(item)
        except Exception, e:
            print "Error removing menu item: %s" % e
        
    def AddToolbarItem(self, item):
        # calculates the number of items on the ToolBar and adds the item 
        # on the end
        try:
            i = 0
            while self.__wTree.get_widget('task_tb').get_nth_item(i) is not None:
                i = i + 1
            self.__wTree.get_widget('task_tb').insert(item, i)
            item.show()
            return i
        except Exception, e:
            print "Error adding a toolbar item: %s" % e
    
    def RemoveToolbarItem(self, item, n=None):
        try:
            if not n:
                self.__wTree.get_widget('task_tb').remove(item)
            else:
                i = 0
                while self.__wTree.get_widget('task_tb').get_nth_item(i) is not None:
                    if i == n:
                        self.__wTree.get_widget('task_tb').remove(self.__wTree.get_widget('task_tb').get_nth_item(i))
                    i = i + 1
        except Exception, e:
            print "Error removing a toolbar item: %s" % e
    
    # adds items to the Task Menu 
    def AddTaskToolbarItem(self, item):
        try:
            i = 0
            while self.__wTree.get_widget('task_tb1').get_nth_item(i) is not None:
                i = i + 1
            self.__wTree.get_widget('task_tb1').insert(item, i)
            item.show()
        except Exception, e:
            print "Error adding a toolbar item in to the TaskEditor: %s" % e
            
    # passes the requester to the plugin
    def getRequester(self):
        return self.__requester
            
    # changes the tasks TreeStore
    def changeTaskTreeStore(self, treestore):
        task_tview = self.__wTree.get_widget("task_tview")
        task_tview.set_model(treestore)
        
    def get_task(self):
        return self.task
    
    def get_task_title(self):
        return self.task.get_title() 
    
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
    
    # defines the child's parent window
    def set_parent_window(self, child):
        child.set_transient_for(self.__window)