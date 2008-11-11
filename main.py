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
            
        
        #self.delete_dialog.connect("destroy", self.delete_dialog.hide)

        #Create our dictionay and connect it
        dic = {
                "on_add_task"       : self.on_add_task,
                "on_edit_task"      : self.on_edit_task,
                "on_delete_task"    : self.on_delete_task,
                "on_mark_as_done"   : self.on_mark_as_done,
                "gtk_main_quit"     : gtk.main_quit,
                "on_select_tag" : self.on_select_tag,
                "on_delete_confirm" : self.on_delete_confirm,
                "on_delete_cancel" : lambda x : x.hide,
                "on_project_selected" : self.on_project_selected
              }
        self.wTree.signal_autoconnect(dic)
        
        #Now we have to open our tasks
        #We create a dict which contains every pair of Backend/project
        #TODO : do this from a projects configuration
        backend1 = Backend("mynote.xml")
        backend2 = Backend("bert.xml")
        project1 = backend1.get_project()
        project2 = backend2.get_project()
        #We assign a random number to each project
        #This way, each project has a unique ID for the session
        #Warning : this is not persistant ! The pid is different
        #for each session !
        # (this is a feature to allow easy import of a project
        project1.set_pid('1')
        project2.set_pid('2')
        #We add the sync function for project
        project1.set_sync_func(backend1.sync_project)
        project2.set_sync_func(backend2.sync_project)
        #self.projects is a list of tuples
        #each tuple is a [backend,project] duo
        #So we always have the relevant backend for a project if needed
        self.projects = {}
        self.projects['1'] = [backend1, project1]
        self.projects['2'] = [backend2, project2]
        
    def __add_active_column(self,name,value) :
        col2 = gtk.TreeViewColumn(name)
        col2.pack_start(self.cell)
        col2.set_resizable(True)        
        col2.set_sort_column_id(value)
        col2.set_attributes(self.cell, markup=value)
        self.task_tview.append_column(col2)
        
    def main(self):
        #Here we will define the main TaskList interface
        self.c_title=1
        self.cellBool = gtk.CellRendererToggle()
        self.cell     = gtk.CellRendererText()
        
        #The project list
        self.project_tview = self.wTree.get_widget("project_tview")
        pcol = gtk.TreeViewColumn("Projects")
        pcol.pack_start(self.cell)
        pcol.set_resizable(True)
        pcol.set_sort_column_id(1)
        pcol.set_attributes(self.cell, markup=1)
        self.project_tview.append_column(pcol)
        self.project_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT,str)
        self.project_tview.set_model(self.project_ts)
        #self.project_ts.set_sort_column_id(self.c_title, gtk.SORT_ASCENDING)
        
        #The Active tasks treeview
        self.task_tview = self.wTree.get_widget("task_tview")
        col = gtk.TreeViewColumn("Actions")
        col.pack_start(self.cellBool)
        col.pack_start(self.cell)
        col.set_resizable(True)        
        col.set_sort_column_id(1)
        col.set_attributes(self.cell, markup=1)
        col.add_attribute(self.cellBool, 'active', 3)
        self.task_tview.append_column(col)
        self.__add_active_column("Due date",2)
        self.task_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT, str, str, bool)
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
        
        #put the content in those treeviews
        self.refresh_projects()
        self.refresh_list()
        #This is the list of tasks that are already opened in an editor
        #of course it's empty right now
        self.opened_task = {}
        
        gtk.main()
        return 0
    
    #We double clicked on a project in the project list
    def on_project_selected(self,widget,row,col) :
        self.refresh_list()
    
    #We refresh the project list. Not needed very often
    def refresh_projects(self) :
        self.project_ts.clear()
        for p_key in self.projects :
            p = self.projects[p_key][1]
            title = p.get_name()
            self.project_ts.append(None,[p_key,title])
        
    #refresh list build/refresh your TreeStore of task
    #to keep it in sync with your self.projects   
    def refresh_list(self) :
        #to refresh the list we first empty it then rebuild it
        #is it acceptable to do that ?
        self.task_ts.clear()
        self.taskdone_ts.clear()
        #We display only tasks of the active projects
        for p_key in self.get_selected_project() :
            p = self.projects[p_key][1]  
            #we first build the active_tasks pane
            for tid in p.active_tasks() :
                t = p.get_task(tid)
                title = t.get_title()
                duedate = t.get_due_date()
                self.task_ts.append(None,[tid,title,duedate,False])
            #then the one with tasks already done
            for tid in p.unactive_tasks() :
                t = p.get_task(tid)
                title = t.get_title()
                self.taskdone_ts.append(None,[tid,title,False])

    #If a Task editor is already opened for a given task, we present it
    #Else, we create a new one.
    def open_task(self,task) :
        t = task
        uid = t.get_id()
        if self.opened_task.has_key(uid) :
            self.opened_task[uid].present()
        else :
            #We need the pid number to get the backend
            tid,pid = uid.split('@')
            backend = self.projects[pid][0]
            #We give to the task the callback to synchronize the list
            t.set_sync_func(backend.sync_task)
            tv = TaskEditor(t,self.refresh_list,self.on_delete_task,self.close_task)
            #registering as opened
            self.opened_task[uid] = tv
    
    #When an editor is closed, it should deregister itself
    def close_task(self,tid) :
        if self.opened_task.has_key(tid) :
            del self.opened_task[tid]
            
    def on_add_task(self,widget) :
        #We have to select the project to which we should add a task
        #TODO : what if multiple projects are selected ?
        #Currently, we take the first one
        p = self.get_selected_project()[0]
        task = self.projects[p][1].new_task()
        self.open_task(task)
    
    #Get_selected_task returns two value :
    # pid (example : '1')
    # uid (example : '21@1')
    #Yes, indeed, it means that the pid appears twice.
    def get_selected_task(self) :
        uid = None
        # Get the selection in the gtk.TreeView
        selection = self.task_tview.get_selection()
        # Get the selection iter
        model, selection_iter = selection.get_selected()
        if selection_iter :
            uid = self.task_ts.get_value(selection_iter, 0)
        #maybe the selection is in the taskdone_tview ?
        else :
            selection = self.taskdone_tview.get_selection()
            model, selection_iter = selection.get_selected()
            if selection_iter :
                uid = self.taskdone_ts.get_value(selection_iter, 0)
        tid,pid = uid.split('@')
        return pid, uid
        
    def get_selected_project(self) :
        #We have to select the project
        #if pid is none, we should handle a default project
        #and display all tasks
        p_selected = self.project_tview.get_selection()
        pmodel, p_iter = p_selected.get_selected()
        if p_iter :
            pid = [self.project_ts.get_value(p_iter, 0)]
        #If no selection, we display all
        else :
            pid = self.projects.keys() 
        return pid
        
    def on_edit_task(self,widget,row=None ,col=None) :
        pid,tid = self.get_selected_task()
        if tid :
            zetask = self.projects[pid][1].get_task(tid)
            self.open_task(zetask)
     
    #if we pass a tid as a parameter, we delete directly
    #otherwise, we will look which tid is selected   
    def on_delete_confirm(self,widget) :
        uid = self.tid_todelete
        pid = uid.split('@')[1]
        pr = self.projects[pid][1]
        pr.delete_task(self.tid_todelete)
        self.tid_todelete = None
        self.refresh_list()
        
    def on_delete_task(self,widget,tid=None) :
        #If we don't have a parameter, then take the selection in the treeview
        if not tid :
            #tid_to_delete is a [project,task] tuple
            pid, self.tid_todelete = self.get_selected_task()
        else :
            self.tid_todelete = tid
        #We must at least have something to delete !
        if self.tid_todelete :
            delete_dialog = self.wTree.get_widget("confirm_delete")
            delete_dialog.run()
            delete_dialog.hide()
            #has the task been deleted ?
            return not self.tid_todelete
        else :
            return False
        
    def on_mark_as_done(self,widget) :
        pid,tid = self.get_selected_task()
        if tid :
            backend = self.projects[pid][0]
            zetask = self.projects[pid][1].get_task(tid)
            zetask.set_status("Done")
            self.refresh_list()
            backend.sync_task(tid)
        
    def on_select_tag(self, widget, row=None ,col=None) :
        print "to implement"

#=== EXECUTION =================================================================

if __name__ == "__main__":
    base = Base()
    base.main()
