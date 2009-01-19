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

        self.tagpopup = self.wTree.get_widget("TagContextMenu")
        self.donebutton = self.wTree.get_widget("mark_as_done_b")
        self.dismissbutton = self.wTree.get_widget("dismiss")
        

        #Create our dictionay and connect it
        dic = {
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
                "on_tag_treeview_button_press_event" : self.on_tag_treeview_button_press_event,
                "on_colorchooser_activate" : self.on_colorchooser_activate,
                "on_workview_toggled" : self.on_workview_toggled

              }
        self.wTree.signal_autoconnect(dic)
        self.selected_rows = None
        
        self.ds = datastore
        self.workview = False
        self.req = self.ds.get_requester()
        
        #The tview and their model
        self.taskdone_tview = self.wTree.get_widget("taskdone_tview")
        self.taskdone_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT, str,str,str)
        self.tag_tview = self.wTree.get_widget("tag_tview")
        self.tag_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT,str,gtk.gdk.Pixbuf,str)
        self.task_tview = self.wTree.get_widget("task_tview")
        self.task_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT, str, str, str,str)
        #Be sure that we are reorderable (not needed normaly)
        self.task_tview.set_reorderable(True)
        
        #this is our manual drag-n-drop handling
        self.task_ts.connect("row-changed",self.row_inserted,"insert")
        self.task_ts.connect("row-deleted",self.row_deleted,"delete")

        
        #The tid that will be deleted
        self.tid_todelete = None
        self.c_title = 1
        
        #This is the list of tasks that are already opened in an editor
        #of course it's empty right now
        self.opened_task = {}
        
        #Variables used during drag-n-drop
        self.drag_sources = []
        self.path_source = None
        self.path_target = None
        self.tid_tomove = None
        self.tid_source_parent = None
        self.tid_target_parent = None
 
    def main(self):
        #Here we will define the main TaskList interface
        
        #The tags treeview
        self.__add_tag_column("Tags",3)
        self.tag_ts = gtk.ListStore(gobject.TYPE_PYOBJECT,str,gtk.gdk.Pixbuf,str)
        self.tag_tview.set_model(self.tag_ts)
   
        #The Active tasks treeview
        self.task_tview.set_rules_hint(False)
        self.__add_active_column("Actions",2)
        self.__add_active_column("Due date",3)
        self.__add_active_column("Left",4)
        self.task_tview.set_model(self.task_ts)
        #self.task_ts.set_sort_column_id(self.c_title, gtk.SORT_ASCENDING)
     
        #The done/dismissed taks treeview
        self.taskdone_tview.set_rules_hint(False)
        self.__add_closed_column("Closed",2)
        self.__add_closed_column("Done date",3)
        self.taskdone_tview.set_model(self.taskdone_ts)
        self.taskdone_ts.set_sort_column_id(self.c_title, gtk.SORT_ASCENDING)
        
        #put the content in those treeviews
        self.refresh_tags()
        self.refresh_list()
        
        selection = self.task_tview.get_selection()
        selection.connect("changed",self.task_cursor_changed)
        closed_selection = self.taskdone_tview.get_selection()
        closed_selection.connect("changed",self.taskdone_cursor_changed)
        
        gtk.main()
        return 0

    def on_colorchooser_activate(self,widget) : #pylint: disable-msg=W0613
        #TODO : Color chooser should be refactorized in its own class
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
            tags,notag_only = self.get_selected_tags() #pylint: disable-msg=W0612
            for t in tags :
                t.set_attribute("color",strcolor)
        self.refresh_tb()
        widget.destroy()
    
    def on_workview_toggled(self,widget) : #pylint: disable-msg=W0613
        self.workview = not self.workview
        self.refresh_tb()

    #If a task asked for the refresh, we don't refresh it to avoid a loop
    def refresh_tb(self,fromtask=None):
        self.refresh_list()
        self.refresh_tags()
        #self.refresh_projects()
        #Refreshing the opened editors
        for uid in self.opened_task :
            if uid != fromtask :
                self.opened_task[uid].refresh_editor()

    #We refresh the tag list. Not needed very often
    def refresh_tags(self) :
        t_model,t_path = self.tag_tview.get_selection().get_selected_rows() #pylint: disable-msg=W0612
        self.tag_ts.clear()
        icon_alltask = gtk.gdk.pixbuf_new_from_file("data/16x16/icons/tags_alltasks.png")
        icon_notag   = gtk.gdk.pixbuf_new_from_file("data/16x16/icons/tags_notag.png")
        self.tag_ts.append([-1,None,icon_alltask,"<span weight=\"bold\">All tags</span>"])
        self.tag_ts.append([-2,None,icon_notag,"<span weight=\"bold\">Tasks without tags</span>"])
        self.tag_ts.append([-3,None,None,"---------------"])

        tags = self.req.get_used_tags()
        #tags.sort()
        for tag in tags:
            color = tag.get_attribute("color")
            self.tag_ts.append([tag,color,None,tag.get_name()])
        #We reselect the selected tag
        if t_path :
            for i in t_path :
                self.tag_tview.get_selection().select_path(i)

    #refresh list build/refresh your TreeStore of task
    #to keep it in sync with your self.projects   
    def refresh_list(self,a=None) : #pylint: disable-msg=W0613
        #selected tasks :
        selected_uid = self.get_selected_task(self.task_tview)
        #selected_closed_uid = self.get_selected_task(self.taskdone_tview)
        t_model,t_path = self.task_tview.get_selection().get_selected_rows() \
                                                #pylint: disable-msg=W0612
        d_model,d_path = self.taskdone_tview.get_selection().get_selected_rows() \
                                                    #pylint: disable-msg=W0612
        #to refresh the list we first empty it then rebuild it
        #is it acceptable to do that ?
        self.task_ts.clear()
        self.taskdone_ts.clear()
        tag_list,notag_only = self.get_selected_tags()
        #We display only tasks of the active projects
        p_list = self.req.get_projects_list()
        nbr_of_tasks = 0
        
        #We build the active tasks pane
        if self.workview :
            tasks = self.req.get_active_tasks_list(projects=p_list,tags=tag_list,\
                        notag_only=notag_only,workable=True, started_only=False)
            for tid in tasks :
                self.add_task_tree_to_list(self.task_ts,tid,None,selected_uid,\
                                                        treeview=False)
            nbr_of_tasks = len(tasks)
                            
        else :
            #building the classical treeview
            active_root_tasks = self.req.get_active_tasks_list(projects=p_list,\
                                tags=tag_list, notag_only=notag_only,\
                                is_root=True, started_only=False)
            active_tasks = self.req.get_active_tasks_list(projects=p_list,\
                            tags=tag_list, notag_only=notag_only,\
                            is_root=False, started_only=False)
            for tid in active_root_tasks :
                self.add_task_tree_to_list(self.task_ts, tid, None,\
                                selected_uid,active_tasks=active_tasks)
            nbr_of_tasks = len(active_tasks)
            
        #Set the title of the window :
        if nbr_of_tasks == 0 :
            parenthesis = "(no active task)"
        elif nbr_of_tasks == 1 :
            parenthesis = "(1 active task)"
        else :
            parenthesis = "(%s actives tasks)"%nbr_of_tasks
        self.window.set_title("Getting Things Gnome %s"%parenthesis)
        
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
            ts,itera = selection.get_selected() #pylint: disable-msg=W0612
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
    
    def on_tag_treeview_button_press_event(self,treeview,event) :
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo #pylint: disable-msg=W0612
                treeview.grab_focus()
                treeview.set_cursor( path, col, 0)
                self.tagpopup.popup( None, None, None, event.button, time)
            return 1
            
    def on_add_task(self,widget) : #pylint: disable-msg=W0613
        #We have to select the project to which we should add a task
        #Currently, we take the first project as the default
        p = self.req.get_projects_list()[0]
        tags,notagonly = self.get_selected_tags() #pylint: disable-msg=W0612
        task = self.req.new_task(p,tags=tags)
        uid = task.get_id()
        self.open_task(uid)
    
    #Get_selected_task returns the uid :
    # uid (example : '21@1')
    #By default, we select in the task_tview
    def get_selected_task(self,tv=None) :
        uid = None
        if not tv : 
            tview = self.task_tview
        else : 
            tview = tv
        # Get the selection in the gtk.TreeView
        selection = tview.get_selection()
        #If we don't have anything and no tview specified
        #Let's have a look in the closed task view
        if selection.count_selected_rows() <= 0 and not tv :
            tview = self.taskdone_tview
            selection = tview.get_selection()
        # Get the selection iter
        model, selection_iter = selection.get_selected() #pylint: disable-msg=W0612
        if selection_iter :
            ts = tview.get_model()
            uid = ts.get_value(selection_iter, 0)
        return uid

    def get_selected_tags(self) :
        t_selected = self.tag_tview.get_selection()
        tmodel, t_iter = t_selected.get_selected() #pylint: disable-msg=W0612
        notag_only = False
        tag = []
        if t_iter :
            selected = [self.tag_ts.get_value(t_iter, 0)]
            if -1 in selected: 
                selected.remove(-1)
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
    
    ###################
    #Drag-drop support#
    ###################
    #Because of bug in pygtk, the rows-reordered signal is never emitted
    #We workaoround this bug by connecting to row_insert and row_deleted
    #Basically, we do the following :
    # 1. If a row is inserted for a task X, look if the task already
    #     exist elsewhere.
    # 2. If yes, it's probably a drag-n-drop so we save those information
    # 3. If the "elsewhere from point 1 is deleted, we are sure it's a 
    #    drag-n-drop so we change the parent of the moved task
    def row_inserted(self,tree, path, it,data=None) :
        #If the row inserted already exists in another position
        #We are in a drag n drop case
        def findsource(model, path, it,data):
            path_move = tree.get_path(data[1])
            path_actual = tree.get_path(it)
            if model.get(it,0) == data[0] and path_move != path_actual:
                self.drag_sources.append(path)
                self.path_source = path
                return True
            else :
                self.path_source = None

        #print "row inserted"
        itera = tree.get_iter(path)
        self.path_target = path
        tid = tree.get(it,0)
        tree.foreach(findsource,[tid,it])
        if self.path_source :
            #We will prepare the drag-n-drop
            iter_source = tree.get_iter(self.path_source)
            iter_target = tree.get_iter(self.path_target)
            iter_source_parent = tree.iter_parent(iter_source)
            iter_target_parent = tree.iter_parent(iter_target)
            #the tid_parent will be None for root tasks
            if iter_source_parent :
                sparent = tree.get(iter_source_parent,0)[0]
            else :
                sparent = None
            if iter_target_parent :
                tparent = tree.get(iter_target_parent,0)[0]
            else :
                tparent = None
            #If target and source are the same, we are moving
            #a child of the deplaced task. Indeed, children are 
            #also moved in the tree but their parents remain !
            if sparent != tparent :
                self.tid_source_parent = sparent
                self.tid_target_parent = tparent
                self.tid_tomove = tid[0]
                #print "row %s will move from %s to %s"%(self.tid_tomove,\
                #          self.tid_source_parent,self.tid_target_parent)
    def row_deleted(self,tree,path,data=None) :
        #If we are removing the path source guessed during the insertion
        #It confirms that we are in a drag-n-drop
        if path in self.drag_sources and self.tid_tomove :
            self.drag_sources.remove(path)
            #print "row %s moved from %s to %s"%(self.tid_tomove,\
            #              self.tid_source_parent,self.tid_target_parent)
            tomove = self.req.get_task(self.tid_tomove)
            tomove.remove_parent(self.tid_source_parent)
            tomove.add_parent(self.tid_target_parent)
            #DO NOT self.refresh_list()
            #Refreshing here make things crash. Don't refresh
            self.drag_sources = []
            self.path_source = None
            self.path_target = None
            self.tid_tomove = None
            self.tid_source_parent = None
            self.tid_target_parent = None
        
        
    def on_edit_active_task(self,widget,row=None ,col=None) : #pylint: disable-msg=W0613
        tid = self.get_selected_task(self.task_tview)
        if tid :
            self.open_task(tid)
    def on_edit_done_task(self,widget,row=None ,col=None) : #pylint: disable-msg=W0613
        tid = self.get_selected_task(self.taskdone_tview)
        if tid :
            self.open_task(tid)
     
    #if we pass a tid as a parameter, we delete directly
    #otherwise, we will look which tid is selected   
    def on_delete_confirm(self,widget) : #pylint: disable-msg=W0613
        self.req.delete_task(self.tid_todelete)
        self.tid_todelete = None
        self.refresh_tb()
        
    def on_delete_task(self,widget,tid=None) : #pylint: disable-msg=W0613
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
        
    def on_mark_as_done(self,widget) : #pylint: disable-msg=W0613
        uid = self.get_selected_task()
        if uid :
            zetask = self.req.get_task(uid)
            status = zetask.get_status() 
            if status == "Done" :
                zetask.set_status("Active")
            else : zetask.set_status("Done")
            self.refresh_tb()
    
    def on_dismiss_task(self,widget) : #pylint: disable-msg=W0613
        uid = self.get_selected_task()
        if uid :
            zetask = self.req.get_task(uid)
            status = zetask.get_status() 
            if status == "Dismiss" :
                zetask.set_status("Active")
            else : zetask.set_status("Dismiss")
            self.refresh_tb()
        
    def on_select_tag(self, widget, row=None ,col=None) : #pylint: disable-msg=W0613
        #When you clic on a tag, you want to unselect the tasks
        self.task_tview.get_selection().unselect_all()
        self.taskdone_tview.get_selection().unselect_all()
        self.refresh_list()

    ##### Useful tools##################
    
    #    Functions that help to build the GUI. Nothing really interesting.
    def __add_active_column(self,name,value) :
        col = self.__add_column(name,value)
        self.task_tview.append_column(col)
        
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
            col.add_attribute(render_pixbuf, "cell_background",1)

        render_text = gtk.CellRendererText()
        col.pack_start(render_text, expand=True)
        col.set_attributes(render_text, markup=value)
        col.add_attribute(render_text, "cell_background",1)
        
        col.set_resizable(True)        
        col.set_sort_column_id(value)
        return col
        
    ######Closing the window
    def close(self,widget=None) : #pylint: disable-msg=W0613
        #Saving is now done in main.py
        gtk.main_quit()

