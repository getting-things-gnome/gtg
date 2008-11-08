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
#=============================================================================== 

#=== IMPORT ====================================================================
#system imports
import pygtk
pygtk.require('2.0')
import gtk
import gobject
import xml.dom.minidom
import gtk.glade
import datetime, time, sys

#our own imports
from task import Task, Project
from taskeditor import TaskEditor
#subfolders are added to the path
sys.path[1:1]=["backends"]
from xml_backend import Backend

#=== OBJECTS ===================================================================

#=== MAIN CLASS ================================================================

class Base:

    def __init__(self):
        
        #Set the Glade file
        self.gladefile = "gtd-gnome.glade"  
        self.wTree = gtk.glade.XML(self.gladefile) 
        
        #Get the Main Window, and connect the "destroy" event
        self.window = self.wTree.get_widget("MainWindow")
        if (self.window):
            self.window.connect("destroy", gtk.main_quit)

        #Create our dictionay and connect it
        dic = {
                "on_add_task"       : self.on_add_task,
                "on_edit_task"      : self.on_edit_task,
                "on_delete_task"    : self.on_delete_task,
                "on_mark_as_done"   : self.on_mark_as_done,
                "gtk_main_quit"     : gtk.main_quit,
                "on_select_tag" : self.on_select_tag
              }
        self.wTree.signal_autoconnect(dic)
        
        #Now we have to open our tasks
        self.backend = Backend()
        self.project = self.backend.get_project()
        self.project.set_sync_func(self.backend.sync_project)
        
    def main(self):
        #Here we will define the main TaskList interface
        self.c_title=1
        #The Active tasks treeview
        self.task_tview = self.wTree.get_widget("task_tview")
        self.cellBool = gtk.CellRendererToggle()
        self.cell     = gtk.CellRendererText()
        col = gtk.TreeViewColumn("Actions")
        col.pack_start(self.cellBool)
        col.pack_start(self.cell)
        col.set_resizable(True)        
        col.set_sort_column_id(1)
        col.set_attributes(self.cell, markup=1)
        col.add_attribute(self.cellBool, 'active', 2)
        self.task_tview.append_column(col)
        self.task_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT, str, bool)
        self.task_tview.set_model(self.task_ts)
        self.task_ts.set_sort_column_id(self.c_title, gtk.SORT_ASCENDING)
        
        #The done/dismissed taks treeview
        self.taskdone_tview = self.wTree.get_widget("taskdone_tview")
        cold = gtk.TreeViewColumn("Done")
        cold.pack_start(self.cellBool)
        cold.pack_start(self.cell)
        cold.set_resizable(True)        
        cold.set_sort_column_id(1)
        cold.set_attributes(self.cell, markup=1)
        cold.add_attribute(self.cellBool, 'active', 2)
        self.taskdone_tview.append_column(cold)
        self.taskdone_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT, str, bool)
        self.taskdone_tview.set_model(self.taskdone_ts)
        self.taskdone_ts.set_sort_column_id(self.c_title, gtk.SORT_ASCENDING)
        
        
        self.refresh_list()
        
        
        gtk.main()
        return 0
     
    #refresh list build/refresh your TreeStore of task
    #to keep it in sync with your self.project   
    def refresh_list(self) :
        #to refresh the list we first empty it then rebuild it
        #is it acceptable to do that ?
        self.task_ts.clear()
        self.taskdone_ts.clear()
        for tid in self.project.active_tasks() :
            t = self.project.get_task(tid)
            title = t.get_title()
            self.task_ts.append(None,[tid,title,False])
        for tid in self.project.unactive_tasks() :
            t = self.project.get_task(tid)
            title = t.get_title()
            self.taskdone_ts.append(None,[tid,title,False])

    
    def open_task(self,task) :
        t = task
        t.set_sync_func(self.backend.sync_task)
        tv = TaskEditor(t,self.refresh_list)
        
    def on_add_task(self,widget) :
        task = self.project.new_task()
        self.open_task(task)
    
    def get_selected_task(self) :
        tid = None
        # Get the selection in the gtk.TreeView
        selection = self.task_tview.get_selection()
        # Get the selection iter
        selection_iter = selection.get_selected()[1]
        if selection_iter :
            tid = self.task_ts.get_value(selection_iter, 0)
        #maybe the selection is in the taskdone_tview ?
        else :
            selection = self.taskdone_tview.get_selection()
            selection_iter = selection.get_selected()[1]
            if selection_iter :
                tid = self.taskdone_ts.get_value(selection_iter, 0)
        return tid
        
    def on_edit_task(self,widget,row=None ,col=None) :
        tid = self.get_selected_task()
        zetask = self.project.get_task(tid)
        self.open_task(zetask)
        
    def on_delete_task(self,widget) :
        tid = self.get_selected_task()
        self.project.delete_task(tid)
        self.refresh_list()
        
    def on_mark_as_done(self,widget) :
        # Get the selection in the gtk.TreeView
        selection = self.task_tview.get_selection()[1]
        # Get the selection iter
        selection_iter = selection.get_selected()
        if (selection_iter):
            tid = self.task_ts.get_value(selection_iter, 0)
            zetask = self.project.get_task(tid)
            zetask.set_status("Done")
            self.refresh_list()
            self.backend.sync_task(tid)
        
    def on_select_tag(self, widget, row=None ,col=None) :
        print "to implement"

#=== EXECUTION =================================================================

if __name__ == "__main__":
    base = Base()
    base.main()
