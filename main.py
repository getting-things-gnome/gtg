#!/usr/bin/env python
# -*- coding: utf-8 -*
#
#===============================================================================
#
# Getting things Gnome!: a gtd-inspired organizer for GNOME
#
# @author : B. Rousseau, L. Dricot
# @date   : November 2008
#
#   main.py contains the configuration and data structures loader
#   taskbrowser.py contains the main GTK interface for the tasklist
#   task.py contains the implementation of a task and a project
#   taskeditor contains the GTK interface for task editing
#       (it's the window you see when writing a task)
#   backends/xml_backend.py is the way to store tasks and project in XML
#
#   tid stand for "Task ID"
#   pid stand for "Project ID"
#   uid stand for "Universal ID" which is generally the tuple [pid,tid]
#
#   Each id are *strings*
#   tid are the form "X@Y" where Y is the pid.
#   For example : 21@2 is the 21th task of the 2nd project
#   This way, we are sure that a tid is unique accross multiple projects 
#
#=============================================================================== 

#=== IMPORT ====================================================================
import sys, os, xml.dom.minidom

#our own imports
from gtg_core.task import Task, Project
from gnome_frontend.taskeditor  import TaskEditor
from gnome_frontend.taskbrowser import TaskBrowser
from gtg_core.datastore   import DataStore
from backends.localfile import Backend
from gtg_core   import CoreConfig
from tools import cleanxml

#=== OBJECTS ===================================================================

#=== MAIN CLASS ================================================================

class Gtg:

    def __init__(self):        
        self.projects = []
    
    def main(self):

        backends_fn = []
        backends = []

        # Check if config dir exists, if not create it
        if not os.path.exists(CoreConfig.DATA_DIR):
            os.mkdir(CoreConfig.DATA_DIR)

        # Read configuration file, if it does not exist, create one
        if os.path.exists(CoreConfig.DATA_DIR + CoreConfig.DATA_FILE) :
            f = open(CoreConfig.DATA_DIR + CoreConfig.DATA_FILE,mode='r')
            # sanitize the pretty XML
            doc=xml.dom.minidom.parse(CoreConfig.DATA_DIR + CoreConfig.DATA_FILE)
            cleanxml.cleanDoc(doc,"\t","\n")
            self.__xmlproject = doc.getElementsByTagName("backend")
            # collect configred backends
            for xp in self.__xmlproject:
                zefile = str(xp.getAttribute("filename"))
                backends_fn.append(str(zefile))
            f.close()
        else:
            print "No config file found! Creating one."
            f = open(CoreConfig.DATA_DIR + CoreConfig.DATA_FILE,mode='w')
            f.write(CoreConfig.DATA_FILE_TEMPLATE)
            f.close()

        # Create & init backends
        for b in backends_fn:
            backends.append(Backend(b))

        # Load data store
        ds = DataStore()
        for b in backends:
            ds.register_backend(b)
        ds.load_data()

        # Launch task browser
        tb = TaskBrowser(ds)
        tb.main()

        # Ideally we should load window geometry configuration from a config.
        # backend like gconf at some point, and restore the appearance of the
        # application as the user last exited it.

        # Ending the application: we save configuration
        s = "<?xml version=\"1.0\" ?><config>\n"
        for b in ds.get_all_backends():
            s = s + "\t<backend filename=\"%s\"/>\n" % b.get_filename()
        s = s + "</config>\n"
        f = open(CoreConfig.DATA_DIR + CoreConfig.DATA_FILE,mode='w')
        f.write(s)
        f.close()

#=== EXECUTION =================================================================

if __name__ == "__main__":
    gtg = Gtg()
    gtg.main()
