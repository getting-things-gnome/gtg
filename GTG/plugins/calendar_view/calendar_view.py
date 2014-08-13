# -*- coding: utf-8 -*-
# Copyright (c) 2014 - Sara Ribeiro <sara.rmgr@gmail.com>

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

from gi.repository import Gtk
from GTG import _
from GTG.plugins.calendar_view.calendar_plugin import CalendarPlugin


class calendarView:

    def __init__(self):
        self.plugin_api = None
        self.tb_button = None

        self.add_task_handle = None
        self.set_task_handle = None
        self.remove_task_handle = None

    def activate(self, plugin_api):
        """ Activates the plugin """
        self.plugin_api = plugin_api
        self.req = self.plugin_api.get_requester()
        self.view_manager = plugin_api.get_view_manager()
        self.calendar = None
        self._init_gtk()

        self.plugin_api.set_active_selection_changed_callback(
            self.selection_changed)

    def _init_calendar(self):
        """ Creates and initializes a calendar, but don't show it yet """
        if not self.calendar:
            self.calendar = CalendarPlugin(self.req, self.view_manager)
        self.calendar.controller.new_task_callback(self.open_task)
        self.calendar.controller.edit_task_callback(self.open_task)
        self.calendar.controller.delete_task_callback(self.delete_task)
        self.calendar.window.hide()

    def deactivate(self, plugin_api):
        """ Removes the gtk widgets and distroy calendar before quitting """
        self._disconnect_signals()
        self._gtk_deactivate()
        del self.calendar

    def show_calendar(self, button):
        """ User clicked to open calendar plugin, so show it """
        if not self.calendar:
            self._init_calendar()
        self._connect_signals()
        self.calendar.window.show()

    def delete_task(self, task_id, widget=None):
        """ Use view manager dialog to ask to delete task """
        self.view_manager.ask_delete_tasks([task_id])

    def selection_changed(self, selection):
        """ Callback for when task selection changes """
        pass

    def open_task(self, task_id=None, thisisnew=False):
        """
        Opens a task in the TaskEditor, if it's not currently opened.
        If task_id is None, it creates a new task and opens it
        """
        if task_id is None:
            task_id = self.req.new_task().get_id()
        self.view_manager.open_task(task_id, thisisnew=thisisnew)

# GTK FUNCTIONS ##############################################################
    def _init_gtk(self):
        """ Initialize all the GTK widgets """

        self.tb_button = Gtk.ToolButton()
        self.tb_button.set_icon_name("x-office-calendar")
        self.tb_button.set_is_important(True)
        self.tb_button.set_label(_("View as calendar"))
        self.tb_button.set_tooltip_text(_("Display tasks with start and due dates in a calendar view"))
        self.tb_button.connect('clicked', self.show_calendar)
        self.tb_button.show()
        self.plugin_api.add_toolbar_item(self.tb_button)

    def _gtk_deactivate(self):
        """ Remove Toolbar Button """
        if self.tb_button:
            self.plugin_api.remove_toolbar_item(self.tb_button)
            self.tb_button = False

# TREE CALLBACKS #############################################################
    def _connect_signals(self):
        """
        Helper function to connect signals
        """
        if not self.add_task_handle:
            self.add_task_handle = self.req.get_main_view().register_cllbck(
                'node-added',
                lambda tid, _: self.calendar.controller.update_tasks())
        if not self.set_task_handle:
            self.set_task_handle = self.req.get_main_view().register_cllbck(
                'node-modified',
                lambda tid, _: self.calendar.controller.update_tasks())
        if not self.remove_task_handle:
            self.remove_task_handle = self.req.get_main_view().register_cllbck(
                'node-deleted',
                lambda tid, _: self.calendar.controller.update_tasks())

    def _disconnect_signals(self):
        """
        Helper function to disconnect signals
        """
        if self.add_task_handle:
            self.req.get_main_view().deregister_cllbck('node-added',
                                                       self.add_task_handle)
            self.add_task_handle = None
        if self.set_task_handle:
            self.req.get_main_view().deregister_cllbck('node-modified',
                                                       self.set_task_handle)
            self.set_task_handle = None
        if self.remove_task_handle:
            self.req.get_main_view().deregister_cllbck('node-deleted',
                                                       self.remove_task_handle)
            self.remove_task_handle = None
