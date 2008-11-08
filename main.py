#!/usr/bin/env python
#
#===============================================================================
#
# GTD-gnome: a gtd organizer for GNOME
#
# @author : B. Rousseau, L. Dricot
# @date   : November 2008
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
        
        self.backend = Backend()
        self.project = self.backend.get_project()
        
    def main(self):
        self.c_title=1
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
        
        
        self.refresh_list()
        
        
        gtk.main()
        return 0
     
    #refresh list build/refresh your TreeStore of task
    #to keep it in sync with your self.project   
    def refresh_list(self) :
        #to refresh the list we first empty it then rebuild it
        #is it acceptable to do that ?
        self.task_ts.clear()
        for tid in self.project.list_tasks() :
            t = self.project.get_task(tid)
            title = t.get_title()
            self.task_ts.append(None,[tid,title,False])
    
    def open_task(self,task) :
        t = task
        t.set_sync_func(self.backend.sync_task)
        tv = TaskEditor(t,self.refresh_list)
        
    def on_add_task(self,widget) :
        task = self.project.new_task()
        self.open_task(task)
        
        
    def on_edit_task(self,widget,row=None ,col=None) :
        # Get the selection in the gtk.TreeView
        selection = self.task_tview.get_selection()
        # Get the selection iter
        model, selection_iter = selection.get_selected()
        if (selection_iter):
            tid = self.task_ts.get_value(selection_iter, 0)
            zetask = self.project.get_task(tid)
            self.open_task(zetask)
        
    def on_delete_task(self,widget) :
        # Get the selection in the gtk.TreeView
        selection = self.task_tview.get_selection()
        # Get the selection iter
        model, selection_iter = selection.get_selected()
        if (selection_iter):
            tid = self.task_ts.get_value(selection_iter, 0)
            self.project.delete_task(tid)
            self.refresh_list()
        
    def on_mark_as_done(self,widget) :
        print "to implement"
        
    def on_select_tag(self, widget, row=None ,col=None) :
        print "to implement"

#=== EXECUTION =================================================================

if __name__ == "__main__":
    base = Base()
    base.main()
