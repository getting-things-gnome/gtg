# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personnal organizer for the GNOME desktop
# Copyright (c) 2008-2009 - Lionel Dricot & Bertrand Rousseau
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------


#=== IMPORT ====================================================================
#system imports
import pygtk
pygtk.require('2.0')
import gobject
import gtk.glade
import threading
import os
from gnome import url_show

#our own imports
import GTG
from GTG.taskeditor.editor            import TaskEditor
from GTG.taskbrowser.CellRendererTags import CellRendererTags
from GTG.taskbrowser                  import GnomeConfig
from GTG.taskbrowser                  import treetools
from GTG.tools                        import colors
from GTG.core                         import CoreConfig

#=== OBJECTS ===================================================================

#=== MAIN CLASS ================================================================

#Some default preferences that we should save in a file
WORKVIEW      = False
SIDEBAR       = False
CLOSED_PANE   = False
QUICKADD_PANE = True

EXPERIMENTAL_NOTES = False

class TaskBrowser:

    def __init__(self, requester, config):
        
        self.priv = {}
        
        #The locks used to avoid unecessary refresh
        self.refresh_lock = threading.Lock()
        self.refresh_lock_lock = threading.Lock()
        # Set the configuration dictionary
        self.config = config
        self.notes = EXPERIMENTAL_NOTES
        
        # Setup default values for view
        self.priv["collapsed_tid"]            = []
        self.priv["tasklist"]                 = {}
        self.priv["tasklist"]["sort_column"]  = None
        self.priv["tasklist"]["sort_order"]   = gtk.SORT_ASCENDING
        self.priv["ctasklist"]                = {}
        self.priv["ctasklist"]["sort_column"] = None
        self.priv["ctasklist"]["sort_order"]  = gtk.SORT_ASCENDING
               
        #Set the Glade file
        self.gladefile = GnomeConfig.GLADE_FILE  
        self.wTree = gtk.glade.XML(self.gladefile) 
        
        #Get the Main Window, and connect the "destroy" event
        self.window = self.wTree.get_widget("MainWindow")
        if (self.window):
            self.window.connect("destroy", gtk.main_quit)

        icon_dirs = [
            GTG.DATA_DIR,
            os.path.join(GTG.DATA_DIR,"icons")
                    ] 

        for i in icon_dirs:
            gtk.icon_theme_get_default().prepend_search_path(i)
            gtk.window_set_default_icon_name("gtg")

        self.tagpopup           = self.wTree.get_widget("TagContextMenu")
        self.taskpopup          = self.wTree.get_widget("TaskContextMenu")
        self.closedtaskpopup    = self.wTree.get_widget("ClosedTaskContextMenu")
        self.donebutton         = self.wTree.get_widget("mark_as_done_b")
        self.dismissbutton      = self.wTree.get_widget("dismiss")
        self.about              = self.wTree.get_widget("aboutdialog1")

        # Initialize "About" dialog
        gtk.about_dialog_set_url_hook(lambda dialog, url: url_show(url))
        self.about.set_website(GTG.URL)
        self.about.set_website_label(GTG.URL)
        self.about.set_version(GTG.VERSION)
        
        # Initialize menu

        #Create our dictionay and connect it
        dic = {
                "on_add_task"         : self.on_add_task,
                "on_add_note"         : (self.on_add_task,'Note'),
                "on_edit_active_task" : self.on_edit_active_task,
                "on_edit_done_task"   : self.on_edit_done_task,
                "on_edit_note"        : self.on_edit_note,
                "on_delete_task"      : self.on_delete_task,
                "on_mark_as_done"     : self.on_mark_as_done,
                "on_dismiss_task"     : self.on_dismiss_task,
                "on_delete"           : self.on_delete,
                "on_move"             : self.on_move,
                "on_size_allocate"    : self.on_size_allocate,
                "gtk_main_quit"       : self.close,
                "on_select_tag"       : self.on_select_tag,
                "on_delete_confirm"   : self.on_delete_confirm,
                "on_delete_cancel"    : lambda x : x.hide,
                "on_add_subtask"      : self.on_add_subtask,
                "on_closed_task_treeview_button_press_event" : self.on_closed_task_treeview_button_press_event,
                "on_task_treeview_button_press_event" : self.on_task_treeview_button_press_event,
                "on_tag_treeview_button_press_event"  : self.on_tag_treeview_button_press_event,
                "on_colorchooser_activate"            : self.on_colorchooser_activate,
                "on_workview_toggled"                 : self.on_workview_toggled,
                "on_note_toggled"                     : self.on_note_toggled,
                "on_view_workview_toggled"            : self.on_workview_toggled,
                "on_view_closed_toggled"              : self.on_closed_toggled,
                "on_view_sidebar_toggled"             : self.on_sidebar_toggled,
                "on_bg_color_toggled"                 : self.on_bg_color_toggled,
                "on_quickadd_field_activate"          : self.quickadd,
                "on_quickadd_button_activate"         : self.quickadd,
                "on_view_quickadd_toggled"            : self.toggle_quickadd,
                "on_about_clicked"                    : self.on_about_clicked,
                "on_about_close"                      : self.on_about_close,
                "on_nonworkviewtag_toggled"           : self.on_nonworkviewtag_toggled
              }
        self.wTree.signal_autoconnect(dic)
        self.selected_rows = None
        
        self.workview = False
        self.req = requester
        
        self.noteview = False
        self.new_note_button = self.wTree.get_widget("new_note_button")
        self.note_toggle = self.wTree.get_widget("note_toggle")
        if not self.notes :
            self.note_toggle.hide()
            self.new_note_button.hide()
        
        # Model constants
        self.TASK_MODEL_OBJ         = 0
        self.TASK_MODEL_TITLE       = 1
        self.TASK_MODEL_TITLE_STR   = 2
        #Warning : this one is duplicated in treetools.py
        #They all should go in treetools
        self.TASK_MODEL_DDATE_STR   = 3
        self.TASK_MODEL_DLEFT_STR   = 4
        self.TASK_MODEL_TAGS        = 5
        self.TASK_MODEL_BGCOL       = 6
        self.TAGS_MODEL_OBJ         = 0
        self.TAGS_MODEL_COLOR       = 1
        self.TAGS_MODEL_NAME        = 2
        self.TAGS_MODEL_COUNT       = 3
        self.TAGS_MODEL_SEP         = 4
        self.CTASKS_MODEL_OBJ       = 0
        self.CTASKS_MODEL_TITLE     = 2
        self.CTASKS_MODEL_DDATE     = 3
        self.CTASKS_MODEL_DDATE_STR = 4
        self.CTASKS_MODEL_BGCOL     = 5
        self.CTASKS_MODEL_TAGS      = 6
                
        #The tview and their model
        self.taskdone_tview = self.wTree.get_widget("taskdone_tview")
        self.taskdone_ts    = gtk.TreeStore(gobject.TYPE_PYOBJECT, str,str,str,str,str,gobject.TYPE_PYOBJECT)
        #self.note_tview = self.wTree.get_widget("note_tview")
        self.note_tview = gtk.TreeView()
        self.note_tview.connect("row-activated",self.on_edit_note)
        self.note_tview.show()
        self.note_ts = gtk.TreeStore(gobject.TYPE_PYOBJECT, str,str)
        self.tag_tview      = self.wTree.get_widget("tag_tview")
        self.tag_ts         = gtk.ListStore(gobject.TYPE_PYOBJECT,str,str,str,bool)
        # TASK MODEL:
        # PYOBJECT:tid, STR:title, STR:due date string,
        # STR:days left string, PYOBJECT:tags, str:my_color
        self.task_tview     = self.wTree.get_widget("task_tview")
        self.task_ts        = treetools.new_task_ts(dnd_func=self.row_dragndrop)
        self.main_pane      = self.wTree.get_widget("main_pane")

        #Be sure that we are reorderable (not needed normaly)
        self.task_tview.set_reorderable(True)
        
        #The menu items widget
        self.menu_view_workview = self.wTree.get_widget("view_workview")
        
        #The buttons
        self.toggle_workview = self.wTree.get_widget("workview_toggle")
        self.quickadd_entry = self.wTree.get_widget("quickadd_field")
        
        #The panes
        self.sidebar       = self.wTree.get_widget("sidebar")
        self.closed_pane   = self.wTree.get_widget("closed_pane")
        self.quickadd_pane = self.wTree.get_widget("quickadd_pane")
               
        #The tid that will be deleted
        self.tid_todelete = None
        
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
        
        #setting the default
        self.menu_view_workview.set_active(WORKVIEW)
        self.wTree.get_widget("view_sidebar").set_active(SIDEBAR)
        self.wTree.get_widget("view_closed").set_active(CLOSED_PANE)
        self.wTree.get_widget("view_quickadd").set_active(QUICKADD_PANE)
        self.priv["bg_color_enable"] = True
    
		#connecting the refresh signal from the requester
        self.lock = threading.Lock()
        self.req.connect("refresh",self.do_refresh)

    def __restore_state_from_conf(self):
        
        # Extract state from configuration dictionary
        if not self.config.has_key("browser"): return
        
        if self.config["browser"].has_key("width") and \
           self.config["browser"].has_key("height"):
               
            width  = int(self.config["browser"]["width"])
            height = int(self.config["browser"]["height"])
            self.window.resize(width, height)
   
        if self.config["browser"].has_key("x_pos") and \
           self.config["browser"].has_key("y_pos"):
               
            xpos   = int(self.config["browser"]["x_pos"])
            ypos   = int(self.config["browser"]["y_pos"])
            self.window.move   (xpos, ypos)
            
        if self.config["browser"].has_key("tag_pane"):
            tag_pane         = eval(self.config["browser"]["tag_pane"])
            if not tag_pane:
                self.sidebar.hide()
                self.wTree.get_widget("view_sidebar").set_active(False)
            else:
                self.sidebar.show()
                self.wTree.get_widget("view_sidebar").set_active(True)
                
        if self.config["browser"].has_key("closed_task_pane"):
            closed_task_pane = eval(self.config["browser"]["closed_task_pane"])
            if not closed_task_pane :
                self.closed_pane.hide()
                self.wTree.get_widget("view_closed").set_active(False)
            else:
                self.closed_pane.show()
                self.wTree.get_widget("view_closed").set_active(True)

        if self.config["browser"].has_key("ctask_pane_height"):
            ctask_pane_height = eval(self.config["browser"]["ctask_pane_height"])
            self.wTree.get_widget("vpaned1").set_position(ctask_pane_height)
                
        if self.config["browser"].has_key("quick_add"):
            quickadd_pane    = eval(self.config["browser"]["quick_add"])
            if not quickadd_pane    :
                self.quickadd_pane.hide()
                self.wTree.get_widget("view_quickadd").set_active(False)
                
        if self.config["browser"].has_key("bg_color_enable"):
            bgcol_enable = eval(self.config["browser"]["bg_color_enable"])
            self.priv["bg_color_enable"] = bgcol_enable
            self.wTree.get_widget("bgcol_enable").set_active(bgcol_enable)
            
        if self.config["browser"].has_key("collapsed_tasks"):
            self.priv["collapsed_tid"] = self.config["browser"]["collapsed_tasks"]
            
        if self.config["browser"].has_key("tasklist_sort"):
            col_id, order = self.config["browser"]["tasklist_sort"]
            self.priv["sort_column"] = col_id
            try:
                col_id, order = int(col_id), int(order)
                sort_col = self.priv["tasklist"]["columns"][col_id]
                self.priv["tasklist"]["sort_column"] = sort_col
                if order == 0 : self.priv["tasklist"]["sort_order"] = gtk.SORT_ASCENDING
                if order == 1 : self.priv["tasklist"]["sort_order"] = gtk.SORT_DESCENDING
            except:
                print "Invalid configuration for sorting columns"

        if self.config["browser"].has_key("view"):
            view = self.config["browser"]["view"]
            if view == "workview": self.do_toggle_workview()
            
        if self.config["browser"].has_key("experimental_notes") :
            self.notes = eval(self.config["browser"]["experimental_notes"])
            if self.notes :
                self.note_toggle.show()
                self.new_note_button.show()
            else :
                self.note_toggle.hide()
                self.new_note_button.hide()
            

    def on_move(self, widget, data): #pylint: disable-msg=W0613
        xpos, ypos = self.window.get_position()
        self.priv["window_xpos"] = xpos
        self.priv["window_ypos"] = ypos

    def on_size_allocate(self, widget, data): #pylint: disable-msg=W0613
        width, height = self.window.get_size()
        self.priv["window_width"]  = width
        self.priv["window_height"] = height
        
    def on_delete(self, widget, user_data): #pylint: disable-msg=W0613
        
        # Save expanded rows
        self.task_ts.foreach(self.update_collapsed_row, None)
        
        # Cleanup collapsed row list
        for tid in self.priv["collapsed_tid"]:
            if not self.req.has_task(tid): self.priv["collapsed_tid"].remove(tid)
        
        # Get configuration values
        tag_sidebar     = self.sidebar.get_property("visible")
        closed_pane     = self.closed_pane.get_property("visible")
        quickadd_pane   = self.quickadd_pane.get_property("visible")
        task_tv_sort_id = self.task_ts.get_sort_column_id()
        sort_column     = self.priv["tasklist"]["sort_column"]
        sort_order      = self.priv["tasklist"]["sort_order"]
        closed_pane_height = self.wTree.get_widget("vpaned1").get_position()
        
        if self.workview : view = "workview"
        else             : view = "default"

        # Populate configuration dictionary
        self.config["browser"] = {}
        self.config["browser"]["width"]             = self.priv["window_width"]
        self.config["browser"]["height"]            = self.priv["window_height"]
        self.config["browser"]["x_pos"]             = self.priv["window_xpos"]
        self.config["browser"]["y_pos"]             = self.priv["window_ypos"]
        self.config["browser"]["tag_pane"]          = tag_sidebar
        self.config["browser"]["closed_task_pane"]  = closed_pane
        self.config["browser"]["ctask_pane_height"] = closed_pane_height
        self.config["browser"]["quick_add"]         = quickadd_pane
        self.config["browser"]["bg_color_enable"]   = self.priv["bg_color_enable"]
        self.config["browser"]["collapsed_tasks"]   = self.priv["collapsed_tid"]
        if   sort_column is not None and sort_order == gtk.SORT_ASCENDING :
            sort_col_id = self.priv["tasklist"]["columns"].index(sort_column)
            self.config["browser"]["tasklist_sort"]  = [sort_col_id, 0]
        elif sort_column is not None and sort_order == gtk.SORT_DESCENDING :
            sort_col_id = self.priv["tasklist"]["columns"].index(sort_column)
            self.config["browser"]["tasklist_sort"]  = [sort_col_id, 1]
        self.config["browser"]["view"]              = view
        if self.notes :
            self.config["browser"]["experimental_notes"] = True
             
    def on_close(self):
        self.__save_state_to_conf()
        self.close()
 
    def main(self):
        #Here we will define the main TaskList interface
        gobject.threads_init()
        
        #The tags treeview
        self.__create_tags_tview()
        self.tag_tview.set_model(self.tag_ts)
   
        #The Active tasks treeview
        self.__create_task_tview()
        self.task_tview.set_model(self.task_ts)
     
        #The done/dismissed taks treeview
        self.__create_closed_tasks_tview()
        self.taskdone_tview.set_model(self.taskdone_ts)
        
        #The treeview for notes
        self.__create_note_tview()
        self.note_tview.set_model(self.note_ts)
                
        #put the content in those treeviews
        self.do_refresh()
        
        selection = self.task_tview.get_selection()
        selection.connect("changed",self.task_cursor_changed)
        closed_selection = self.taskdone_tview.get_selection()
        closed_selection.connect("changed",self.taskdone_cursor_changed)
        note_selection = self.note_tview.get_selection()
        note_selection.connect("changed",self.note_cursor_changed)
        
        
        # Restore state from config
        self.__restore_state_from_conf()
        self.window.show()
        
        gtk.main()
        return 0

    def on_about_clicked(self, widget): #pylint: disable-msg=W0613
        self.about.show()

    def on_about_close(self, widget, response): #pylint: disable-msg=W0613
        self.about.hide()

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
        self.do_refresh()
        widget.destroy()
    
    def on_workview_toggled(self,widget) : #pylint: disable-msg=W0613
        self.do_toggle_workview()
    
    def do_toggle_workview(self):
        #We have to be careful here to avoid a loop of signals
        menu_state   = self.menu_view_workview.get_active()
        button_state = self.toggle_workview.get_active()
        #We cannot have note and workview at the same time
        if not self.workview and self.note_toggle.get_active() :
            self.note_toggle.set_active(False)
        #We do something only if both widget are in different state
        tobeset = not self.workview
        self.menu_view_workview.set_active(tobeset)
        self.toggle_workview.set_active(tobeset)
        self.workview = tobeset
        self.do_refresh()

    def on_sidebar_toggled(self,widget) :
        if widget.get_active() :
            self.sidebar.show()
        else :
            self.sidebar.hide()
            
    def on_note_toggled(self,widget) :
        self.noteview = not self.noteview
        workview_state = self.toggle_workview.get_active()
        if workview_state :
            self.toggle_workview.set_active(False)
        self.do_refresh()
    
    def on_closed_toggled(self,widget) :
        if widget.get_active() :
            self.closed_pane.show()
        else :
            self.closed_pane.hide()

    def on_bg_color_toggled(self,widget) :
        if widget.get_active() :
            self.priv["bg_color_enable"] = True
        else :
            self.priv["bg_color_enable"] = False
        self.do_refresh()
            
    def toggle_quickadd(self,widget) :
        if widget.get_active() :
            self.quickadd_pane.show()
        else :
            self.quickadd_pane.hide()
            
    def quickadd(self,widget) : #pylint: disable-msg=W0613
        text = self.quickadd_entry.get_text()
        if text :
            tags,notagonly = self.get_selected_tags() #pylint: disable-msg=W0612
            task = self.req.new_task(tags=tags,newtask=True)
            task.set_title(text)
            self.quickadd_entry.set_text('')
            self.do_refresh()
    
    
    def do_refresh(self,sender=None,param=None) : #pylint: disable-msg=W0613
        #We ask to do the refresh in a gtk thread
        #We use a lock_lock like described in 
        #http://ploum.frimouvy.org/?202-the-signals-and-threads-flying-circus
        if self.refresh_lock_lock.acquire(False) :
            gobject.idle_add(self.refresh_tb,param)

    #If a task asked for the refresh, we don't refresh it to avoid a loop
    #New use refresh_tb directly, use "do_refresh"
    def refresh_tb(self,fromtask=None):
        self.refresh_lock.acquire()
        self.refresh_lock_lock.release()
        current_pane = self.main_pane.get_child()
        if self.noteview :
            if current_pane == self.task_tview :
                self.main_pane.remove(current_pane)
                self.main_pane.add(self.note_tview)
            self.refresh_note()
        else :
            if current_pane == self.note_tview :
                self.main_pane.remove(current_pane)
                self.main_pane.add(self.task_tview)
            self.refresh_list()
        self.refresh_closed()
        self.refresh_tags()
        #Refreshing the opened editors
        for uid in self.opened_task :
            if uid != fromtask :
                self.opened_task[uid].refresh_editor()
        self.refresh_lock.release()


    #We refresh the tag list. Not needed very often
    def refresh_tags(self) :
        select = self.tag_tview.get_selection()
        t_path = None
        if select :
            t_model,t_path = select.get_selected_rows() #pylint: disable-msg=W0612
        self.tag_ts.clear()
        alltag       = self.req.get_alltag_tag()
        notag        = self.req.get_notag_tag()

        count_all_task = len(self.req.get_tasks_list())
        count_no_tags  = len(self.req.get_tasks_list(notag_only=True))
        self.tag_ts.append([alltag,None,"<span weight=\"bold\">All tags</span>",str(count_all_task),False])
        self.tag_ts.append([notag,None,"<span weight=\"bold\">Tasks without tags</span>",str(count_no_tags),False])
        self.tag_ts.append([None,None,"","",True])

        tags = self.req.get_used_tags()
        
        tags.sort(cmp=lambda x,y: cmp(x.get_name().lower(),y.get_name().lower()))

        for tag in tags:
            color = tag.get_attribute("color")
            count = len(self.req.get_tasks_list(tags=[tag]))
            #We display the tags without the "@" (but we could)
            if count != 0:
                self.tag_ts.append([tag,color,tag.get_name()[1:], str(count), False])
            
        #We reselect the selected tag
        if t_path :
            for i in t_path :
                self.tag_tview.get_selection().select_path(i)

    def tag_separator_filter(self, model, itera, user_data=None):#pylint: disable-msg=W0613
        return model.get_value(itera, self.TAGS_MODEL_SEP)
        
    def update_collapsed_row(self, model, path, itera, user_data): #pylint: disable-msg=W0613
        """Build a list of task that must showed as collapsed in Treeview"""
        tid = self.task_ts.get_value(itera,0)
        # Remove expanded rows
        if   self.task_ts.iter_has_child(itera) and \
             self.task_tview.row_expanded(path) and \
             tid in self.priv["collapsed_tid"]:

            self.priv["collapsed_tid"].remove(tid)

        # Append collapsed rows
        elif self.task_ts.iter_has_child(itera)     and \
             not self.task_tview.row_expanded(path) and \
             tid not in self.priv["collapsed_tid"]:

            self.priv["collapsed_tid"].append(tid)

        return False # Return False or the TreeModel.foreach() function ends
                    
    def restore_collapsed(self,treeview,path,data) :
        itera = self.task_ts.get_iter(path)
        tid   = self.task_ts.get_value(itera,0)
        if tid in self.priv["collapsed_tid"] :
            treeview.collapse_row(path)
        
    #refresh list build/refresh your TreeStore of task
    #to keep it in sync with your self.projects   
    def refresh_list(self,a=None) : #pylint: disable-msg=W0613
        
        # Save collapsed rows
        self.task_ts.foreach(self.update_collapsed_row, None)
        
        #selected tasks :
        selected_uid = self.get_selected_task(self.task_tview)
        tselect = self.task_tview.get_selection()
        t_path = None
        if tselect :
            t_model,t_path = tselect.get_selected_rows() #pylint: disable-msg=W0612
            
        #Scroll position :
        vscroll_value = self.task_tview.get_vadjustment().get_value()
        hscroll_value = self.task_tview.get_hadjustment().get_value()    
        
        #to refresh the list we build a new treestore then replace the existing
        new_taskts = treetools.new_task_ts(dnd_func=self.row_dragndrop)
        tag_list,notag_only = self.get_selected_tags()
        nbr_of_tasks = 0
        
        #We build the active tasks pane
        if self.workview :
            tasks = self.req.get_active_tasks_list(tags=tag_list,\
                        notag_only=notag_only,workable=True, started_only=False)
            for tid in tasks :
                self.add_task_tree_to_list(new_taskts,tid,None,selected_uid,\
                                                        treeview=False)
            nbr_of_tasks = len(tasks)
                            
        else :
            #building the classical treeview
            active_root_tasks = self.req.get_active_tasks_list(tags=tag_list,\
                            notag_only=notag_only, is_root=True, started_only=False)
            active_tasks = self.req.get_active_tasks_list(tags=tag_list,\
                            notag_only=notag_only, is_root=False, started_only=False)
            for tid in active_root_tasks :
                self.add_task_tree_to_list(new_taskts, tid, None,\
                                selected_uid,active_tasks=active_tasks)
            nbr_of_tasks = len(active_tasks)
            
        #Set the title of the window :
        if nbr_of_tasks == 0 :
            parenthesis = "(no active task)"
        elif nbr_of_tasks == 1 :
            parenthesis = "(1 active task)"
        else :
            parenthesis = "(%s active tasks)"%nbr_of_tasks
        self.window.set_title("Getting Things Gnome! %s"%parenthesis)
        self.task_tview.set_model(new_taskts)
        self.task_ts = new_taskts
        #We expand all the we close the tasks who were not saved as "expanded"
        self.task_tview.expand_all()
        self.task_tview.map_expanded_rows(self.restore_collapsed,None)
        # Restore sorting
        if not self.noteview :
            if self.priv["tasklist"].has_key("sort_column") and \
               self.priv["tasklist"].has_key("sort_order")      :
                if self.priv["tasklist"]["sort_column"] is not None and \
                   self.priv["tasklist"]["sort_order"]  is not None     :
                    self.sort_tasklist_rows(self.priv["tasklist"]["sort_column"], \
                                            self.priv["tasklist"]["sort_order"])
        #We reselect the selected tasks
        selection = self.task_tview.get_selection()
        if t_path :
            for i in t_path :
                selection.select_path(i)
                
        #scroll position
        #We have to call that in another thread, else it will not work
        def restore_vscroll(old_position) :
            vadjust = self.task_tview.get_vadjustment()
            #We ensure that we will not scroll out of the window
            #It was bug #331285
            vscroll = min(old_position,(vadjust.upper - vadjust.page_size))
            vadjust.set_value(vscroll)
        def restore_hscroll(old_position) :
            hadjust = self.task_tview.get_hadjustment()
            hscroll = min(old_position,(hadjust.upper - hadjust.page_size))
            hadjust.set_value(hscroll)
        gobject.idle_add(restore_vscroll,vscroll_value)
        gobject.idle_add(restore_hscroll,hscroll_value)

    #Refresh the closed tasks pane
    def refresh_closed(self) :
        #We build the closed tasks pane
        dselect = self.taskdone_tview.get_selection()
        d_path = None
        if dselect :
            d_model,d_path = dselect.get_selected_rows() #pylint: disable-msg=W0612
        #We empty the pane
        self.taskdone_ts.clear()
        #We rebuild it
        tag_list,notag_only = self.get_selected_tags()
        closed_tasks = self.req.get_closed_tasks_list(tags=tag_list,\
                                                    notag_only=notag_only)
        for tid in closed_tasks :
            t              = self.req.get_task(tid)
            title_str      = t.get_title()
            closeddate     = t.get_closed_date()
            closeddate_str = closeddate
            tags           = t.get_tags()
            if self.priv["bg_color_enable"] and t.has_tags() :
                my_color = colors.background_color(t.get_tags())
            else:
                my_color = None
            if t.get_status() == "Dismiss":
                title_str      = "<span color=\"#AAAAAA\">%s</span>" % title_str
                closeddate_str = "<span color=\"#AAAAAA\">%s</span>" % closeddate
            self.taskdone_ts.append(None,[tid,t.get_color(),title_str,closeddate,closeddate_str,my_color,tags])
        closed_selection = self.taskdone_tview.get_selection()
        if d_path :
            for i in d_path :
                closed_selection.select_path(i)
        self.taskdone_ts.set_sort_column_id(self.CTASKS_MODEL_DDATE, gtk.SORT_DESCENDING)
        
    #Refresh the notes pane
    def refresh_note(self) :
        #We build the notes pane
        dselect = self.note_tview.get_selection()
        d_path = None
        if dselect :
            d_model,d_path = dselect.get_selected_rows() #pylint: disable-msg=W0612
        #We empty the pane
        self.note_ts.clear()
        #We rebuild it
        tag_list,notag_only = self.get_selected_tags()
        notes = self.req.get_notes_list(tags=tag_list, notag_only=notag_only)
        for tid in notes :
            t              = self.req.get_task(tid)
            title_str      = t.get_title()
            self.note_ts.append(None,[tid,t.get_color(),title_str])
        note_selection = self.note_tview.get_selection()
        if d_path :
            for i in d_path :
                note_selection.select_path(i)
        #self.note_ts.set_sort_column_id(self.CTASKS_MODEL_DDATE, gtk.SORT_DESCENDING)
                
    #Add tasks to a treeview. If treeview is False, it becomes a flat list
    def add_task_tree_to_list(self, tree_store, tid, parent, selected_uid=None,\
                                        active_tasks=[], treeview=True):
        task     = self.req.get_task(tid)
        st_count = self.__count_tasks_rec(task, active_tasks)
        if selected_uid and selected_uid == tid :
            # Temporarily disabled
            #title = self.__build_task_title(task,extended=True)
            title_str = self.__build_task_title(task, st_count, extended=False)
        else :
            title_str = self.__build_task_title(task, st_count, extended=False)

        # Extract data
        title       = task.get_title() 
        duedate_str = task.get_due_date()
        left_str    = task.get_days_left()
        tags        = task.get_tags()
        if self.priv["bg_color_enable"] :
            my_color = colors.background_color(tags)
        else:
            my_color = None
        
        if not parent and len(task.get_subtasks()) == 0:
            itera = tree_store.get_iter_first()
            my_row = tree_store.insert_before(None, itera, row=[tid,title,title_str,duedate_str,left_str,tags,my_color])
        else:
            #None should be "parent" but crashing with thread
            my_row = tree_store.append(parent,\
                        [tid,title,title_str,duedate_str,left_str,tags,my_color])
        #If treeview, we add add the active childs
        if treeview :
            for c in task.get_subtasks():
                cid = c.get_id()
                if cid in active_tasks:
                    #None should be cid
                    self.add_task_tree_to_list(tree_store, cid, my_row,selected_uid,\
                                        active_tasks=active_tasks)
    
    #This function is called when the selection change in the closed task view
    #It will displays the selected task differently           
    def taskdone_cursor_changed(self,selection=None) :
        #We unselect all in the active task view
        #Only if something is selected in the closed task list
        #And we change the status of the Done/dismiss button
        self.donebutton.set_icon_name("gtg-task-done")
        self.dismissbutton.set_icon_name("gtg-task-dismiss")
        if selection.count_selected_rows() > 0 :
            tid = self.get_selected_task(self.taskdone_tview)
            task = self.req.get_task(tid)
            self.task_tview.get_selection().unselect_all()
            self.note_tview.get_selection().unselect_all()
            if task.get_status() == "Dismiss" :
                self.dismissbutton.set_label(GnomeConfig.MARK_UNDISMISS)
                self.donebutton.set_label(GnomeConfig.MARK_DONE)
                self.dismissbutton.set_icon_name("gtg-task-undismiss")
            else :
                self.donebutton.set_label(GnomeConfig.MARK_UNDONE)
                self.dismissbutton.set_label(GnomeConfig.MARK_DISMISS)
                self.donebutton.set_icon_name("gtg-task-undone")
                
    #This function is called when the selection change in the active task view
    #It will displays the selected task differently
    def task_cursor_changed(self,selection=None) :
        #We unselect all in the closed task view
        #Only if something is selected in the active task list
        self.donebutton.set_icon_name("gtg-task-done")
        self.dismissbutton.set_icon_name("gtg-task-dismiss")
        if selection.count_selected_rows() > 0 :
            self.taskdone_tview.get_selection().unselect_all()
            self.note_tview.get_selection().unselect_all()
            self.donebutton.set_label(GnomeConfig.MARK_DONE)
            self.dismissbutton.set_label(GnomeConfig.MARK_DISMISS)
        #We reset the previously selected task
        if self.selected_rows and self.task_ts.iter_is_valid(self.selected_rows):
            tid = self.task_ts.get_value(self.selected_rows, self.TASK_MODEL_OBJ)
            task = self.req.get_task(tid)
            title = self.__build_task_title(task,extended=False)
            self.task_ts.set_value(self.selected_rows,self.TASK_MODEL_TITLE,title)
        #We change the selection title
        #if selection :
            #ts,itera = selection.get_selected() #pylint: disable-msg=W0612
            #if itera and self.task_ts.iter_is_valid(itera) :
                #tid = self.task_ts.get_value(itera, self.TASK_MODEL_OBJ)
                #task = self.req.get_task(tid)
                #self.selected_rows = itera
                # Extended title is temporarily disabled
                #title = self.__build_task_title(task,extended=True)
                #title = self.__build_task_title(task,extended=False)
                #self.task_ts.set_value(self.selected_rows,self.TASK_MODEL_TITLE,title)
                
    def note_cursor_changed(self,selection=None) :
        #We unselect all in the closed task view
        #Only if something is selected in the active task list
        if selection.count_selected_rows() > 0 :
            self.taskdone_tview.get_selection().unselect_all()
            self.task_tview.get_selection().unselect_all()

    def __count_tasks_rec(self, my_task, active_tasks):
        count = 0
        for t in my_task.get_subtasks():
            if t.get_id() in active_tasks:
                if len(t.get_subtasks()) != 0:
                    count = count + 1 + self.__count_tasks_rec(t, active_tasks)
                else:
                    count = count + 1
        return count
    
    def __build_task_title(self,task,count,extended=False):
        if extended :
            excerpt = task.get_excerpt(lines=2)
            if excerpt.strip() != "" :
                title   = "<b><big>%s</big></b>\n<small>%s</small>" %(task.get_title(),excerpt)
            else : 
                title   = "<b><big>%s</big></b>" %task.get_title()
        else :
            if (not self.workview):
                if count == 0:
                    title = "<span>%s</span>" % (task.get_title() )
                else:
                    title = "<span>%s (%s)</span>" % (task.get_title(), count )
            else:
                title = task.get_title()
        return title

    #If a Task editor is already opened for a given task, we present it
    #Else, we create a new one.
    def open_task(self,uid) :
        t = self.req.get_task(uid)
        if self.opened_task.has_key(uid) :
            self.opened_task[uid].present()
        else :
            tv = TaskEditor(self.req,t,self.do_refresh,self.on_delete_task,
                            self.close_task,self.open_task,self.get_tasktitle,
                            notes=self.notes)
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
                tags = self.get_selected_tags()[0]
                nonworkview_item = self.tagpopup.get_children()[1]
                nonworkview_item.hide()
                if len(tags) > 0 :
                    tag = tags[0]
                    attri = tag.get_attribute("nonworkview")
                    #We must inverse because the tagstore has True
                    #for tasks that are not in workview
                    if attri == "True" : toset = False
                    else : toset = True
                    nonworkview_item.set_active(toset)
                    nonworkview_item.show()
                else :
                    nonworkview_item.hide()
            return 1
            
    def on_nonworkviewtag_toggled(self,widget) : #pylint: disable-msg=W0613
        tags = self.get_selected_tags()[0]
        nonworkview_item = self.tagpopup.get_children()[1]
        #We must inverse because the tagstore has True
        #for tasks that are not in workview (and also convert to string)
        toset = str(not nonworkview_item.get_active())
        if len(tags) > 0 :
            tags[0].set_attribute("nonworkview",toset)
        self.do_refresh()

    def on_task_treeview_button_press_event(self,treeview,event) :
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo #pylint: disable-msg=W0612
                treeview.grab_focus()
                treeview.set_cursor( path, col, 0)
                self.taskpopup.popup( None, None, None, event.button, time)
            return 1

    def on_closed_task_treeview_button_press_event(self,treeview,event) :
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo #pylint: disable-msg=W0612
                treeview.grab_focus()
                treeview.set_cursor( path, col, 0)
                self.closedtaskpopup.popup( None, None, None, event.button, time)
            return 1
            
    def on_add_task(self,widget,status=None) : #pylint: disable-msg=W0613
        tags,notagonly = self.get_selected_tags() #pylint: disable-msg=W0612
        task = self.req.new_task(tags=tags,newtask=True)
        uid = task.get_id()
        if status :
            task.set_status(status)
        self.open_task(uid)

    def on_add_subtask(self,widget) : #pylint: disable-msg=W0613
        uid = self.get_selected_task()
        if uid :
            zetask = self.req.get_task(uid)    
            tags   = zetask.get_tags()
            task   = self.req.new_task(tags=tags,newtask=True)
            task.add_parent(uid)
            zetask.add_subtask(task.get_id())
            self.open_task(task.get_id())
            self.do_refresh()
    
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
        if selection and selection.count_selected_rows() <= 0 and not tv :
            tview = self.taskdone_tview
            selection = tview.get_selection()
        #Then in the notes pane
        if selection and selection.count_selected_rows() <= 0 and not tv :
            tview = self.note_tview
            selection = tview.get_selection()
        # Get the selection iter
        if selection :
            model, selection_iter = selection.get_selected() #pylint: disable-msg=W0612
            if selection_iter :
                ts = tview.get_model()
                uid = ts.get_value(selection_iter, 0)
        return uid

    def get_selected_tags(self) :
        t_selected = self.tag_tview.get_selection()
        t_iter = None
        if t_selected :
            tmodel, t_iter = t_selected.get_selected() #pylint: disable-msg=W0612
        notag_only = False
        tag = []
        if t_iter :
            selected = self.tag_ts.get_value(t_iter, 0)
            special = selected.get_attribute("special")
            if special == "all" : 
                tag = []
                selected = None
            #notag means we want to display only tasks without any tag
            if special == "notag" :
                notag_only = True
            if not notag_only and selected :
                tag.append(selected)
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
    # 3. If the "elsewhere" from point 1 is deleted, we are sure it's a 
    #    drag-n-drop so we change the parent of the moved task
    def row_dragndrop(self,tree, path, it,data=None) : #pylint: disable-msg=W0613
        if data == "insert" :
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
                    # "row %s will move from %s to %s"%(self.tid_tomove,\
                    #          self.tid_source_parent,self.tid_target_parent)
#    def row_deleted(self,tree,path,data=None) : #pylint: disable-msg=W0613
        elif data == "delete" :
            #If we are removing the path source guessed during the insertion
            #It confirms that we are in a drag-n-drop
            if path in self.drag_sources and self.tid_tomove :
                self.drag_sources.remove(path)
                # "row %s moved from %s to %s"%(self.tid_tomove,\
                #             self.tid_source_parent,self.tid_target_parent)
                tomove = self.req.get_task(self.tid_tomove)
                tomove.set_to_keep()
                tomove.remove_parent(self.tid_source_parent)
                tomove.add_parent(self.tid_target_parent)
                #DO NOT self.refresh_list()
                #Refreshing here make things crash. Don't refresh
                #self.drag_sources = []
                self.path_source = None
                self.path_target = None
                self.tid_tomove = None
                self.tid_source_parent = None
                self.tid_target_parent = None
            
    ###############################
    ##### End of the drag-n-drop part
    ###############################
        
        
    def on_edit_active_task(self,widget,row=None ,col=None) : #pylint: disable-msg=W0613
        tid = self.get_selected_task(self.task_tview)
        if tid :
            self.open_task(tid)
    def on_edit_done_task(self,widget,row=None ,col=None) : #pylint: disable-msg=W0613
        tid = self.get_selected_task(self.taskdone_tview)
        if tid :
            self.open_task(tid)
    def on_edit_note(self,widget,row=None,col=None) : #pylint: disable-msg=W0613
        tid = self.get_selected_task(self.note_tview)
        if tid :
            self.open_task(tid)
     
    #if we pass a tid as a parameter, we delete directly
    #otherwise, we will look which tid is selected   
    def on_delete_confirm(self,widget) : #pylint: disable-msg=W0613
        self.req.delete_task(self.tid_todelete)
        self.tid_todelete = None
        self.do_refresh()
        
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
            self.do_refresh()
    
    def on_dismiss_task(self,widget) : #pylint: disable-msg=W0613
        uid = self.get_selected_task()
        if uid :
            zetask = self.req.get_task(uid)
            status = zetask.get_status() 
            if status == "Dismiss" :
                zetask.set_status("Active")
            else : zetask.set_status("Dismiss")
            self.do_refresh()
        
    def on_select_tag(self, widget, row=None ,col=None) : #pylint: disable-msg=W0613
        #When you clic on a tag, you want to unselect the tasks
        self.task_tview.get_selection().unselect_all()
        self.taskdone_tview.get_selection().unselect_all()
        self.do_refresh()
        #self.do_refresh()

    ##### Useful tools##################

    def __create_tags_tview(self):
         
        # Tag column
        tag_col      = gtk.TreeViewColumn()
        render_text  = gtk.CellRendererText()
        render_count = gtk.CellRendererText()
        render_tags  = CellRendererTags()
        tag_col.set_title             ("Tags")
        tag_col.set_clickable         (False)
        tag_col.pack_start            (render_tags  , expand=False)
        tag_col.set_attributes        (render_tags  , tag=self.TAGS_MODEL_OBJ)
        tag_col.pack_start            (render_text  , expand=True)
        tag_col.set_attributes        (render_text  , markup=self.TAGS_MODEL_NAME)
        tag_col.pack_end              (render_count , expand=False)
        tag_col.set_attributes        (render_count , markup=self.TAGS_MODEL_COUNT)
        render_count.set_property     ("foreground","#888a85")
        render_count.set_property     ('xalign', 1.0)
        render_tags.set_property      ('ypad'  , 3)
        render_text.set_property      ('ypad'  , 3)
        render_count.set_property     ('xpad'  , 3)
        render_count.set_property     ('ypad'  , 3)
        tag_col.set_sort_column_id    (-1)
        tag_col.set_expand            (True)
        self.tag_tview.append_column  (tag_col)
        # Global treeview properties
        self.tag_tview.set_row_separator_func(self.tag_separator_filter)

    def cmp_duedate_str(self, key1, key2):
        if self.priv["tasklist"]["sort_order"] == gtk.SORT_ASCENDING:
            if   key1 == "" and key2 == "" : return  0
            elif key1 == "" and key2 != "" : return -1
            elif key1 != "" and key2 == "" : return  1
            else                           : return cmp(key1,key2)
        else:
            if   key1 == "" and key2 == "" : return  0
            elif key1 == "" and key2 != "" : return  1
            elif key1 != "" and key2 == "" : return -1
            else                           : return cmp(key1,key2)
        
    def sort_tasklist_rows(self, column, sort_order=None):        
        """ Sort the rows based on the given column """
    
        # Extract sorting state
        last_sort_col   = self.priv["tasklist"]["sort_column"]
        last_sort_order = self.priv["tasklist"]["sort_order"]
        
        # Cleanup
        if last_sort_col is not None:
            last_sort_col.set_sort_indicator(False)
    
        # Ascending or descending?
        if sort_order is None:
            if last_sort_col == column:
                if last_sort_order == gtk.SORT_ASCENDING:
                    sort_order = gtk.SORT_DESCENDING
                else:
                    sort_order = gtk.SORT_ASCENDING
            else:
                sort_order = gtk.SORT_DESCENDING

        # Store sorting state
        self.priv["tasklist"]["sort_column"] = column
        self.priv["tasklist"]["sort_order"]  = sort_order

        # Determine row sorting depending on column
        if column == self.priv["tasklist"]["columns"][self.TASKLIST_COL_TITLE]:
            cmp_func = lambda x,y: cmp(x.lower(),y.lower())
            sort_key = lambda x:x[self.TASK_MODEL_TITLE]
        else:
            cmp_func = self.cmp_duedate_str
            sort_key = lambda x:x[self.TASK_MODEL_DDATE_STR]
            
        # Determine sorting direction
        if sort_order == gtk.SORT_ASCENDING: sort_reverse = True
        else                               : sort_reverse = False

        # Sort rows
        rows = [tuple(r) + (i,) for i, r in enumerate(self.task_ts)]
        if len(rows) != 0:
            rows.sort(key=lambda x:x[self.TASK_MODEL_TITLE].lower())
            rows.sort(cmp=cmp_func,key=sort_key,reverse=sort_reverse)
            self.task_ts.reorder(None, [r[-1] for r in rows])
    
        # Display the sort indicator
        column.set_sort_indicator(True)
        column.set_sort_order(sort_order)

    def __create_task_tview(self):
  
        self.priv["tasklist"]["columns"] = []
  
        # Tag column
        self.TASKLIST_COL_TAGS = 0
        tag_col     = gtk.TreeViewColumn()
        render_tags = CellRendererTags()
        tag_col.set_title             ("Tags")
        tag_col.pack_start            (render_tags, expand=False)
        tag_col.add_attribute         (render_tags, "tag_list", self.TASK_MODEL_TAGS)
        render_tags.set_property      ('xalign', 0.0)
        tag_col.set_resizable         (False)
        tag_col.add_attribute         (render_tags, "cell-background", self.TASK_MODEL_BGCOL)
        #tag_col.set_clickable         (True)
        #tag_col.connect               ('clicked', self.sort_tasklist_rows)
        self.task_tview.append_column (tag_col)
        self.priv["tasklist"]["columns"].insert(self.TASKLIST_COL_TAGS, tag_col)
        
        # Title column
        self.TASKLIST_COL_TITLE = 1
        title_col   = gtk.TreeViewColumn()
        render_text = gtk.CellRendererText()
        title_col.set_title           ("Title")
        title_col.pack_start          (render_text, expand=False)
        title_col.add_attribute       (render_text, "markup", self.TASK_MODEL_TITLE_STR)
        title_col.set_resizable       (True)
        title_col.set_expand          (True)
        #The following line seems to fix bug #317469
        #I don't understand why !!! It's voodoo !
        #Is there a Rubber Chicken With a Pulley in the Middle ?
        title_col.set_max_width       (100)
        title_col.add_attribute       (render_text, "cell_background", self.TASK_MODEL_BGCOL)
        title_col.set_clickable       (True)
        title_col.connect             ('clicked', self.sort_tasklist_rows)
        self.task_tview.append_column (title_col)
        self.priv["tasklist"]["columns"].insert(self.TASKLIST_COL_TITLE, title_col)
        
        # Due date column
        self.TASKLIST_COL_DDATE = 2
        ddate_col   = gtk.TreeViewColumn()
        render_text = gtk.CellRendererText()
        ddate_col.set_title           ("Due date")
        ddate_col.pack_start          (render_text, expand=False)
        ddate_col.add_attribute       (render_text, "markup", self.TASK_MODEL_DDATE_STR)
        ddate_col.set_resizable       (False)
        ddate_col.add_attribute       (render_text, "cell_background", self.TASK_MODEL_BGCOL)
        ddate_col.set_clickable       (True)
        ddate_col.connect             ('clicked', self.sort_tasklist_rows)
        self.task_tview.append_column (ddate_col)
        self.priv["tasklist"]["columns"].insert(self.TASKLIST_COL_DDATE, ddate_col)
        
        # days left
        self.TASKLIST_COL_DLEFT = 3
        dleft_col   = gtk.TreeViewColumn()
        render_text = gtk.CellRendererText()
        dleft_col.set_title           ("Days left")
        dleft_col.pack_start          (render_text, expand=False)
        dleft_col.add_attribute       (render_text, "markup", self.TASK_MODEL_DLEFT_STR)
        dleft_col.set_resizable       (False)
        dleft_col.add_attribute       (render_text, "cell_background", self.TASK_MODEL_BGCOL)
        dleft_col.set_clickable       (True)
        dleft_col.connect             ('clicked', self.sort_tasklist_rows)
        self.task_tview.append_column (dleft_col)
        self.priv["tasklist"]["columns"].insert(self.TASKLIST_COL_DLEFT, dleft_col)

        # Global treeview properties
        self.task_tview.set_property   ("expander-column", title_col)
        self.task_tview.set_property   ("enable-tree-lines", False)
        self.task_tview.set_rules_hint (False)

    def __create_closed_tasks_tview(self):

        self.priv["ctasklist"]["columns"] = []

        # Tag column
        self.CTASKLIST_COL_TAGS = 0
        tag_col     = gtk.TreeViewColumn()
        render_tags = CellRendererTags()
        tag_col.set_title             ("Tags")
        tag_col.pack_start            (render_tags, expand=False)
        tag_col.add_attribute         (render_tags, "tag_list", self.CTASKS_MODEL_TAGS)
        render_tags.set_property      ('xalign', 0.0)
        tag_col.set_resizable         (False)
        tag_col.add_attribute         (render_tags, "cell-background", self.CTASKS_MODEL_BGCOL)
        #tag_col.set_clickable         (True)
        #tag_col.connect               ('clicked', self.sort_tasklist_rows)
        self.taskdone_tview.append_column (tag_col)
        self.priv["ctasklist"]["columns"].insert(self.CTASKLIST_COL_TAGS, tag_col)
         
        # Done date column
        self.CTASKLIST_COL_DDATE = 1
        ddate_col    = gtk.TreeViewColumn()
        render_text  = gtk.CellRendererText()
        ddate_col.set_title                ("Closing date")
        ddate_col.pack_start               (render_text  , expand=True)
        ddate_col.set_attributes           (render_text  , markup=self.CTASKS_MODEL_DDATE_STR)
        ddate_col.set_sort_column_id       (self.CTASKS_MODEL_DDATE)
        ddate_col.add_attribute            (render_text, "cell_background", self.CTASKS_MODEL_BGCOL)
        self.taskdone_tview.append_column  (ddate_col)
        self.priv["ctasklist"]["columns"].insert(self.CTASKLIST_COL_DDATE, ddate_col)
                 
        # Title column
        self.CTASKLIST_COL_TITLE = 2
        title_col    = gtk.TreeViewColumn()
        render_text  = gtk.CellRendererText()
        title_col.set_title                ("Title")
        title_col.pack_start               (render_text  , expand=True)
        title_col.set_attributes           (render_text  , markup=self.CTASKS_MODEL_TITLE)
        title_col.set_sort_column_id       (self.CTASKS_MODEL_TITLE)
        title_col.set_expand               (True)
        title_col.add_attribute            (render_text, "cell_background", self.CTASKS_MODEL_BGCOL)
        self.taskdone_tview.append_column  (title_col)
        self.priv["ctasklist"]["columns"].insert(self.CTASKLIST_COL_TITLE, title_col)
        
        # Global treeview properties
        self.taskdone_ts.set_sort_column_id(self.CTASKS_MODEL_DDATE, gtk.SORT_DESCENDING)
        
    def __create_note_tview(self):
        # Title column
        title_col    = gtk.TreeViewColumn()
        render_text  = gtk.CellRendererText()
        title_col.set_title                ("Notes")
        title_col.pack_start               (render_text  , expand=True)
        title_col.set_attributes           (render_text  , markup=self.CTASKS_MODEL_TITLE)
        title_col.set_sort_column_id       (self.CTASKS_MODEL_TITLE)
        title_col.set_expand               (True)
        self.note_tview.append_column  (title_col)

        # Global treeview properties
        #self.taskdone_ts.set_sort_column_id(self.CTASKS_MODEL_DDATE, gtk.SORT_DESCENDING)

       
    ######Closing the window
    def close(self,widget=None) : #pylint: disable-msg=W0613
        #Saving is now done in main.py
        gtk.main_quit()
