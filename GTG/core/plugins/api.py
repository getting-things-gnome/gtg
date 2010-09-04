# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things Gnome! - a personal organizer for the GNOME desktop
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

import os
import gtk
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
                 tagpopup,
                 tagview,
                 view_manager,
                 task=None,
                 texteditor=None,
                 quick_add_cbs=[]):
        """Construct a L{PluginAPI} object.

        @param window: The window where the plugin API object is being 
        created.
        @param config: The config object.
        @param data_dir: The data dir path.
        @param builder: The window's gtkBuilder object.
        @param requester: The requester.
        @param tagpopup: The tag popup menu of the tag view.
        @param tagview: The tag view object.
        @param task: The current task (Only works with the task editor).
        @param view_manager: The view manager
        """
        self.__window = window
        self.config = config
        self.data_dir = data_dir
        self.__builder = builder
        self.__requester = requester

        self.__tagpopup = tagpopup
        self.tagview = tagview
        self.__quick_add_cbs = quick_add_cbs

        #those are added widgets dictionaries
        self.taskwidget_id = 0
        self.taskwidget_widg = {}
        self.view_manager = view_manager

        if task:
            self.task = task
        else:
            self.task = None

        if texteditor:
            self.taskeditor = texteditor
            self.textview = texteditor.textview
            self.__task_toolbar = self.__builder.get_object('task_tb1')
        else:
            self.taskeditor = None
            self.textview= None

    def is_editor(self):
        if self.taskeditor:
            return True
        else:
            return False

    def is_browser(self):
        print "is_browser method in plugin/api should be updated"

    def get_view_manager(self):
        return self.view_manager

#=== General Methods ==========================================================
    def add_menu_item(self, item):
        """Adds a menu entry to the Plugin Menu of the Main Window 
        (task browser).

        @param item: The gtk.MenuItem that is going to be added.  
        """
        widget = self.__builder.get_object('plugin_mi')
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
            wi = self.__builder.get_object('plugin_mi')
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
        wi.pack_start(item)

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
    def add_task_toolbar_item(self, widget):
        """Adds a widget to the task editor's toolbar. 

        @param item: The gtk.ToolButton that is going to be added 
                     to the toolbar.
        """
        #-1 means "append". Very programmer friendly.
        self.__task_toolbar.insert(widget, -1)

    def remove_task_toolbar_item(self, widget):
        """
        Remove a widget from the task editor's toolbar.
        """
        try:
            print "REMOVING", widget
            print "CONTENT"
            for i in xrange(self.__task_toolbar.get_n_items()):
                print self.__task_toolbar.get_nth_item(i)
            self.__task_toolbar.remove(widget)
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

    def set_parent_window(self, child):
        """Sets the plugin dialog as a child of it's parent window, 
        depending on were it is called the parent window can be either 
        the task browser or the task editor.

        @param child: The dialog that is meant to be set as a child. 
        """
        child.set_transient_for(self.__window)

    def get_selected_task(self):
        """Returns the selected task in the task view.

        @return: A task. 
        """
        print "get_selected_task in plugins/api should be updated"
        if self.is_editor():
            return self.task
        elif self.is_browser():
            raise Exception
#        elif self.is_browser():
#            selection = self.taskview.get_selection()
#            model, paths = selection.get_selected_rows()
#            iters = [model.get_iter(path) for path in paths]
#            if len(iters) > 0 and iters[0]:
#                return self.__requester.get_task(model.get_value(iters[0], 0))
#            else:
#                return None
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

#=== Task related methods =====================================================

    def insert_tag(self, tag):
        """Inserts a tag into the current task (in the textview).

        Note: this method only works with the onTaskOpened method. 

        @param tag: The tag's name.
        """
        itera = self.textview.get_insert()
        spacer = ""
        if itera.starts_line():
            spacer = " "
        self.textview.insert_text(spacer + tag, itera)
        self.textview.grab_focus()

    def get_textview(self):
        """Returns the task editor's text view (object).

        Note: this method only works with the onTaskOpened method.

        @return: The task editor's text view (gtk.TextView)
        """
        return self.textview

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

