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

'''
Localfile is a read/write backend that will store your tasks in an XML file
This file will be in your $XDG_DATA_DIR/gtg folder.

This backend contains comments that are meant as a reference, in case someone
wants to write a backend.
'''

import os

from GTG import _
from GTG.backends.genericbackend import GenericBackend
from GTG.core import CoreConfig
from GTG.tools import cleanxml, taskxml

# Ignore all other elements but this one
TASK_NODE = "task"


class Backend(GenericBackend):
    """
    Localfile backend, which stores your tasks in a XML file in the standard
    XDG_DATA_DIR/gtg folder (the path is configurable).
    An instance of this class is used as the default backend for GTG.
    This backend loads all the tasks stored in the localfile after it's enabled
    and from that point on just writes the changes to the file: it does not
    listen for eventual file changes
    """

    # General description of the backend: these are used to show a description
    # of the backend to the user when s/he is considering adding it.
    # BACKEND_NAME is the name of the backend used internally (it must be
    # unique).
    # Please note that BACKEND_NAME and BACKEND_ICON_NAME should *not* be
    # translated.
    _general_description = {
        GenericBackend.BACKEND_NAME: "backend_localfile",
        GenericBackend.BACKEND_HUMAN_NAME: _("Local File"),
        GenericBackend.BACKEND_AUTHORS: ["Lionel Dricot",
                                         "Luca Invernizzi"],
        GenericBackend.BACKEND_TYPE: GenericBackend.TYPE_READWRITE,
        GenericBackend.BACKEND_DESCRIPTION:
        _("Your tasks are saved in a text file (XML format). " +
          " This is the most basic and the default way " +
          "for GTG to save your tasks."),
    }

    # These are the parameters to configure a new backend of this type. A
    # parameter has a name, a type and a default value.
    # Here, we define a parameter "path", which is a string, and has a default
    # value as a random file in the default path
    _static_parameters = {
        "path": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE:
            "gtg_tasks.xml"}}

    def __init__(self, parameters):
        """
        Instantiates a new backend.

        @param parameters: A dictionary of parameters, generated from
        _static_parameters. A few parameters are added to those, the list of
        these is in the "DefaultBackend" class, look for the KEY_* constants.

        The backend should take care if one expected value is None or
        does not exist in the dictionary.
        """
        super(Backend, self).__init__(parameters)
        # RETROCOMPATIBILIY
        # NOTE: retrocompatibility from the 0.2 series to 0.3.
        # We convert "filename" to "path and we forget about "filename "
        if "need_conversion" in parameters:
            parameters["path"] = parameters.pop("need_conversion")
        if not self.KEY_DEFAULT_BACKEND in parameters:
            parameters[self.KEY_DEFAULT_BACKEND] = True

        self.doc, self.xmlproj = cleanxml.openxmlfile(
            self.get_path(), "project")
        # Make safety daily backup after loading
        cleanxml.savexml(self.get_path(), self.doc, backup=True)

    def get_path(self):
        """
        Return the current path to XML

        Path can be relative to projects.xml
        """
        path = self._parameters["path"]
        if os.sep not in path:
            # Local path
            data_dir = CoreConfig().get_data_dir()
            path = os.path.join(data_dir, path)
        return os.path.abspath(path)

    def initialize(self):
        """ This is called when a backend is enabled """
        super(Backend, self).initialize()
        self.doc, self.xmlproj = cleanxml.openxmlfile(
            self.get_path(), "project")

    def this_is_the_first_run(self, xml):
        """ Called upon the very first GTG startup.
        This function is needed only in this backend, because it can be used as
        default one.
        The xml parameter is an object containing GTG default tasks. It will be
        saved to a file, and the backend will be set as default.
        @param xml: an xml object containing the default tasks.
        """
        self._parameters[self.KEY_DEFAULT_BACKEND] = True
        cleanxml.savexml(self.get_path(), xml)
        self.doc, self.xmlproj = cleanxml.openxmlfile(
            self.get_path(), "project")

    def start_get_tasks(self):
        """ This function starts submitting the tasks from the XML file into
        GTG core. It's run as a separate thread.

        @return: start_get_tasks() might not return or finish
        """
        for node in self.xmlproj.childNodes:
            if node.nodeName != TASK_NODE:
                continue
            tid = node.getAttribute("id")
            task = self.datastore.task_factory(tid)
            if task:
                task = taskxml.task_from_xml(task, node)
                self.datastore.push_task(task)

    def set_task(self, task):
        """
        This function is called from GTG core whenever a task should be
        saved, either because it's a new one or it has been modified.
        This function will look into the loaded XML object if the task is
        present, and if it's not, it will create it. Then, it will save the
        task data in the XML object.

        @param task: the task object to save
        """
        tid = task.get_id()
        # We create an XML representation of the task
        t_xml = taskxml.task_to_xml(self.doc, task)

        # we find if the task exists in the XML treenode.
        existing = None
        for node in self.xmlproj.childNodes:
            if node.nodeName == TASK_NODE and node.getAttribute("id") == tid:
                existing = node

        modified = False
        # We then replace the existing node
        if existing and t_xml:
            # We will write only if the task has changed
            if t_xml.toxml() != existing.toxml():
                self.xmlproj.replaceChild(t_xml, existing)
                modified = True
        # If the node doesn't exist, we create it
        else:
            self.xmlproj.appendChild(t_xml)
            modified = True

        # if the XML object has changed, we save it to file
        if modified and self._parameters["path"] and self.doc:
            cleanxml.savexml(self.get_path(), self.doc)

    def remove_task(self, tid):
        """ This function is called from GTG core whenever a task must be
        removed from the backend. Note that the task could be not present here.

        @param tid: the id of the task to delete
        """
        modified = False
        for node in self.xmlproj.childNodes:
            if node.nodeName == TASK_NODE and node.getAttribute("id") == tid:
                modified = True
                self.xmlproj.removeChild(node)

        # We save the XML file only if it's necessary
        if modified:
            cleanxml.savexml(self.get_path(), self.doc, backup=True)
