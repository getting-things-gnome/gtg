# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
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

from __future__ import with_statement

import os
import pickle
from xdg.BaseDirectory import xdg_config_home

class PluginAPI:
    """The plugin engine's API.

    L{PluginAPI} is a object that provides a nice API for
    plugins to interact with GTG.
    
    Multiple L{PluginAPI}s can exist. A instance is created to be used
    with the task browser and another instance is created to be used
    with the task editor.
    """
        
    def __init__(self,
                 window,
                 config,
                 data_dir,
                 builder,
                 requester,
                 taskview,
                 ctask_modelsort,
                 ctaskview,
                 task_modelsort,
                 filter_cbs,
                 tagpopup,
                 tagview,
                 browser,
                 task=None,
                 texteditor=None,
                 quick_add_cbs=[],
                 logger = None):
        """Construct a L{PluginAPI} object.
        
        @param window: The window where the plugin API object is being 
        created.
        @param config: The config object.
        @param data_dir: The data dir path.
        @param builder: The window's gtkBuilder object.
        @param requester: The requester.
        @param taskview: The task view object.
        @param filter_cbs: The filter callback list.
        @param tagpopup: The tag popoup menu of the tag view.
        @param tagview: The tag view object.
        @param task: The current task (Only works with the task editor).
        @param textview: The task editor's text view (Only works with the task editor).  
        @param ctextview: The task editor's closed tasks text view (Only works with the task editor).  
        @param task_modelsort: The browser's active task model.  
        @param ctask_modelsort: The browser's closed task model.  
        """
        self.__window = window
        self.config = config
        self.data_dir = data_dir
        self.__builder = builder
        self.__requester = requester
        
        self.taskview = taskview
        self.task_modelsort = task_modelsort

        self.ctaskview = taskview
        self.ctask_modelsort = ctask_modelsort
        
        self.__tagpopup = tagpopup
        self.tagview = tagview
        
        self.__filter_cbs = filter_cbs
        self.__quick_add_cbs = quick_add_cbs
        
        #those are added widgets dictionaries
        self.tasktoolbar_id = 0
        self.tasktoolbar_widg = {}
        self.taskwidget_id = 0
        self.taskwidget_widg = {}
        self.logger = logger
        self.browser = browser
        
        if task:
            self.task = task
        else:
            self.task = None
                 
        if texteditor:
            self.taskeditor = texteditor
            self.textview = texteditor.textview
        else:
            self.taskeditor = None
            self.textview= None
            
    def is_editor(self):
        if self.taskeditor:
            return True
        else:
            return False
            
    def is_browser(self):
        if self.taskview:
            return True
        else:
            return False

    def get_browser(self):
        return self.browser

#=== General Methods ==========================================================
    def add_menu_item(self, item):
        """Adds a menu entry to the Plugin Menu of the Main Window 
        (task browser).

        @param item: The gtk.MenuItem that is going to be added.  
        """
        widget = self.__builder.get_object('menu_plugin')
        if widget:
            widget.show_all()
            widget.get_submenu().append(item)
        item.show()
         
    def remove_menu_item(self, item):
        """Removes a menu entry from the Plugin Menu of the Main Window 
        (task browser).

        @param item: The gtk.MenuItem that is going to be removed.
        @return: Returns C{True} if the operation has sucess or c{False} if it 
        fails.  
        """
        try:
            wi = self.__builder.get_object('menu_plugin')
            if wi:
                menu = wi.get_submenu()
                menu.remove(item)
                if len(menu.get_children()) == 0:
                    wi.hide()
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
            wi = self.__builder.get_object('task_tb')
            if wi:
                while wi.get_nth_item(i) is not None:
                    i = i + 1
                wi.insert(item, i)
                item.show()
                return i
            else:
                return -1
        except Exception, e:
            print "Error adding a toolbar item: %s" % e
    
    def remove_toolbar_item(self, item, n=None):
        """Removes a toolbar button from the task browser's toolbar.  

        @param item: The gtk.ToolButton that is going to be removed.  
        @param n: The position of the item to be removed.
        
        Note: It's useful to remove gtk.SeparatorToolItem(). 
        ie, remove_toolbar_item(None, 14)
        """
        if self.is_browser():
            try:
                wi = self.__builder.get_object('task_tb')
                if wi and item:
                    if not n or n < 0:
                        wi.remove(item)
                    else:
                        i = 0
                        while wi.get_nth_item(i) is not None:
                            if i == n:
                                wi.remove(wi.get_nth_item(i))
                            i = i + 1
            except Exception, e:
                print "Error removing a toolbar item: %s" % e
    
    # adds items to the Task Menu 
    def add_task_toolbar_item(self, item):
        """Adds a button to the task editor's toolbar. 
         return an ID number for this added widget.

        @param item: The gtk.ToolButton that is going to be added 
                     to the toolbar.
        """
        try:
            i = 0
            wi = self.__builder.get_object('task_tb1')
            if wi:
                while wi.get_nth_item(i) is not None:
                    i = i + 1
                wi.insert(item, i)
                item.show()
                #this id will grow, this is not a problem
                self.tasktoolbar_id += 1
                self.tasktoolbar_widg[self.tasktoolbar_id] = item
                if self.taskeditor:
                    self.taskeditor.refresh_editor()
                return self.tasktoolbar_id
            else:
                return None
        except Exception, e:
            print "Error adding a toolbar item in to the TaskEditor: %s" %e
            
    def remove_task_toolbar_item(self,widg_id):
        """Remove a button from the task editor's toolbar. 

        @param item: The ID of the widget to be removed. If None, nothing is removed.
        """
        if self.is_editor() and widg_id:
            try:
                wi = self.__builder.get_object('task_tb1')
                if wi and widg_id in self.tasktoolbar_widg:
                    #removing from the window and the dictionnary
                    # in one line.
                    wi.remove(self.tasktoolbar_widg.pop(widg_id))
            except Exception, e:
                print "Error removing the toolbar item in the TaskEditor: %s" %e
            
    def add_widget_to_taskeditor(self, widget):
        """Adds a widget to the bottom of the task editor dialog
        
        @param widget: The gtk.Widget that is going to be added. 
        """
        vbox = self.__builder.get_object('vbox4')
        if vbox:
            vbox.pack_start(widget)
            vbox.reorder_child(widget, -2)
            widget.show_all()
            self.taskwidget_id += 1
            self.taskwidget_widg[self.taskwidget_id] = widget
            return self.taskwidget_id
        else:
            return None
            
    def remove_widget_from_taskeditor(self,widg_id):
        """Remove a widget from the bottom of the task editor dialog
        
        @param widget: The gtk.Widget that is going to be removed
        """
        if self.is_editor() and widg_id:
            try:
                wi = self.__builder.get_object('vbox4')
                if wi and widg_id in self.taskwidget_widg:
                    wi.remove(self.taskwidget_widg.pop(widg_id))
            except Exception, e:
                print "Error removing the toolbar item in the TaskEditor: %s" %e
            
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
        task_tview = self.__builder.get_object("task_tview")
        if task_tview:
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

    def get_task_modelsort(self):
        """Returns the current Active task browser view. 
        
        @return: The gtk.TreeModelSort task object for visible active tasks.
        """
        return self.task_modelsort
    
    def get_closed_taskview(self):
        """Returns the closed task view object. 
        
        @return: The gtk.TreeView task view object.
        """
        return self.ctaskview

    def get_ctask_modelsort(self):
        """Returns the current Done task browser view. 
        
        @return: The gtk.TreeModelSort task object for visible closed tasks.
        """
        return self.ctask_modelsort
    
    def get_selected_task(self):
        """Returns the selected task in the task view.
        
        @return: A task. 
        """
        if self.is_editor():
            return self.task
        elif self.is_browser():
            selection = self.taskview.get_selection()
            model, paths = selection.get_selected_rows()
            iters = [model.get_iter(path) for path in paths]
            if len(iters) > 0 and iters[0]:
                return self.__requester.get_task(model.get_value(iters[0], 0))
            else:
                return None
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
        wi = self.__builder.get_object("about_dialog")
        if wi:
            return wi
        else:
            return None
    
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

    def get_logger(self):
        """Returns the logger, used for debug output""" 
        return self.logger

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
        if itera.starts_line():
            self.textview.insert_text("@" + tag,itera)
        else:
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

    def register_quick_add_cb(self, func):
        """Registers a callback that will be called each time a new task is
        added using the "quick add" entry.

        @param func: The function that is going to be registered.

        """
        if func not in self.__quick_add_cbs:
            self.__quick_add_cbs.append(func)

    def unregister_quick_add_cb(self, func):
        """Unregisters a previously registered "quick add" callback.

        @param func: The function that is going to be unregistered.
        """
        if func in self.__quick_add_cbs:
            self.__quick_add_cbs.remove(func)

#=== file saving/loading ======================================================

    def load_configuration_object(self, plugin_name, filename, \
                                  basedir = xdg_config_home):
        dirname = os.path.join(basedir, 'gtg/plugins', plugin_name)
        path = os.path.join(dirname, filename)
        if os.path.isdir(dirname):
            if os.path.isfile(path):
                try:
                    with open(path, 'r') as file:
                        item = pickle.load(file)
                except:
                    return None
                return item
        else:
            os.makedirs(dirname)

    def save_configuration_object(self, plugin_name, filename, item, \
                                 basedir = xdg_config_home):
        dirname = os.path.join(basedir, 'gtg/plugins', plugin_name)
        path = os.path.join(dirname, filename)
        with open(path, 'wb') as file:
             pickle.dump(item, file)

