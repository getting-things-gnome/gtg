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
import threading

import pygtk
pygtk.require('2.0')
import gobject
import gtk

#our own imports
import GTG
from GTG.backends.backendsignals import BackendSignals
from GTG.gtk.browser.custominfobar import CustomInfoBar
from GTG.core                       import CoreConfig
from GTG                         import _, info, ngettext
from GTG.core.task               import Task
from GTG.gtk.browser             import GnomeConfig
from GTG.gtk.browser.treeview_factory import TreeviewFactory
from GTG.tools                   import openurl
from GTG.tools.dates             import no_date,\
                                        get_canonical_date
from GTG.tools.logger            import Log
from GTG.tools.tags              import extract_tags_from_text
#from GTG.tools                   import clipboard


#=== MAIN CLASS ===============================================================

WINDOW_TITLE = "Getting Things GNOME!"
DOCUMENTATION_URL = "http://live.gnome.org/gtg/documentation"

#Some default preferences that we should save in a file
TIME             = 0


class Timer:
    def __init__(self,st):
        self.st = st
    def __enter__(self): self.start = time.time()
    def __exit__(self, *args): 
        print "%s : %s" %(self.st,time.time() - self.start)


class TaskBrowser(gobject.GObject):
    """ The UI for browsing open and closed tasks, and listing tags in a tree """

    __string_signal__ = (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (str, ))
    __none_signal__ = (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, tuple())
    __gsignals__ = {'task-added-via-quick-add' : __string_signal__, \
                    'visibility-toggled': __none_signal__,
                   }

    def __init__(self, requester, vmanager):
        gobject.GObject.__init__(self)
        # Object prime variables
        self.priv   = {}
        self.req    = requester
        self.vmanager = vmanager
        self.config = self.req.get_config('browser')
        self.tag_active = False
        
        #treeviews handlers
        self.vtree_panes = {}
        self.tv_factory = TreeviewFactory(self.req,self.config)
        self.activetree = self.req.get_tasks_tree(name='active',refresh=False)
        self.vtree_panes['active'] = \
                self.tv_factory.active_tasks_treeview(self.activetree)


        ### YOU CAN DEFINE YOUR INTERNAL MECHANICS VARIABLES BELOW
        self.in_toggle_workview = False

        # Setup default values for view
        self._init_browser_config()

        # Setup GTG icon theme
        self._init_icon_theme()

        # Set up models
        # Active Tasks
        self.activetree.apply_filter('active',refresh=False)
        # Tags
        self.tagtree = None
        self.tagtreeview = None

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

        # Define accelerator keys
        self._init_accelerators()
        
        # Rember values from last time
        self.last_added_tags = "NewTag"
        self.last_apply_tags_to_subtasks = False
        
        self.restore_state_from_conf()

        self.on_select_tag()
        self.browser_shown = False
        
        #Update the title when a task change
        self.activetree.register_cllbck('node-added-inview',self._update_window_title)
        self.activetree.register_cllbck('node-deleted-inview',self._update_window_title)

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

    def _init_icon_theme(self):
        icon_dirs = CoreConfig().get_icons_directories()
        for i in icon_dirs:
            gtk.icon_theme_get_default().prepend_search_path(i)
            gtk.window_set_default_icon_name("gtg")


    def _init_widget_aliases(self):
        self.window             = self.builder.get_object("MainWindow")
        self.tagpopup           = self.builder.get_object("tag_context_menu")
        self.nonworkviewtag_cb  = self.builder.get_object("nonworkviewtag_mi")
        self.nonworkviewtag_cb.set_label(GnomeConfig.TAG_IN_WORKVIEW_TOGG)
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
        self.vbox_toolbars      = self.builder.get_object("vbox_toolbars")
        
        self.closed_pane        = None

    def _init_ui_widget(self):
        # The Active tasks treeview
        self.main_pane.add(self.vtree_panes['active'])

    def init_tags_sidebar(self):
        # The tags treeview
        self.tagtree = self.req.get_tag_tree()
        self.tagtreeview = self.tv_factory.tags_treeview(self.tagtree)
        self._init_tag_completion()
        #Tags treeview
        self.tagtreeview.connect('cursor-changed',\
            self.on_select_tag)
        self.tagtreeview.connect('row-activated',\
            self.on_select_tag)
        self.tagtreeview.connect('button-press-event',\
            self.on_tag_treeview_button_press_event)
        self.sidebar_container.add(self.tagtreeview)

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
            "on_start_for_tomorrow":
                self.on_start_for_tomorrow,
            "on_start_for_next_week":
                self.on_start_for_next_week,
            "on_start_for_next_month":
                self.on_start_for_next_month,
            "on_start_for_next_year":
                self.on_start_for_next_year,
            "on_start_clear":
                self.on_start_clear,
            "on_set_due_today":
                self.on_set_due_today,
            "on_set_due_tomorrow":
                self.on_set_due_tomorrow,
            "on_set_due_next_week":
                self.on_set_due_next_week,
            "on_set_due_next_month":
                self.on_set_due_next_month,
            "on_set_due_next_year":
                self.on_set_due_next_year,
            "on_set_due_now":
                self.on_set_due_now,
            "on_set_due_soon":
                self.on_set_due_soon,
            "on_set_due_later":
                self.on_set_due_later,
            "on_set_due_clear":
                self.on_set_due_clear,
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
            "on_edit_backends_activate":
                self.open_edit_backends,
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

        b_signals = BackendSignals()
        b_signals.connect(b_signals.BACKEND_FAILED, self.on_backend_failed)
        b_signals.connect(b_signals.BACKEND_STATE_TOGGLED, \
                          self.remove_backend_infobar)
        b_signals.connect(b_signals.INTERACTION_REQUESTED, \
                          self.on_backend_needing_interaction)
        # Selection changes
        self.selection = self.vtree_panes['active'].get_selection()
        self.selection.connect("changed", self.on_task_cursor_changed)
        self.req.connect("task-deleted", self.update_buttons_sensitivity)

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

    def _init_tag_completion(self):
        #Initialize tag completion.
        self.tag_completion = gtk.EntryCompletion()
        self.tag_completion.set_model(self.tagtreeview.get_model())
        self.tag_completion.set_text_column(3)
        self.tag_completion.set_match_func(self.tag_match_func, 3)
        self.tag_completion.set_inline_completion(True)
        self.tag_completion.set_inline_selection(True)
        self.tag_completion.set_popup_single_match(False)

### HELPER FUNCTIONS ########################################################

    def open_preferences(self, widget):
        self.vmanager.open_preferences(self.config)
        
    def open_edit_backends(self, widget):
        self.vmanager.open_edit_backends()

    def quit(self,widget=None):
        self.vmanager.close_browser()
        
    def restore_state_from_conf(self):

#        # Extract state from configuration dictionary
#        if not "browser" in self.config:
#            #necessary to have the minimum width of the tag pane
#            # inferior to the "first run" width
#            self.builder.get_object("hpaned1").set_position(250)
#            return

        width = self.config.get('width')
        height = self.config.get('height')
        if width and height:
            self.window.resize(width, height)

        xpos = self.config.get("x_pos")
        ypos = self.config.get("y_pos")
        if ypos and xpos:
            self.window.move(xpos, ypos)

        tag_pane = self.config.get("tag_pane")
        if not tag_pane:
            self.builder.get_object("view_sidebar").set_active(False)
            self.sidebar.hide()
        else:
            self.builder.get_object("view_sidebar").set_active(True)
            if not self.tagtreeview:
                self.init_tags_sidebar()
            self.sidebar.show()

        sidebar_width = self.config.get("sidebar_width")
        self.builder.get_object("hpaned1").set_position(sidebar_width)

        closed_task_pane = self.config.get("closed_task_pane")
        if not closed_task_pane:
            self.hide_closed_pane()
        else:
            self.show_closed_pane()

        botpos = self.config.get("bottom_pane_position")
        self.builder.get_object("vpaned1").set_position(botpos)

        toolbar = self.config.get("toolbar")
        if toolbar:
            self.builder.get_object("view_toolbar").set_active(1)
        else:
            self.toolbar.hide()
            self.builder.get_object("view_toolbar").set_active(False)

        quickadd_pane = self.config.get("quick_add")
        if quickadd_pane:
            self.builder.get_object("view_quickadd").set_active(True)
        else:
            self.quickadd_pane.hide()
            self.builder.get_object("view_quickadd").set_active(False)

        bgcol_enable = self.config.get("bg_color_enable")
        self.builder.get_object("bgcol_enable").set_active(bgcol_enable)
        
        for path_s in self.config.get("collapsed_tasks"):
            #the tuple was stored as a string. we have to reconstruct it
            path = ()
            for p in path_s[1:-1].split(","):
                p = p.strip(" '")
                path += (p,)
            if path[-1] == '':
                path = path[:-1]
            self.vtree_panes['active'].collapse_node(path)
                
        for t in self.config.get("collapsed_tags"):
            #FIXME
            print "Collapsing tag %s not implememted in browser.py" %t
#            self.tagtreeview.set_collapsed_tags(toset)

        self.set_view(self.config.get("view"))

#FIXME this is just a big hack, it should be refractored in the future,
# maybe better designed
        def open_task(req, t):
            if req.has_task(t):
                self.vmanager.open_task(t)
                # Do not do it again
                return False
            else:
                # Try it later
                return True
                
        if self._start_gtg_maximized():
            odic = self.config.get("opened_tasks")
            #This should be removed. This is bad !
#            #odic can contain also "None" or "None,", so we skip them
#            if odic == "None" or (len(odic)> 0 and odic[0] == "None"):
#                return
            for t in odic:
                gobject.idle_add(open_task, self.req, t)

    def _start_gtg_maximized(self):
        #This is needed as a hook point to let the Notification are plugin
        #start gtg minimized
        return True

    def do_toggle_workview(self):
        """ Switch between default and work view

        Updating tags is disabled while changing view. It consumes
        a lot of CPU cycles and the user does not see it. Afterwards,
        updating of tags is re-enabled and all tags are refreshed.

        Because workview can be switched from more than one button
        (currently toggle button and check menu item), we need to change
        status of others also. It invokes again this method => 
        a loop of signals.
        
        It is more flexible to have a dedicated variable
        (self.in_toggle_workview) which prevents that recursion. The other way
        how to solve this is to checking state of those two buttons and check
        if they are not the same. Adding another way may complicate things...
        """

        if self.in_toggle_workview:
            return
        self.in_toggle_workview = True
        self.tv_factory.disable_update_tags()

        if self.config.get('view') == 'workview':
            self.set_view('default')
        else:
            self.set_view('workview')

        self.tv_factory.enable_update_tags()
        self.tagtree.refresh_all()
        self.in_toggle_workview = False
        
    def set_view(self,viewname):
        if viewname == 'default':
            self.activetree.unapply_filter('workview')
            workview = False
        elif viewname == 'workview':
            self.activetree.apply_filter('workview')
            workview = True
        else:
            raise Exception('Cannot set the view %s' %viewname)
        self.menu_view_workview.set_active(workview)
        self.toggle_workview.set_active(workview)
        #The config_set has to be after the toggle, else you will have a loop
        self.config.set('view',viewname)
        self.vtree_panes['active'].set_col_visible('startdate',not workview)

    def _update_window_title(self,nid=None,path=None,state_id=None):
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


    def tag_match_func(self, completion, key, iter, column):
        model = completion.get_model()
        text = model.get_value(iter, column)
        if text:
            # key is lowercase regardless of input, so text should be
            # lowercase as well, otherwise we leave out all tags beginning
            # with an uppercase letter.
            text = text.lower()
            # Exclude the special tags.
            if text.startswith("<span") or text.startswith('gtg-tags-'):
                return False
            # Are we typing the first letters of a tag?
            elif text.startswith(key):
                #FIXME: this doesn't work for UNICODE, I don't know why
                return True
            else:
#                print "no completion for text %s" %text
#                print " key is %s (len=%s)" %(key,len(key))
#                print " start of text is : %s" %(text[:len(key)])
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
        self.config.set('x_pos',xpos)
        self.config.set('y_pos',ypos)

    def on_size_allocate(self, widget = None, data = None):
        width, height = self.window.get_size()
        self.config.set('width',width)
        self.config.set('height',height)

    #on_delete is called when the user close the window
    def on_delete(self, widget, user_data):
        # Cleanup collapsed row list
        #TODO: the cleanup should better be done on task deletion
        botpos = self.builder.get_object("vpaned1").get_position()
        self.config.set('bottom_pane_position',botpos)
        sidepos = self.builder.get_object("hpaned1").get_position()
        self.config.set('sidebar_width',sidepos)

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
        tags = self.get_selected_tags()
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
        tags= self.get_selected_tags()
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
            tags = self.get_selected_tags()
            for t in tags:
                t.set_attribute("color", strcolor)
        self.reset_cursor()
        color_dialog.destroy()
        
    def on_resetcolor_activate(self, widget):
        self.set_target_cursor()
        tags = self.get_selected_tags()
        for tname in tags:
            t = self.req.get_tag(tname)
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
            self.config.set("tag_pane",False)
            self.sidebar.hide()
        else:
            view_sidebar.set_active(True)
            if not self.tagtreeview:
                self.init_tags_sidebar()
            self.sidebar.show()
            self.config.set("tag_pane",True)

    def on_closed_toggled(self, widget):
        if widget.get_active():
            self.show_closed_pane()
        else:
            self.hide_closed_pane()

    def __create_closed_tree(self):
        closedtree = self.req.get_tasks_tree(name='closed',refresh=False)
        closedtree.apply_filter('closed',refresh=False)
        return closedtree
            
    def show_closed_pane(self):
        # The done/dismissed tasks treeview
        if not self.vtree_panes.has_key('closed'):
            ctree = self.__create_closed_tree()
            self.vtree_panes['closed'] = \
                         self.tv_factory.closed_tasks_treeview(ctree)
                    # Closed tasks TreeView
            self.vtree_panes['closed'].connect('row-activated',\
                self.on_edit_done_task)
            self.vtree_panes['closed'].connect('button-press-event',\
                self.on_closed_task_treeview_button_press_event)
            self.vtree_panes['closed'].connect('key-press-event',\
                self.on_closed_task_treeview_key_press_event)
                
            self.closed_selection = self.vtree_panes['closed'].get_selection()
            self.closed_selection.connect("changed", self.on_taskdone_cursor_changed)
            ctree.apply_filter(self.get_selected_tags()[0],refresh=True)
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
        self.config.set('closed_task_pane',True)

    def hide_closed_pane(self):
        #If we destroy completely the vtree, we cannot display it anymore
        #Check is to hide/show the closed task pane multiple times.
        #I let this code commented for now because it might be useful
        #for performance reason, to really destroy the view when we don't 
        #display it. (Lionel, 17092010)
#        if self.vtree_panes.has_key('closed'):
#            self.vtree_panes['closed'].set_model(None)
#            del self.vtree_panes['closed']
        self.remove_page_from_accessory_notebook(self.closed_pane)
        self.builder.get_object("view_closed").set_active(False)
        self.config.set('closed_task_pane',False)

    def on_bg_color_toggled(self, widget):
        if widget.get_active():
            self.config.set("bg_color_enable",True)
        else:
            self.config.set("bg_color_enable",False)

    def on_toolbar_toggled(self, widget):
        if widget.get_active():
            self.toolbar.show()
            self.config.set('toolbar',True)
        else:
            self.toolbar.hide()
            self.config.set('toolbar',False)

    def on_toggle_quickadd(self, widget):
        if widget.get_active():
            self.quickadd_pane.show()
            self.config.set('quick_add',True)
        else:
            self.quickadd_pane.hide()
            self.config.set('quick_add',False)

    def on_task_expanded(self, sender, tid):
        colt = self.config.get("collapsed_tasks")
        if tid in colt:
            colt.remove(tid)
        
    def on_task_collapsed(self, sender, tid):
        colt = self.config.get("collapsed_tasks")
        if tid not in colt:
            colt.append(str(tid))

    def on_quickadd_activate(self, widget):
        text = unicode(self.quickadd_entry.get_text())
        due_date = no_date
        defer_date = no_date
        if text:
            tags = self.get_selected_tags(nospecial=True)
            #We will select quick-added task in browser.
            #This has proven to be quite complex and deserves an explanation.
            #We register a callback on the sorted treemodel that we're
            #displaying, which is a TreeModelSort. When a row gets added, we're
            #notified of it.
            # We have to verify that that row belongs to the task we should
            # select. So, we have to wait for the task to be created, and then
            # wait for its tid to show up (invernizzi)
            def select_next_added_task_in_browser(treemodelsort, path, iter, self):
                def selecter(treemodelsort, path, iter, self):
                    self.__last_quick_added_tid_event.wait()
                    treeview = self.vtree_panes['active']
                    tid = self.activetree.get_node_for_path(path)
                    if self.__last_quick_added_tid == tid:
                        #this is the correct task
                        treemodelsort.disconnect(self.__quick_add_select_handle)
                        selection = treeview.get_selection()
                        selection.unselect_all()
                        selection.select_path(path)
                #It cannot be another thread than the main gtk thread !
                gobject.idle_add(selecter,treemodelsort, path, iter, self)
            #event that is set when the new task is created
            self.__last_quick_added_tid_event = threading.Event()
            self.__quick_add_select_handle = \
                self.vtree_panes['active'].get_model().connect(\
                                    "row-inserted",
                                    select_next_added_task_in_browser,
                                    self)
            task = self.req.new_task(newtask=True)
            self.__last_quick_added_tid = task.get_id()
            self.__last_quick_added_tid_event.set()
            task.set_complex_title(text,tags=tags)
            self.quickadd_entry.set_text('')

            #signal the event for the plugins to catch
            gobject.idle_add(self.emit, "task-added-via-quick-add",
                             task.get_id())
        else:
            #if no text is selected, we open the currently selected task
            nids = self.vtree_panes['active'].get_selected_nodes()
            for nid in nids:
                self.vmanager.open_task(nid)
            

    def on_tag_treeview_button_press_event(self, treeview, event):
        Log.debug("Received button event #%d at %d,%d" %(event.button, event.x, event.y))
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
                #the nospecial=True disable right clicking for special tags
                selected_tags = self.get_selected_tags(nospecial=True)
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
        tag_id = self.get_selected_tags()[0]
        #We must inverse because the tagstore has True
        #for tasks that are not in workview (and also convert to string)
        toset = not self.nonworkviewtag_cb.get_active()
        tag = self.req.get_tag(tag_id)
        tag.set_attribute("nonworkview", str(toset))
        if toset:
            label = GnomeConfig.TAG_NOTIN_WORKVIEW_TOGG
        else:
            label = GnomeConfig.TAG_IN_WORKVIEW_TOGG
        self.nonworkviewtag_cb.set_label(label)
        if not self.dont_reset:
            self.reset_cursor()

    def on_task_treeview_button_press_event(self, treeview, event):
        """Pop up context menu on right mouse click in the main task tree view"""
        Log.debug("Received button event #%d at %d,%d" %(event.button, event.x, event.y))
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                selection = treeview.get_selection()
                if selection.count_selected_rows() > 0 :
                    if not selection.path_is_selected(path) :
                        treeview.set_cursor(path, col, 0)
                else :
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
        tags = [tag for tag in self.get_selected_tags() if not tag.startswith('gtg-tag')]
        task = self.req.new_task(tags=tags, newtask=True)
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
            if not tids_todelete:
                return
        else:
            tids_todelete = [tid]
        Log.debug("going to delete %s" % tids_todelete)
        self.vmanager.ask_delete_tasks(tids_todelete)

    def update_start_date(self, widget, new_start_date):
        tasks = [self.req.get_task(uid) 
            for uid in self.get_selected_tasks()
            if uid is not None]

        if new_start_date:
            start_date = get_canonical_date(new_start_date)
        else:
            start_date = no_date

        for task in tasks:
            task.set_start_date(start_date)
        #FIXME: If the task dialog is displayed, refresh its start_date widget

    def on_mark_as_started(self, widget):
        self.update_start_date(widget, "today")

    def on_start_for_tomorrow(self, widget):
        self.update_start_date(widget, "tomorrow")

    def on_start_for_next_week(self, widget):
        self.update_start_date(widget, "next week")

    def on_start_for_next_month(self, widget):
        self.update_start_date(widget, "next month")

    def on_start_for_next_year(self, widget):
        self.update_start_date(widget, "next year")

    def on_start_clear(self, widget):
        self.update_start_date(widget, None)
        
    def update_due_date(self, widget, new_due_date):
        tasks = [self.req.get_task(uid) 
            for uid in self.get_selected_tasks()
            if uid is not None]

        if new_due_date:
            due_date = get_canonical_date(new_due_date)
        else:
            due_date = no_date

        for task in tasks:
            task.set_due_date(due_date)
        #FIXME: If the task dialog is displayed, refresh its due_date widget

    def on_set_due_today(self, widget):
        self.update_due_date(widget, "today")

    def on_set_due_tomorrow(self, widget):
        self.update_due_date(widget, "tomorrow")

    def on_set_due_next_week(self, widget):
        self.update_due_date(widget, "next week")

    def on_set_due_next_month(self, widget):
        self.update_due_date(widget, "next month")

    def on_set_due_next_year(self, widget):
        self.update_due_date(widget, "next year")
        
    def on_set_due_now(self, widget):
        self.update_due_date(widget, "now")
        
    def on_set_due_soon(self, widget):
        self.update_due_date(widget, "soon")
        
    def on_set_due_later(self, widget):
        self.update_due_date(widget, "later")

    def on_set_due_clear(self, widget):
        self.update_due_date(widget, None)

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
                tag_entry.set_text(self.last_added_tags)
                tag_entry.set_completion(self.tag_completion)
                apply_to_subtasks.set_active(self.last_apply_tags_to_subtasks)
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
                    if not tag.startswith('@'):
                        tag = "@" + tag 
                    new_tags.append(tag)
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

        # Rember the last actions
        self.last_added_tags = tag_entry.get_text()
        self.last_apply_tags_to_subtasks = apply_to_subtasks.get_active()
      
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
        self.tv_factory.disable_update_tags()

        #When you click on a tag, you want to unselect the tasks
        taglist = self.get_selected_tags()
        #We apply filters for every visible ViewTree
        for t in self.vtree_panes:
            #1st we reset the tags filter
            vtree = self.req.get_tasks_tree(name=t,refresh=False)
            vtree.reset_filters(refresh=False,transparent_only=True)
            #then applying the tag
            if len(taglist) > 0:
                #FIXME : support for multiple tags selection
                vtree.apply_filter(taglist[0],refresh=True)

        # When enable_update_tags we should update all tags to match
        # the current state. However, applying tag filter does not influence
        # other tags, because of transparent filter. Therefore there is no
        # self.tagree.refresh_all() => a significant optimization!
        # See do_toggle_workview()
        self.tv_factory.enable_update_tags()

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
        
    #If nospecial=True, only normal @tag are considered
    def get_selected_tags(self,nospecial=False):
        taglist = []
        if self.tagtreeview:
            taglist = self.tagtreeview.get_selected_nodes()
        #If no selection, we display all
        if not nospecial and (not taglist or len(taglist) < 0):
            taglist = ['gtg-tags-all']
        if nospecial:
            for t in list(taglist):
                if not t.startswith('@'):
                    taglist.remove(t)
        return taglist
    
    def reset_cursor(self):
        """ Returns the cursor to the tag that was selected prior
            to any right click action. Should be used whenever we're done
            working with any tag through a right click menu action.
            """
        if self.tag_active:
            self.tag_active = False
            path, col = self.previous_cursor
            if self.tagtreeview:
                self.tagtreeview.set_cursor(path, col, 0)
                
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
            if self.tagtreeview:
                self.tagtreeview.set_cursor(path, col, 0)

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
        self.browser_shown = False
        self.window.hide()
        gobject.idle_add(self.emit, "visibility-toggled")

    def show(self):
        """ Unhides the TaskBrowser """
        self.browser_shown = True
        self.window.present()
        #redraws the GDK window, bringing it to front
        self.window.show()
        gobject.idle_add(self.emit, "visibility-toggled")

    def iconify(self):
        """ Minimizes the TaskBrowser """
        self.window.iconify()

    def is_visible(self):
        """ Returns true if window is shown or false if hidden. """
        return self.window.get_property("visible")

    def is_active(self):
        """ Returns true if window is the currently active window """
        return self.window.get_property("is-active")

    def get_builder(self):
        return self.builder

    def get_window(self):
        return self.window

    def get_active_tree(self):
        '''
        Returns the browser tree with all the filters applied. The tasks in
        the tree are the same as the ones shown in the browser current view
        '''
        return self.activetree

    def get_closed_tree(self):
        '''
        Returns the browser tree with all the filters applied. The tasks in
        the tree are the same as the ones shown in the browser current closed
        view.
        '''
        return self.__create_closed_tree()

    def is_shown(self):
        return self.browser_shown

## BACKENDS RELATED METHODS ##################################################

    def on_backend_failed(self, sender, backend_id, error_code):
        '''
        Signal callback.
        When a backend fails to work, loads a gtk.Infobar to alert the user

        @param sender: not used, only here for signal compatibility
        @param backend_id: the id of the failing backend 
        @param error_code: a backend error code, as specified in BackendsSignals
        '''
        infobar = self._new_infobar(backend_id)
        infobar.set_error_code(error_code)

    def on_backend_needing_interaction(self, sender, backend_id, description, \
                                       interaction_type, callback):
        '''
        Signal callback.
        When a backend needs some kind of feedback from the user,
        loads a gtk.Infobar to alert the user.
        This is used, for example, to request confirmation after authenticating
        via OAuth.

        @param sender: not used, only here for signal compatibility
        @param backend_id: the id of the failing backend 
        @param description: a string describing the interaction needed
        @param interaction_type: a string describing the type of interaction
                                 (yes/no, only confirm, ok/cancel...)
        @param callback: the function to call when the user provides the
                         feedback
        '''
        infobar = self._new_infobar(backend_id)
        infobar.set_interaction_request(description, interaction_type, callback)


    def __remove_backend_infobar(self, child, backend_id):
        '''
        Helper function to remove an gtk.Infobar related to a backend

        @param child: a gtk.Infobar
        @param backend_id: the id of the backend which gtk.Infobar should be
                            removed.
        '''
        if isinstance(child, CustomInfoBar) and\
            child.get_backend_id() == backend_id:
            if self.vbox_toolbars:
                self.vbox_toolbars.remove(child)

    def remove_backend_infobar(self, sender, backend_id):
        '''
        Signal callback.
        Deletes the gtk.Infobars related to a backend

        @param sender: not used, only here for signal compatibility
        @param backend_id: the id of the backend which gtk.Infobar should be
                            removed.
        '''
        backend = self.req.get_backend(backend_id)
        if not backend or (backend and backend.is_enabled()):
            #remove old infobar related to backend_id, if any
            if self.vbox_toolbars:
                self.vbox_toolbars.foreach(self.__remove_backend_infobar, \
                                       backend_id)

    def _new_infobar(self, backend_id):
        '''
        Helper function to create a new infobar for a backend
        
        @param backend_id: the backend for which we're creating the infobar
        @returns gtk.Infobar: the created infobar
        '''
        #remove old infobar related to backend_id, if any
        if not self.vbox_toolbars:
            return
        self.vbox_toolbars.foreach(self.__remove_backend_infobar, backend_id)
        #add a new one
        infobar = CustomInfoBar(self.req, self, self.vmanager, backend_id)
        self.vbox_toolbars.pack_start(infobar, True)
        return infobar
