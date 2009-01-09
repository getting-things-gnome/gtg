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
from gtg_core.task import Task, Project
from gnome_frontend.taskeditor import TaskEditor
from gnome_frontend.project_ui import ProjectEditDialog
from gnome_frontend import GnomeConfig

#=== OBJECTS ===================================================================

#=== MAIN CLASS ================================================================

class TaskBrowser:

    def __init__(self, datastore):
        
        #Set the Glade file
        self.gladefile = GnomeConfig.GLADE_FILE  
        self.wTree = gtk.glade.XML(self.gladefile) 
        
        #Get the Main Window, and connect the "destroy" event
        self.window = self.wTree.get_widget("MainWindow")
        if (self.window):
            self.window.connect("destroy", gtk.main_quit)
        self.window.set_icon_from_file("data/gtg.svg")

        self.projectpopup = self.wTree.get_widget("ProjectContextMenu")
        self.tagpopup = self.wTree.get_widget("TagContextMenu")
        
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
                "on_project_treeview_button_press_event" : self.on_project_treeview_button_press_event,
                "on_tag_treeview_button_press_event" : self.on_tag_treeview_button_press_event,
                "on_edit_item_activate"     : self.on_edit_item_activate,
                "on_delete_item_activate" : self.on_delete_item_activate,
                "on_colorchooser_activate" : self.on_colorchooser_activate
                #This signal cancel on_edit_task
                #"on_task_tview_cursor_changed" : self.task_cursor_changed

              }
        self.wTree.signal_autoconnect(dic)
        self.selected_rows = None
        
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
        #self.project_ts.set_sort_column_id(self.c_title, gtk.SORT_ASCENDING)
        
        #The tags treeview
        self.tag_tview = self.wTree.get_widget("tag_tview")
        self.__add_tag_column("Tags",1)
        self.tag_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT,str)
        self.tag_tview.set_model(self.tag_ts)
   
        #The Active tasks treeview
        self.task_tview = self.wTree.get_widget("task_tview")
        self.__add_active_column("Actions",1)
        self.__add_active_column("Due date",2)
        self.__add_active_column("Left",3)
        self.task_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT, str, str, str)
        self.task_tview.set_model(self.task_ts)
        #self.task_ts.set_sort_column_id(self.c_title, gtk.SORT_ASCENDING)
     
        #The done/dismissed taks treeview
        self.taskdone_tview = self.wTree.get_widget("taskdone_tview")
        self.__add_closed_column("Closed",2)
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
        
        selection = self.task_tview.get_selection()
        selection.connect("changed",self.task_cursor_changed)
        
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
        self.refresh_projects()
        
    def on_colorchooser_activate(self,widget) :
        #TODO : This should be refactorized in its own class
        wTree = gtk.glade.XML(self.gladefile, "ColorChooser") 
        #Create our dictionay and connect it
        dic = {
                "on_color_response" : self.on_color_response
              }
        wTree.signal_autoconnect(dic)
        window = wTree.get_widget("ColorChooser")
        window.show()
        print "color activated"
    
    def on_color_response(self,a,b) :
        print "color response %s - %s" %(a,b)
        a.destroy()
    
    
    #We double clicked on a project in the project list
    def on_project_selected(self,widget,row=None ,col=None) :
        #When you clic on a project, you want to unselect the tasks
        self.task_tview.get_selection().unselect_all()
        self.taskdone_tview.get_selection().unselect_all()
        self.refresh_list()
    
    #We refresh the project list. Not needed very often
    def refresh_projects(self) :
        p_model,p_path = self.project_tview.get_selection().get_selected_rows()
        self.project_ts.clear()
        self.project_ts.append(None,[-1, "<span weight=\"bold\">All projects</span>"])
        projects = self.ds.get_all_projects()
        for p_key in projects:
            p = projects[p_key][1]
            title = p.get_name()
            at_num = len(p.active_tasks())
            p_str  = "%s (%d)" % (title, at_num)
            self.project_ts.append(None,[p_key, p_str])
        #We reselect the selected project
        if p_path :
            for i in p_path :
                self.project_tview.get_selection().select_path(i)

    def refresh_tb(self):
        self.refresh_list()
        self.refresh_tags()
        self.refresh_projects()

    #We refresh the tag list. Not needed very often
    def refresh_tags(self) :
        t_model,t_path = self.tag_tview.get_selection().get_selected_rows()
        self.tag_ts.clear()
        self.tag_ts.append(None,[-1,"<span weight=\"bold\">All tags</span>"])
        self.tag_ts.append(None,[-2,"<span weight=\"bold\">Task without tags</span>"])
#        self.ds.reload_tags()
        tags = self.ds.get_used_tags()
        #tags.sort()
        for tag in tags:
            self.tag_ts.append(None,[tag,tag.get_name()])
        #We reselect the selected tag
        if t_path :
            for i in t_path :
                self.tag_tview.get_selection().select_path(i)

    #refresh list build/refresh your TreeStore of task
    #to keep it in sync with your self.projects   
    def refresh_list(self,a=None) :
        #selected tasks :
        pid, selected_uid = self.get_selected_task()
        t_model,t_path = self.task_tview.get_selection().get_selected_rows()
        d_model,d_path = self.taskdone_tview.get_selection().get_selected_rows()
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
                if not t.has_parents(tag=tag_list) and (tag_list==[] or t.has_tags(tag_list)):
                    self.add_task_tree_to_list(p, self.task_ts, t, None,selected_uid,tags=tag_list)
                #If tag_list is none, we display tasks without any tags
                elif not t.has_parents(tag=tag_list) and tag_list==[None] and t.get_tags_name()==[]:
                    self.add_task_tree_to_list(p, self.task_ts, t, None,selected_uid,tags=tag_list)
            #then the one with tasks already done
            for tid in p.unactive_tasks() :
                t = p.get_task(tid)
                title = t.get_title()
                donedate = t.get_done_date()
                if tag_list==[] or t.has_tags(tag_list):
                    self.taskdone_ts.append(None,[tid,False,title,donedate])
                #If tag_list is none, we display tasks without any tags
                elif tag_list==[None] and t.get_tags_name()==[]:
                    self.taskdone_ts.append(None,[tid,False,title,donedate])
        self.task_tview.expand_all()
        #We reselect the selected tasks
        selection = self.task_tview.get_selection()
        if t_path :
            for i in t_path :
                selection.select_path(i)
        if d_path :
            for i in d_path :
                selection.select_path(i)
                
    #This function is called when the selection change in the active task view
    #It will displays the selected task differently
    def task_cursor_changed(self,selection=None) :
        tid_row = 0
        title_row = 1
        #We reset the previously selected task
        if self.selected_rows and self.task_ts.iter_is_valid(self.selected_rows):
            tid = self.task_ts.get_value(self.selected_rows, tid_row)
            if tid :
                uid,pid = tid.split('@')
                task = self.ds.get_all_projects()[pid][1].get_task(tid)
                title = self.__build_task_title(task,extended=False)
                self.task_ts.set_value(self.selected_rows,title_row,title)
        #We change the selection title
        if selection :
            ts,itera = selection.get_selected()
            if itera and self.task_ts.iter_is_valid(itera) :
                tid = self.task_ts.get_value(itera, tid_row)
                if tid :
                    uid,pid = tid.split('@')
                    task = self.ds.get_all_projects()[pid][1].get_task(tid)
                    self.selected_rows = itera
                    title = self.__build_task_title(task,extended=True)
                    self.task_ts.set_value(self.selected_rows,title_row,title)
    
    def __build_task_title(self,task,extended=False):
        if extended :
            excerpt = task.get_excerpt(lines=2)
            if excerpt.strip() != "" :
                title   = "<b><big>%s</big></b>\n<small><small>%s</small></small>" %(task.get_title(),excerpt)
            else : 
                title   = "<b><big>%s</big></b>" %task.get_title()
        else :
            title = task.get_title()
        return title

    def add_task_tree_to_list(self, project, tree_store, task, parent,selected_uid=None,tags=None):
        if task.has_tags(tags) :
            tid     = task.get_id()
            if selected_uid and selected_uid == tid:
                title = self.__build_task_title(task,extended=True)
            else :
                title = self.__build_task_title(task,extended=False)
            duedate = task.get_due_date()
            left    = task.get_days_left()
            my_row  = self.task_ts.append(parent, [tid,title,duedate,left])
            for c in task.get_subtasks():
                if c.get_id() in project.active_tasks():
                    self.add_task_tree_to_list(project, tree_store, c, my_row,selected_uid,tags=tags)

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
            tv = TaskEditor(t,self.refresh_tb,self.on_delete_task,
                            self.close_task,self.open_task_byid,self.get_tasktitle)
            #registering as opened
            self.opened_task[uid] = tv
            
    def get_tasktitle(self,tid) :
        task = self.__get_task_byid(tid)
        return task.get_title()
            
    def open_task_byid(self,tid) :
        task = self.__get_task_byid(tid)
        self.open_task(task)
    
    #When an editor is closed, it should deregister itself
    def close_task(self,tid) :
        if self.opened_task.has_key(tid) :
            del self.opened_task[tid]

    def on_project_treeview_button_press_event(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor( path, col, 0)
                self.projectpopup.popup( None, None, None, event.button, time)
            return 1        
    
    def on_tag_treeview_button_press_event(self,treeview,event) :
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor( path, col, 0)
                self.tagpopup.popup( None, None, None, event.button, time)
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
        if uid :
            tid,pid = uid.split('@')
        else :
            pid = None
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
            selected = [self.tag_ts.get_value(t_iter, 0)]
            tag = []
            if -1 in selected: selected.remove(-1)
            #-2 means we want to display only tasks without any tag
            if -2 in selected:
                selected.remove(-2)
                tag.append(None)
            for t in selected :
                if t :
                    tag.append(t.get_name())
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
        self.refresh_tags()
        
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
        #When you clic on a tag, you want to unselect the tasks
        self.task_tview.get_selection().unselect_all()
        self.taskdone_tview.get_selection().unselect_all()
        self.refresh_list()

    ##### Useful tools##################
    
    #Getting a task by its ID
    def __get_task_byid(self,tid) :
        tiid,pid = tid.split('@')
        proj = self.ds.get_project_with_pid(pid)[1]
        task = proj.get_task(tid)
        return task
    
    #    Functions that help to build the GUI. Nothing really interesting.
    def __add_active_column(self,name,value) :
        col = self.__add_column(name,value)
        self.task_tview.append_column(col)
        
    def __add_project_column(self,name,value) :
        col = self.__add_column(name,value)
        col.set_clickable(False)
        self.project_tview.append_column(col)
        
    def __add_closed_column(self,name,value) :
        col = self.__add_column(name,value)
        self.taskdone_tview.append_column(col)

    def __add_tag_column(self,name,value) :
        col = self.__add_column(name,value)
        col.set_clickable(False)
        self.tag_tview.append_column(col)

    def __add_column(self,name,value) :
        col = gtk.TreeViewColumn(name)
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

