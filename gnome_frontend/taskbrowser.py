#=== IMPORT ====================================================================
#system imports
import pygtk
pygtk.require('2.0')
import gobject
import gtk.glade

#our own imports
from gnome_frontend.taskeditor import TaskEditor
#from gnome_frontend.project_ui import ProjectEditDialog
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
        self.window.set_icon_from_file("data/16x16/app/gtg.png")

#        self.projectpopup = self.wTree.get_widget("ProjectContextMenu")
        self.tagpopup = self.wTree.get_widget("TagContextMenu")
        self.donebutton = self.wTree.get_widget("mark_as_done_b")
        self.dismissbutton = self.wTree.get_widget("dismiss")
        
        #self.delete_dialog.connect("destroy", self.delete_dialog.hide)

        #Create our dictionay and connect it
        dic = {
#                "on_add_project"      : self.on_add_project,
                "on_add_task"         : self.on_add_task,
                "on_edit_active_task"        : self.on_edit_active_task,
                "on_edit_done_task" :   self.on_edit_done_task,
                "on_delete_task"      : self.on_delete_task,
                "on_mark_as_done"     : self.on_mark_as_done,
                "on_dismiss_task"   : self.on_dismiss_task,
                "gtk_main_quit"       : self.close,
                "on_select_tag"       : self.on_select_tag,
                "on_delete_confirm"   : self.on_delete_confirm,
                "on_delete_cancel"    : lambda x : x.hide,
#                "on_project_selected" : self.on_project_selected,
#                "on_project_treeview_button_press_event" : self.on_project_treeview_button_press_event,
                "on_tag_treeview_button_press_event" : self.on_tag_treeview_button_press_event,
#                "on_edit_item_activate"     : self.on_edit_item_activate,
#                "on_delete_item_activate" : self.on_delete_item_activate,
                "on_colorchooser_activate" : self.on_colorchooser_activate,
                "on_workview_toggled" : self.on_workview_toggled

              }
        self.wTree.signal_autoconnect(dic)
        self.selected_rows = None
        
        self.ds = datastore
        self.workview = False
        self.req = self.ds.get_requester()
        
    def main(self):
        #Here we will define the main TaskList interface
        self.c_title=1
        
        #The project list
#        self.project_tview = self.wTree.get_widget("project_tview")
#        self.__add_project_column("Projects",2)
#        self.project_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT,str,str)
#        self.project_tview.set_model(self.project_ts)
#        #self.project_ts.set_sort_column_id(self.c_title, gtk.SORT_ASCENDING)
        
        #The tags treeview
        self.tag_tview = self.wTree.get_widget("tag_tview")
        self.__add_tag_column("Tags",3)
        self.tag_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT,str,gtk.gdk.Pixbuf,str)
        self.tag_tview.set_model(self.tag_ts)
   
        #The Active tasks treeview
        self.task_tview = self.wTree.get_widget("task_tview")
        self.task_tview.set_rules_hint(False)
        self.__add_active_column("Actions",2)
        self.__add_active_column("Due date",3)
        self.__add_active_column("Left",4)
        self.task_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT, str, str, str,str)
        self.task_tview.set_model(self.task_ts)
        #self.task_ts.set_sort_column_id(self.c_title, gtk.SORT_ASCENDING)
     
        #The done/dismissed taks treeview
        self.taskdone_tview = self.wTree.get_widget("taskdone_tview")
        self.taskdone_tview.set_rules_hint(False)
        self.__add_closed_column("Closed",2)
        self.__add_closed_column("Done date",3)
        self.taskdone_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT, str,str,str)
        self.taskdone_tview.set_model(self.taskdone_ts)
        self.taskdone_ts.set_sort_column_id(self.c_title, gtk.SORT_ASCENDING)
        
        #put the content in those treeviews
#        self.refresh_projects()
        self.refresh_tags()
        self.refresh_list()
        #This is the list of tasks that are already opened in an editor
        #of course it's empty right now
        self.opened_task = {}
        
        selection = self.task_tview.get_selection()
        selection.connect("changed",self.task_cursor_changed)
        closed_selection = self.taskdone_tview.get_selection()
        closed_selection.connect("changed",self.taskdone_cursor_changed)
        
        gtk.main()
        return 0

#    def on_add_project(self, widget):
#        pd = ProjectEditDialog(self.ds)
#        pd.set_on_close_cb(self.refresh_projects)
#        pd.main()

#    def on_edit_item_activate(self, widget):
#        ppid = self.req.get_projects_list()[0]
#        p  = self.req.get_project_from_pid(ppid)
#        pd = ProjectEditDialog(self.ds, p)
#        pd.set_on_close_cb(self.refresh_projects)
#        pd.main()

#    def on_delete_item_activate(self, widget):
#        ppid = self.req.get_projects_list()[0]
#        self.req.remove_project(ppid)
#        self.refresh_projects()
        
    def on_colorchooser_activate(self,widget) :
        #TODO : This should be refactorized in its own class
        #Well, in fact we should have a TagPropertiesEditor (like for project)
        #Also, color change should be immediate. There's no reason for a Ok/Cancel
        wTree = gtk.glade.XML(self.gladefile, "ColorChooser") 
        #Create our dictionay and connect it
        dic = {
                "on_color_response" : self.on_color_response
              }
        wTree.signal_autoconnect(dic)
        window = wTree.get_widget("ColorChooser")
        window.show()
    
    def on_color_response(self,widget,response) :
        #the OK button return -5. Don't ask me why.
        if response == -5 :
            colorsel = widget.colorsel
            gtkcolor = colorsel.get_current_color()
            strcolor = gtk.color_selection_palette_to_string([gtkcolor])
            tags,notag_only = self.get_selected_tags()
            for t in tags :
                t.set_attribute("color",strcolor)
        self.refresh_tb()
        widget.destroy()
    
    def on_workview_toggled(self,widget) :
        self.workview = not self.workview
        self.refresh_tb()
    
    
#    #We double clicked on a project in the project list
#    def on_project_selected(self,widget,row=None ,col=None) :
#        #When you clic on a project, you want to unselect the tasks
#        self.task_tview.get_selection().unselect_all()
#        self.taskdone_tview.get_selection().unselect_all()
#        self.refresh_list()
    
    #We refresh the project list. Not needed very often
#    def refresh_projects(self) :
#        color = None
#        p_model,p_path = self.project_tview.get_selection().get_selected_rows()
#        self.project_ts.clear()
#        self.project_ts.append(None,[-1, color, "<span weight=\"bold\">All projects</span>"])
#        projects = self.req.get_projects()
#        for p in projects:
#            p_str  = "%s (%d)" % (p["name"], p["nbr"])
#            self.project_ts.append(None,[p["pid"], color, p_str])
#        #We reselect the selected project
#        if p_path :
#            for i in p_path :
#                self.project_tview.get_selection().select_path(i)

    def refresh_tb(self):
        self.refresh_list()
        self.refresh_tags()
        #self.refresh_projects()
        #Refreshing the opened editors
        for uid in self.opened_task :
            self.opened_task[uid].refresh_editor()

    #We refresh the tag list. Not needed very often
    def refresh_tags(self) :
        t_model,t_path = self.tag_tview.get_selection().get_selected_rows()
        self.tag_ts.clear()
        icon_alltask = gtk.gdk.pixbuf_new_from_file("data/16x16/icons/tags_alltasks.png")
        icon_notag   = gtk.gdk.pixbuf_new_from_file("data/16x16/icons/tags_notag.png")
        self.tag_ts.append(None,[-1,None,icon_alltask,"<span weight=\"bold\">All tags</span>"])
        self.tag_ts.append(None,[-2,None,icon_notag,"<span weight=\"bold\">Task without tags</span>"])
        tags = self.req.get_used_tags()
        #tags.sort()
        for tag in tags:
            color = tag.get_attribute("color")
            self.tag_ts.append(None,[tag,color,None,tag.get_name()])
        #We reselect the selected tag
        if t_path :
            for i in t_path :
                self.tag_tview.get_selection().select_path(i)

    #refresh list build/refresh your TreeStore of task
    #to keep it in sync with your self.projects   
    def refresh_list(self,a=None) :
        #selected tasks :
        selected_uid = self.get_selected_task(self.task_tview)
        #selected_closed_uid = self.get_selected_task(self.taskdone_tview)
        t_model,t_path = self.task_tview.get_selection().get_selected_rows()
        d_model,d_path = self.taskdone_tview.get_selection().get_selected_rows()
        #to refresh the list we first empty it then rebuild it
        #is it acceptable to do that ?
        self.task_ts.clear()
        self.taskdone_ts.clear()
        tag_list,notag_only = self.get_selected_tags()
        #We display only tasks of the active projects
        p_list = self.req.get_projects_list()
        
        #We build the active tasks pane
        if self.workview :
            tasks = self.req.get_active_tasks_list(projects=p_list,tags=tag_list,\
                                            notag_only=notag_only,workable=True)
            for tid in tasks :
                self.add_task_tree_to_list(self.task_ts,tid,None,selected_uid,\
                                                        treeview=False)
                            
        else :
            #building the classical treeview
            active_root_tasks = self.req.get_active_tasks_list(projects=p_list,\
                                tags=tag_list, notag_only=notag_only,is_root=True)
            active_tasks = self.req.get_active_tasks_list(projects=p_list,\
                                tags=tag_list, notag_only=notag_only,is_root=False)
            for tid in active_root_tasks :
                self.add_task_tree_to_list(self.task_ts, tid, None,selected_uid,\
                                                        active_tasks=active_tasks)
            
        
        #We build the closed tasks pane
        closed_tasks = self.req.get_closed_tasks_list(projects=p_list,tags=tag_list,\
                                                    notag_only=notag_only)
        for tid in closed_tasks :
            t = self.req.get_task(tid)
            title = t.get_title()
            donedate = t.get_done_date()
            self.taskdone_ts.append(None,[tid,t.get_color(),title,donedate])

        self.task_tview.expand_all()
        #We reselect the selected tasks
        selection = self.task_tview.get_selection()
        closed_selection = self.taskdone_tview.get_selection()
        if t_path :
            for i in t_path :
                selection.select_path(i)
        if d_path :
            for i in d_path :
                closed_selection.select_path(i)
    
    #This function is called when the selection change in the closed task view
    #It will displays the selected task differently           
    def taskdone_cursor_changed(self,selection=None) :
        #We unselect all in the active task view
        #Only if something is selected in the closed task list
        #And we change the status of the Done/dismiss button
        if selection.count_selected_rows() > 0 :
            tid = self.get_selected_task(self.taskdone_tview)
            task = self.req.get_task(tid)
            self.task_tview.get_selection().unselect_all()
            if task.get_status() == "Dismiss" :
                self.dismissbutton.set_label(GnomeConfig.MARK_UNDISMISS)
                self.donebutton.set_label(GnomeConfig.MARK_DONE)
            else :
                self.donebutton.set_label(GnomeConfig.MARK_UNDONE)
                self.dismissbutton.set_label(GnomeConfig.MARK_DISMISS)
                
    #This function is called when the selection change in the active task view
    #It will displays the selected task differently
    def task_cursor_changed(self,selection=None) :
        tid_row = 0
        title_row = 2
        #We unselect all in the closed task view
        #Only if something is selected in the active task list
        if selection.count_selected_rows() > 0 :
            self.taskdone_tview.get_selection().unselect_all()
            self.donebutton.set_label(GnomeConfig.MARK_DONE)
            self.dismissbutton.set_label(GnomeConfig.MARK_DISMISS)
        #We reset the previously selected task
        if self.selected_rows and self.task_ts.iter_is_valid(self.selected_rows):
            tid = self.task_ts.get_value(self.selected_rows, tid_row)
            task = self.req.get_task(tid)
            title = self.__build_task_title(task,extended=False)
            self.task_ts.set_value(self.selected_rows,title_row,title)
        #We change the selection title
        if selection :
            ts,itera = selection.get_selected()
            if itera and self.task_ts.iter_is_valid(itera) :
                tid = self.task_ts.get_value(itera, tid_row)
                task = self.req.get_task(tid)
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

    #Add tasks to a treeview. If treeview is False, it becomes a flat list
    def add_task_tree_to_list(self, tree_store, tid, parent,selected_uid=None,\
                                        active_tasks=[],treeview=True):
        task = self.req.get_task(tid)
        if selected_uid and selected_uid == tid :
            title = self.__build_task_title(task,extended=True)
        else :
            title = self.__build_task_title(task,extended=False)
        duedate = task.get_due_date()
        left    = task.get_days_left()
        color = task.get_color()
        my_row  = self.task_ts.append(parent, [tid,color,title,duedate,left])
        #If treeview, we add add the active childs
        if treeview :
            for c in task.get_subtasks():
                cid = c.get_id()
                if cid in active_tasks:
                    self.add_task_tree_to_list(tree_store, cid, my_row,selected_uid,\
                                        active_tasks=active_tasks)

    #If a Task editor is already opened for a given task, we present it
    #Else, we create a new one.
    def open_task(self,uid) :
        t = self.req.get_task(uid)
        if self.opened_task.has_key(uid) :
            self.opened_task[uid].present()
        else :
            tv = TaskEditor(self.req,t,self.refresh_tb,self.on_delete_task,
                            self.close_task,self.open_task,self.get_tasktitle)
            #registering as opened
            self.opened_task[uid] = tv
            
    def get_tasktitle(self,tid) :
        task = self.req.get_task(tid)
        return task.get_title()
    
    #When an editor is closed, it should deregister itself
    def close_task(self,tid) :
        if self.opened_task.has_key(tid) :
            del self.opened_task[tid]

#    def on_project_treeview_button_press_event(self, treeview, event):
#        if event.button == 3:
#            x = int(event.x)
#            y = int(event.y)
#            time = event.time
#            pthinfo = treeview.get_path_at_pos(x, y)
#            if pthinfo is not None:
#                path, col, cellx, celly = pthinfo
#                treeview.grab_focus()
#                treeview.set_cursor( path, col, 0)
#                self.projectpopup.popup( None, None, None, event.button, time)
#            return 1        
    
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
        p = self.req.get_projects_list()[0]
        tags,notagonly = self.get_selected_tags() 
        task = self.req.new_task(p,tags=tags)
        uid = task.get_id()
        self.open_task(uid)
    
    #Get_selected_task returns the uid :
    # uid (example : '21@1')
    #By default, we select in the task_tview
    def get_selected_task(self,tv=None) :
        uid = None
        if not tv : tview = self.task_tview
        else : tview = tv
        # Get the selection in the gtk.TreeView
        selection = tview.get_selection()
        #If we don't have anything and no tview specified
        #Let's have a look in the closed task view
        if selection.count_selected_rows() <= 0 and not tv :
            tview = self.taskdone_tview
            selection = tview.get_selection()
        # Get the selection iter
        model, selection_iter = selection.get_selected()
        if selection_iter :
            ts = tview.get_model()
            uid = ts.get_value(selection_iter, 0)
        return uid
        
#    def get_selected_project(self) :
#        #We have to select the project
#        #if pid is none, we should handle a default project
#        #and display all tasks
#        p_selected = self.project_tview.get_selection()
#        pmodel, p_iter = p_selected.get_selected()
#        if p_iter :
#            pid = [self.project_ts.get_value(p_iter, 0)]
#            if -1 in pid: pid = self.req.get_projects_list()
#        #If no selection, we display all
#        else :
#            pid = self.req.get_projects_list()
#        return pid

    def get_selected_tags(self) :
        t_selected = self.tag_tview.get_selection()
        tmodel, t_iter = t_selected.get_selected()
        notag_only = False
        tag = []
        if t_iter :
            selected = [self.tag_ts.get_value(t_iter, 0)]
            if -1 in selected: selected.remove(-1)
            #-2 means we want to display only tasks without any tag
            if -2 in selected:
                selected.remove(-2)
                notag_only = True
            if not notag_only :
                for t in selected :
                    if t :
                        tag.append(t)
        #If no selection, we display all
        return tag,notag_only
        
    def on_edit_active_task(self,widget,row=None ,col=None) :
        tid = self.get_selected_task(self.task_tview)
        if tid :
            self.open_task(tid)
    def on_edit_done_task(self,widget,row=None ,col=None) :
        tid = self.get_selected_task(self.taskdone_tview)
        if tid :
            self.open_task(tid)
     
    #if we pass a tid as a parameter, we delete directly
    #otherwise, we will look which tid is selected   
    def on_delete_confirm(self,widget) :
        self.req.delete_task(self.tid_todelete)
        self.tid_todelete = None
        self.refresh_tb()
        
    def on_delete_task(self,widget,tid=None) :
        #If we don't have a parameter, then take the selection in the treeview
        if not tid :
            #tid_to_delete is a [project,task] tuple
            self.tid_todelete = self.get_selected_task()
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
        uid = self.get_selected_task()
        if uid :
            zetask = self.req.get_task(uid)
            status = zetask.get_status() 
            if status == "Done" :
                zetask.set_status("Active")
            else : zetask.set_status("Done")
            self.refresh_tb()
    
    def on_dismiss_task(self,widget) :
        uid = self.get_selected_task()
        if uid :
            zetask = self.req.get_task(uid)
            status = zetask.get_status() 
            if status == "Dismiss" :
                zetask.set_status("Active")
            else : zetask.set_status("Dismiss")
            self.refresh_tb()
        
    def on_select_tag(self, widget, row=None ,col=None) :
        #When you clic on a tag, you want to unselect the tasks
        self.task_tview.get_selection().unselect_all()
        self.taskdone_tview.get_selection().unselect_all()
        self.refresh_list()

    ##### Useful tools##################
    
    #    Functions that help to build the GUI. Nothing really interesting.
    def __add_active_column(self,name,value) :
        col = self.__add_column(name,value)
        self.task_tview.append_column(col)
        
#    def __add_project_column(self,name,value) :
#        col = self.__add_column(name,value)
#        col.set_clickable(False)
#        self.project_tview.append_column(col)
        
    def __add_closed_column(self,name,value) :
        col = self.__add_column(name,value)
        self.taskdone_tview.append_column(col)

    def __add_tag_column(self,name,value) :
        col = self.__add_column(name,value,icon=True)
        col.set_clickable(False)
        self.tag_tview.append_column(col)

    def __add_column(self,name, value, icon=False) :
  
        col = gtk.TreeViewColumn()
        col.set_title(name)
        
        if icon:
            render_pixbuf = gtk.CellRendererPixbuf()
            col.pack_start(render_pixbuf, expand=False)
            col.add_attribute(render_pixbuf, 'pixbuf', 2)

        render_text = gtk.CellRendererText()
        col.pack_start(render_text, expand=True)
        col.set_attributes(render_text, markup=value)
        col.add_attribute(render_text, "cell_background",1)
        
        #col.pack_start(renderer)
        col.set_resizable(True)        
        col.set_sort_column_id(value)
        return col
        
    ######Closing the window
    def close(self,widget=None) :
        #Saving is now done in main.py
        gtk.main_quit()

