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

#our own imports
from taskbrowser.browser import TaskBrowser
from gtg_core.datastore   import DataStore
from backends.localfile import Backend
from gtg_core   import CoreConfig

#=== OBJECTS ===================================================================

#=== MAIN CLASS ================================================================

class Gtg:
 
    def main(self):
        config = CoreConfig()
        #bl = config.get_backends_list()
        #TODO : list available backends
        #TODO : get backend list
        #Currently we will use bl to build a fake backend list of dic
        bl = ['4af9e35b-8854-477e-b1f1-d95553664b5f.xml', \
                            'f8c7d20e-a627-49da-bf66-82f1fff293a6.xml']
        backend_list = []
        for i in bl :
            dic = {}
            dic["filename"] = i
            dic["module"] = "localfile"
            backend_list.append(dic)
        
        # Load data store
        ds = DataStore()
        backends = []
        
        #Now we import all the backends
        for b in backend_list :
            #We need to remove the module name from the dictionnary
            #We dynamically import modules needed
            module_name = "backends.%s"%b.pop("module")
            module = __import__(module_name)
            classobj = getattr(module, "localfile")
            
            back = classobj.Backend(b,ds)
            backends.append(back)
        
#        # Create & init backends
#        backends = []
#        for b in bl:
#            backends.append(Backend(b,ds))

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
        config.save_datastore(ds)

#=== EXECUTION =================================================================

if __name__ == "__main__":
    gtg = Gtg()
    gtg.main()
