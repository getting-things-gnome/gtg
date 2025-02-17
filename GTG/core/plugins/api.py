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

import os
import pickle
import logging
from gi.repository import GLib # type: ignore[import-untyped]
from GTG.core.dirs import plugin_configuration_dir

log = logging.getLogger(__name__)


class PluginAPI():
    """The plugin engine's API.

    L{PluginAPI} is a object that provides a nice API for
    plugins to interact with GTG.

    Multiple L{PluginAPI}s can exist. A instance is created to be used
    with the task browser and another instance is created to be used
    with the task editor.
    """

    def __init__(self,
                 app,
                 taskeditor=None):
        """
        Construct a PluginAPI object.

        @param requester: The requester.
        @param view_manager: The view manager
        @param task_id: The Editor, if we are in one
        otherwise.
        """

        self.app = app
        self.ds = app.ds
        self.browser = app.browser

        self.selection_changed_callback_listeners = []

        if taskeditor:
            self.__ui = taskeditor
            self.__task_id = taskeditor.get_task()
        else:
            self.__ui = self.browser
            self.__task_id = None

            for pane in self.browser.panes.values():
                pane.task_selection.connect('selection-changed', self.__selection_changed, pane)

        self.taskwidget_id = 0
        self.taskwidget_widg = []

    def __selection_changed(self, model, position, n_items, user_data=None):
        for func in self.selection_changed_callback_listeners:
            func(user_data.get_selection())

# Accessor methods ============================================================
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
        return self.app

    def get_ui(self):
        """
        Returns a Browser or an Editor
        """
        return self.__ui

    def get_browser(self):
        """
        Returns a Browser
        """
        return self.browser

    def get_menu(self):
        """
        Return the menu entry to the menu of the Task Browser or Task Editor.
        """
        return self.__ui.get_menu()

    def get_header(self):
        """Return the headerbar of the mainwindow"""
        return self.__ui.get_headerbar()

    def get_quickadd_pane(self):
        """Return the quickadd pane"""
        return self.__ui.get_quickadd_pane()

    def get_selected(self):
        """
        Returns the selected tasks in the browser or the task ID if the editor
        """
        if self.is_editor():
            return self.__task_id
        else:
            return self.browser.get_selected_tasks()

    def set_active_selection_changed_callback(self, func):
        if func not in self.selection_changed_callback_listeners:
            self.selection_changed_callback_listeners.append(func)

    def remove_active_selection_changed_callback(self, plugin_class):
        new_list = [func for func in self.selection_changed_callback_listeners
                    if func.__class__ != plugin_class]
        self.selection_changed_callback_listeners = new_list

# Changing the UI ===========================================================
    def add_menu_item(self, item):
        """Adds a menu entry to the menu of the Task Browser or Task Editor.

        @param item: The Gio.MenuItem that is going to be added.
        """
        # All menu items are added to the first section
        _, _, menu = self.__ui.get_menu().iterate_item_links(0).get_next()
        menu.append_item(item)

    def remove_menu_item(self, item):
        """Remove a menu entry to the menu of the Task Browser or Task Editor.

        @param item: The Gio.MenuItem that is going to be removed.
        """
        # you cannot remove items by identity since there values are simply copied
        # when adding a new one. A reliable solution is to instead find the first one
        # with the same label as the given one.
        # All menu items are added to the first section
        _, _, menu = self.get_menu().iterate_item_links(0).get_next()

        length = menu.get_n_items()
        i = 0
        while i < length:
            name = ''.join(menu.get_item_attribute_value(
                i,
                'label',
                GLib.VariantType.new('s')).get_string()
            )

            if name == ''.join(item.get_attribute_value(
                'label',
                GLib.VariantType.new('s')).get_string()
            ):
                menu.remove(i)
                return
            i += 1

    def add_widget_to_taskeditor(self, widget):
        """Adds a widget to the bottom of the task editor dialog

        @param widget: The Gtk.Widget that is going to be added.
        """
        vbox = self.__ui.get_plugin_box()
        if vbox:
            vbox.append(widget)
            self.taskwidget_id += 1
            self.taskwidget_widg.append(widget)
            return self.taskwidget_id
        else:
            return None

    def remove_widget_from_taskeditor(self, widg_id):
        """Remove a widget from the bottom of the task editor dialog

        @param widget: The Gtk.Widget that is going to be removed
        """
        if self.is_editor() and widg_id:
            try:
                wi = self.__ui.get_plugin_box()
                if wi and widg_id in self.taskwidget_widg:
                    wi.remove(self.taskwidget_widg.pop(widg_id))
            except Exception:
                log.exception("Error removing the toolbar item in the "
                              "TaskEditor:")

    def set_bgcolor_func(self, func=None):
        """ Set a function which defines a background color for each task

        NOTE: This function stronglye depend on browser and could be easily
        broken by changes in browser code
        """
        # browser = self.get_browser()

        # set default bgcolor?
        # if func is None:
        #     func = browser.tv_factory.get_task_bg_color

        # for pane in browser.vtree_panes.values():
        #     pane.set_bg_color(func, 'bg_color')
        #     pane.basetree.get_basetree().refresh_all()

# file saving/loading =======================================================
    def load_configuration_object(self, plugin_name, filename,
                                  default_values=None):
        if default_values is not None:
            config = dict(default_values)
        else:
            config = dict()

        dirname = plugin_configuration_dir(plugin_name)
        path = os.path.join(dirname, filename)
        try:
            with open(path, 'rb') as file:
                item = pickle.load(file)
                config.update(item)
        except Exception:
            pass
        return config

    def save_configuration_object(self, plugin_name, filename, item):
        dirname = plugin_configuration_dir(plugin_name)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        path = os.path.join(dirname, filename)
        with open(path, 'wb') as file:
            pickle.dump(item, file)
