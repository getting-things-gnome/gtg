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

'''
Localfile is a read/write backend that will store your tasks in an XML file
This file will be in your $XDG_DATA_DIR/gtg folder.
'''

import os
import uuid
from collections import deque
import threading

from GTG.backends.genericbackend import GenericBackend
from GTG.core                    import CoreConfig
from GTG.tools                   import cleanxml, taskxml
from GTG                         import _
from GTG.tools.logger            import Log



class Backend(GenericBackend):
    

    DEFAULT_PATH = CoreConfig().get_data_dir() #default path for filenames


    #Description of the backend (mainly it's data we show the user, only the
    # name is used internally. Please note that BACKEND_NAME and
    # BACKEND_ICON_NAME should *not* be translated.
    _general_description = { \
        GenericBackend.BACKEND_NAME:       "backend_localfile", \
        GenericBackend.BACKEND_HUMAN_NAME: _("Local File"), \
        GenericBackend.BACKEND_AUTHORS:    ["Lionel Dricot", \
                                            "Luca Invernizzi"], \
        GenericBackend.BACKEND_TYPE:       GenericBackend.TYPE_READWRITE, \
        GenericBackend.BACKEND_DESCRIPTION: \
            _("Your tasks are saved in a text file (XML format). " + \
              " This is the most basic and the default way " +   \
              "for GTG to save your tasks."),\
        }

    #parameters to configure a new backend of this type.
    #NOTE: should we always give back a different default filename? it can be
    #      done, but I'd like to keep this backend simple, so that it can be
    #      used as example (invernizzi)
    _static_parameters = { \
        "path": { \
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING, \
            GenericBackend.PARAM_DEFAULT_VALUE: \
                 os.path.join(DEFAULT_PATH, "gtg_tasks-%s.xml" %(uuid.uuid4()))
        }}

    def _get_default_filename_path(self, filename = None):
        '''
        Generates a default path with a random filename
        @param filename: specify a filename
        '''
        if not filename:
            filename = "gtg_tasks-%s.xml" % (uuid.uuid4())
        return os.path.join(self.DEFAULT_PATH, filename)

    def __init__(self, parameters):
        """
        Instantiates a new backend.

        @param parameters: should match the dictionary returned in
        get_parameters. Anyway, the backend should care if one expected
        value is None or does not exist in the dictionary. 
        @firstrun: only needed for the default backend. It should be
        omitted for all other backends.
        """
        super(Backend, self).__init__(parameters)
        self.tids = []
        #####RETROCOMPATIBILIY
        #NOTE: retrocompatibility. We convert "filename" to "path"
        #      and we forget about "filename"
        if "need_conversion" in parameters:
            parameters["path"] = os.path.join(self.DEFAULT_PATH, \
                                        parameters["need_conversion"])
            del parameters["need_conversion"]
        if not self.KEY_DEFAULT_BACKEND in parameters:
            parameters[self.KEY_DEFAULT_BACKEND] = True
        ####
        self.doc, self.xmlproj = cleanxml.openxmlfile( \
                                self._parameters["path"], "project")

    def initialize(self):
        super(Backend, self).initialize()
        self.doc, self.xmlproj = cleanxml.openxmlfile( \
                                self._parameters["path"], "project")

    def this_is_the_first_run(self, xml):
        #Create the default tasks for the first run.
        #We write the XML object in a file
        self._parameters[self.KEY_DEFAULT_BACKEND] = True
        cleanxml.savexml(self._parameters["path"], xml)
        self.doc, self.xmlproj = cleanxml.openxmlfile(\
                        self._parameters["path"], "project")
        self._parameters[self.KEY_DEFAULT_BACKEND] = True

    def start_get_tasks(self):
        '''
        Once this function is launched, the backend can start pushing
        tasks to gtg parameters.
        
        @return: start_get_tasks() might not return or finish
        '''
        tid_list = []
        for node in self.xmlproj.childNodes:
            tid = node.getAttribute("id")
            if tid not in self.tids:
                self.tids.append(tid)
            task = self.datastore.task_factory(tid)
            print "****LOADING tid", tid 
            if task:
                task = taskxml.task_from_xml(task, node)
                print "**GOT TASK", task.get_title()
                self.datastore.push_task(task)
            else:
                print "tried to load task with the same tid"
        #print "#### finishing pushing tasks"

    def set_task(self, task):
            tid = task.get_id()
            existing = None
            #First, we find the existing task from the treenode
            for node in self.xmlproj.childNodes:
                if node.getAttribute("id") == tid:
                    existing = node
            t_xml = taskxml.task_to_xml(self.doc, task)
            modified = False
            #We then replace the existing node
            if existing and t_xml:
                #We will write only if the task has changed
                if t_xml.toxml() != existing.toxml():
                    self.xmlproj.replaceChild(t_xml, existing)
                    modified = True
            #If the node doesn't exist, we create it
            # (it might not be the case in all backends
            else:
                self.xmlproj.appendChild(t_xml)
                modified = True
            #In this particular backend, we write all the tasks
            #This is inherent to the XML file backend
            if modified and self._parameters["path"] and self.doc :
                cleanxml.savexml(self._parameters["path"], self.doc)

    def remove_task(self, tid):
        ''' Completely remove the task with ID = tid '''
        print "REMOVING "+self._parameters["path"]
        for node in self.xmlproj.childNodes:
            print node.getAttribute("id")
            if node.getAttribute("id") == tid:
                self.xmlproj.removeChild(node)
                #                print "still in datastore" , self.datastore.has_task(tid)
                if tid in self.tids:
                    self.tids.remove(tid)
        cleanxml.savexml(self._parameters["path"], self.doc)


    def quit(self, disable = False):
        '''
        Called when GTG quits or disconnects the backend.
        '''
        super(Backend, self).quit(disable)
        print "quitting " + self._parameters["path"]

    def save_state(self):
        cleanxml.savexml(self._parameters["path"], self.doc, backup=True)

    def get_number_of_tasks(self):
        '''
        Returns the number of tasks stored in the backend. Doesn't need to be a
        fast function, is called just for the UI
        '''
        return len(self.tids)
