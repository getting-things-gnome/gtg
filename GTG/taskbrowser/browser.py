# -*- coding: utf-8 -*-
# pylint: disable-msg=W0201
# -----------------------------------------------------------------------------
# Getting Things Gnome! - a personal organizer for the GNOME desktop
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

""" The main window for GTG, listing tags, and open and closed tasks """

#=== IMPORT ===================================================================
#system imports
import pygtk
pygtk.require('2.0')
import gobject
import os
import gtk
import locale
import re
import time
import webbrowser

#our own imports
import GTG
from GTG import info
from GTG import _
from GTG import ngettext
from GTG.tools.logger                 import Log
from GTG.core.task                    import Task
#from GTG.core.tagstore                import Tag
from GTG.taskbrowser                  import GnomeConfig
from GTG.taskbrowser                  import tasktree
#from GTG.taskbrowser.preferences      import PreferencesDialog
from GTG.taskbrowser.tasktree         import TaskTreeModel,\
                                             ActiveTaskTreeView,\
                                             ClosedTaskTreeView
from GTG.taskbrowser                  import tagtree
from GTG.taskbrowser.tagtree          import TagTreeModel,\
                                             TagTreeView
from GTG.tools                        import openurl
from GTG.tools.dates                  import strtodate,\
                                             no_date,\
                                             FuzzyDate, \
                                             get_canonical_date
#from GTG.tools                        import clipboard

#=== MAIN CLASS ===============================================================

WINDOW_TITLE = "Getting Things GNOME!"
DOCUMENTATION_URL = "http://live.gnome.org/gtg/documentation"

#Some default preferences that we should save in a file
WORKVIEW         = False
SIDEBAR          = False
CLOSED_PANE      = False
QUICKADD_PANE    = True
TOOLBAR          = True
BG_COLOR         = True
CONTENTS_PREVIEW = True
TIME             = 0

class Timer:
    def __init__(self,st):
        self.st = st
    def __enter__(self): self.start = time.time()
    def __exit__(self, *args): 
        print "%s : %s" %(self.st,time.time() - self.start)

class TaskBrowser:
    """ The UI for browsing open and closed tasks, and listing tags in a tree """

    def __init__(self, requester, vmanager, config):
        # Object prime variables
        self.priv   = {}
        self.req    = requester
        self.vmanager = vmanager
        self.config = config
        self.tag_active = False
        
        #treeviews handlers
        self.tags_tv = None
        self.tasks_tv = None
        self.ctask_tv = ClosedTaskTreeView(self.req)
        self.ctask_tree = None

        ### YOU CAN DEFINE YOUR INTERNAL MECHANICS VARIABLES BELOW
        
        # Setup default values for view
        self._init_browser_config()

        # Setup GTG icon theme
        self._init_icon_theme()

        # Set up models
        self._init_models()

        # Load window tree
        self.builder = gtk.Builder() 
        self.builder.add_from_file(GnomeConfig.GLADE_FILE)

        # Define aliases for specific widgets
        self._init_widget_aliases()

        # Init non-glade widgets
        self._init_ui_widget()

        #Set the tooltip for the toolbar buttons
        self._init_toolbar_tooltips()

        # Initialize "About" dialog
        self._init_about_dialog()

        #Create our dictionary and connect it
        self._init_signal_connections()

        # Setting the default for the view
        # When there is no config, this should define the first configuration
        # of the UI
        self._init_view_defaults()

        # Define accelerator keys
        self._init_accelerators()
        
        #Autocompletion for Tags
        self._init_tag_list()
        self._init_tag_completion()
        
        self.restore_state_from_conf()
        self.window.show()

### INIT HELPER FUNCTIONS #####################################################
#
    def _init_browser_config(self):
        self.priv["collapsed_tids"]           = []
        self.priv["collapsed_tags"]           = []
        self.priv["tasklist"]                 = {}
        self.priv["tasklist"]["sort_column"]  = None
        self.priv["tasklist"]["sort_order"]   = gtk.SORT_ASCENDING
        self.priv["ctasklist"]                = {}
        self.priv["ctasklist"]["sort_column"] = None
        self.priv["ctasklist"]["sort_order"]  = gtk.SORT_ASCENDING
        self.priv['selected_rows']            = None
        self.priv['workview']                 = False
        self.priv['filter_cbs']               = []
        self.priv['quick_add_cbs']            = []

    def _init_icon_theme(self):
        icon_dirs = [GTG.DATA_DIR, os.path.join(GTG.DATA_DIR, "icons")]
        for i in icon_dirs:
            gtk.icon_theme_get_default().prepend_search_path(i)
            gtk.window_set_default_icon_name("gtg")

    #FIXME: we should group the initialization by widgets, not by type of methods
    # it should be "init_active_tasks_pane", "init_sidebar", etc.
    def _init_models(self):
        # Active Tasks
        self.req.apply_filter('active')
        self.task_tree_model = TaskTreeModel(self.req, self.priv)
        self.task_modelsort = gtk.TreeModelSort(self.task_tree_model)
        self.task_modelsort.set_sort_func(\
            tasktree.COL_DDATE, self.dleft_sort_func)
        self.task_modelsort.set_sort_func(\
            tasktree.COL_DLEFT, self.dleft_sort_func)

        # Tags
        self.tag_model = TagTreeModel(requester=self.req)
        self.tag_modelfilter = self.tag_model.filter_new()
        self.tag_modelfilter.set_visible_func(self.tag_visible_func)
        self.tag_modelsort = gtk.TreeModelSort(self.tag_modelfilter)
        self.tag_modelsort.set_sort_func(\
            tagtree.COL_ID, self.tag_sort_func)

    def _init_widget_aliases(self):
        self.window             = self.builder.get_object("MainWindow")
        self.tagpopup           = self.builder.get_object("tag_context_menu")
        self.nonworkviewtag_cb  = self.builder.get_object("nonworkviewtag_mi")
        self.taskpopup          = self.builder.get_object("task_context_menu")
        self.defertopopup       = self.builder.get_object("defer_to_context_menu")
        self.ctaskpopup         = self.builder.get_object("closed_task_context_menu")
        self.editbutton         = self.builder.get_object("edit_b")
        self.edit_mi            = self.builder.get_object("edit_mi")
        self.donebutton         = self.builder.get_object("done_b")
        self.done_mi            = self.builder.get_object("done_mi")
        self.deletebutton       = self.builder.get_object("delete_b")
        self.delete_mi          = self.builder.get_object("delete_mi")
        self.newtask            = self.builder.get_object("new_task_b")
        self.newsubtask         = self.builder.get_object("new_subtask_b")
        self.new_subtask_mi     = self.builder.get_object("new_subtask_mi")
        self.dismissbutton      = self.builder.get_object("dismiss_b")
        self.dismiss_mi         = self.builder.get_object("dismiss_mi")
        self.about              = self.builder.get_object("about_dialog")
        self.main_pane          = self.builder.get_object("main_pane")
        self.menu_view_workview = self.builder.get_object("view_workview")
        self.toggle_workview    = self.builder.get_object("workview_toggle")
        self.quickadd_entry     = self.builder.get_object("quickadd_field")
        self.closed_pane        = self.builder.get_object("closed_pane")
        self.toolbar            = self.builder.get_object("task_toolbar")
        self.quickadd_pane      = self.builder.get_object("quickadd_pane")
        self.sidebar            = self.builder.get_object("sidebar_vbox")
        self.sidebar_container  = self.builder.get_object("sidebar-scroll")
        
        self.closed_pane.add(self.ctask_tv)

    def _init_ui_widget(self):
        # The Active tasks treeview
        self.task_tv = ActiveTaskTreeView(self.req)
        self.task_tv.set_model(self.task_modelsort)
        self.main_pane.add(self.task_tv)

        # The tags treeview
        self.tags_tv = TagTreeView()
        self.tags_tv.set_model(self.tag_modelsort)
        self.sidebar_container.add(self.tags_tv)

    def _init_toolbar_tooltips(self):
        self.donebutton.set_tooltip_text(GnomeConfig.MARK_DONE_TOOLTIP)
        self.editbutton.set_tooltip_text(GnomeConfig.EDIT_TOOLTIP)
        self.dismissbutton.set_tooltip_text(GnomeConfig.MARK_DISMISS_TOOLTIP)
        self.newtask.set_tooltip_text(GnomeConfig.NEW_TASK_TOOLTIP)
        self.newsubtask.set_tooltip_text(GnomeConfig.NEW_SUBTASK_TOOLTIP)
        self.toggle_workview.set_tooltip_text(\
            GnomeConfig.WORKVIEW_TOGGLE_TOOLTIP)

    def _init_about_dialog(self):
        gtk.about_dialog_set_url_hook(lambda dialog, url: openurl.openurl(url))
        self.about.set_website(info.URL)
        self.about.set_website_label(info.URL)
        self.about.set_version(info.VERSION)
        self.about.set_authors(info.AUTHORS)
        self.about.set_artists(info.ARTISTS)
        self.about.set_translator_credits(info.TRANSLATORS)

    def _init_signal_connections(self):
        SIGNAL_CONNECTIONS_DIC = {
            "on_add_task":
                self.on_add_task,
            "on_edit_active_task":
                self.on_edit_active_task,
            "on_edit_done_task":
                self.on_edit_done_task,
            "on_delete_task":
                self.on_delete_tasks,
            "on_add_new_tag":
                self.on_add_new_tag,
            "on_mark_as_done":
                self.on_mark_as_done,
            "on_mark_as_started":
                self.on_mark_as_started,
            "on_schedule_for_tomorrow":
                self.on_schedule_for_tomorrow,
            "on_schedule_for_next_week":
                self.on_schedule_for_next_week,
            "on_schedule_for_next_month":
                self.on_schedule_for_next_month,
            "on_schedule_for_next_year":
                self.on_schedule_for_next_year,
            "on_dismiss_task":
                self.on_dismiss_task,
            "on_move":
                self.on_move,
            "on_size_allocate":
                self.on_size_allocate,
            "gtk_main_quit":
                self.on_close,
            "on_addtag_confirm":
                self.on_addtag_confirm,
            "on_addtag_cancel":
                lambda x: x.hide,
            "on_tag_entry_key_press_event":
                self.on_tag_entry_key_press_event,
            "on_add_subtask":
                self.on_add_subtask,
            "on_colorchooser_activate":
                self.on_colorchooser_activate,
            "on_resetcolor_activate":
                self.on_resetcolor_activate,
            "on_tagcontext_deactivate":
                self.on_tagcontext_deactivate,
            "on_workview_toggled":
                self.on_workview_toggled,
            "on_view_workview_toggled":
                self.on_workview_toggled,
            "on_view_closed_toggled":
                self.on_closed_toggled,
            "on_view_sidebar_toggled":
                self.on_sidebar_toggled,
            "on_bg_color_toggled":
                self.on_bg_color_toggled,
            "on_quickadd_field_activate":
                self.on_quickadd_activate,
            "on_quickadd_button_activate":
                self.on_quickadd_activate,
            "on_view_quickadd_toggled":
                self.on_toggle_quickadd,
            "on_view_toolbar_toggled":
                self.on_toolbar_toggled,
            "on_about_clicked":
                self.on_about_clicked,
            "on_about_delete":
                self.on_about_close,
            "on_about_close":
                self.on_about_close,
            "on_documentation_clicked":
                self.on_documentation_clicked,
            "on_nonworkviewtag_toggled":
                self.on_nonworkviewtag_toggled,
            "on_preferences_activate":
                self.open_preferences,
        }
        self.builder.connect_signals(SIGNAL_CONNECTIONS_DIC)

        if (self.window):
            self.window.connect("destroy", self.quit)
            #The following is needed to let the Notification Area plugin to
            # minimize the window instead of closing the program
            self.delete_event_handle = \
                    self.window.connect("delete-event", self.on_delete)

        # Active tasks TreeView
        self.task_tv.connect('row-activated',\
            self.on_edit_active_task)
        self.task_tv.connect('button-press-event',\
            self.on_task_treeview_button_press_event)
        self.task_tv.connect('key-press-event',\
            self.on_task_treeview_key_press_event)
        self.task_tv.connect('row-expanded',\
            self.on_task_treeview_row_expanded)
        self.task_tv.connect('row-collapsed',\
            self.on_task_treeview_row_collapsed)

        # Closed tasks TreeView
        self.ctask_tv.connect('row-activated',\
            self.on_edit_done_task)
        self.ctask_tv.connect('button-press-event',\
            self.on_closed_task_treeview_button_press_event)
        self.ctask_tv.connect('key-press-event',\
            self.on_closed_task_treeview_key_press_event)

        # Tags TreeView
        self.tags_tv.connect('cursor-changed',\
            self.on_select_tag)
        self.tags_tv.connect('row-activated',\
            self.on_select_tag)
        self.tags_tv.connect('button-press-event',\
            self.on_tag_treeview_button_press_event)
        self.tags_tv.connect('row-expanded',\
            self.on_tag_treeview_row_expanded)
        self.tags_tv.connect('row-collapsed',\
            self.on_tag_treeview_row_collapsed)

        # Connect requester signals to TreeModels
        self.req.connect("task-added", self.on_task_added) 
        self.req.connect("task-deleted", self.on_task_deleted)
        
        # Connect signals from models
        self.task_modelsort.connect("row-has-child-toggled",\
                                    self.on_task_child_toggled)
        self.tag_modelsort.connect("row-has-child-toggled",\
                                    self.on_tag_child_toggled)
        # Selection changes
        self.selection = self.task_tv.get_selection()
        self.closed_selection = self.ctask_tv.get_selection()
        self.selection.connect("changed", self.on_task_cursor_changed)
        self.closed_selection.connect("changed", self.on_taskdone_cursor_changed)
        self.req.connect("task-deleted", self.update_buttons_sensitivity)

    def _init_view_defaults(self):
        self.menu_view_workview.set_active(WORKVIEW)
        self.builder.get_object("view_sidebar").set_active(SIDEBAR)
        self.builder.get_object("view_closed").set_active(CLOSED_PANE)
        self.builder.get_object("view_quickadd").set_active(QUICKADD_PANE)
        self.builder.get_object("view_toolbar").set_active(TOOLBAR)
        self.priv["bg_color_enable"] = BG_COLOR
        self.priv["contents_preview_enable"] = CONTENTS_PREVIEW
        # Set sorting order
        self.task_modelsort.set_sort_column_id(\
            tasktree.COL_DLEFT, gtk.SORT_ASCENDING)
        self.tag_modelsort.set_sort_column_id(\
            tagtree.COL_ID, gtk.SORT_ASCENDING)

    def _add_accelerator_for_widget(self, agr, name, accel):
        widget    = self.builder.get_object(name)
        key, mod  = gtk.accelerator_parse(accel)
        widget.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)

    def _init_accelerators(self):
        agr = gtk.AccelGroup()
        self.builder.get_object("MainWindow").add_accel_group(agr)

        self._add_accelerator_for_widget(agr, "view_sidebar",   "F9")
        self._add_accelerator_for_widget(agr, "file_quit",      "<Control>q")
        self._add_accelerator_for_widget(agr, "edit_undo",      "<Control>z")
        self._add_accelerator_for_widget(agr, "edit_redo",      "<Control>y")
        self._add_accelerator_for_widget(agr, "new_task_mi",    "<Control>n")
        self._add_accelerator_for_widget(agr, "new_subtask_mi", "<Control><Shift>n")
        self._add_accelerator_for_widget(agr, "done_mi",        "<Control>d")
        self._add_accelerator_for_widget(agr, "dismiss_mi",     "<Control>i")
        self._add_accelerator_for_widget(agr, "delete_mi",      "Cancel")
        self._add_accelerator_for_widget(agr, "tcm_addtag",     "<Control>t")
        self._add_accelerator_for_widget(agr, "view_closed",    "<Control>F9")

        edit_button = self.builder.get_object("edit_b")
        key, mod    = gtk.accelerator_parse("<Control>e")
        edit_button.add_accelerator("clicked", agr, key, mod, gtk.ACCEL_VISIBLE)

        quickadd_field = self.builder.get_object("quickadd_field")
        key, mod = gtk.accelerator_parse("<Control>l")
        quickadd_field.add_accelerator("grab-focus", agr, key, mod, gtk.ACCEL_VISIBLE)

    def _init_tag_list(self):
        self.tag_list_model = gtk.ListStore(gobject.TYPE_STRING)
        self.tag_list = self.req.get_all_tags()
        for i in self.tag_list:
            self.tag_list_model.append([i.get_name()[1:]])
               
    def _init_tag_completion(self):
        #Initialize tag completion.
        self.tag_completion = gtk.EntryCompletion()
        self.tag_completion.set_model(self.tag_list_model)
        self.tag_completion.set_text_column(0)
        self.tag_completion.set_match_func(self.tag_match_func, 0)
        self.tag_completion.set_inline_completion(True)
        self.tag_completion.set_inline_selection(True)
        self.tag_completion.set_popup_single_match(False)

### HELPER FUNCTIONS ########################################################

    def open_preferences(self,widget):
        self.vmanager.show_preferences(self.priv)
        
    def quit(self,widget=None):
        self.vmanager.close_browser()
        
    def restore_state_from_conf(self):

        # Extract state from configuration dictionary
        if not "browser" in self.config:
            #necessary to have the minimum width of the tag pane
            # inferior to the "first run" width
            self.builder.get_object("hpaned1").set_position(250)
            return

        if ("width" in self.config["browser"] and
            "height" in self.config["browser"]):
            width = int(self.config["browser"]["width"])
            height = int(self.config["browser"]["height"])
            self.window.resize(width, height)

        if ("x_pos" in self.config["browser"] and
            "y_pos" in self.config["browser"]):

            xpos = int(self.config["browser"]["x_pos"])
            ypos = int(self.config["browser"]["y_pos"])
            self.window.move(xpos, ypos)

        if "tag_pane" in self.config["browser"]:
            tag_pane = eval(self.config["browser"]["tag_pane"])
            if not tag_pane:
                self.builder.get_object("view_sidebar").set_active(False)
                self.sidebar.hide()
            else:
                self.builder.get_object("view_sidebar").set_active(True)
                self.sidebar.show()

        if "tag_pane_width" in self.config["browser"]:
            tag_pane_width = int(self.config["browser"]["tag_pane_width"])
            self.builder.get_object("hpaned1").set_position(tag_pane_width)

        if "closed_task_pane" in self.config["browser"]:
            closed_task_pane = eval(
                self.config["browser"]["closed_task_pane"])
            if not closed_task_pane:
                self.hide_closed_pane()
            else:
                self.show_closed_pane()

        if "ctask_pane_height" in self.config["browser"]:
            ctask_pane_height = eval(
                self.config["browser"]["ctask_pane_height"])
            self.builder.get_object("vpaned1").set_position(ctask_pane_height)

        if "toolbar" in self.config["browser"]:
            toolbar = eval(self.config["browser"]["toolbar"])
            if not toolbar:
                self.toolbar.hide()
                self.builder.get_object("view_toolbar").set_active(False)

        if "quick_add" in self.config["browser"]:
            quickadd_pane = eval(self.config["browser"]["quick_add"])
            if not quickadd_pane:
                self.quickadd_pane.hide()
                self.builder.get_object("view_quickadd").set_active(False)

        if "bg_color_enable" in self.config["browser"]:
            bgcol_enable = eval(self.config["browser"]["bg_color_enable"])
            self.priv["bg_color_enable"] = bgcol_enable
            self.builder.get_object("bgcol_enable").set_active(bgcol_enable)

        if "contents_preview_enable" in self.config["browser"]:
            self.priv["contents_preview_enable"] = \
                    eval(self.config["browser"]["contents_preview_enable"])
        
        if "collapsed_tasks" in self.config["browser"]:
            self.priv["collapsed_tids"] = self.config[
                "browser"]["collapsed_tasks"]
                
        if "collapsed_tags" in self.config["browser"]:
            self.priv["collapsed_tags"] = self.config[
                "browser"]["collapsed_tags"]

        if "tasklist_sort" in self.config["browser"]:
            col_id, order = self.config["browser"]["tasklist_sort"]
            self.priv["sort_column"] = col_id
            try:
                col_id, order = int(col_id), int(order)
                self.priv["tasklist"]["sort_column"] = col_id
                if order == 0:
                    self.priv["tasklist"]["sort_order"] = gtk.SORT_ASCENDING
                if order == 1:
                    self.priv["tasklist"]["sort_order"] = gtk.SORT_DESCENDING
                self.task_modelsort.set_sort_column_id(\
                    col_id,\
                    self.priv["tasklist"]["sort_order"])
            except:
                print "Invalid configuration for sorting columns"

        if "view" in self.config["browser"]:
            view = self.config["browser"]["view"]
            if view == "workview":
                self.do_toggle_workview()
                
        if self._start_gtg_maximized() and \
           "opened_tasks" in self.config["browser"]:
            odic = self.config["browser"]["opened_tasks"]
            #odic can contain also "None" or "None,", so we skip them
            if odic == "None" or (len(odic)> 0 and odic[0] == "None"):
                return
            for t in odic:
                ted = self.vmanager.open_task(t)

    
    def _start_gtg_maximized(self):
        #This is needed as a hook point to let the Notification are plugin
        #start gtg minimized
        return True

    def do_toggle_workview(self):
        #We have to be careful here to avoid a loop of signals
        #menu_state   = self.menu_view_workview.get_active()
        #button_state = self.toggle_workview.get_active()
        #We do something only if both widget are in different state
        tobeset = not self.priv['workview']
        self.menu_view_workview.set_active(tobeset)
        self.toggle_workview.set_active(tobeset)
        self.priv['workview'] = tobeset
        self.tag_model.set_workview(self.priv['workview'])
        if tobeset:
            self.req.apply_filter('workview')
        else:
            self.req.unapply_filter('workview')
        self.tag_modelfilter.refilter()
        self._update_window_title()

    def _update_window_title(self):
        count = self.req.get_main_n_tasks()
        #Set the title of the window:
        parenthesis = ""
        if count == 0:
            parenthesis = _("no active tasks")
        else:
            parenthesis = ngettext("%(tasks)d active task", \
                                   "%(tasks)d active tasks", \
                                   count) % {'tasks': count}
        self.window.set_title("%s - "%parenthesis + WINDOW_TITLE)


    def get_tasktitle(self, tid):
        task = self.req.get_task(tid)
        return task.get_title()

    def tag_visible_func(self, model, iter, user_data=None):
        """Return True if the row must be displayed in the treeview.
        @param model: the model of the filtered treeview
        @param iter: the iter whose visiblity must be evaluated
        @param user_data:
        """
        tag = model.get_value(iter, tagtree.COL_OBJ)
        
        # show the tag if any children are shown
        child = model.iter_children(iter)
        while child:
            if self.tag_visible_func(model, child):
                return True
            child=model.iter_next(child)
        
        if not tag.get_attribute("special"):
            #Those two lines hide tags without tasks in the workview
            count = model.get_value(iter, tagtree.COL_COUNT)
            return count != '0'
            #the following display tags in the workview, even with 0 tasks
           # return tag.is_actively_used()
        else:
            return True

    def dleft_sort_func(self, model, iter1, iter2, user_data=None):
        order = self.task_modelsort.get_sort_column_id()[1]
        task1 = model.get_value(iter1, tasktree.COL_OBJ)
        task2 = model.get_value(iter2, tasktree.COL_OBJ)
        if task1 and task2:
            t1_dleft = task1.get_due_date()
            t2_dleft = task2.get_due_date()
            sort = cmp(t2_dleft, t1_dleft)
        else:
            sort = -1
        
        #sort = 0
        
        def reverse_if_descending(s):
            """Make a cmp() result relative to the top instead of following 
               user-specified sort direction"""
            if order == gtk.SORT_ASCENDING:
                return s
            else:
                return -1 * s
        
        
        
        if sort == 0:
            # Put fuzzy dates below real dates
            if isinstance(t1_dleft, FuzzyDate) and not isinstance(t2_dleft, FuzzyDate):
                sort = reverse_if_descending(1)
            elif isinstance(t2_dleft, FuzzyDate) and not isinstance(t1_dleft, FuzzyDate):
                sort = reverse_if_descending(-1)
        
        if sort == 0: # Group tasks with the same tag together for visual cleanness 
            t1_tags = task1.get_tags_name()
            t1_tags.sort()
            t2_tags = task2.get_tags_name()
            t2_tags.sort()
            sort = reverse_if_descending(cmp(t1_tags, t2_tags))
            
        if sort == 0:  # Break ties by sorting by title
            t1_title = task1.get_title()
            t2_title = task2.get_title()
            t1_title = locale.strxfrm(t1_title)
            t2_title = locale.strxfrm(t2_title)
            sort = reverse_if_descending(cmp(t1_title, t2_title))
                
        return sort

    def tag_sort_func(self, model, iter1, iter2, user_data=None):
        order = self.tags_tv.get_model().get_sort_column_id()[1]
        try:
            t1 = model.get_value(iter1, tagtree.COL_OBJ)
            t2 = model.get_value(iter2, tagtree.COL_OBJ)
        except TypeError:
            print "Error: Undefined iter1 in tag_sort_func, assuming ascending sort"
            return 1
        t1_sp = t1.get_attribute("special")
        t2_sp = t2.get_attribute("special")
        t1_name = locale.strxfrm(t1.get_name())
        t2_name = locale.strxfrm(t2.get_name())
        if not t1_sp and not t2_sp:
            return cmp(t1_name, t2_name)
        elif not t1_sp and t2_sp:
            if order == gtk.SORT_ASCENDING:
                return 1
            else:
                return -1
        elif t1_sp and not t2_sp:
            if order == gtk.SORT_ASCENDING:
                return -1
            else:
                return 1
        else:
            t1_order = t1.get_attribute("order")
            t2_order = t2.get_attribute("order")
            if order == gtk.SORT_ASCENDING:
                return cmp(t1_order, t2_order)
            else:
                return cmp(t2_order, t1_order)
                
    def tag_match_func(self, completion, key, iter, column):
        model = completion.get_model()
        text = model.get_value(iter, column)
        if text:
            # key is lowercase regardless of input, so text should be
            # lowercase as well, otherwise we leave out all tags beginning
            # with an uppercase letter.
            text = text.lower()
            # Exclude the special tags.
            if text == "tg-tags-all" or text == "tg-tags-sep" or \
               text =="tg-tags-none":
                return False
            # Are we typing the first letters of a tag?
            elif text.startswith(key):
                return True
            else:
                return False          
            
    def tag_list_refresh(self):
        taglist = self.req.get_all_tags()
        if not taglist == self.tag_list:
            for i in taglist:
                if i not in self.tag_list:
                    self.tag_list_model.append([i.get_name()[1:]])
            self.tag_list = taglist

### SIGNAL CALLBACKS ##########################################################
# Typically, reaction to user input & interactions with the GUI
#
    def register_filter_callback(self, cb):
        if cb not in self.priv['filter_cbs']:
            self.priv['filter_cbs'].append(cb)
        
    def unregister_filter_callback(self, cb):
        if cb in self.priv['filter_cbs']:
            self.priv['filter_cbs'].remove(cb)
        
    def on_move(self, widget = None, data = None):
        xpos, ypos = self.window.get_position()
        self.priv["window_xpos"] = xpos
        self.priv["window_ypos"] = ypos

    def on_size_allocate(self, widget = None, data = None):
        width, height = self.window.get_size()
        self.priv["window_width"]  = width
        self.priv["window_height"] = height

    def on_delete(self, widget, user_data):
        # Cleanup collapsed row list
        for tid in self.priv["collapsed_tids"]:
            if not self.req.has_task(tid):
                self.priv["collapsed_tids"].remove(tid)

        # Get configuration values
        tag_sidebar        = self.sidebar.get_property("visible")
        tag_sidebar_width  = self.builder.get_object("hpaned1").get_position()
        closed_pane        = self.closed_pane.get_property("visible")
        quickadd_pane      = self.quickadd_pane.get_property("visible")
        toolbar            = self.toolbar.get_property("visible")
        #task_tv_sort_id    = self.task_ts.get_sort_column_id()
        sort_column, sort_order = self.task_modelsort.get_sort_column_id()
        closed_pane_height = self.builder.get_object("vpaned1").get_position()

        if self.priv['workview']:
            view = "workview"
        else:
            view = "default"

        # Populate configuration dictionary
        self.config["browser"] = {
            'width':
                self.priv["window_width"],
            'height':
                self.priv["window_height"],
            'x_pos':
                self.priv["window_xpos"],
            'y_pos':
                self.priv["window_ypos"],
            'bg_color_enable':
                self.priv["bg_color_enable"],
            'contents_preview_enable':
                self.priv["contents_preview_enable"],
            'collapsed_tasks':
                self.priv["collapsed_tids"],
            'collapsed_tags':
                self.priv["collapsed_tags"],
            'tag_pane':
                tag_sidebar,
            'tag_pane_width':
                tag_sidebar_width,
            'closed_task_pane':
                closed_pane,
            'ctask_pane_height':
                closed_pane_height,
            'toolbar':
                toolbar,
            'quick_add':
                quickadd_pane,
            'view':
                view,
            }
        if   sort_column is not None and sort_order == gtk.SORT_ASCENDING:
            self.config["browser"]["tasklist_sort"]  = [sort_column, 0]
        elif sort_column is not None and sort_order == gtk.SORT_DESCENDING:
            self.config["browser"]["tasklist_sort"]  = [sort_column, 1]
        self.config["browser"]["view"] = view

    def on_about_clicked(self, widget):
        self.about.show()

    def on_about_close(self, widget, response):
        self.about.hide()
        return True

    def on_documentation_clicked(self, widget):
        webbrowser.open(DOCUMENTATION_URL)

    def on_color_changed(self, widget):
        gtkcolor = widget.get_current_color()
        strcolor = gtk.color_selection_palette_to_string([gtkcolor])
        tags, notag_only = self.get_selected_tags()
        for t in tags:
            t.set_attribute("color", strcolor)
        self.task_tv.refresh()
        self.tags_tv.refresh()

    def on_colorchooser_activate(self, widget):
        #TODO: Color chooser should be refactorized in its own class. Well, in
        #fact we should have a TagPropertiesEditor (like for project) Also,
        #color change should be immediate. There's no reason for a Ok/Cancel
        self.set_target_cursor()
        color_dialog = gtk.ColorSelectionDialog('Choose color')
        colorsel = color_dialog.colorsel
        colorsel.connect("color_changed", self.on_color_changed)

        # Get previous color
        tags, notag_only = self.get_selected_tags()
        init_color = None
        if len(tags) == 1:
            color = tags[0].get_attribute("color")
            if color != None:
                colorspec = gtk.gdk.color_parse(color)
                colorsel.set_previous_color(colorspec)
                colorsel.set_current_color(colorspec)
                init_color = colorsel.get_current_color()
        response = color_dialog.run()
        # Check response and set color if required
        if response != gtk.RESPONSE_OK and init_color:
            strcolor = gtk.color_selection_palette_to_string([init_color])
            tags, notag_only = self.get_selected_tags()
            for t in tags:
                t.set_attribute("color", strcolor)
        self.reset_cursor()
        self.task_tv.refresh()
        color_dialog.destroy()
        
    def on_resetcolor_activate(self, widget):
        self.set_target_cursor()
        tags, notag_only = self.get_selected_tags()
        for t in tags:
            t.del_attribute("color")
        self.reset_cursor()
        self.task_tv.refresh()
        self.tags_tv.refresh()
        
    def on_tagcontext_deactivate(self, menushell):
        self.reset_cursor()

    def on_workview_toggled(self, widget):
        self.do_toggle_workview()

    def on_sidebar_toggled(self, widget):
        view_sidebar = self.builder.get_object("view_sidebar")
        if self.sidebar.get_property("visible"):
            view_sidebar.set_active(False)
            self.sidebar.hide()
        else:
            view_sidebar.set_active(True)
            self.sidebar.show()

    def on_closed_toggled(self, widget):
        if widget.get_active():
            self.show_closed_pane()
        else:
            self.hide_closed_pane()
            
    def show_closed_pane(self):
        # The done/dismissed taks treeview
        self.ctask_tree = self.req.get_custom_tasks_tree()
        self.ctask_tree.apply_filter('closed')
        ctask_tree_model = TaskTreeModel(self.req, self.priv, \
                                         self.ctask_tree)
        ctask_modelsort = gtk.TreeModelSort(ctask_tree_model)
        self.ctask_tv.set_model(ctask_modelsort)
        ctask_modelsort.set_sort_column_id(\
            tasktree.COL_CDATE, gtk.SORT_DESCENDING)
        self.closed_pane.show()
        self.builder.get_object("view_closed").set_active(True)

    def hide_closed_pane(self):
        self.closed_pane.hide()
        self.ctask_tv.set_model(None)
        self.ctask_tree = None
        self.builder.get_object("view_closed").set_active(False)

    def on_bg_color_toggled(self, widget):
        if widget.get_active():
            self.priv["bg_color_enable"] = True
            self.task_tv.set_bg_color(True)
            self.ctask_tv.set_bg_color(True)
        else:
            self.priv["bg_color_enable"] = False
            self.task_tv.set_bg_color(False)
            self.ctask_tv.set_bg_color(False)

    def on_toolbar_toggled(self, widget):
        if widget.get_active():
            self.toolbar.show()
        else:
            self.toolbar.hide()

    def on_toggle_quickadd(self, widget):
        if widget.get_active():
            self.quickadd_pane.show()
        else:
            self.quickadd_pane.hide()

    def on_task_child_toggled(self, model, path, iter):
        tid = model.get_value(iter, tasktree.COL_TID)
        if tid not in self.priv.get("collapsed_tids", []):
            self.task_tv.expand_row(path, False)
        else:
            self.task_tv.collapse_row(path)

    def on_task_treeview_row_expanded(self, treeview, iter, path):
        tid = treeview.get_model().get_value(iter, tasktree.COL_TID)
        if tid in self.priv["collapsed_tids"]:
            self.priv["collapsed_tids"].remove(tid)
        
    def on_task_treeview_row_collapsed(self, treeview, iter, path):
        tid = treeview.get_model().get_value(iter, tasktree.COL_TID)
        if tid not in self.priv["collapsed_tids"]:
            self.priv["collapsed_tids"].append(tid)

    def on_tag_child_toggled(self, model, path, iter):
        tag = model.get_value(iter, tagtree.COL_ID)
        if tag not in self.priv.get("collapsed_tags", []):
            self.tags_tv.expand_row(path, False)
        else:
            self.tags_tv.collapse_row(path)
            
    def on_tag_treeview_row_expanded(self, treeview, iter, path):
        tag = treeview.get_model().get_value(iter, tagtree.COL_ID)
        if tag in self.priv["collapsed_tags"]:
            self.priv["collapsed_tags"].remove(tag)
        
    def on_tag_treeview_row_collapsed(self, treeview, iter, path):
        tag = treeview.get_model().get_value(iter, tagtree.COL_ID)
        if tag not in self.priv["collapsed_tags"]:
            self.priv["collapsed_tags"].append(tag)

    def on_quickadd_activate(self, widget):
        text = self.quickadd_entry.get_text()
        due_date = no_date
        defer_date = no_date
        if text:
            tags, notagonly = self.get_selected_tags()
            # Get tags in the title
            #NOTE: the ?: tells regexp that the first one is 
            # a non-capturing group, so it must not be returned
            # to findall. http://www.amk.ca/python/howto/regex/regex.html
            # ~~~~Invernizzi
            for match in re.findall(r'(?:^|[\s])(@\w+)', text):
                tags.append(GTG.core.tagstore.Tag(match))
                # Remove the @
                #text =text.replace(match,match[1:],1)
            # Get attributes
            regexp = r'([\s]*)([\w-]+):([^\s]+)'
            for spaces, attribute, args in re.findall(regexp, text):
                valid_attribute = True
                if attribute.lower() in ["tags", "tag"] or \
                   attribute.lower() in [_("tags"), _("tag")]:
                    for tag in args.split(","):
                        if not tag.startswith("@") :
                            tag = "@"+tag
                        tags.append(GTG.core.tagstore.Tag(tag))
                elif attribute.lower() == "defer" or \
                     attribute.lower() == _("defer"):
                    defer_date = get_canonical_date(args)
                    if not defer_date:
                        valid_attribute = False
                elif attribute.lower() == "due" or \
                     attribute.lower() == _("due"):
                    due_date = get_canonical_date(args)
                    if not due_date:
                        valid_attribute = False
                else:
                    # attribute is unknown
                    valid_attribute = False
                if valid_attribute:
                    # if the command is valid we have to remove it
                    # from the task title
                    text = \
                        text.replace("%s%s:%s" % (spaces, attribute, args), "")
            # Create the new task
            task = self.req.new_task(tags=[t.get_name() for t in tags], newtask=True)
            if text != "":
                task.set_title(text.strip())
                task.set_to_keep()
            task.set_due_date(due_date)
            task.set_start_date(defer_date)
            id_toselect = task.get_id()
            self.quickadd_entry.set_text('')
            # Refresh the treeview
            #self.do_refresh(toselect=id_toselect)
            for f in self.priv['quick_add_cbs']:
                f(task)

    def on_tag_treeview_button_press_event(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo #pylint: disable-msg=W0612
                treeview.grab_focus()
                # The location we want the cursor to return to 
                # after we're done.
                self.previous_cursor = treeview.get_cursor()
                # For use in is_task_visible
                self.previous_tag = self.get_selected_tags()
                # Let's us know that we're working on a tag.
                self.tag_active = True

                # This location is stored in case we need to work with it
                # later on.
                self.target_cursor = path, col
                treeview.set_cursor(path, col, 0)
                selected_tags = self.get_selected_tags()[0]
                if len(selected_tags) > 0:
                    # Then we are looking at single, normal tag rather than
                    # the special 'All tags' or 'Tasks without tags'. We only
                    # want to popup the menu for normal tags.

                    display_in_workview_item = self.tagpopup.get_children()[2]
                    selected_tag = selected_tags[0]
                    nonworkview = selected_tag.get_attribute("nonworkview")
                    # We must invert because the tagstore has "True" for tasks
                    # that are *not* in workview, and the checkbox is set if
                    # the tag *is* shown in the workview.
                    if nonworkview == "True":
                        shown = False
                    else:
                        shown = True
                    # HACK: CheckMenuItem.set_active() emits a toggled() when 
                    # switching between True and False, which will reset 
                    # the cursor. Using self.dont_reset to work around that.
                    # Calling set_target_cursor after set_active() is another
                    # option, but there's noticeable amount of lag when right
                    # clicking tags that way.
                    self.dont_reset = True
                    display_in_workview_item.set_active(shown)
                    self.dont_reset = False
                    self.tagpopup.popup(None, None, None, event.button, time)
                else:
                    self.reset_cursor()
            return 1

    def on_nonworkviewtag_toggled(self, widget):
        self.set_target_cursor()
        tags = self.get_selected_tags()[0]
        #We must inverse because the tagstore has True
        #for tasks that are not in workview (and also convert to string)
        toset = str(not self.nonworkview_cb.get_active())
        if len(tags) > 0:
            tags[0].set_attribute("nonworkview", toset)
        if self.priv['workview']:
            self.tag_modelfilter.refilter()
        if not self.dont_reset:
            self.reset_cursor()

    def on_task_treeview_button_press_event(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                if treeview.get_selection().count_selected_rows() <= 0:
                    path, col, cellx, celly = pthinfo
                    treeview.set_cursor(path, col, 0)
                treeview.grab_focus()
                self.taskpopup.popup(None, None, None, event.button, time)
            return 1

    def on_task_treeview_key_press_event(self, treeview, event):
        if gtk.gdk.keyval_name(event.keyval) == "Delete":
            self.on_delete_tasks()

    def on_closed_task_treeview_button_press_event(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor(path, col, 0)
                self.ctaskpopup.popup(None, None, None, event.button, time)
            return 1

    def on_closed_task_treeview_key_press_event(self, treeview, event):
        if gtk.gdk.keyval_name(event.keyval) == "Delete":
            self.on_delete_tasks()

    def on_add_task(self, widget, status=None):
        tags, notagonly = self.get_selected_tags()
        task = self.req.new_task(tags=[t.get_name() for t in tags], newtask=True)
        uid = task.get_id()
        if status:
            task.set_status(status)
        self.vmanager.open_task(uid,thisisnew=True)

    def on_add_subtask(self, widget):
        uid = self.get_selected_task()
        if uid:
            zetask = self.req.get_task(uid)
            tags   = zetask.get_tags()
            task   = self.req.new_task(tags=[t.get_name() for t in tags], newtask=True)
            #task.add_parent(uid)
            zetask.add_child(task.get_id())
            self.vmanager.open_task(task.get_id(),thisisnew=True)
            #self.do_refresh()

    def on_edit_active_task(self, widget, row=None, col=None):
        tid = self.get_selected_task()
        if tid:
            self.vmanager.open_task(tid)

    def on_edit_done_task(self, widget, row=None, col=None):
        tid = self.get_selected_task(self.ctask_tv)
        if tid:
            self.vmanager.open_task(tid)

    def on_delete_tasks(self, widget=None, tid=None):
        #If we don't have a parameter, then take the selection in the treeview
        if not tid:
            #tid_to_delete is a [project,task] tuple
            tids_todelete = self.get_selected_tasks()
        else:
            tids_todelete = [tid]
        Log.debug("going to delete %s" % tids_todelete)
        self.vmanager.ask_delete_tasks(tids_todelete)

    def update_start_date(self, widget, new_start_date):
        tasks_uid = filter(lambda uid: uid != None, self.get_selected_tasks())
        if len(tasks_uid) == 0:
            return
        tasks = [self.req.get_task(uid) for uid in tasks_uid]
        tasks_status = [task.get_status() for task in tasks]
        for uid, task, status in zip(tasks_uid, tasks, tasks_status):
            task.set_start_date(get_canonical_date(new_start_date))
        #FIXME: If the task dialog is displayed, refresh its start_date widget

    def on_mark_as_started(self, widget):
        self.update_start_date(widget, "today")

    def on_schedule_for_tomorrow(self, widget):
        self.update_start_date(widget, "tomorrow")

    def on_schedule_for_next_week(self, widget):
        self.update_start_date(widget, "next week")

    def on_schedule_for_next_month(self, widget):
        self.update_start_date(widget, "next month")

    def on_schedule_for_next_year(self, widget):
        self.update_start_date(widget, "next year")

    def on_add_new_tag(self, widget=None, tid=None, tryagain = False):
        if not tid:
            self.tids_to_addtag = self.get_selected_tasks()
        else:
            self.tids_to_addtag = [tid]

        if not self.tids_to_addtag == [None]:
            tag_entry = self.builder.get_object("tag_entry")
            apply_to_subtasks = self.builder.get_object("apply_to_subtasks")
            # We don't want to reset the text entry and checkbox if we got
            # sent back here after a warning.
            if not tryagain:
                tag_entry.set_text("NewTag")
                apply_to_subtasks.set_active(False)
                tag_entry.set_completion(self.tag_completion)
            tag_entry.grab_focus()
            addtag_dialog = self.builder.get_object("addtag_dialog")
            addtag_dialog.run()
            addtag_dialog.hide()
            self.tids_to_addtag = None            
        else:
            return False
    
    def on_addtag_confirm(self, widget):
        tag_entry = self.builder.get_object("tag_entry")
        addtag_dialog = self.builder.get_object("addtag_dialog")
        apply_to_subtasks = self.builder.get_object("apply_to_subtasks")
        addtag_error = False
        entry_text = tag_entry.get_text()
        entry_text = [entry_text.strip()]
        # Set up a warning message if the user leaves the text entry empty.
        if not entry_text[0]:
            error_message = "Please enter a tag name."
            addtag_error = True
 
        new_tags = []
        if "," in entry_text[0]:
            entry_text = entry_text[0].split(",")
        # Remove extraneous whitespace, make sure none of the tags contain
        # spaces, and, finally, place a "@" symbol in front of the tagname.
        for tagname in entry_text:
            tagname = tagname.strip()
            if not addtag_error:
                if " " in tagname:
                    error_message = "Tag name must not contain spaces."
                    addtag_error = True
                    break
            new_tags.append("@" + tagname)
        # If we ran into a problem earlier, let us know, and then
        # let us try again.
        if addtag_error:
            error_dialog = gtk.MessageDialog(None, 0, gtk.MESSAGE_WARNING, \
                                            gtk.BUTTONS_OK, error_message)
            if error_dialog.run():
                error_dialog.destroy()
                self.on_add_new_tag(tryagain = True)
                return
        # If the checkbox is checked, add all the subtasks to the list of
        # tasks to add.
        if apply_to_subtasks.get_active():
            for tid in self.tids_to_addtag:
                task = self.req.get_task(tid)
                for i in task.get_self_and_all_subtasks():
                    taskid = i.get_id()
                    if taskid not in self.tids_to_addtag: 
                        self.tids_to_addtag.append(taskid)        
        
        for tid in self.tids_to_addtag:
            task = self.req.get_task(tid)
            for new_tag in new_tags:
                task.add_tag(new_tag)
            task.sync()
      
    def on_tag_entry_key_press_event(self, widget, event):
        if gtk.gdk.keyval_name(event.keyval) == "Return":
            self.on_addtag_confirm()
    
    def on_mark_as_done(self, widget):
        tasks_uid = filter(lambda uid: uid != None, self.get_selected_tasks())
        if len(tasks_uid) == 0:
            return
        tasks = [self.req.get_task(uid) for uid in tasks_uid]
        tasks_status = [task.get_status() for task in tasks]
        for uid, task, status in zip(tasks_uid, tasks, tasks_status):
            if status == Task.STA_DONE:
                task.set_status(Task.STA_ACTIVE)
            else:
                task.set_status(Task.STA_DONE)

    def on_dismiss_task(self, widget):
        tasks_uid = filter(lambda uid: uid != None, self.get_selected_tasks())
        if len(tasks_uid) == 0:
            return
        tasks = [self.req.get_task(uid) for uid in tasks_uid]
        tasks_status = [task.get_status() for task in tasks]
        for uid, task, status in zip(tasks_uid, tasks, tasks_status):
            if status == Task.STA_DISMISSED:
                task.set_status(Task.STA_ACTIVE)
            else:
                task.set_status(Task.STA_DISMISSED)

    def on_select_tag(self, widget, row=None, col=None):
        #When you clic on a tag, you want to unselect the tasks
        taglist, notag = self.get_selected_tags()
        if notag:
            newtag = ["notag"]
        else:
            if len(taglist) == 0:
                newtag = []
            else:
                newtag = [taglist[0].get_name()]
        #FIXME:handle multiple tags case
        if len(newtag) > 0:
            print "applying filter %s" %newtag[0]
            self.req.reset_tag_filters(refilter=False)
            self.req.apply_filter(newtag[0])
            if self.ctask_tree:
                self.ctask_tree.apply_filter(newtag[0])
        else:
            self.req.reset_tag_filters()
            if self.ctask_tree:
                self.ctask_tree.reset_tag_filters()
                        
#        self.task_tv.get_selection().unselect_all()
        self.ctask_tv.get_selection().unselect_all()
        self._update_window_title()

    def on_taskdone_cursor_changed(self, selection=None):
        """Called when selection changes in closed task view.

        Changes the way the selected task is displayed.
        """
        settings_done = {"label":     GnomeConfig.MARK_DONE,
                         "tooltip":   GnomeConfig.MARK_DONE_TOOLTIP,
                         "icon-name": "gtg-task-done"}
        settings_undone = {"label":     GnomeConfig.MARK_UNDONE,
                           "tooltip":   GnomeConfig.MARK_UNDONE_TOOLTIP,
                           "icon-name": "gtg-task-undone"}
        settings_dismiss = {"label":     GnomeConfig.MARK_DISMISS,
                           "tooltip":   GnomeConfig.MARK_DISMISS_TOOLTIP,
                           "icon-name": "gtg-task-dismiss"}
        settings_undismiss = {"label":     GnomeConfig.MARK_UNDISMISS,
                              "tooltip":   GnomeConfig.MARK_UNDISMISS_TOOLTIP,
                              "icon-name": "gtg-task-undismiss"}

        def update_button(button, settings): 
            button.set_icon_name(settings["icon-name"])
            button.set_label(settings["label"])
            
        def update_menu_item(menu_item, settings): 
            image = gtk.image_new_from_icon_name(settings["icon-name"], 16)
            image.set_pixel_size(16)
            image.show()
            menu_item.set_image(image)
            menu_item.set_label(settings["label"])

        #We unselect all in the active task view
        #Only if something is selected in the closed task list
        #And we change the status of the Done/dismiss button
        update_button(self.donebutton, settings_done)
        update_menu_item(self.done_mi, settings_done)
        update_button(self.dismissbutton, settings_dismiss)
        update_menu_item(self.dismiss_mi, settings_dismiss)
        if selection.count_selected_rows() > 0:
            tid = self.get_selected_task(self.ctask_tv)
            task = self.req.get_task(tid)
            self.task_tv.get_selection().unselect_all()
            if task.get_status() == "Dismiss":
                self.builder.get_object(
                    "ctcm_mark_as_not_done").set_sensitive(False)
                self.builder.get_object("ctcm_undismiss").set_sensitive(True)
                update_button(self.dismissbutton, settings_undismiss)
                update_menu_item(self.dismiss_mi, settings_undismiss)
            else:
                self.builder.get_object(
                    "ctcm_mark_as_not_done").set_sensitive(True)
                self.builder.get_object(
                    "ctcm_undismiss").set_sensitive(False)
                update_button(self.donebutton, settings_undone)
                update_menu_item(self.done_mi, settings_undone)
        self.update_buttons_sensitivity()

    def on_task_cursor_changed(self, selection=None):
        """Called when selection changes in the active task view.

        Changes the way the selected task is displayed.
        """
        #We unselect all in the closed task view
        #Only if something is selected in the active task list
        self.donebutton.set_icon_name("gtg-task-done")
        self.dismissbutton.set_icon_name("gtg-task-dismiss")
        if selection.count_selected_rows() > 0:
            self.ctask_tv.get_selection().unselect_all()
            self.donebutton.set_label(GnomeConfig.MARK_DONE)
            self.donebutton.set_tooltip_text(GnomeConfig.MARK_DONE_TOOLTIP)
            self.dismissbutton.set_label(GnomeConfig.MARK_DISMISS)
        self.update_buttons_sensitivity()

    def on_close(self, widget=None):
        """Closing the window."""
        #Saving is now done in main.py
        self.on_delete(None, None)
        self.quit()

    def on_task_added(self, sender, tid):
        Log.debug("Add task with ID: %s" % tid)
        self._update_window_title()

    def on_task_deleted(self, sender, tid):
        self._update_window_title()

    #using dummy parameters that are given by the signal
    def update_buttons_sensitivity(self,a=None,b=None,c=None):
        enable = self.selection.count_selected_rows() + \
           self.closed_selection.count_selected_rows() > 0
        self.edit_mi.set_sensitive(enable)
        self.new_subtask_mi.set_sensitive(enable)
        self.done_mi.set_sensitive(enable)
        self.dismiss_mi.set_sensitive(enable)
        self.delete_mi.set_sensitive(enable)
        self.donebutton.set_sensitive(enable)
        self.dismissbutton.set_sensitive(enable)
        self.deletebutton.set_sensitive(enable)

### PUBLIC METHODS #########################################################
    def get_selected_task(self, tv=None):
        """Returns the'uid' of the selected task, if any.
           If multiple tasks are selected, returns only the first and 
           takes care of selecting only that (unselecting the others)

        :param tv: The tree view to find the selected task in. Defaults to
            the task_tview.
        """
        if not tv:
            tview = self.task_tv
            selection = tview.get_selection()
            #If we don't have anything and no tview specified
            #Let's have a look in the closed task view
            if selection and selection.count_selected_rows() <= 0 and not tv:
                tview = self.ctask_tv
                selection = tview.get_selection()
            if selection.count_selected_rows() <= 0:
                return None
            else:
                model, paths = selection.get_selected_rows()
                if len(paths) >0 :
                    selection.unselect_all()
                    selection.select_path(paths[0])

        ids = self.get_selected_tasks(tv)
        if ids != None:
            return ids[0]
        else:
            return None

    def get_selected_tasks(self, tv=None):
        """Returns a list of 'uids' of the selected tasks, and the corresponding
           iters

        :param tv: The tree view to find the selected task in. Defaults to
            the task_tview.
        """
        if not tv:
            tview = self.task_tv
        else:
            tview = tv
        # Get the selection in the gtk.TreeView
        selection = tview.get_selection()
        #If we don't have anything and no tview specified
        #Let's have a look in the closed task view
        if selection and selection.count_selected_rows() <= 0 and not tv:
            tview = self.ctask_tv
            selection = tview.get_selection()
        # Get the selection iter
        if selection.count_selected_rows() <= 0:
            ids = [None]
        else:
            model, paths = selection.get_selected_rows()
            iters = [model.get_iter(path) for path in paths]
            ts  = tview.get_model()
            ids = [ts.get_value(iter, tasktree.COL_TID) for iter in iters]
        return ids

    def get_selected_tags(self):
        notag_only = False
        tag = []
        if self.tags_tv:
            t_selected = self.tags_tv.get_selection()
            model      = self.tags_tv.get_model()
            t_iter = None
            if t_selected:
                tmodel, t_iter = t_selected.get_selected()
            if t_iter:
                selected = model.get_value(t_iter, tagtree.COL_OBJ)
                special  = selected.get_attribute("special")
                if special == "all":
                    tag = []
                    selected = None
                #notag means we want to display only tasks without any tag
                if special == "notag":
                    notag_only = True
                if not notag_only and selected:
                    tag.append(selected)
            #If no selection, we display all
        return tag, notag_only
    
    def reset_cursor(self):
        """ Returns the cursor to the tag that was selected prior
            to any right click action. Should be used whenever we're done
            working with any tag through a right click menu action.
            """
        if self.tag_active:
            self.tag_active = False
            path, col = self.previous_cursor
            self.tags_tv.set_cursor(path, col, 0)
                
    def set_target_cursor(self):
        """ Selects the last tag to be right clicked. 
        
            We need this because the context menu will deactivate
            (and in turn, call reset_cursor()) before, for example, the color
            picker dialog begins. Should be used at the beginning of any tag
            editing function to remind the user which tag they're working with.
            """
        if not self.tag_active:
            self.tag_active = True
            path, col = self.target_cursor
            self.tags_tv.set_cursor(path, col, 0)

    def hide(self):
        """Hides the task browser"""
        self.window.hide()

    def show(self):
        """Unhides the TaskBrowser"""
        self.window.present()
        #redraws the GDK window, bringing it to front
        self.window.show()
