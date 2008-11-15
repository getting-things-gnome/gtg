#!/usr/bin/env python
#
#===============================================================================
#
# Getting things Gnome!: a gtd-inspired organizer for GNOME
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
import sys, os, xml.dom.minidom

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

    CONFIG_FILE = "config.xml"

    def __init__(self):        
        self.projects = []
    
    def main(self):

        backends_fn = []
        backends = []

        # Read configuration
        if os.path.exists(self.CONFIG_FILE) :
            f = open(self.CONFIG_FILE,mode='r')
            # sanitize the pretty XML
            doc=xml.dom.minidom.parse(self.CONFIG_FILE)
            self.__cleanDoc(doc,"\t","\n")
            self.__xmlproject = doc.getElementsByTagName("backend")
            for xp in self.__xmlproject:
                backends_fn.append(str(xp.getAttribute("filename")))
            f.close()
        else:
            print "No config file found!"

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

        # save configuration
        s = "<?xml version=\"1.0\" ?><config>\n"
        for b in ds.get_all_backends():
            s = s + "\t<backend filename=\"%s\"/>\n" % b.get_filename()
        s = s + "</config>\n"
        f = open(self.CONFIG_FILE,mode='w')
        f.write(s)
        f.close()

    #Those two functions are there only to be able to read prettyXML
    #Source : http://yumenokaze.free.fr/?/Informatique/Snipplet/Python/cleandom       
    def __cleanDoc(self,document,indent="",newl=""):
        node=document.documentElement
        self.__cleanNode(node,indent,newl)
 
    def __cleanNode(self,currentNode,indent,newl):
        filter=indent+newl
        if currentNode.hasChildNodes:
            for node in currentNode.childNodes:
                if node.nodeType == 3 :
                    node.nodeValue = node.nodeValue.lstrip(filter).strip(filter)
                    if node.nodeValue == "":
                        currentNode.removeChild(node)
            for node in currentNode.childNodes:
                self.__cleanNode(node,indent,newl)


#=== EXECUTION =================================================================

if __name__ == "__main__":
    gtg = Gtg()
    gtg.main()
