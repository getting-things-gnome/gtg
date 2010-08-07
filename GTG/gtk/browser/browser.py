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
import locale
import time
import webbrowser

import pygtk
pygtk.require('2.0')
import gobject
import gtk

#our own imports
import GTG
from GTG.core                       import CoreConfig
from GTG                         import _, info, ngettext
from GTG.core.task               import Task
from GTG.gtk.browser             import GnomeConfig
from GTG.gtk.browser.treeview_factory import TreeviewFactory
from GTG.tools                   import openurl
from GTG.tools.dates             import no_date,\
                                        get_canonical_date
from GTG.tools.logger            import Log
#from GTG.tools                   import clipboard


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
        self.vtree_panes = {}
        self.tv_factory = TreeviewFactory(self.req,self.config)
        self.activetree = self.req.get_tasks_tree(name='active')
        self.vtree_panes['active'] = \
                self.tv_factory.active_tasks_treeview(self.activetree)


        ### YOU CAN DEFINE YOUR INTERNAL MECHANICS VARIABLES BELOW
        
        # Setup default values for view
        self._init_browser_config()

        # Setup GTG icon theme
        self._init_icon_theme()

        # Set up models
        # Active Tasks
        self.activetree.apply_filter('active',refresh=False)
        # Tags
        self.tagtree = self.tv_factory.tags_treeview(self.req.get_tag_tree())

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

        #Expand all the tasks in the taskview
#        print "********* Will expand ************"
#        r = self.vtree_panes['active'].expand_all()
#        print "********** expanded ***************"
        self.on_select_tag()
        self.window.show()

### INIT HELPER FUNCTIONS #####################################################
#
    def _init_browser_config(self):
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
        icon_dirs = CoreConfig().get_icons_directories()
        for i in icon_dirs:
            gtk.icon_theme_get_default().prepend_search_path(i)
            gtk.window_set_default_icon_name("gtg")


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
        self.toolbar            = self.builder.get_object("task_toolbar")
        self.quickadd_pane      = self.builder.get_object("quickadd_pane")
        self.sidebar            = self.builder.get_object("sidebar_vbox")
        self.sidebar_container  = self.builder.get_object("sidebar-scroll")
        self.sidebar_notebook   = self.builder.get_object("sidebar_notebook")
        self.main_notebook      = self.builder.get_object("main_notebook")
        self.accessory_notebook = self.builder.get_object("accessory_notebook")
        
        self.closed_pane        = None

    def _init_ui_widget(self):
        # The Active tasks treeview
        self.main_pane.add(self.vtree_panes['active'])

        # The tags treeview
        self.sidebar_container.add(self.tagtree)

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
        self.vtree_panes['active'].connect('row-activated',\
            self.on_edit_active_task)
        self.vtree_panes['active'].connect('button-press-event',\
            self.on_task_treeview_button_press_event)
        self.vtree_panes['active'].connect('key-press-event',\
            self.on_task_treeview_key_press_event)
        self.vtree_panes['active'].connect('node-expanded',\
            self.on_task_expanded)
        self.vtree_panes['active'].connect('node-collapsed',\
            self.on_task_collapsed)

        # Connect requester signals to TreeModels
        self.req.connect("task-added", self.on_task_added) 
        self.req.connect("task-deleted", self.on_task_deleted)

        #Tags treeview
        self.tagtree.connect('cursor-changed',\
            self.on_select_tag)
        self.tagtree.connect('row-activated',\
            self.on_select_tag)
        self.tagtree.connect('button-press-event',\
            self.on_tag_treeview_button_press_event)
        
        # Selection changes
        self.selection = self.vtree_panes['active'].get_selection()
        self.selection.connect("changed", self.on_task_cursor_changed)
        self.req.connect("task-deleted", self.update_buttons_sensitivity)

    def _init_view_defaults(self):
        self.menu_view_workview.set_active(WORKVIEW)
        self.builder.get_object("view_sidebar").set_active(SIDEBAR)
        self.builder.get_object("view_closed").set_active(CLOSED_PANE)
        self.builder.get_object("view_quickadd").set_active(QUICKADD_PANE)
        self.builder.get_object("view_toolbar").set_active(TOOLBAR)
        if not self.config.has_key('browser'):
            self.config['browser'] = {}
        self.config["browser"]["bg_color_enable"] = BG_COLOR
        self.priv["contents_preview_enable"] = CONTENTS_PREVIEW

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
        self.tag_list = self.req.get_tag_tree().get_all_nodes()
        for i in self.tag_list:
            self.tag_list_model.append([i[1:]])
               
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
        self.vmanager.open_preferences(self.priv)
        
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
            bgcol_enable = self.config["browser"].get("bg_color_enable",BG_COLOR)
            self.builder.get_object("bgcol_enable").set_active(bgcol_enable)

        if "contents_preview_enable" in self.config["browser"]:
            self.priv["contents_preview_enable"] = \
                    eval(self.config["browser"]["contents_preview_enable"])
        
        if "collapsed_tasks" not in self.config["browser"]:
            self.config["browser"]["collapsed_tasks"] = []
                
        if "collapsed_tags" in self.config["browser"]:
            toset = self.config["browser"]["collapsed_tags"]
            #FIXME: Not available in liblarch
#            self.tagtree.set_collapsed_tags(toset)

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
        if tobeset:
            self.activetree.apply_filter('workview')
        else:
            self.activetree.unapply_filter('workview')
        self.vtree_panes['active'].set_col_visible('startdate',not tobeset)
        self._update_window_title()

    def _update_window_title(self):
        count = self.activetree.get_n_nodes()
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

    def _add_page(self, notebook, label, page):
        notebook.append_page(page, label)
        if notebook.get_n_pages() > 1:
            notebook.set_show_tabs(True)
        page_num = notebook.page_num(page)
        notebook.set_tab_detachable(page, True)
        notebook.set_tab_reorderable(page, True)
        notebook.set_current_page(page_num)
        notebook.show_all()
        return page_num

    def _remove_page(self, notebook, page):
        if page:
            page.hide()
            notebook.remove(page)
        if notebook.get_n_pages() == 1:
            notebook.set_show_tabs(False)
        elif notebook.get_n_pages() == 0:
            notebook.hide()

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
        for tid in self.config['browser']["collapsed_tasks"]:
            if not self.req.has_task(tid):
                self.config['browser']["collapsed_tasks"].remove(tid)

        # Get configuration values
        tag_sidebar        = self.sidebar.get_property("visible")
        tag_sidebar_width  = self.builder.get_object("hpaned1").get_position()
        if self.closed_pane:
            closed_pane    = self.closed_pane.get_property("visible")
        else:
            closed_pane    = False
        quickadd_pane      = self.quickadd_pane.get_property("visible")
        toolbar            = self.toolbar.get_property("visible")
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
            'contents_preview_enable':
                self.priv["contents_preview_enable"],
            #FIXME : to implement in liblarch
#            'collapsed_tags':
#                self.tagtree.get_collapsed_tags(),
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
#        if   sort_column is not None and sort_order == gtk.SORT_ASCENDING:
#            self.config["browser"]["tasklist_sort"]  = [sort_column, 0]
#        elif sort_column is not None and sort_order == gtk.SORT_DESCENDING:
#            self.config["browser"]["tasklist_sort"]  = [sort_column, 1]
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
        for tname in tags:
            t = self.req.get_tag(tname)
            t.set_attribute("color", strcolor)

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
            ta = self.req.get_tag(tags[0])
            color = ta.get_attribute("color")
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
        color_dialog.destroy()
        
    def on_resetcolor_activate(self, widget):
        self.set_target_cursor()
        tags, notag_only = self.get_selected_tags()
        for t in tags:
            t.del_attribute("color")
        self.reset_cursor()
        
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
        if not self.vtree_panes.has_key('closed'):
            closedtree = self.req.get_tasks_tree(name='closed')
            self.vtree_panes['closed'] = \
                        self.tv_factory.closed_tasks_treeview(closedtree)
            closedtree.apply_filter('closed')
                    # Closed tasks TreeView
            self.vtree_panes['closed'].connect('row-activated',\
                self.on_edit_done_task)
            self.vtree_panes['closed'].connect('button-press-event',\
                self.on_closed_task_treeview_button_press_event)
            self.vtree_panes['closed'].connect('key-press-event',\
                self.on_closed_task_treeview_key_press_event)
                
            self.closed_selection = self.vtree_panes['closed'].get_selection()
            self.closed_selection.connect("changed", self.on_taskdone_cursor_changed)

        if not self.closed_pane:
            self.closed_pane = gtk.ScrolledWindow()
            self.closed_pane.set_size_request(-1, 100)
            self.closed_pane.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            self.closed_pane.add(self.vtree_panes['closed'])

        elif self.accessory_notebook.page_num(self.closed_pane) != -1:
            # Already contains the closed pane
            return

        self.add_page_to_accessory_notebook("Closed", self.closed_pane)
        self.builder.get_object("view_closed").set_active(True)

    def hide_closed_pane(self):
        if self.vtree_panes.has_key('closed'):
            self.vtree_panes['closed'].set_model(None)
            del self.vtree_panes['closed']
        self.remove_page_from_accessory_notebook(self.closed_pane)
        self.builder.get_object("view_closed").set_active(False)

    def on_bg_color_toggled(self, widget):
        if widget.get_active():
            self.config["browser"]["bg_color_enable"] = True
        else:
            self.config["browser"]["bg_color_enable"] = False

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

    def on_task_expanded(self, sender, tid):
        if tid in self.config['browser']["collapsed_tasks"]:
            self.config['browser']["collapsed_tasks"].remove(tid)
        
    def on_task_collapsed(self, sender, tid):
        if tid not in self.config['browser'].get("collapsed_tasks",[]):
            self.config['browser']["collapsed_tasks"].append(tid)

    def on_quickadd_activate(self, widget):
        text = self.quickadd_entry.get_text()
        if text:
            tags, notagonly = self.get_selected_tags()
            task = self.req.new_task(newtask=True)
            task.set_complex_title(text,tags=tags)
            self.quickadd_entry.set_text('')
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
                    selected_tag = self.req.get_tag(selected_tags[0])
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
        toset = str(not self.nonworkviewtag_cb.get_active())
        if len(tags) > 0:
            tags[0].set_attribute("nonworkview", toset)
        #Following should not be needed with liblarch
#        if self.priv['workview']:
#            self.tagtree.refilter()
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
        tid = self.get_selected_task('closed')
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
        #use spaces and commas as separators
        new_tags = []
        for text in entry_text.split(","):
            tags = [t.strip() for t in text.split(" ")]
            for tag in tags:
                if tag:
                    new_tags.append("@" + tag)
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

    def on_select_tag(self, widget=None, row=None, col=None):
        #When you clic on a tag, you want to unselect the tasks
        taglist, notag = self.get_selected_tags()
        if notag:
            newtag = ["notag"]
        else:
            if taglist and len(taglist) > 0:
                newtag = [taglist[0]]
            else:
                newtag = ['no_disabled_tag']
        #FIXME:handle multiple tags case
        #We apply filters for every visible ViewTree
        for t in self.vtree_panes:
            #1st we reset the tags filter
            vtree = self.req.get_tasks_tree(name=t)
            vtree.reset_filters(refresh=False,transparent_only=True)
            #then applying the tag
            if len(newtag) > 0:
                vtree.apply_filter(newtag[0])
                        
#        self.ctask_tv.get_selection().unselect_all()
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
            tid = self.get_selected_task('closed')
            task = self.req.get_task(tid)
            self.vtree_panes['active'].get_selection().unselect_all()
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
            if self.vtree_panes.has_key('closed'):
                self.vtree_panes['closed'].get_selection().unselect_all()
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
        enable = self.selection.count_selected_rows() 
        if self.vtree_panes.has_key('closed'):
            enable += self.closed_selection.count_selected_rows() > 0
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
        ids = self.get_selected_tasks(tv)
        if len(ids) > 0:
            #fixme : we should also unselect all the others
            return ids[0]
        else:
            return None

    def get_selected_tasks(self, tv=None):
        """Returns a list of 'uids' of the selected tasks, and the corresponding
           iters

        :param tv: The tree view to find the selected task in. Defaults to
            the task_tview.
        """
        selected = []
        if tv:
            selected = self.vtree_panes[tv].get_selected_nodes()
        else:
            if self.vtree_panes.has_key('active'):
                selected = self.vtree_panes['active'].get_selected_nodes()
            for i in self.vtree_panes:
                if len(selected) == 0:
                    selected = self.vtree_panes[i].get_selected_nodes()
        return selected
        

    def get_selected_tags(self):
        #Fixme : the notag only !
        notag_only = False
        tag = []
        if self.tagtree:
            tag = self.tagtree.get_selected_nodes()
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
            self.tagtree.set_cursor(path, col, 0)
                
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
            self.tagtree.set_cursor(path, col, 0)

    def add_page_to_sidebar_notebook(self, icon, page):
        """Adds a new page tab to the left panel.  The tab will 
        be added as the last tab.  Also causes the tabs to be
        shown if they're not.
        @param icon: a gtk.Image picture to display on the tab
        @param page: gtk.Frame-based panel to be added
        """
        return self._add_page(self.sidebar_notebook, icon, page)

    def add_page_to_main_notebook(self, title, page):
        """Adds a new page tab to the top right main panel.  The tab
        will be added as the last tab.  Also causes the tabs to be
        shown.
        @param title: Short text to use for the tab label
        @param page: gtk.Frame-based panel to be added
        """
        return self._add_page(self.main_notebook, gtk.Label(title), page)

    def add_page_to_accessory_notebook(self, title, page):
        """Adds a new page tab to the lower right accessory panel.  The
        tab will be added as the last tab.  Also causes the tabs to be
        shown.
        @param title: Short text to use for the tab label
        @param page: gtk.Frame-based panel to be added
        """
        return self._add_page(self.accessory_notebook, gtk.Label(title), page)

    def remove_page_from_sidebar_notebook(self, page):
        """Removes a new page tab from the left panel.  If this leaves
        only one tab in the notebook, the tab selector will be hidden.
        @param page: gtk.Frame-based panel to be removed
        """
        return self._remove_page(self.sidebar_notebook, page)

    def remove_page_from_main_notebook(self, page):
        """Removes a new page tab from the top right main panel.  If
        this leaves only one tab in the notebook, the tab selector will
        be hidden.
        @param page: gtk.Frame-based panel to be removed
        """
        return self._remove_page(self.main_notebook, page)

    def remove_page_from_accessory_notebook(self, page):
        """Removes a new page tab from the lower right accessory panel.
        If this leaves only one tab in the notebook, the tab selector
        will be hidden.
        @param page: gtk.Frame-based panel to be removed
        """
        return self._remove_page(self.accessory_notebook, page)

    def hide(self):
        """ Hides the task browser """
        self.window.hide()

    def show(self):
        """ Unhides the TaskBrowser """
        self.window.present()
        #redraws the GDK window, bringing it to front
        self.window.show()

    def iconify(self):
        """ Minimizes the TaskBrowser """
        self.window.iconify()

    def is_visible(self):
        """ Returns true if window is shown or false if hidden. """
        return self.window.get_property("visible")

    def is_active(self):
        """ Returns true if window is the currently active window """
        return self.window.get_property("is-active")

