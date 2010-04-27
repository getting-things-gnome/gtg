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

from GTG.core  import CoreConfig
from GTG.tools import cleanxml, taskxml

def get_name():
    """Returns the name of the backend as it should be displayed in the UI"""
    return "Local File"

def get_description():
    """Returns a description of the backend"""
    return "Your tasks are saved in an XML file located in your HOME folder"

def get_parameters():
    """
    Returns a dictionary of parameters. Keys should be strings and
    are the name of the parameter.
    Values are string with value : string, password, int, bool
    and are an information about the type of the parameter
    Currently, only string is supported.
    """
    dic = {}
    dic["filename"] = "string"
    return dic

def get_features():
    """Returns a dict of features supported by this backend"""
    return {}

def get_type():
    """Type is one of : readwrite, readonly, import, export"""
    return "readwrite"

class Backend:
    def __init__(self, parameters, firstrunxml=None):
        """
        Instantiates a new backend.

        @param parameters: should match the dictionary returned in
         get_parameters. Anyway, the backend should care if one expected value is
         None or does not exist in the dictionary.
        @firstrun: only needed for the default backend. It should be omitted for
         all other backends.
        """
        self.tids = []
        self.pid = 1
        if "filename" in parameters:
            zefile = parameters["filename"]
        #If zefile is None, we create a new file
        else:
            zefile = "%s.xml" %(uuid.uuid4())
            parameters["filename"] = zefile
        #For the day we want to open files somewhere else
        default_folder = True
        if default_folder:
            self.zefile = os.path.join(CoreConfig.DATA_DIR, zefile)
            self.filename = zefile
        else:
            self.zefile = zefile
            self.filename = zefile
        #Create the default tasks for the first run.
        #We write the XML object in a file
        if firstrunxml and not os.path.exists(zefile):
            #shutil.copy(firstrunfile,self.zefile)
            cleanxml.savexml(self.zefile, firstrunxml)
        self.doc, self.xmlproj = cleanxml.openxmlfile(self.zefile, "project")

    def start_get_tasks(self,push_task_func,task_factory_func):
        '''
        Once this function is launched, the backend can start pushing
        tasks to gtg parameters.

        @push_task_func: a function that takes a Task as parameter
         and pushes it into GTG.
        @task_factory_func: a function that takes a tid as parameter
         and returns a Task object with the given pid. 

        @return: start_get_tasks() might not return or finish
        '''
        tid_list = []
        for node in self.xmlproj.childNodes:
            #time.sleep(2)
            tid = node.getAttribute("id")
            if tid not in self.tids:
                self.tids.append(tid)
            task = task_factory_func(tid)
            task = taskxml.task_from_xml(task,node)
            push_task_func(task)
        #print "#### finishing pushing tasks"

    def set_task(self, task):
        ''' Save the task in the backend '''
        #time.sleep(4)
        tid = task.get_id()
        if tid not in self.tids:
            self.tids.append(tid)
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
        if modified and self.zefile and self.doc :
            cleanxml.savexml(self.zefile, self.doc)
        return None

    def remove_task(self, tid):
        ''' Completely remove the task with ID = tid '''
        for node in self.xmlproj.childNodes:
            if node.getAttribute("id") == tid:
                self.xmlproj.removeChild(node)
                if tid in self.tids:
                    self.tids.remove(tid)
        cleanxml.savexml(self.zefile, self.doc)

    def new_task_id(self):
        '''
        Returns an available ID for a new task so that a task with this ID
        can be saved with set_task later.
        If None, then GTG will create a new ID by itself.
        The ID cannot contain the character "@".
        '''
        k = 0
        pid = self.pid
        newid = "%s@%s" %(k, pid)
        while str(newid) in self.tids:
            k += 1
            newid = "%s@%s" %(k, pid)
        self.tids.append(newid)
        return newid

    def quit(self):
        '''
        Called when GTG quits or disconnects the backend.
        (Subclasses might pass here)
        '''
        cleanxml.savexml(self.zefile, self.doc, backup=True)
