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
    """The plugin engine's API.

    L{PluginAPI} is a object that provides a nice API for
    plugins to interact with GTG.
    
    Multiple L{PluginAPI}s can exist. A instance is created to be used
    with the task browser and another instance is created to be used
    with the task editor.
    """
        
    def __init__(self, window, config, data_dir, wTree, requester,\
                 taskview, filter_cbs, tagpopup, tagview, task=None,\
                 textview=None):
        """Construct a L{PluginAPI} object.
        
        @param window: The window where the plugin API object is being 
        created.
        @param config: The config object.
        @param data_dir: The data dir path.
        @param wTree: The window's wTree object.
        @param requester: The requester.
        @param taskview: The task view object.
        @param filter_cbs: The filter callback list.
        @param tagpopup: The tag popoup menu of the tag view.
        @param tagview: The tag view object.
        @param task: The current task (Only works with the task editor).
        @param textview: The task editor's text view (Only works with the task editor).  
        """
        self.__window = window
        self.config = config
        self.data_dir = data_dir
        self.__wTree = wTree
        self.__requester = requester
        
        self.taskview = taskview
        
        self.__tagpopup = tagpopup
        self.tagview = tagview
        
        self.__filter_cbs = filter_cbs
        
        if task:
            self.task = task
                 
        if textview:
            self.textview = textview

#=== General Methods ==========================================================
    def add_menu_item(self, item):
        """Adds a menu entry to the Plugin Menu of the Main Window 
        (task browser).

        @param item: The gtk.MenuItem that is going to be added.  
        """
        self.__wTree.get_widget('menu_plugin').get_submenu().append(item)
        item.show()
         
    def remove_menu_item(self, item):
        """Removes a menu entry from the Plugin Menu of the Main Window 
        (task browser).

        @param item: The gtk.MenuItem that is going to be removed.
        @return: Returns C{True} if the operation has sucess or c{False} if it 
        fails.  
        """
        try:
            self.__wTree.get_widget('menu_plugin').get_submenu().remove(item)
            return True
        except Exception, e:
            print "Error removing menu item: %s" % e
            return True
        
    def add_toolbar_item(self, item):
        """Adds a button to the task browser's toolbar.  

        @param item: The gtk.ToolButton that is going to be added to the 
        toolbar.
        @return: Integer that represents the position of the item in the 
        toolbar.   
        """
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
    
    def remove_toolbar_item(self, item, n=None):
        """Removes a toolbar button from the task browser's toolbar.  

        @param item: The gtk.ToolButton that is going to be removed.  
        @param n: The position of the item to be removed.
        
        Note: It's useful to remove gtk.SeparatorToolItem(). 
        ie, remove_toolbar_item(None, 14)
        """
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
    def add_task_toolbar_item(self, item):
        """Adds a button to the task editor's toolbar. 

        @param item: The gtk.ToolButton that is going to be added to the toolbar.  
        """
        try:
            i = 0
            while self.__wTree.get_widget('task_tb1').get_nth_item(i) is not None:
                i = i + 1
            self.__wTree.get_widget('task_tb1').insert(item, i)
            item.show()
        except Exception, e:
            print "Error adding a toolbar item in to the TaskEditor: %s" % e
            
    def add_widget_to_taskeditor(self, widget):
        """Adds a widget to the bottom of the task editor dialog
        
        @param widget: The gtk.Widget that is going to be added. 
        """
        vbox = self.__wTree.get_widget('vbox4')
        vbox.pack_start(widget)
        vbox.reorder_child(widget, -2)
        widget.show_all()
            
    def get_requester(self):
        """Returns the requester.
        
        @return: The requester.
        """
        return self.__requester
    
    def requester_connect(self, action, func):
        """Connects a function to a requester signal. 
        
        @param action: The signal action. 
        @param func: The function that is connected to the signal. 
        """
        self.__requester.connect(action, func)
            
    def change_task_tree_store(self, treestore):
        """Changes the TreeStore in the task browser's task view. 
        
        @param treestore: The new gtk.TreeStore model. 
        """
        task_tview = self.__wTree.get_widget("task_tview")
        task_tview.set_model(treestore)
    
    def set_parent_window(self, child):
        """Sets the plugin dialog as a child of it's parent window, 
        depending on were it is called the parent window can be either 
        the task browser or the task editor.
        
        @param child: The dialog that is meant to be set as a child. 
        """
        child.set_transient_for(self.__window) 
    
    def get_taskview(self):
        """Returns the task view object. 
        
        @return: The gtk.TreeView task view object.
        """
        return self.taskview
    
    def get_selected_task(self):
        """Returns the selected task in the task view.
        
        @return: A task. 
        """
        selected = self.taskview.get_selection()
        model, iter = selected.get_selected()
        if iter:
            return self.__requester.get_task(model.get_value(iter, 0))
        else:
            return None
        
    def get_config(self):
        """Returns the config object.
        
        @return: The config dictionary.
        """
        return self.config
    
    def get_about_dialog(self):
        """Returns the about dialog.
        
        @return: The about dialog.
        """
        return self.__wTree.get_widget("aboutdialog1")
    
    def get_data_dir(self):
        """Returns the data dir path.
        
        @return: The data dir path.
        """
        return self.data_dir
    
    def hide_window(self):
        """Hides the main GTG window (task browser)"""
        self.__window.hide()
        
    def show_window(self):
        """Shows the main GTG window (task browser)"""
        self.__window.show()

    def get_window(self):
        """Returns the window for which the plug-in has been created"""
        return self.__window
#=== General Methods ==========================================================


#=== Task related methods =====================================================
    def get_all_tasks(self):
        """Returns a list with all existing tasks. 
        
        @return: A list of tasks.
        """
        return self.__requester.get_tasks_list()    
    
    def get_task(self, tid=None):
        """Returns the current or a matching task.
        
        Note: the default action is to be used with the task editor 
        (onTaskOpened method).
        
        @param tid: The task's id.
        @return: A task.
        """
        if tid:
            return self.__requester.get_task(tid)
        else:
            return self.task
    
    def get_task_title(self, tid=None):
        """Returns the current or a matching task's title.
        
        Note: the default action is to be used with the task editor 
        (onTaskOpened method).
        
        @param tid: The task's id.
        @return: The task's title (String).
        """
        if tid:
            return self.__requester.get_task(tid).get_title()
        else:
            return self.task.get_title() 
        
    def insert_tag(self, tag):
        """Inserts a tag into the current task (in the textview).
        
        Note: this method only works with the onTaskOpened method. 
        
        @param tag: The tag's name (without the '@').  
        """
        itera = self.textview.get_insert()
        if itera.starts_line() :
            self.textview.insert_text("@" + tag,itera)
        else :
            self.textview.insert_text(" @" + tag,itera)
        self.textview.grab_focus()
    
    def add_tag(self, tag, tid=None):
        """Adds a tag directly to a task. 
        
        Note: the default action is to be used with the task editor 
        (onTaskOpened method).
        
        @param tag: The tag's name (without the '@').  
        @param tid: The task's id.
        """
        if tid:
             self.__requester.get_task(tid).add_tag("@" + tag)
        else:    
            self.task.add_tag("@" + tag)
        
    def add_tag_attribute(self, tag, attrib_name, attrib_value):
        """Adds an attribute to a tag in the current task.
        
        Note: this method only works with the onTaskOpened method.
        
        @param attrib_name: The attribute's name.
        @param attrib_value: The attribute's value.  
        """
        try:
            tags = self.task.get_tags()
            for t in tags:
                if t.get_name() == tag:
                    t.set_attribute(attrib_name, attrib_value)
                    return True
        except:
            return False
    
    def get_tags(self, tid=None):
        """Returns all the tags the current task or a matching task has. 
        
        Note: the default action is to be used with the task editor 
        (onTaskOpened method).
        
        @param tid: The task's id.
        """
        if tid:
            return self.__requester.get_task(tid).get_tags()
        else:
            return self.task.get_tags()
    
    def get_textview(self):
        """Returns the task editor's text view (object).
        
        Note: this method only works with the onTaskOpened method.
        
        @return: The task editor's text view (gtk.TextView)
        """
        return self.textview
#=== Task related methods =====================================================

    
#=== Tag view methods =========================================================
    def add_menu_tagpopup(self, item):
        """Adds a menu to the tag popup menu of the tag view. 
        
        @param item: The menu that is going to be removed from the tag 
        popup menu. 
        """
        self.__tagpopup.append(item)
        item.show()
        
    def remove_menu_tagpopup(self, item):
        """Removes a menu from the tag popup menu of the tag view. 
        
        @param item: The menu that is going to be removed from the tag popup 
        menu.
        @return: Returns C{True} if the operation has sucess or c{False} if it 
        fails.
        """
        try:
            self.__tagpopup.remove(item)
            return True
        except Exception, e:
            return False
        
    def get_tagpopup_tag(self):
        """ Returns the selected tag in the tag view. 
        
        @return: The selected tag (tag name) in the tag view.
        """
        selected = self.tagview.get_selection()
        model, iter = selected.get_selected()
        tag = model.get_value(iter, 0)
        return self.__requester.get_tag(tag)
#=== Tag view methods =========================================================

    
#=== Filtering methods ========================================================
    def add_task_to_filter(self, tid):
        """Adds a task to the task filter. 
        
        @param tid: The task's id. 
        """
        self.__requester.add_task_to_filter(tid)
    
    def remove_task_from_filter(self, tid):
        """Removes a task from the task filter. 
        
        @param tid: The task's id. 
        """
        self.__requester.remove_task_from_filter(tid)
        
    def add_tag_to_filter(self, tag):
        """Adds all tasks that contain a certain tag to the task filter. 
        
        @param tag: The tag name.
        """
        self.__requester.add_tag_to_filter(tag)
        
    def remove_tag_from_filter(self, tag):
        """Removes all tasks that contain a certain tag from the task 
        filter.
        
        @param tag: The tag name.
        """
        self.__requester.remove_tag_from_filter(tag)
      
    def register_filter_cb(self, func):
        """Registers a callback filter function with the callback filter. 
        
        @param func: The function that is going to be registered. 
        
        """
        if func not in self.__filter_cbs:
            self.__filter_cbs.append(func)
    
    def unregister_filter_cb(self, func):
        """Unregisters a previously registered callback filter function. 
        
        @param func: The function that is going to be unregistered. 
        """
        if func in self.__filter_cbs:
            self.__filter_cbs.remove(func)    
#=== Filtering methods ========================================================
