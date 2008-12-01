#=== IMPORT ====================================================================
#system imports
import os
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
from project_ui import ProjectEditDialog

#=== OBJECTS ===================================================================

#=== MAIN CLASS ================================================================

class TaskBrowser:

    def __init__(self, datastore):
        
        #Set the Glade file
        self.gladefile = "gtd-gnome.glade"  
        self.wTree = gtk.glade.XML(self.gladefile) 
        
        #Get the Main Window, and connect the "destroy" event
        self.window = self.wTree.get_widget("MainWindow")
        if (self.window):
            self.window.connect("destroy", gtk.main_quit)

        self.popup = self.wTree.get_widget("ProjectContextMenu")
        
        #self.delete_dialog.connect("destroy", self.delete_dialog.hide)

        #Create our dictionay and connect it
        dic = {
                "on_add_project"      : self.on_add_project,
                "on_add_task"         : self.on_add_task,
                "on_edit_task"        : self.on_edit_task,
                "on_delete_task"      : self.on_delete_task,
                "on_mark_as_done"     : self.on_mark_as_done,
                "gtk_main_quit"       : self.close,
                "on_select_tag"       : self.on_select_tag,
                "on_delete_confirm"   : self.on_delete_confirm,
                "on_delete_cancel"    : lambda x : x.hide,
                "on_project_selected" : self.on_project_selected,
                "on_treeview_button_press_event" : self.on_treeview_button_press_event,
                "on_edit_item_activate"     : self.on_edit_item_activate,
                "on_delete_item_activate" : self.on_delete_item_activate

              }
        self.wTree.signal_autoconnect(dic)
        
        self.ds = datastore
        
    def main(self):
        #Here we will define the main TaskList interface
        self.c_title=1
        self.cellBool = gtk.CellRendererToggle()
        self.cell     = gtk.CellRendererText()
        
        #The project list
        self.project_tview = self.wTree.get_widget("project_tview")
        self.__add_project_column("Projects",1)
        self.project_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT,str)
        self.project_tview.set_model(self.project_ts)
        
        #The tags treeview
        self.tag_tview = self.wTree.get_widget("tag_tview")
        self.__add_tag_column("Tags",1)
        self.tag_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT,str)
        self.tag_tview.set_model(self.tag_ts)

   
        #The Active tasks treeview
        self.task_tview = self.wTree.get_widget("task_tview")
        self.__add_active_column("Actions",2,checkbox=1)
        self.__add_active_column("Due date",3)
        self.__add_active_column("Left",4)
        self.task_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT, bool, str, str, str)
        self.task_tview.set_model(self.task_ts)
        self.task_ts.set_sort_column_id(self.c_title, gtk.SORT_ASCENDING)
     
        #The done/dismissed taks treeview
        self.taskdone_tview = self.wTree.get_widget("taskdone_tview")
        self.__add_closed_column("Closed",2,checkbox=1)
        self.__add_closed_column("Done date",3)
        self.taskdone_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT, bool,str,str)
        self.taskdone_tview.set_model(self.taskdone_ts)
        self.taskdone_ts.set_sort_column_id(self.c_title, gtk.SORT_ASCENDING)
        
        #put the content in those treeviews
        self.refresh_projects()
        self.refresh_tags()
        self.refresh_list()
        #This is the list of tasks that are already opened in an editor
        #of course it's empty right now
        self.opened_task = {}
        
        gtk.main()
        return 0

    def on_add_project(self, widget):
        pd = ProjectEditDialog(self.ds)
        pd.set_on_close_cb(self.refresh_projects)
        pd.main()

    def on_edit_item_activate(self, widget):
        ppid = self.get_selected_project()[0]
        p  = self.ds.get_project_with_pid(ppid)[1]
        pd = ProjectEditDialog(self.ds, p)
        pd.set_on_close_cb(self.refresh_projects)
        pd.main()

    def on_delete_item_activate(self, widget):
        ppid = self.get_selected_project()[0]
        b  = self.ds.get_project_with_pid(ppid)[0]
        p  = self.ds.get_project_with_pid(ppid)[1]
        self.ds.remove_project(p)
        self.ds.unregister_backend(b)
        fn = b.get_filename()
        os.remove(fn)
        self.refresh_projects()
    
    #We double clicked on a project in the project list
    def on_project_selected(self,widget,row=None ,col=None) :
        self.refresh_list()
    
    #We refresh the project list. Not needed very often
    def refresh_projects(self) :
        self.project_ts.clear()
        self.project_ts.append(None,[-1,"<span weight=\"bold\">All projects</span>"])
        projects = self.ds.get_all_projects()
        for p_key in projects:
            p = projects[p_key][1]
            title = p.get_name()
            self.project_ts.append(None,[p_key,title])

    #We refresh the tag list. Not needed very often
    def refresh_tags(self) :
        self.tag_ts.clear()
        self.tag_ts.append(None,[-1,"<span weight=\"bold\">All tags</span>"])
        tags = self.ds.get_all_tags()
        tags.sort()
        for tag in tags:
            self.tag_ts.append(None,[tag,tag])

    #refresh list build/refresh your TreeStore of task
    #to keep it in sync with your self.projects   
    def refresh_list(self) :
        #to refresh the list we first empty it then rebuild it
        #is it acceptable to do that ?
        self.task_ts.clear()
        self.taskdone_ts.clear()
        tag_list = self.get_selected_tags()
        #We display only tasks of the active projects
        #TODO: implement queries in DataStore, and use it here
        for p_key in self.get_selected_project() :
            p = self.ds.get_all_projects()[p_key][1]  
            #we first build the active_tasks pane
            for tid in p.active_tasks() :
                t = p.get_task(tid)
                title = t.get_title()
                duedate = t.get_due_date()
                left = t.get_days_left()
                if tag_list==[] or t.has_tags(tag_list):
                    self.task_ts.append(None,[tid,False,title,duedate,left])
            #then the one with tasks already done
            for tid in p.unactive_tasks() :
                t = p.get_task(tid)
                title = t.get_title()
                donedate = t.get_done_date()
                if tag_list==[] or t.has_tags(tag_list):
                    self.taskdone_ts.append(None,[tid,False,title,donedate])

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
            backend = self.ds.get_all_projects()[pid][0]
            #We give to the task the callback to synchronize the list
            t.set_sync_func(backend.sync_task)
            tv = TaskEditor(t,self.refresh_list,self.on_delete_task,self.close_task)
            #registering as opened
            self.opened_task[uid] = tv
    
    #When an editor is closed, it should deregister itself
    def close_task(self,tid) :
        if self.opened_task.has_key(tid) :
            del self.opened_task[tid]

    def on_treeview_button_press_event(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor( path, col, 0)
                self.popup.popup( None, None, None, event.button, time)
            return 1        
            
    def on_add_task(self,widget) :
        #We have to select the project to which we should add a task
        #TODO : what if multiple projects are selected ?
        #Currently, we take the first one
        p = self.get_selected_project()[0]
        task = self.ds.get_all_projects()[p][1].new_task()
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
            if -1 in pid: pid = self.ds.get_all_projects().keys()
        #If no selection, we display all
        else :
            pid = self.ds.get_all_projects().keys() 
        return pid

    def get_selected_tags(self) :
        t_selected = self.tag_tview.get_selection()
        tmodel, t_iter = t_selected.get_selected()
        if t_iter :
            tag = [self.tag_ts.get_value(t_iter, 0)]
            if -1 in tag: tag.remove(-1)
        #If no selection, we display all
        else :
            tag = []
        return tag
        
    def on_edit_task(self,widget,row=None ,col=None) :
        pid,tid = self.get_selected_task()
        if tid :
            zetask = self.ds.get_all_projects()[pid][1].get_task(tid)
            self.open_task(zetask)
     
    #if we pass a tid as a parameter, we delete directly
    #otherwise, we will look which tid is selected   
    def on_delete_confirm(self,widget) :
        uid = self.tid_todelete
        pid = uid.split('@')[1]
        pr = self.ds.get_all_projects()[pid][1]
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
            backend = self.ds.get_all_projects()[pid][0]
            zetask = self.ds.get_all_projects()[pid][1].get_task(tid)
            zetask.set_status("Done")
            self.refresh_list()
            backend.sync_task(tid)
        
    def on_select_tag(self, widget, row=None ,col=None) :
        self.refresh_list()

    ##### Useful tools##################
    #    Functions that help to build the GUI. Nothing really interesting.
    def __add_active_column(self,name,value,checkbox=False) :
        col = self.__add_column(name,value,checkbox)
        self.task_tview.append_column(col)
        
    def __add_project_column(self,name,value,checkbox=False) :
        col = self.__add_column(name,value,checkbox)
        col.set_clickable(False)
        self.project_tview.append_column(col)
        
    def __add_closed_column(self,name,value,checkbox=False) :
        col = self.__add_column(name,value,checkbox)
        self.taskdone_tview.append_column(col)

    def __add_tag_column(self,name,value,checkbox=False) :
        col = self.__add_column(name,value,checkbox)
        col.set_clickable(False)
        self.tag_tview.append_column(col)

    def __add_column(self,name,value,checkbox=False) :
        col = gtk.TreeViewColumn(name)
        if checkbox :
            col.pack_start(self.cellBool)
            col.add_attribute(self.cellBool, 'active', checkbox)
        col.pack_start(self.cell)
        col.set_resizable(True)        
        col.set_sort_column_id(value)
        col.set_attributes(self.cell, markup=value)
        return col
        
    ######Closing the window
    def close(self,widget=None) :
        #Saving all projects
        for p in self.projects :
            self.projects[p][1].sync()
        gtk.main_quit()

