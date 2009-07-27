# -*- coding: utf-8 -*-
# pylint: disable-msg=W0201
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


#=== IMPORT ===================================================================
#system imports
import pygtk
pygtk.require('2.0')
import gobject
import gtk.glade
import threading
import xml.sax.saxutils as saxutils
import os
import locale
import re
import datetime

#our own imports
import GTG
from GTG import info
from GTG import _
from GTG.taskeditor.editor            import TaskEditor
from GTG.taskbrowser                  import GnomeConfig
from GTG.taskbrowser                  import browser_tools
from GTG.tools                        import colors, openurl

#=== OBJECTS ==================================================================

#=== MAIN CLASS ===============================================================

#Some default preferences that we should save in a file
WORKVIEW           = False
SIDEBAR            = False
CLOSED_PANE        = False
QUICKADD_PANE      = True
TOOLBAR            = True
BG_COLOR           = True
EXPERIMENTAL_NOTES = False


class TaskBrowser:

    def __init__(self, requester, config):

        # Object prime variables
        self.priv   = {}
        self.req    = requester
        self.config = config

        ### YOU CAN DEFINE YOUR INTERNAL MECHANICS VARIABLES BELOW
        # Task deletion
        self.tid_todelete = None # The tid that will be deleted
        # Editors
        self.opened_task  = {}   # This is the list of tasks that are already
                                 # opened in an editor of course it's empty
                                 # right now
        # Drag & drop
        self.drag_sources      = []
        self.path_source       = None
        self.path_target       = None
        self.tid_tomove        = None
        self.tid_source_parent = None
        self.tid_target_parent = None

        # Define various locks for multi-threading
        self.refresh_lock      = threading.Lock()
        self.refresh_lock_lock = threading.Lock()
        self.lock              = threading.Lock()

        # Setup default values for view
        self.init_browser_config()

        # Setup GTG icon theme
        self.init_icon_theme()

        # Load window tree
        self.wTree = gtk.glade.XML(GnomeConfig.GLADE_FILE)

        # Define aliases for specific widgets
        self.init_widget_aliases()

        #Set the tooltip for the toolbar buttons
        self.init_toolbar_tooltips()

        # Initialize "About" dialog
        self.init_about_dialog()

        #Create our dictionay and connect it
        self.init_signal_connections()

        # The tview and their model
        self.ctask_ts = browser_tools.new_ctask_ts()
        self.tag_ts   = browser_tools.new_tag_ts()
        self.task_ts  = browser_tools.new_task_ts(dnd_func=self.row_dragndrop)

        # Setting the default for the view
        # When there is no config, this should define the first configuration
        # of the UI
        self.init_view_defaults()

        # Connecting the refresh signal from the requester
        self.req.connect("refresh", self.do_refresh)

        # Define accelerator keys
        self.init_accelerators()

        # NOTES
        self.init_note_support()
        

### INIT HELPER FUNCTIONS #####################################################
    def init_browser_config(self):
        self.priv["collapsed_tid"]            = []
        self.priv["tasklist"]                 = {}
        self.priv["tasklist"]["sort_column"]  = None
        self.priv["tasklist"]["sort_order"]   = gtk.SORT_ASCENDING
        self.priv["ctasklist"]                = {}
        self.priv["ctasklist"]["sort_column"] = None
        self.priv["ctasklist"]["sort_order"]  = gtk.SORT_ASCENDING
        self.priv['selected_rows']            = None
        self.priv['workview']                 = False
        self.priv['noteview']                 = False

    def init_icon_theme(self):
        icon_dirs = [GTG.DATA_DIR, os.path.join(GTG.DATA_DIR, "icons")]
        for i in icon_dirs:
            gtk.icon_theme_get_default().prepend_search_path(i)
            gtk.window_set_default_icon_name("gtg")

    def init_widget_aliases(self):
        self.window             = self.wTree.get_widget("MainWindow")
        self.tagpopup           = self.wTree.get_widget("TagContextMenu")
        self.taskpopup          = self.wTree.get_widget("TaskContextMenu")
        self.ctaskpopup = \
            self.wTree.get_widget("ClosedTaskContextMenu")
        self.editbutton         = self.wTree.get_widget("edit_b")
        self.donebutton         = self.wTree.get_widget("mark_as_done_b")
        self.newtask            = self.wTree.get_widget("new_task_b")
        self.newsubtask         = self.wTree.get_widget("new_subtask_b")
        self.dismissbutton      = self.wTree.get_widget("dismiss")
        self.about              = self.wTree.get_widget("aboutdialog1")
        self.edit_mi            = self.wTree.get_widget("edit_mi")
        self.main_pane          = self.wTree.get_widget("main_pane")
        self.menu_view_workview = self.wTree.get_widget("view_workview")
        self.toggle_workview    = self.wTree.get_widget("workview_toggle")
        self.quickadd_entry     = self.wTree.get_widget("quickadd_field")
        self.sidebar            = self.wTree.get_widget("sidebar")
        self.closed_pane        = self.wTree.get_widget("closed_pane")
        self.toolbar            = self.wTree.get_widget("task_tb")
        self.quickadd_pane      = self.wTree.get_widget("quickadd_pane")
        # Tree views
        self.task_tview         = self.wTree.get_widget("task_tview")
        self.tag_tview          = self.wTree.get_widget("tag_tview")
        self.ctask_tview        = self.wTree.get_widget("taskdone_tview")
        # NOTES
        self.new_note_button    = self.wTree.get_widget("new_note_button")
        self.note_toggle        = self.wTree.get_widget("note_toggle")

    def init_toolbar_tooltips(self):
        self.donebutton.set_tooltip_text(GnomeConfig.MARK_DONE_TOOLTIP)
        self.editbutton.set_tooltip_text(GnomeConfig.EDIT_TOOLTIP)
        self.dismissbutton.set_tooltip_text(GnomeConfig.MARK_DISMISS_TOOLTIP)
        self.newtask.set_tooltip_text(GnomeConfig.NEW_TASK_TOOLTIP)
        self.newsubtask.set_tooltip_text(GnomeConfig.NEW_SUBTASK_TOOLTIP)
        self.toggle_workview.set_tooltip_text(\
            GnomeConfig.WORKVIEW_TOGGLE_TOOLTIP)

    def init_about_dialog(self):
        gtk.about_dialog_set_url_hook(lambda dialog, url: openurl.openurl(url))
        self.about.set_website(info.URL)
        self.about.set_website_label(info.URL)
        self.about.set_version(info.VERSION)
        self.about.set_authors(info.AUTHORS)
        self.about.set_artists(info.ARTISTS)
        self.about.set_translator_credits(info.TRANSLATORS)

    def init_signal_connections(self):

        SIGNAL_CONNECTIONS_DIC = {
            "on_add_task":
                self.on_add_task,
            "on_add_note":
                (self.on_add_task, 'Note'),
            "on_edit_active_task":
                self.on_edit_active_task,
            "on_edit_done_task":
                self.on_edit_done_task,
            "on_edit_note":
                self.on_edit_note,
            "on_delete_task":
                self.on_delete_task,
            "on_mark_as_done":
                self.on_mark_as_done,
            "on_dismiss_task":
                self.on_dismiss_task,
            "on_delete":
                self.on_delete,
            "on_move":
                self.on_move,
            "on_size_allocate":
                self.on_size_allocate,
            "gtk_main_quit":
                self.on_close,
            "on_select_tag":
                self.on_select_tag,
            "on_delete_confirm":
                self.on_delete_confirm,
            "on_delete_cancel":
                lambda x: x.hide,
            "on_add_subtask":
                self.on_add_subtask,
            "on_closed_task_treeview_button_press_event":
                self.on_closed_task_treeview_button_press_event,
            "on_closed_task_treeview_key_press_event":
                self.on_closed_task_treeview_key_press_event,
            "on_task_treeview_button_press_event":
                self.on_task_treeview_button_press_event,
            "on_task_treeview_key_press_event":
                self.on_task_treeview_key_press_event,
            "on_tag_treeview_button_press_event":
                self.on_tag_treeview_button_press_event,
            "on_colorchooser_activate":
                self.on_colorchooser_activate,
            "on_workview_toggled":
                self.on_workview_toggled,
            "on_note_toggled":
                self.on_note_toggled,
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
            "on_about_clicked":
                self.on_about_clicked,
            "on_about_close":
                self.on_about_close,
            "on_nonworkviewtag_toggled":
                self.on_nonworkviewtag_toggled}

        self.wTree.signal_autoconnect(SIGNAL_CONNECTIONS_DIC)
        if (self.window):
            self.window.connect("destroy", gtk.main_quit)

    def init_view_defaults(self):
        self.menu_view_workview.set_active(WORKVIEW)
        self.wTree.get_widget("view_sidebar").set_active(SIDEBAR)
        self.wTree.get_widget("view_closed").set_active(CLOSED_PANE)
        self.wTree.get_widget("view_quickadd").set_active(QUICKADD_PANE)
        self.wTree.get_widget("view_toolbar").set_active(TOOLBAR)
        self.priv["bg_color_enable"] = BG_COLOR
        self.ctask_ts.set_sort_column_id(browser_tools.CTASKS_MODEL_DDATE,\
            gtk.SORT_DESCENDING)

    def init_accelerators(self):

        agr = gtk.AccelGroup()
        self.wTree.get_widget("MainWindow").add_accel_group(agr)

        view_sidebar = self.wTree.get_widget("view_sidebar")
        key, mod     = gtk.accelerator_parse("F9")
        view_sidebar.add_accelerator("activate", agr, key, mod,\
            gtk.ACCEL_VISIBLE)

        file_quit = self.wTree.get_widget("file_quit")
        key, mod  = gtk.accelerator_parse("<Control>q")
        file_quit.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)

        edit_undo = self.wTree.get_widget("edit_undo")
        key, mod  = gtk.accelerator_parse("<Control>z")
        edit_undo.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)

        edit_redo = self.wTree.get_widget("edit_redo")
        key, mod  = gtk.accelerator_parse("<Control>y")
        edit_redo.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)

        new_task_mi = self.wTree.get_widget("new_task_mi")
        key, mod    = gtk.accelerator_parse("<Control>n")
        new_task_mi.add_accelerator("activate", agr, key, mod,\
            gtk.ACCEL_VISIBLE)

        new_subtask_mi = self.wTree.get_widget("new_subtask_mi")
        key, mod       = gtk.accelerator_parse("<Control><Shift>n")
        new_subtask_mi.add_accelerator("activate", agr, key, mod,\
            gtk.ACCEL_VISIBLE)

        edit_button = self.wTree.get_widget("edit_b")
        key, mod    = gtk.accelerator_parse("<Control>e")
        edit_button.add_accelerator("clicked", agr, key, mod,\
            gtk.ACCEL_VISIBLE)

        quickadd_field = self.wTree.get_widget('quickadd_field')
        key, mod = gtk.accelerator_parse('<Control>l')
        quickadd_field.add_accelerator(
            'grab-focus', agr, key, mod, gtk.ACCEL_VISIBLE)

        mark_done_mi = self.wTree.get_widget('mark_done_mi')
        key, mod = gtk.accelerator_parse('<Control>d')
        mark_done_mi.add_accelerator(
            'activate', agr, key, mod, gtk.ACCEL_VISIBLE)

        task_dismiss = self.wTree.get_widget('task_dismiss')
        key, mod = gtk.accelerator_parse('<Control>i')
        task_dismiss.add_accelerator(
            'activate', agr, key, mod, gtk.ACCEL_VISIBLE)

    def init_note_support(self):
        self.notes  = EXPERIMENTAL_NOTES
        # Hide notes if disabled
        if not self.notes:
            self.note_toggle.hide()
            self.new_note_button.hide()
        #Set the tooltip for the toolbar button
        self.new_note_button.set_tooltip_text("Create a new note")
        self.note_tview = self.wTree.get_widget("note_tview")
        self.note_tview = gtk.TreeView()
        self.note_tview.connect("row-activated", self.on_edit_note)
        self.note_tview.show()
        self.note_ts    = gtk.TreeStore(gobject.TYPE_PYOBJECT, str, str)

### HELPER FUNCTIONS ##########################################################
    def restore_state_from_conf(self):

        # Extract state from configuration dictionary
        if not "browser" in self.config:
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
                self.wTree.get_widget("view_sidebar").set_active(False)
                self.sidebar.hide()
            else:
                self.wTree.get_widget("view_sidebar").set_active(True)
                self.sidebar.show()


        if "closed_task_pane" in self.config["browser"]:
            closed_task_pane = eval(
                self.config["browser"]["closed_task_pane"])
            if not closed_task_pane:
                self.closed_pane.hide()
                self.wTree.get_widget("view_closed").set_active(False)
            else:
                self.closed_pane.show()
                self.wTree.get_widget("view_closed").set_active(True)

        if "ctask_pane_height" in self.config["browser"]:
            ctask_pane_height = eval(
                self.config["browser"]["ctask_pane_height"])
            self.wTree.get_widget("vpaned1").set_position(ctask_pane_height)

        if "toolbar" in self.config["browser"]:
            toolbar = eval(self.config["browser"]["toolbar"])
            if not toolbar:
                self.toolbar.hide()
                self.wTree.get_widget("view_toolbar").set_active(False)

        if "quick_add" in self.config["browser"]:
            quickadd_pane = eval(self.config["browser"]["quick_add"])
            if not quickadd_pane:
                self.quickadd_pane.hide()
                self.wTree.get_widget("view_quickadd").set_active(False)

        if "bg_color_enable" in self.config["browser"]:
            bgcol_enable = eval(self.config["browser"]["bg_color_enable"])
            self.priv["bg_color_enable"] = bgcol_enable
            self.wTree.get_widget("bgcol_enable").set_active(bgcol_enable)

        if "collapsed_tasks" in self.config["browser"]:
            self.priv["collapsed_tid"] = self.config[
                "browser"]["collapsed_tasks"]

        if "tasklist_sort" in self.config["browser"]:
            col_id, order = self.config["browser"]["tasklist_sort"]
            self.priv["sort_column"] = col_id
            try:
                col_id, order = int(col_id), int(order)
                sort_col = self.priv["tasklist"]["columns"][col_id]
                self.priv["tasklist"]["sort_column"] = sort_col
                if order == 0:
                    self.priv["tasklist"]["sort_order"] = gtk.SORT_ASCENDING
                if order == 1:
                    self.priv["tasklist"]["sort_order"] = gtk.SORT_DESCENDING
            except:
                print "Invalid configuration for sorting columns"

        if "view" in self.config["browser"]:
            view = self.config["browser"]["view"]
            if view == "workview":
                self.do_toggle_workview()

        if "experimental_notes" in self.config["browser"]:
            self.notes = eval(self.config["browser"]["experimental_notes"])
            if self.notes:
                self.note_toggle.show()
                self.new_note_button.show()
            else:
                self.note_toggle.hide()
                self.new_note_button.hide()

    def count_tasks_rec(self, my_task, active_tasks):
        count = 0
        for t in my_task.get_subtasks():
            if t.get_id() in active_tasks:
                if len(t.get_subtasks()) != 0:
                    count = count + 1 + self.count_tasks_rec(t, active_tasks)
                else:
                    count = count + 1
        return count

    def build_task_title(self, task, count, extended=False):
        simple_title = saxutils.escape(task.get_title())
        if extended:
            excerpt = task.get_excerpt(lines=2)
            if excerpt.strip() != "":
                title   = "<b><big>%s</big></b>\n<small>%s</small>"\
                     % (simple_title, excerpt)
            else:
                title   = "<b><big>%s</big></b>" % simple_title
        else:
            if (not self.priv['workview']):
                if count == 0:
                    title = "<span>%s</span>" % (simple_title)
                else:
                    title = "<span>%s (%s)</span>" % (simple_title, count)
            else:
                title = simple_title
        return title

    def do_toggle_workview(self):
        #We have to be careful here to avoid a loop of signals
        #menu_state   = self.menu_view_workview.get_active()
        #button_state = self.toggle_workview.get_active()
        #We cannot have note and workview at the same time
        if not self.priv['workview'] and self.note_toggle.get_active():
            self.note_toggle.set_active(False)
        #We do something only if both widget are in different state
        tobeset = not self.priv['workview']
        self.menu_view_workview.set_active(tobeset)
        self.toggle_workview.set_active(tobeset)
        self.priv['workview'] = tobeset
        self.do_refresh()

    def get_canonical_date(self, arg):
        """
        Transform "arg" in a valid yyyy-mm-dd date or return None.
        "arg" can be a yyyy-mm-dd, yyyymmdd, mmdd, today or a weekday name.
        """
        day_names_en = ["monday", "tuesday", "wednesday", "thursday",
                        "friday", "saturday", "sunday"]
        day_names = [_("monday"), _("tuesday"), _("wednesday"),
                     _("thursday"), _("friday"), _("saturday"),
                     _("sunday")]
        if re.match(r'\d{4}-\d{2}-\d{2}', arg):
            date = arg
        elif arg.isdigit():
            if len(arg) == 8:
                date = "%s-%s-%s" % (arg[:4], arg[4:6], arg[6:])
            elif len(arg) == 4:
                year = datetime.date.today().year
                date = "%i-%s-%s" % (year, arg[:2], arg[2:])
        elif arg.lower() == "today" or arg.lower() == _("today"):
            today = datetime.date.today()
            year = today.year
            month = today.month
            day = today.day
            date = "%i-%i-%i" % (year, month, day)
        elif arg.lower() == "tomorrow" or\
          arg.lower() == _("tomorrow"):
            today = datetime.date.today()
            tomorrow = today + datetime.timedelta(days=1)
            year = tomorrow.year
            month = tomorrow.month
            day = tomorrow.day
            date = "%i-%i-%i" % (year, month, day)
        elif arg.lower() in day_names_en or arg.lower() in day_names:
            today = datetime.date.today()
            today_day = today.weekday()
            if arg.lower() in day_names_en:
                arg_day = day_names_en.index(arg)
            else:
                arg_day = day_names.index(arg)
            if arg_day > today_day:
                delta = datetime.timedelta(days = arg_day-today_day)
            else:
                delta = datetime.timedelta(days = arg_day-today_day+7)
            next_date = today + delta
            year = next_date.year
            month = next_date.month
            day = next_date.day
            date = "%i-%i-%i" % (year, month, day)
        else:
            return None
        if self.is_date_valid(date):
            return date
        else:
            return None

    def is_date_valid(self, fulldate):
        """
        Return True if the date exists. False else.
        "fulldate" is yyyy-mm-dd
        """
        splited_date = fulldate.split("-")
        if len(splited_date) != 3:
            return False
        year, month, day = splited_date
        try:
            date = datetime.date(int(year), int(month), int(day))
        except ValueError:
            return False
        else:
            return True

    def update_collapsed_row(self, model, path, itera, user_data):
        """Build a list of task that must showed as collapsed in Treeview"""
        tid = self.task_ts.get_value(itera, 0)
        # Remove expanded rows
        if (self.task_ts.iter_has_child(itera) and
            self.task_tview.row_expanded(path) and
            tid in self.priv["collapsed_tid"]):

            self.priv["collapsed_tid"].remove(tid)

        # Append collapsed rows
        elif (self.task_ts.iter_has_child(itera) and
              not self.task_tview.row_expanded(path) and
              tid not in self.priv["collapsed_tid"]):

            self.priv["collapsed_tid"].append(tid)

        return False # Return False or the TreeModel.foreach() function ends

    def restore_collapsed(self, treeview, path, data):
        itera = self.task_ts.get_iter(path)
        tid = self.task_ts.get_value(itera, 0)
        if tid in self.priv["collapsed_tid"]:
            treeview.collapse_row(path)

    def add_task_tree_to_list(self, tree_store, tid, parent, selected_uid=None,
                              active_tasks=[], treeview=True):
        """Add tasks to a treeview.

        If 'treeview' is False, it becomes a flat list.
        """
        task = self.req.get_task(tid)
        st_count = self.count_tasks_rec(task, active_tasks)
        if selected_uid and selected_uid == tid:
            # Temporarily disabled
            #title = self.build_task_title(task, extended=True)
            title_str = self.build_task_title(task, st_count, extended=False)
        else:
            title_str = self.build_task_title(task, st_count, extended=False)


        # Extract data
        title = saxutils.escape(task.get_title())
        duedate_str = task.get_due_date()
        left_str = task.get_days_left()
        tags = task.get_tags()
        if self.priv["bg_color_enable"]:
            my_color = colors.background_color(tags)
        else:
            my_color = None

        if not parent and len(task.get_subtasks()) == 0:
            itera = tree_store.get_iter_first()
            my_row = tree_store.insert_before(
                None, itera,
                row=[tid, title, title_str, duedate_str, left_str, tags,
                     my_color])
        else:
            #None should be "parent" but crashing with thread
            my_row = tree_store.append(
                parent,
                [tid, title, title_str, duedate_str, left_str, tags, my_color])
        #If treeview, we add add the active childs
        if treeview:
            for c in task.get_subtasks():
                cid = c.get_id()
                if cid in active_tasks:
                    #None should be cid
                    self.add_task_tree_to_list(
                        tree_store, cid, my_row, selected_uid,
                        active_tasks=active_tasks)

    def select_task(self, id_toselect):
        """Select a task with tid 'id_toselect'.

        This works only in the main task_tview. If it cannot find the
        requested task, nothing is selected.
        """

        #We will loop over all task_tview element to find the newly added one
        model = self.task_tview.get_model()
        tempit = model.get_iter_first()
        it = None
        while (tempit and not it):
            if tempit:
                tid = model.get_value(tempit, 0)
                if tid == id_toselect:
                    it = tempit
            #First we try to see if there is child task
            tempit2 = model.iter_children(tempit)
            #if no children, then take the tasks on the same level
            if not tempit2:
                tempit2 = model.iter_next(tempit)
            #if no task on the same level, go back to the parent
            #and then to the next task on the parent level
            if not tempit2:
                tempit2 = model.iter_parent(tempit)
                if tempit2:
                    tempit2 = model.iter_next(tempit2)
            tempit = tempit2
        if it:
            selection = self.task_tview.get_selection()
            selection.select_iter(it)

    def open_task(self, uid):
        """Open the task identified by 'uid'.

        If a Task editor is already opened for a given task, we present it.
        Else, we create a new one.
        """
        t = self.req.get_task(uid)
        if uid in self.opened_task:
            self.opened_task[uid].present()
        else:
            tv = TaskEditor(
                self.req, t, self.do_refresh, self.on_delete_task,
                self.close_task, self.open_task, self.get_tasktitle,
                notes=self.notes)
            #registering as opened
            self.opened_task[uid] = tv

    def get_tasktitle(self, tid):
        task = self.req.get_task(tid)
        return task.get_title()

    def close_task(self, tid):
        # When an editor is closed, it should deregister itself.
        if tid in self.opened_task:
            del self.opened_task[tid]

    def row_dragndrop(self, tree, path, it, data=None):
        """Drag and drop support."""
        #Because of bug in pygtk, the rows-reordered signal is never emitted
        #We workaoround this bug by connecting to row_insert and row_deleted
        #Basically, we do the following:
        # 1. If a row is inserted for a task X, look if the task already
        #     exist elsewhere.
        # 2. If yes, it's probably a drag-n-drop so we save those information
        # 3. If the "elsewhere" from point 1 is deleted, we are sure it's a
        #    drag-n-drop so we change the parent of the moved task
        if data == "insert":
            #If the row inserted already exists in another position
            #We are in a drag n drop case
            def findsource(model, path, it, data):
                path_move = tree.get_path(data[1])
                path_actual = tree.get_path(it)
                if model.get(it, 0) == data[0] and path_move != path_actual:
                    self.drag_sources.append(path)
                    self.path_source = path
                    return True
                else:
                    self.path_source = None

            self.path_target = path
            tid = tree.get(it, 0)
            tree.foreach(findsource, [tid, it])
            if self.path_source:
                #We will prepare the drag-n-drop
                iter_source = tree.get_iter(self.path_source)
                iter_target = tree.get_iter(self.path_target)
                iter_source_parent = tree.iter_parent(iter_source)
                iter_target_parent = tree.iter_parent(iter_target)
                #the tid_parent will be None for root tasks
                if iter_source_parent:
                    sparent = tree.get(iter_source_parent, 0)[0]
                else:
                    sparent = None
                if iter_target_parent:
                    tparent = tree.get(iter_target_parent, 0)[0]
                else:
                    tparent = None
                #If target and source are the same, we are moving
                #a child of the deplaced task. Indeed, children are
                #also moved in the tree but their parents remain !
                if sparent != tparent:
                    self.tid_source_parent = sparent
                    self.tid_target_parent = tparent
                    self.tid_tomove = tid[0]
                    # "row %s will move from %s to %s"%(self.tid_tomove,\
                    #          self.tid_source_parent, self.tid_target_parent)
#    def row_deleted(self, tree, path, data=None): #pylint: disable-msg=W0613
        elif data == "delete":
            #If we are removing the path source guessed during the insertion
            #It confirms that we are in a drag-n-drop
            if path in self.drag_sources and self.tid_tomove:
                self.drag_sources.remove(path)
                # "row %s moved from %s to %s"%(self.tid_tomove,\
                #             self.tid_source_parent, self.tid_target_parent)
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

    def cmp_duedate_str(self, key1, key2):
        if self.priv["tasklist"]["sort_order"] == gtk.SORT_ASCENDING:
            if   key1 == "" and key2 == "":
                return  0
            elif key1 == "" and key2 != "":
                return -1
            elif key1 != "" and key2 == "":
                return  1
            else:
                return cmp(key1, key2)
        else:
            if   key1 == "" and key2 == "":
                return  0
            elif key1 == "" and key2 != "":
                return  1
            elif key1 != "" and key2 == "":
                return -1
            else:
                return cmp(key1, key2)

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
        if column == self.priv["tasklist"]["columns"]\
            [browser_tools.TASKLIST_COL_TITLE]:
            cmp_func = lambda x, y: locale.strcoll(x.lower(), y.lower())
            sort_key = lambda x: x[browser_tools.TASK_MODEL_TITLE]
        else:
            cmp_func = self.cmp_duedate_str
            sort_key = lambda x: x[browser_tools.TASK_MODEL_DDATE_STR]

        # Determine sorting direction
        if sort_order == gtk.SORT_ASCENDING:
            sort_reverse = True
        else:
            sort_reverse = False

        # Sort rows
        rows = [tuple(r) + (i, ) for i, r in enumerate(self.task_ts)]
        if len(rows) != 0:
            rows.sort(key=lambda x: x[browser_tools.TASK_MODEL_TITLE].lower())
            rows.sort(cmp=cmp_func, key=sort_key, reverse=sort_reverse)
            self.task_ts.reorder(None, [r[-1] for r in rows])

        # Display the sort indicator
        column.set_sort_indicator(True)
        column.set_sort_order(sort_order)

### SIGNAL CALLBACKS ##########################################################
# Typically, reaction to user input @ interactions with the GUI
#
    def on_move(self, widget, data):
        xpos, ypos = self.window.get_position()
        self.priv["window_xpos"] = xpos
        self.priv["window_ypos"] = ypos

    def on_size_allocate(self, widget, data):
        width, height = self.window.get_size()
        self.priv["window_width"]  = width
        self.priv["window_height"] = height

    def on_delete(self, widget, user_data):

        # Save expanded rows
        self.task_ts.foreach(self.update_collapsed_row, None)

        # Cleanup collapsed row list
        for tid in self.priv["collapsed_tid"]:
            if not self.req.has_task(tid):
                self.priv["collapsed_tid"].remove(tid)

        # Get configuration values
        tag_sidebar        = self.sidebar.get_property("visible")
        closed_pane        = self.closed_pane.get_property("visible")
        quickadd_pane      = self.quickadd_pane.get_property("visible")
        toolbar            = self.toolbar.get_property("visible")
        #task_tv_sort_id    = self.task_ts.get_sort_column_id()
        sort_column        = self.priv["tasklist"]["sort_column"]
        sort_order         = self.priv["tasklist"]["sort_order"]
        closed_pane_height = self.wTree.get_widget("vpaned1").get_position()

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
            'collapsed_tasks':
                self.priv["collapsed_tid"],
            'tag_pane':
                tag_sidebar,
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
            sort_col_id = self.priv["tasklist"]["columns"].index(sort_column)
            self.config["browser"]["tasklist_sort"]  = [sort_col_id, 0]
        elif sort_column is not None and sort_order == gtk.SORT_DESCENDING:
            sort_col_id = self.priv["tasklist"]["columns"].index(sort_column)
            self.config["browser"]["tasklist_sort"]  = [sort_col_id, 1]
        self.config["browser"]["view"]              = view
        if self.notes:
            self.config["browser"]["experimental_notes"] = True

    def on_about_clicked(self, widget):
        self.about.show()

    def on_about_close(self, widget, response):
        self.about.hide()

    def on_colorchooser_activate(self, widget):
        #TODO: Color chooser should be refactorized in its own class. Well, in
        #fact we should have a TagPropertiesEditor (like for project) Also,
        #color change should be immediate. There's no reason for a Ok/Cancel
        wTree = gtk.glade.XML(GnomeConfig.GLADE_FILE, "ColorChooser")
        #Create our dictionay and connect it
        dic = {"on_color_response": self.on_color_response}
        wTree.signal_autoconnect(dic)
        window = wTree.get_widget("ColorChooser")
        # Get previous color
        tags, notag_only = self.get_selected_tags()
        if len(tags) == 1:
            color = tags[0].get_attribute("color")
            if color != None:
                colorspec = gtk.gdk.Color(color)
                colorsel = window.colorsel
                colorsel.set_previous_color(colorspec)
                colorsel.set_current_color(colorspec)
        window.show()

    def on_color_response(self, widget, response):
        #the OK button return -5. Don't ask me why.
        if response == -5:
            colorsel = widget.colorsel
            gtkcolor = colorsel.get_current_color()
            strcolor = gtk.color_selection_palette_to_string([gtkcolor])
            tags, notag_only = self.get_selected_tags()
            for t in tags:
                t.set_attribute("color", strcolor)
        self.do_refresh()
        widget.destroy()

    def on_workview_toggled(self, widget):
        self.do_toggle_workview()

    def on_sidebar_toggled(self, widget):
        view_sidebar = self.wTree.get_widget("view_sidebar")
        if self.sidebar.get_property("visible"):
            view_sidebar.set_active(False)
            self.sidebar.hide()
        else:
            view_sidebar.set_active(True)
            self.sidebar.show()

    def on_note_toggled(self, widget):
        self.priv['noteview'] = not self.priv['noteview']
        workview_state = self.toggle_workview.get_active()
        if workview_state:
            self.toggle_workview.set_active(False)
        self.do_refresh()

    def on_closed_toggled(self, widget):
        if widget.get_active():
            self.closed_pane.show()
        else:
            self.closed_pane.hide()

    def on_bg_color_toggled(self, widget):
        if widget.get_active():
            self.priv["bg_color_enable"] = True
        else:
            self.priv["bg_color_enable"] = False
        self.do_refresh()

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

    def on_quickadd_activate(self, widget):
        text = self.quickadd_entry.get_text()
        due_date = None
        defer_date = None
        if text:
            tags, notagonly = self.get_selected_tags()
            # Get tags in the title
            for match in re.findall(r'[\s](@[^@,\s]+)', text):
                tags.append(GTG.core.tagstore.Tag(match))
                # Remove the @
                #text =text.replace(match,match[1:],1)
            # Get attributes
            regexp = r'([\s]*)([a-zA-Z0-9_-]+):([^\s]+)'
            for spaces, attribute, args in re.findall(regexp, text):
                valid_attribute = True
                if attribute.lower() == "tags" or \
                   attribute.lower() == _("tags"):
                    for tag in args.split(","):
                        tags.append(GTG.core.tagstore.Tag("@"+tag))
                elif attribute.lower() == "defer" or \
                     attribute.lower() == _("defer"):
                    defer_date = self.get_canonical_date(args)
                    if defer_date is None:
                        valid_attribute = False
                elif attribute.lower() == "due" or \
                     attribute.lower() == _("due"):
                    due_date = self.get_canonical_date(args)
                    if due_date is None:
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
            task = self.req.new_task(tags=tags, newtask=True)
            if text != "":
                task.set_title(text)
            if not due_date is None:
                task.set_due_date(due_date)
            if not defer_date is None:
                task.set_start_date(defer_date)
            id_toselect = task.get_id()
            #############
            self.quickadd_entry.set_text('')
            # Refresh the treeview
            self.do_refresh(toselect=id_toselect)

    def on_tag_treeview_button_press_event(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo #pylint: disable-msg=W0612
                treeview.grab_focus()
                treeview.set_cursor(path, col, 0)
                selected_tags = self.get_selected_tags()[0]
                if len(selected_tags) > 0:
                    # Then we are looking at single, normal tag rather than
                    # the special 'All tags' or 'Tasks without tags'. We only
                    # want to popup the menu for normal tags.
                    display_in_workview_item = self.tagpopup.get_children()[1]
                    selected_tag = selected_tags[0]
                    nonworkview = selected_tag.get_attribute("nonworkview")
                    # We must invert because the tagstore has "True" for tasks
                    # that are *not* in workview, and the checkbox is set if
                    # the tag *is* shown in the workview.
                    if nonworkview == "True":
                        shown = False
                    else:
                        shown = True
                    display_in_workview_item.set_active(shown)
                    self.tagpopup.popup(None, None, None, event.button, time)
            return 1

    def on_nonworkviewtag_toggled(self, widget):
        tags = self.get_selected_tags()[0]
        nonworkview_item = self.tagpopup.get_children()[1]
        #We must inverse because the tagstore has True
        #for tasks that are not in workview (and also convert to string)
        toset = str(not nonworkview_item.get_active())
        if len(tags) > 0:
            tags[0].set_attribute("nonworkview", toset)
        self.do_refresh()

    def on_task_treeview_button_press_event(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor(path, col, 0)
                self.taskpopup.popup(None, None, None, event.button, time)
            return 1

    def on_task_treeview_key_press_event(self, treeview, event):
        if gtk.gdk.keyval_name(event.keyval) == "Delete":
            self.on_delete_task()

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
            self.on_delete_task()

    def on_add_task(self, widget, status=None):
        tags, notagonly = self.get_selected_tags()
        task = self.req.new_task(tags=tags, newtask=True)
        uid = task.get_id()
        if status:
            task.set_status(status)
        self.open_task(uid)

    def on_add_subtask(self, widget):
        uid = self.get_selected_task()
        if uid:
            zetask = self.req.get_task(uid)
            tags   = zetask.get_tags()
            task   = self.req.new_task(tags=tags, newtask=True)
            task.add_parent(uid)
            zetask.add_subtask(task.get_id())
            self.open_task(task.get_id())
            self.do_refresh()

    def on_edit_active_task(self, widget, row=None, col=None):
        tid = self.get_selected_task()
        if tid:
            self.open_task(tid)

    def on_edit_done_task(self, widget, row=None, col=None):
        tid = self.get_selected_task(self.ctask_tview)
        if tid:
            self.open_task(tid)

    def on_edit_note(self, widget, row=None, col=None):
        tid = self.get_selected_task(self.note_tview)
        if tid:
            self.open_task(tid)

    def on_delete_confirm(self, widget):
        """if we pass a tid as a parameter, we delete directly
        otherwise, we will look which tid is selected"""
        self.req.delete_task(self.tid_todelete)
        self.tid_todelete = None
        self.do_refresh()

    def on_delete_task(self, widget=None, tid=None):
        #If we don't have a parameter, then take the selection in the treeview
        if not tid:
            #tid_to_delete is a [project,task] tuple
            self.tid_todelete = self.get_selected_task()
        else:
            self.tid_todelete = tid
        #We must at least have something to delete !
        if self.tid_todelete:
            delete_dialog = self.wTree.get_widget("confirm_delete")
            delete_dialog.run()
            delete_dialog.hide()
            #has the task been deleted ?
            return not self.tid_todelete
        else:
            return False

    def on_mark_as_done(self, widget):
        uid = self.get_selected_task()
        if uid:
            zetask = self.req.get_task(uid)
            status = zetask.get_status()
            if status == "Done":
                zetask.set_status("Active")
            else:
                zetask.set_status("Done")
            self.do_refresh()

    def on_dismiss_task(self, widget):
        uid = self.get_selected_task()
        if uid:
            zetask = self.req.get_task(uid)
            status = zetask.get_status()
            if status == "Dismiss":
                zetask.set_status("Active")
            else:
                zetask.set_status("Dismiss")
            self.do_refresh()

    def on_select_tag(self, widget, row=None, col=None):
        #When you clic on a tag, you want to unselect the tasks
        self.task_tview.get_selection().unselect_all()
        self.ctask_tview.get_selection().unselect_all()
        self.do_refresh()

    def on_taskdone_cursor_changed(self, selection=None):
        """Called when selection changes in closed task view.

        Changes the way the selected task is displayed.
        """
        #We unselect all in the active task view
        #Only if something is selected in the closed task list
        #And we change the status of the Done/dismiss button
        self.donebutton.set_icon_name("gtg-task-done")
        self.dismissbutton.set_icon_name("gtg-task-dismiss")
        if selection.count_selected_rows() > 0:
            tid = self.get_selected_task(self.ctask_tview)
            task = self.req.get_task(tid)
            self.task_tview.get_selection().unselect_all()
            self.note_tview.get_selection().unselect_all()
            if task.get_status() == "Dismiss":
                self.wTree.get_widget(
                    "ctcm_mark_as_not_done").set_sensitive(False)
                self.wTree.get_widget("ctcm_undismiss").set_sensitive(True)
                self.dismissbutton.set_label(GnomeConfig.MARK_UNDISMISS)
                self.donebutton.set_label(GnomeConfig.MARK_DONE)
                self.donebutton.set_tooltip_text(GnomeConfig.MARK_DONE_TOOLTIP)
                self.dismissbutton.set_icon_name("gtg-task-undismiss")
                self.dismissbutton.set_tooltip_text(
                    GnomeConfig.MARK_UNDISMISS_TOOLTIP)
#                self.editbutton.connect('clicked', self.on_edit_done_task)
#                self.edit_mi.connect('activate', self.on_edit_done_task)
            else:
                self.wTree.get_widget(
                    "ctcm_mark_as_not_done").set_sensitive(True)
                self.wTree.get_widget("ctcm_undismiss").set_sensitive(False)
                self.donebutton.set_label(GnomeConfig.MARK_UNDONE)
                self.donebutton.set_tooltip_text(
                    GnomeConfig.MARK_UNDONE_TOOLTIP)
                self.dismissbutton.set_label(GnomeConfig.MARK_DISMISS)
                self.dismissbutton.set_tooltip_text(
                    GnomeConfig.MARK_DISMISS_TOOLTIP)
                self.donebutton.set_icon_name("gtg-task-undone")

    def on_task_cursor_changed(self, selection=None):
        """Called when selection changes in the active task view.

        Changes the way the selected task is displayed.
        """
        #We unselect all in the closed task view
        #Only if something is selected in the active task list
        self.donebutton.set_icon_name("gtg-task-done")
        self.dismissbutton.set_icon_name("gtg-task-dismiss")
        if selection.count_selected_rows() > 0:
            self.ctask_tview.get_selection().unselect_all()
            self.note_tview.get_selection().unselect_all()
            self.donebutton.set_label(GnomeConfig.MARK_DONE)
            self.donebutton.set_tooltip_text(GnomeConfig.MARK_DONE_TOOLTIP)
            self.dismissbutton.set_label(GnomeConfig.MARK_DISMISS)
        #We reset the previously selected task
        if (self.priv["selected_rows"]
            and self.task_ts.iter_is_valid(self.priv["selected_rows"])):
            tid = self.task_ts.get_value(
                self.priv["selected_rows"], self.TASK_MODEL_OBJ)
            task = self.req.get_task(tid)
            title = self.build_task_title(task, extended=False)
            self.task_ts.set_value(
                self.priv["selected_rows"], self.TASK_MODEL_TITLE, title)
        #We change the selection title
        #if selection:
            #ts, itera = selection.get_selected() #pylint: disable-msg=W0612
            #if itera and self.task_ts.iter_is_valid(itera):
                #tid = self.task_ts.get_value(itera, self.TASK_MODEL_OBJ)
                #task = self.req.get_task(tid)
                #self.priv["selected_rows"] = itera
                # Extended title is temporarily disabled
                #title = self.build_task_title(task, extended=True)
                #title = self.build_task_title(task, extended=False)
                #self.task_ts.set_value(
                #    self.priv["selected_rows"], self.TASK_MODEL_TITLE, title)
        return

    def on_note_cursor_changed(self, selection=None):
        #We unselect all in the closed task view
        #Only if something is selected in the active task list
        if selection.count_selected_rows() > 0:
            self.ctask_tview.get_selection().unselect_all()
            self.task_tview.get_selection().unselect_all()

    def on_close(self, widget=None):
        """Closing the window."""
        #Saving is now done in main.py
        self.on_delete(None, None)
        gtk.main_quit()

### LIST REFRESH FUNCTIONS ####################################################
#
    def do_refresh(self, sender=None, param=None, toselect=None):
        #We ask to do the refresh in a gtk thread
        #We use a lock_lock like described in
        #http://ploum.frimouvy.org/?202-the-signals-and-threads-flying-circus
        if self.refresh_lock_lock.acquire(False):
            gobject.idle_add(self.refresh_tb, sender, toselect)
        #If we have something toselect, we cannot skip the refresh
        elif toselect:
            gobject.idle_add(self.select_task, toselect)

    def refresh_tb(self, fromtask=None, toselect=None):
        """Refresh the task browser.

        If a task asked for the refresh, we don't refresh it to avoid a loop
        New use refresh_tb directly, use "do_refresh".
        """
        self.refresh_lock.acquire()
        try:
            self.refresh_lock_lock.release()
            current_pane = self.main_pane.get_child()
            if self.priv['noteview']:
                if current_pane == self.task_tview:
                    self.main_pane.remove(current_pane)
                    self.main_pane.add(self.note_tview)
                self.refresh_note()
            else:
                if current_pane == self.note_tview:
                    self.main_pane.remove(current_pane)
                    self.main_pane.add(self.task_tview)
                self.refresh_list(toselect=toselect)
            self.refresh_closed()
            self.refresh_tags()
            #Refreshing the opened editors
            for uid in self.opened_task:
                if uid != fromtask:
                    self.opened_task[uid].refresh_editor()
        finally:
            self.refresh_lock.release()

    def refresh_tags(self):
        """Refresh the tag list.

        Not needed very often.
        """
        select = self.tag_tview.get_selection()
        t_path = None
        if select:
            t_model, t_path = select.get_selected_rows()
        self.tag_ts.clear()
        alltag       = self.req.get_alltag_tag()
        notag        = self.req.get_notag_tag()
        if self.priv['workview']:
            count_all_task = len(self.req.get_active_tasks_list(workable=True))
            count_no_tags  = len(\
                self.req.get_active_tasks_list(notag_only=True, workable=True))
        else:
            count_all_task = len(self.req.get_tasks_list(started_only=False))
            count_no_tags  = len(self.req.get_tasks_list(notag_only=True,\
                                                         started_only=False))

        self.tag_ts.append([alltag, None,
            _("<span weight=\"bold\">All tags</span>"),
            str(count_all_task), False])
        self.tag_ts.append([notag, None,
            _("<span weight=\"bold\">Tasks without tags</span>"),
            str(count_no_tags), False])
        self.tag_ts.append([None, None, "", "", True])

        tags = self.req.get_used_tags()
        for tag in tags:
            color = tag.get_attribute("color")
            if self.priv['workview']:
                count = len(\
                    self.req.get_active_tasks_list(tags=[tag], workable=True))
            else:
                count = len(\
                    self.req.get_tasks_list(started_only=False, tags=[tag]))
            #We display the tags without the "@" (but we could)
            if count != 0:
                self.tag_ts.append([tag, color, tag.get_name()[1:],\
                    str(count), False])

        #We reselect the selected tag
        if t_path:
            for i in t_path:
                self.tag_tview.get_selection().select_path(i)

    def refresh_list(self, a=None, toselect=None):
        """Refresh or build the TreeStore of tasks."""

        # Save collapsed rows
        self.task_ts.foreach(self.update_collapsed_row, None)

        #selected tasks:
        selected_uid = self.get_selected_task(self.task_tview)
        tselect = self.task_tview.get_selection()
        t_path = None
        if tselect:
            t_model, t_path = tselect.get_selected_rows()

        #Scroll position:
        vscroll_value = self.task_tview.get_vadjustment().get_value()
        hscroll_value = self.task_tview.get_hadjustment().get_value()

        #to refresh the list we build a new treestore then replace the existing
        new_taskts = browser_tools.new_task_ts(dnd_func=self.row_dragndrop)
        tag_list, notag_only = self.get_selected_tags()
        nbr_of_tasks = 0

        #We build the active tasks pane
        if self.priv["workview"]:
            tasks = self.req.get_active_tasks_list(
                tags=tag_list, notag_only=notag_only, workable=True,
                started_only=False)
            for tid in tasks:
                self.add_task_tree_to_list(
                    new_taskts, tid, None, selected_uid, treeview=False)
            nbr_of_tasks = len(tasks)

        else:
            #building the classical treeview
            active_root_tasks = self.req.get_active_tasks_list(
                tags=tag_list, notag_only=notag_only, is_root=True,
                started_only=False)
            active_tasks = self.req.get_active_tasks_list(
                tags=tag_list, notag_only=notag_only, is_root=False,
                started_only=False)
            for tid in active_root_tasks:
                self.add_task_tree_to_list(
                    new_taskts, tid, None, selected_uid,
                    active_tasks=active_tasks)
            nbr_of_tasks = len(active_tasks)

        #Set the title of the window:
        if nbr_of_tasks == 0:
            parenthesis = _("(no active tasks)")
        elif nbr_of_tasks == 1:
            parenthesis = _("(1 active task)")
        else:
            parenthesis = "(%s active tasks)"%nbr_of_tasks
        self.window.set_title("Getting Things GNOME! %s"%parenthesis)
        self.task_tview.set_model(new_taskts)
        self.task_ts = new_taskts
        #We expand all the we close the tasks who were not saved as "expanded"
        self.task_tview.expand_all()
        self.task_tview.map_expanded_rows(self.restore_collapsed, None)
        # Restore sorting
        if not self.priv["noteview"]:
            # XXX: This can be done much more simply using {}.get(). -- jml,
            # 2009-07-18.
            if ('sort_column' in self.priv["tasklist"] and
                'sort_order' in self.priv["tasklist"]):
                if (self.priv["tasklist"]["sort_column"] is not None and
                    self.priv["tasklist"]["sort_order"] is not None):
                    self.sort_tasklist_rows(
                        self.priv["tasklist"]["sort_column"],
                        self.priv["tasklist"]["sort_order"])
        #We reselect the selected tasks
        if toselect:
            self.select_task(toselect)
        elif t_path:
            selection = self.task_tview.get_selection()
            for i in t_path:
                selection.select_path(i)

        def restore_vscroll(old_position):
            vadjust = self.task_tview.get_vadjustment()
            #We ensure that we will not scroll out of the window
            #It was bug #331285
            vscroll = min(old_position, (vadjust.upper - vadjust.page_size))
            vadjust.set_value(vscroll)

        def restore_hscroll(old_position):
            hadjust = self.task_tview.get_hadjustment()
            hscroll = min(old_position, (hadjust.upper - hadjust.page_size))
            hadjust.set_value(hscroll)

        #scroll position
        #We have to call that in another thread, else it will not work
        gobject.idle_add(restore_vscroll, vscroll_value)
        gobject.idle_add(restore_hscroll, hscroll_value)

    def refresh_closed(self):
        """Refresh the closed tasks pane."""

        #We build the closed tasks pane
        dselect = self.ctask_tview.get_selection()
        d_path = None
        if dselect:
            d_model, d_path = dselect.get_selected_rows()
        #We empty the pane
        self.ctask_ts.clear()
        #We rebuild it
        tag_list, notag_only = self.get_selected_tags()
        closed_tasks = self.req.get_closed_tasks_list(tags=tag_list,\
                                                    notag_only=notag_only)
        for tid in closed_tasks:
            t              = self.req.get_task(tid)
            title_str      = saxutils.escape(t.get_title())
            closeddate     = t.get_closed_date()
            closeddate_str = closeddate
            tags           = t.get_tags()
            if self.priv["bg_color_enable"] and t.has_tags():
                my_color = colors.background_color(t.get_tags())
            else:
                my_color = None
            if t.get_status() == "Dismiss":
                title_str =\
                     "<span color=\"#AAAAAA\">%s</span>" % title_str
                closeddate_str =\
                     "<span color=\"#AAAAAA\">%s</span>" % closeddate
            self.ctask_ts.append(None, [\
                tid, t.get_color(), title_str, closeddate, closeddate_str,
                my_color, tags])
        closed_selection = self.ctask_tview.get_selection()
        if d_path:
            for i in d_path:
                closed_selection.select_path(i)
        self.ctask_ts.set_sort_column_id(\
            browser_tools.CTASKS_MODEL_DDATE, gtk.SORT_DESCENDING)

    def refresh_note(self):
        """Refresh the notes pane."""

        #We build the notes pane
        dselect = self.note_tview.get_selection()
        d_path = None
        if dselect:
            d_model, d_path = dselect.get_selected_rows()
        #We empty the pane
        self.note_ts.clear()
        #We rebuild it
        tag_list, notag_only = self.get_selected_tags()
        notes = self.req.get_notes_list(tags=tag_list, notag_only=notag_only)
        for tid in notes:
            t              = self.req.get_task(tid)
            title_str      = saxutils.escape(t.get_title())
            self.note_ts.append(None, [tid, t.get_color(), title_str])
        note_selection = self.note_tview.get_selection()
        if d_path:
            for i in d_path:
                note_selection.select_path(i)
        #self.note_ts.set_sort_column_id\
        #(browser_tools.CTASKS_MODEL_DDATE, gtk.SORT_DESCENDING)
        return

### PUBLIC METHODS ############################################################
#
    def get_selected_task(self, tv=None):
        """Return the 'uid' of the selected task

        :param tv: The tree view to find the selected task in. Defaults to
            the task_tview.
        """
        uid = None
        if not tv:
            tview = self.task_tview
        else:
            tview = tv
        # Get the selection in the gtk.TreeView
        selection = tview.get_selection()
        #If we don't have anything and no tview specified
        #Let's have a look in the closed task view
        if selection and selection.count_selected_rows() <= 0 and not tv:
            tview = self.ctask_tview
            selection = tview.get_selection()
        #Then in the notes pane
        if selection and selection.count_selected_rows() <= 0 and not tv:
            tview = self.note_tview
            selection = tview.get_selection()
        # Get the selection iter
        if selection:
            model, selection_iter = selection.get_selected()
            if selection_iter:
                ts = tview.get_model()
                uid = ts.get_value(selection_iter, 0)
        return uid

    def get_selected_tags(self):
        t_selected = self.tag_tview.get_selection()
        t_iter = None
        if t_selected:
            tmodel, t_iter = t_selected.get_selected()
        notag_only = False
        tag = []
        if t_iter:
            selected = self.tag_ts.get_value(t_iter, 0)
            special = selected.get_attribute("special")
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

### MAIN ######################################################################
#
    def _visible_func(self, model, titer):
        return True

    def main(self):

        # Here we will define the main TaskList interface
        gobject.threads_init()

        # The tags treeview
        browser_tools.init_tags_tview(self.tag_tview)
        self.tag_tview.set_model(self.tag_ts)

        # The Active tasks treeview
        col = browser_tools.init_task_tview(\
            self.task_tview, self.sort_tasklist_rows)
        self.priv["tasklist"]["columns"] = col
        modelfilter = self.task_ts.filter_new()
        modelfilter.set_visible_func(self._visible_func)
        self.task_tview.set_model(modelfilter)
        #self.task_tview.set_model(self.task_ts)

        # The done/dismissed taks treeview
        col = browser_tools.init_closed_tasks_tview(\
            self.ctask_tview, self.sort_tasklist_rows)
        self.priv["ctasklist"]["columns"] = col
        self.ctask_tview.set_model(self.ctask_ts)

        # The treeview for notes
        browser_tools.init_note_tview(self.note_tview)
        self.note_tview.set_model(self.note_ts)

        # Put the content in those treeviews
        self.do_refresh()

        # Watch for selections in the treeview
        selection = self.task_tview.get_selection()
        closed_selection = self.ctask_tview.get_selection()
        note_selection = self.note_tview.get_selection()
        selection.connect("changed", self.on_task_cursor_changed)
        closed_selection.connect("changed", self.on_taskdone_cursor_changed)
        note_selection.connect("changed", self.on_note_cursor_changed)

        # Restore state from config
        self.restore_state_from_conf()
        self.window.show()

        gtk.main()
        return 0
