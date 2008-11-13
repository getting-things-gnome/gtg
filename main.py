#!/usr/bin/env python
#
#===============================================================================
#
# GTD-gnome: a gtd organizer for GNOME
#
# @author : B. Rousseau, L. Dricot
# @date   : November 2008
#
#   main.py contains the main GTK interface for the tasklist
#   task.py contains the implementation of a task and a project
#   taskeditor contains the GTK interface for task editing
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
import sys

#our own imports
from task import Task, Project
from taskeditor  import TaskEditor
from taskbrowser import TaskBrowser
from datastore   import DataStore
#subfolders are added to the path
sys.path[1:1]=["backends"]
from xml_backend import Backend

#=== OBJECTS ===================================================================

#=== MAIN CLASS ================================================================

class Gtg:

    def __init__(self):        
        self.projects = [] 
        
    def main(self):

        # Read configuration
        # TODO: implement configuration storage (gconf?)

        # Create & init backends
        # TODO: implement generic (configuration-dependent) code
        backend1 = Backend("mynote.xml")
        backend2 = Backend("bert.xml")

        # Load data store
        ds = DataStore()
        ds.register_backend(backend1)
        ds.register_backend(backend2)
        ds.load_data()

        # Launch task browser
        tb = TaskBrowser(ds.get_all_projects())
        tb.main()

        

#=== EXECUTION =================================================================

if __name__ == "__main__":
    gtg = Gtg()
    gtg.main()
