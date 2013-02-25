# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 - Lionel Dricot & Bertrand Rousseau
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
import pickle
from xdg.BaseDirectory import xdg_config_home

from GTG.tools.logger import Log


class PluginAPI:
    """The plugin engine's API.

    L{PluginAPI} is a object that provides a nice API for
    plugins to interact with GTG.

    Multiple L{PluginAPI}s can exist. A instance is created to be used
    with the task browser and another instance is created to be used
    with the task editor.
    """

    def __init__(self,
                 requester,
                 view_manager,
                 taskeditor=None):
        """
        Construct a PluginAPI object.

        @param requester: The requester.
        @param view_manager: The view manager
        @param task_id: The Editor, if we are in one
        otherwise.
        """
        self.__requester = requester
        self.__view_manager = view_manager
        self.selection_changed_callback = None
        if taskeditor:
            self.__ui = taskeditor
            self.__builder = self.__ui.get_builder()
            self.__toolbar = self.__builder.get_object('task_tb1')
            self.__task_id = taskeditor.get_task()
        else:
            self.__ui = self.__view_manager.get_browser()
            self.__builder = self.__ui.get_builder()
            self.__toolbar = self.__builder.get_object('task_toolbar')
            self.__task_id = None
            self.__view_manager.browser.selection.connect(
                "changed", self.__selection_changed)

    def __selection_changed(self, selection):
        if self.selection_changed_callback:
            self.selection_changed_callback(selection)

#=== Accessor methods ========================================================
    def is_editor(self):
        """
        Returns true if this is an Editor API
        """
        return bool(self.__task_id)

    def is_browser(self):
        """
        Returns true if this is a Browser API
        """
        return not self.is_editor()

    def get_view_manager(self):
        """
        returns a GTG.gtk.manager.Manager
        """
        return self.__view_manager

    def get_requester(self):
        """
        returns a GTG.core.requester.Requester
        """
        return self.__requester

    def get_gtk_builder(self):
        """
        Returns the gtk builder for the parent window
        """
        return self.__builder

    def get_ui(self):
        '''
        Returns a Browser or an Editor
        '''
        return self.__ui

    def get_selected(self):
        '''
        Returns the selected tasks in the browser or the task ID if the editor
        '''
        if self.is_editor():
            return self.__task_id
        else:
            return self.__view_manager.browser.get_selected_tasks()

    def set_active_selection_changed_callback(self, func):
        self.selection_changed_callback = func

#=== Changing the UI =========================================================
    def add_menu_item(self, item):
        """Adds a menu entry to the Plugin Menu of the Main Window
        (task browser).

        @param item: The gtk.MenuItem that is going to be added.
        """
        widget = self.__builder.get_object('plugin_mi')
        widget.get_submenu().append(item)
        widget.show_all()

    def remove_menu_item(self, item):
        """Removes a menu entry from the Plugin Menu of the Main Window
        (task browser).

        @param item: The gtk.MenuItem that is going to be removed.
        @return: Returns C{True} if the operation has sucess or c{False} if it
        fails.
        """
        menu = self.__builder.get_object('plugin_mi')
        submenu = menu.get_submenu()
        try:
            submenu.remove(item)
        except:
            pass
        if not submenu.get_children():
                menu.hide()

    def add_toolbar_item(self, widget):
        """Adds a button to the task browser's toolbar or the task editor
        toolbar, depending on which plugin api it's being used.

        @param widget: The gtk.ToolButton that is going to be added to the
        toolbar.
        """
        #-1 means "append to the end"
        self.__toolbar.insert(widget, -1)

    def remove_toolbar_item(self, widget):
        """
        Remove a widget from the toolbar.
        """
        try:
            self.__toolbar.remove(widget)
        except Exception, e:
            print "Error removing the toolbar item in the TaskEditor: %s" % e

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

    def remove_widget_from_taskeditor(self, widg_id):
        """Remove a widget from the bottom of the task editor dialog

        @param widget: The gtk.Widget that is going to be removed
        """
        if self.is_editor() and widg_id:
            try:
                wi = self.__builder.get_object('vbox4')
                if wi and widg_id in self.taskwidget_widg:
                    wi.remove(self.taskwidget_widg.pop(widg_id))
            except Exception, e:
                Log.debug("Error removing the toolbar item in the TaskEditor:"
                          "%s" % e)

    def set_bgcolor_func(self, func=None):
        """ Set a function which defines a background color for each task

        NOTE: This function stronglye depend on browser and could be easily
        broken by changes in browser code
        """
        browser = self.__ui

        # set default bgcolor?
        if func is None:
            func = browser.tv_factory.task_bg_color

        for pane in browser.vtree_panes.itervalues():
            pane.set_bg_color(func, 'bg_color')
            pane.basetree.get_basetree().refresh_all()

#=== file saving/loading =====================================================
    def load_configuration_object(self, plugin_name, filename,
                                  basedir=xdg_config_home,
                                  default_values=None):
        if default_values is not None:
            config = dict(default_values)
        else:
            config = dict()

        dirname = os.path.join(basedir, 'gtg/plugins', plugin_name)
        path = os.path.join(dirname, filename)
        if os.path.isdir(dirname):
            if os.path.isfile(path):
                try:
                    with open(path, 'r') as file:
                        item = pickle.load(file)
                        config.update(item)
                except:
                    pass
        else:
            os.makedirs(dirname)
        return config

    def save_configuration_object(self, plugin_name, filename, item,
                                  basedir=xdg_config_home):
        dirname = os.path.join(basedir, 'gtg/plugins', plugin_name)
        path = os.path.join(dirname, filename)
        with open(path, 'wb') as file:
            pickle.dump(item, file)
