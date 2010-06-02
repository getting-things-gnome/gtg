# -*- coding: utf-8 -*-
# pylint: disable-msg=W0201
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
import unicodedata

import dbus
import dbus.glib
import dbus.service

from GTG.core  import CoreConfig
from GTG.tools import dates


BUSNAME = CoreConfig.BUSNAME
BUSFACE = CoreConfig.BUSINTERFACE


def dsanitize(data):
    """
    Clean up a dict so that it can be transmitted through D-Bus.
    D-Bus does not have concepts for empty or null arrays or values 
    so these need to be converted into blank values D-Bus accepts.
    @return: Cleaned up dictionary
    """
    for k, v in data.items():
        # Manually specify an arbitrary content type for empty Python arrays
        # because D-Bus can't handle the type conversion for empty arrays
        if not v and isinstance(v, list):
            data[k] = dbus.Array([], "s")
        # D-Bus has no concept of a null or empty value so we have to convert
        # None types to something else. I use an empty string because it has
        # the same behavior as None in a Python conditional expression
        elif v == None:
            data[k] = ""

    return data


def task_to_dict(task):
    """
    Translate a task object into a D-Bus dictionary
    """
    return dbus.Dictionary(dsanitize({
          "id": task.get_id(),
          "status": task.get_status(),
          "title": task.get_title(),
          "duedate": str(task.get_due_date()),
          "startdate": str(task.get_start_date()),
          "donedate": str(task.get_closed_date()),
          "tags": task.get_tags_name(),
          "text": task.get_text(),
          "subtask": task.get_children(),
          "parents": task.get_parents(),
          }), signature="sv")


class DBusTaskWrapper(dbus.service.Object):
    """
    D-Bus service object that exposes GTG's task store to third-party apps
    """

    def __init__(self, req, view_manager):
        # Attach the object to D-Bus
        self.bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(BUSNAME, bus=self.bus)
        dbus.service.Object.__init__(self, bus_name, BUSFACE)
        self.req = req
        self.view_manager = view_manager

    @dbus.service.method(BUSNAME)
    def get_task(self, tid):
        """
        Retrieve a specific task by ID and return the data
        """
        toret = task_to_dict(self.req.get_task(tid))
        return toret

    @dbus.service.method(BUSNAME)
    def get_tasks(self):
        """
        Retrieve a list of task data dicts
        """
        return self.get_tasks_filtered(['all'])

    @dbus.service.method(BUSNAME, in_signature="as")
    def get_active_tasks(self, tags):
        """
        Retrieve a list of task data dicts
        """
        return self.get_tasks_filtered(['active', 'workable'])

    @dbus.service.method(BUSNAME, in_signature="as")
    def get_task_ids_filtered(self, filters):
        """
        Filters the task list and provides list of remaining ids
        @param:  List of strings for filters to apply.  See the
         filters_bank documentation for a list of stock filters.
        @return: List of ids
        """
        tree = self.req.get_custom_tasks_tree()
        for filter in filters:
            tree.apply_filter(filter)
        return tree.get_all_keys()

    @dbus.service.method(BUSNAME, in_signature="as")
    def get_tasks_filtered(self, filters):
        """
        Gets a list of tasks for the given filters
        @param:  List of strings for filters to apply.  See the
         filters_bank documentation for a list of stock filters.
        @return: List of task dicts
        """
        tasks = self.get_task_ids_filtered(filters)
        if tasks:
            return [self.get_task(id) for id in tasks]
        else:
            return dbus.Array([], "s")

    @dbus.service.method(BUSNAME)
    def has_task(self, tid):
        """
        Returns true if the task id is present in the task backend.
        Task could be either open or closed, but not deleted.
        """
        return self.req.has_task(tid)

    @dbus.service.method(BUSNAME)
    def delete_task(self, tid):
        """
        Delete the given task id from the repository.
        """
        self.req.delete_task(tid)

    @dbus.service.method(BUSNAME, in_signature="sssssassas")
    def new_task(self, status, title, duedate, startdate, donedate, tags,
                 text, subtasks):
        """
        Generate a new task object and return the task data as a dict
        @param status:     One of 'Active', 'Dismiss', or 'Done'
        @param title:      String name of the task
        @param duedate:    Date the task is due, such as "2010-05-01".
         also supports 'now', 'soon', 'later'
        @param startdate:  Date the task will be started
        @param donedate:   Date the task was finished
        @param tags:       List of strings for tags to apply for this task
        @param text:       String description
        @param subtasks:   A list of task ids of tasks to add as children
        @return: A dictionary with the data of the newly created task
        """
        nt = self.req.new_task(tags=tags)
        for sub in subtasks:
            nt.add_child(sub)
        nt.set_status(status, donedate=dates.strtodate(donedate))
        nt.set_title(title)
        nt.set_due_date(dates.strtodate(duedate))
        nt.set_start_date(dates.strtodate(startdate))
        nt.set_text(text)
        return task_to_dict(nt)

    @dbus.service.method(BUSNAME)
    def modify_task(self, tid, task_data):
        """
        Updates the task with ID tid using the provided information
        in the task_data structure.  Note that any fields left blank
        or undefined in task_data will clear the value in the task,
        so the best way to update a task is to first retrieve it via
        get_task(tid), modify entries as desired, and send it back
        via this function.        
        """
        task = self.req.get_task(tid)
        task.set_status(task_data["status"], donedate=dates.strtodate(task_data["donedate"]))
        task.set_title(task_data["title"])
        task.set_due_date(dates.strtodate(task_data["duedate"]))
        task.set_start_date(dates.strtodate(task_data["startdate"]))
        task.set_text(task_data["text"])

        for tag in task_data["tags"]:
            task.add_tag(tag)
        for sub in task_data["subtask"]:
            task.add_child(sub)
        return task_to_dict(task)

    @dbus.service.method(BUSNAME)
    def open_task_editor(self, tid):
        """
        Launches the GUI task editor showing the task with ID tid.

        This routine returns as soon as the GUI has launched.
        """
        self.view_manager.open_task(tid)
        
    @dbus.service.method(BUSNAME, in_signature="ss")
    def open_new_task(self, title, description):
        """
        Launches the GUI task editor with a new task.  The task is not
        guaranteed to exist after the editor is closed, since the user
        could cancel the editing session.

        This routine returns as soon as the GUI has launched.
        """
        nt = self.req.new_task(newtask=True)
        nt.set_title(title)
        if description != "":
            nt.set_text(description)
        uid = nt.get_id()
        self.view_manager.open_task(uid,thisisnew=True)

    @dbus.service.method(BUSNAME)
    def hide_task_browser(self):
        """
        Causes the main task browser to become invisible.  It is still
        running but there will be no visible indication of this.
        """
        self.view_manager.hide_browser()

    @dbus.service.method(BUSNAME)
    def iconify_task_browser(self):
        """
        Minimizes the task browser
        """
        self.view_manager.iconify_browser()

    @dbus.service.method(BUSNAME)
    def show_task_browser(self):
        """
        Shows and unminimizes the task browser and brings it to the
        top of the z-order.
        """
        self.view_manager.show_browser()

    @dbus.service.method(BUSNAME)
    def is_task_browser_visible(self):
        """
        Returns true if task browser is visible, either minimized or
        unminimized, with or without active focus.
        """
        return self.view_manager.is_browser_visible()
