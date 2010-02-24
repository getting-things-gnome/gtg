# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
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

import gtk
import gobject
import pango
import xml.sax.saxutils as saxutils

from GTG import _
from GTG.core.tree import Tree, TreeNode
from GTG.tools     import colors
from GTG.core.task import Task
from GTG.taskbrowser.CellRendererTags import CellRendererTags

COL_TID       = 0
COL_OBJ       = 1
COL_TITLE     = 2
COL_DDATE     = 3
COL_CDATE     = 4
COL_CDATE_STR = 5
COL_DLEFT     = 6
COL_TAGS      = 7
COL_LABEL     = 9
COL_SDATE     = 10
COL_DUE       = 11

class TaskTreeModel(gtk.GenericTreeModel):

    column_types = (\
        str,\
        gobject.TYPE_PYOBJECT,\
        str,\
        str,\
        str,\
        str,\
        str,\
        gobject.TYPE_PYOBJECT,\
        str,\
        str,\
        str,\
        str)

    def __init__(self, requester,tree=None):
        
        gtk.GenericTreeModel.__init__(self)
        self.req  = requester
        if tree:
            self.tree = tree
        else:
            self.tree = self.req.get_main_tasks_tree()
        self.tree.register_view(self)

### TREE MODEL HELPER FUNCTIONS ###############################################

    def _count_active_subtasks_rec(self, task):
        count = 0
        if task.has_child():
            for tid in task.get_children():
                task = self.req.get_task(tid)
                if task and task.get_status() == Task.STA_ACTIVE:
                    count = count + 1 + self._count_active_subtasks_rec(task)
        return count

### TREEMODEL INTERFACE ######################################################
#
    def on_get_flags(self):
#        print "on_get_flags"
        return gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
#        print "on_get_n_columns"
        return len(self.column_types)

    def on_get_column_type(self, n):
#        print "on_get_column_type %s" %n
        return self.column_types[n]

    def on_get_value(self, node, column):
#        print "on_get_value for %s, col %s" %(node.get_id(),column)
        if not node:
            return None
        else:
            #FIXME. The Task is a TreeNode object but
            #TreeNode is not recognized as a Task!
            task = self.req.get_task(node.get_id())
            if not task:
                return None
        if   column == COL_TID:
            return task.get_id()
        elif column == COL_OBJ:
            return task
        elif column == COL_TITLE:
            return saxutils.escape(task.get_title())
        elif column == COL_SDATE:
            return task.get_start_date().to_readable_string()
        elif column == COL_DDATE:
            return task.get_due_date().to_readable_string()
        elif column == COL_DUE:
            return task.get_due_date().to_readable_string()
        elif column == COL_CDATE:
            return task.get_closed_date().to_readable_string()
        elif column == COL_CDATE_STR:
            if task.get_status() == Task.STA_DISMISSED:
                date = "<span color='#AAAAAA'>" +\
                    str(task.get_closed_date()) + "</span>"
            else:
                date = str(task.get_closed_date())
            return date
        elif column == COL_DLEFT:
            return task.get_days_left()
        elif column == COL_TAGS:
            tags = task.get_tags()
            tags.sort(key = lambda x: x.get_name())
            return tags
        elif column == COL_LABEL:
            if task.get_status() == Task.STA_ACTIVE:
                count = self._count_active_subtasks_rec(task)
                if count != 0:
                    title = saxutils.escape(task.get_title()) + " (%s)" % count
                else:
                    title = saxutils.escape(task.get_title())
            elif task.get_status() == Task.STA_DISMISSED:
                    title = "<span color='#AAAAAA'>"\
                        + saxutils.escape(task.get_title()) + "</span>"
            else:
                title = saxutils.escape(task.get_title())
            return title

    def on_get_iter(self, path):
#        print "on_get_iter for %s" %(str(path))
        return self.tree.get_node_for_path(path)

    def on_get_path(self, node):
#        print "on_get_path: %s" %node.get_id()
        return self.tree.get_path_for_node(node)

    def on_iter_next(self, node):
#        print "on_iter_next %s" %node.get_id()
        return self.tree.next_node(node)

    def on_iter_children(self, node):
#        print "on_iter_children %s" %node.get_id()
        return self.tree.node_children(node)

    def on_iter_has_child(self, node):
#        print "on_iter_has_child %s" %node.get_id()
        return self.tree.node_has_child(node)

    def on_iter_n_children(self, node):
#        if node:
#            id = node.get_id()
#        else:
#            id = "Null node"
#        print "on_iter_n_children %s" %id
        return self.tree.node_n_children(node)

    def on_iter_nth_child(self, node, n):
#        if node:
#            id = node.get_id()
#        else:
#            id = "Null node"
#        print "on_iter_nth_child %s - %s" %(id,n)
        return self.tree.node_nth_child(node,n)

    def on_iter_parent(self, node):
#        print "on_iter_parent %s" %node.get_id()
        return self.tree.node_parent(node)

    def update_task(self, tid):
#        # get the node and signal it's changed
#        print "tasktree update_task"
        my_node = self.tree.get_node(tid)
        if my_node and my_node.is_loaded():
            node_path = self.tree.get_path_for_node(my_node)
            if node_path:
#                print "**** tasktree update_task %s to path %s" %(tid,str(node_path))
                node_iter = self.get_iter(node_path)
                self.row_changed(node_path, node_iter)
                self.row_has_child_toggled(node_path, node_iter)
#                parent = self.tree.node_parent(my_node)
#                if parent:
#                    par_path = self.tree.get_path_for_node(parent)
#                    par_iter = self.get_iter(par_path)
##                    print "tasktree child toogled %s" %tid
#                    self.row_has_child_toggled(par_path, par_iter)
            else: 
                print "!!!!!!!!! no path for node %s" %tid
        
#        print "################"
#        print self.tree.print_tree()
#        print "tree nodes : %s" %self.tree.get_all_keys()
#        print "root children = %s" %self.tree.get_root().get_children()
        
    def add_task(self, tid):
#        print "tasktree add_task %s" %tid
##        nodes = []
##        # get the task
        task = self.tree.get_node(tid)
        if task:
            node_path = self.tree.get_path_for_node(task)
            #if node_path is null, the task is not currently displayed
            if node_path:
                node_iter = self.get_iter(node_path)
#                print "tasktree add_task %s at %s" %(tid,node_path)
                self.row_inserted(node_path, node_iter)
                parent = self.tree.node_parent(task)
                if parent:
                    par_path = self.tree.get_path_for_node(parent)
                    par_iter = self.get_iter(par_path)
#                    print "tasktree child toogled %s" %tid
                    self.row_has_child_toggled(par_path, par_iter)
##        # insert the task in the tree (root)
##        #TreeNode
##        my_node = task
##        self.tree.add_node(task)

##        nodes.append(my_node)
##        # has the task parents?
##        if task.has_parents():
##            # get every path from parents
##            par_list = task.get_parents()
##            # get every paths going to each parent
##            for par_tid in par_list:
##                if not self.tree.has_node(par_tid):
##                    #print " - %s: %s is not loaded." % (tid, par_tid)
##                    continue
##                else:
##                    par_node = self.tree.get_node(par_tid)
##                    self.tree.add_node(task, parent=par_node)
##                    node_path = self.tree.get_path_for_node(task)
##                    node_iter = self.get_iter(node_path)
##                    self.row_inserted(node_path, node_iter)
##                    nodes.append(task)
##        # has the task children?
##        for node in nodes:
##            self._add_all_subtasks(node, task)
##            node_path = self.tree.get_path_for_node(node)
##            if node_path:
##                node_iter = self.get_iter(node_path)
##                self.row_has_child_toggled(node_path, node_iter)

    def remove_task(self, tid):
        #print "tasktree remove_task %s" %tid
        node = self.tree.get_node(tid)
        removed = False
        node_path = self.tree.get_path_for_node(node)
        if node_path:
#            print "* tasktree REMOVE %s - %s " %(tid,node_path)
            self.row_deleted(node_path)
            removed = True
        return removed
                    
    def move_task(self, parent, child):
        print "dummy Moving %s below %s (tasktree)" % (child, parent)
#        # Get child
#        child_tid  = self.get_value(child, COL_TID)
#        child_task = self.req.get_task(child_tid)
#        #if we move a task, this task should be saved, even if new
#        child_task.set_to_keep()
#        # Get old parent
#        old_par = self.iter_parent(child)
#        if old_par:
#            old_par_tid  = self.get_value(old_par, COL_TID)
#            old_par_task = self.req.get_task(old_par_tid)
#        else:
#            old_par_task = None
#        # Get new parent
#        if parent:
#            new_par_tid  = self.get_value(parent, COL_TID)
#            new_par_task = self.req.get_task(new_par_tid)
#        else:
#            new_par_task = None
#            
#        # prevent illegal moves
#        c = parent
#        while c is not None:
#            t = self.get_value(c, COL_OBJ)
#            if t is child_task: return
#            c = self.iter_parent(c)
#        
#        # Remove child from old parent
#        if old_par_task:
#            old_par_task.remove_subtask(child_tid)
#        # Remove old parent from child
#        if old_par_task:
#            child_task.remove_parent(old_par_tid)
#        # Add child to new parent (add_subtask also add new parent to child)
#        if new_par_task:
#            new_par_task.add_subtask(child_tid)

#    def refilter(self):
#        for tid in self.req.get_all_tasks_list():
#            self.update_task(tid)

class TaskTreeView(gtk.TreeView):
    """TreeView for display of a list of task. Handles DnD primitives too."""

    def __init__(self, model=None):
        gtk.TreeView.__init__(self)
        self.columns = []
        self.bg_color_enable = True
        self.show()
        
    def set_bg_color(self, val):
        self.bg_color_enable = val

    def _celldatafunction(self, column, cell, model, iter):
        if self.bg_color_enable:
            bgcolor = column.get_tree_view().get_style().base[gtk.STATE_NORMAL]
            value = model.get_value(iter, COL_TAGS)
            if value:
                col = colors.background_color(value, bgcolor)
            else:
                col = None
        else:
            col = None
        cell.set_property("cell-background", col)

    def get_column(self, index):
        return self.columns[index]

    def get_column_index(self, col_id):
        return self.columns.index(col_id)

    def refresh(self, collapsed_rows=None):
        print "dummy refresh"
#        self.expand_all()
#        self.get_model().foreach(self._refresh_func, collapsed_rows)

    def _refresh_func(self, model, path, iter, collapsed_rows=None):
        if collapsed_rows:
            tid = model.get_value(iter, COL_TID)
            if tid in collapsed_rows:
                self.collapse_row(path)
        model.row_changed(path, iter)

class ActiveTaskTreeView(TaskTreeView):
    """TreeView for display of a list of task. Handles DnD primitives too."""

    DND_TARGETS = [
        ('gtg/task-iter-str', gtk.TARGET_SAME_WIDGET, 0)
    ]

    def __init__(self):
        TaskTreeView.__init__(self)
        self._init_tree_view()
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

        # Drag and drop
        self.enable_model_drag_source(\
            gtk.gdk.BUTTON1_MASK,
            self.DND_TARGETS,
            gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_MOVE)
        self.enable_model_drag_dest(\
            self.DND_TARGETS,
            gtk.gdk.ACTION_DEFAULT)
 
        self.drag_source_set(\
            gtk.gdk.BUTTON1_MASK,
            self.DND_TARGETS,
            gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_MOVE)

        self.drag_dest_set(\
            gtk.DEST_DEFAULT_ALL,
            self.DND_TARGETS,
            gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_MOVE)

        self.connect('drag_drop', self.on_drag_drop)
        self.connect('drag_data_get', self.on_drag_data_get)
        self.connect('drag_data_received', self.on_drag_data_received)
        self.connect('button_press_event', self.on_button_press)
        self.connect('button_release_event', self.on_button_release)
        self.defer_select = False

    def _init_tree_view(self):
        # Tag column
        tag_col     = gtk.TreeViewColumn()
        render_tags = CellRendererTags()
        tag_col.set_title(_("Tags"))
        tag_col.pack_start(render_tags, expand=False)
        tag_col.add_attribute(render_tags, "tag_list", COL_TAGS)
        render_tags.set_property('xalign', 0.0)
        tag_col.set_resizable(False)
        tag_col.set_cell_data_func(render_tags, self._celldatafunction)
        #tag_col.set_clickable         (True)
        #tag_col.connect               ('clicked', tv_sort_cb)
        self.append_column(tag_col)
        self.columns.insert(COL_TAGS, tag_col)

        # Title column
        title_col   = gtk.TreeViewColumn()
        render_text = gtk.CellRendererText()
        render_text.set_property("ellipsize", pango.ELLIPSIZE_END)
        title_col.set_title(_("Title"))
        title_col.pack_start(render_text, expand=True)
        title_col.add_attribute(render_text, "markup", COL_LABEL)
        title_col.set_resizable(True)
        title_col.set_expand(True)
        title_col.set_sort_column_id(COL_TITLE)
        title_col.set_cell_data_func(render_text, self._celldatafunction)
        self.append_column(title_col)
        self.columns.insert(COL_TITLE, title_col)
        self.set_search_column(COL_TITLE)

        # Start date column
        sdate_col   = gtk.TreeViewColumn()
        render_text = gtk.CellRendererText()
        sdate_col.set_title(_("Start date"))
        sdate_col.pack_start(render_text, expand=False)
        sdate_col.add_attribute(render_text, "markup", COL_SDATE)
        sdate_col.set_resizable(False)
        sdate_col.set_sort_column_id(COL_SDATE)
        sdate_col.set_cell_data_func(render_text, self._celldatafunction)
        self.append_column(sdate_col)
        self.columns.insert(COL_SDATE, sdate_col)

        # Due column
        ddate_col   = gtk.TreeViewColumn()
        render_text = gtk.CellRendererText()
        ddate_col.set_title(_("Due"))
        ddate_col.pack_start(render_text, expand=False)
        ddate_col.add_attribute(render_text, "markup", COL_DUE)
        ddate_col.set_resizable(False)
        ddate_col.set_sort_column_id(COL_DDATE)
        ddate_col.set_cell_data_func(render_text, self._celldatafunction)
        self.append_column(ddate_col)
        self.columns.insert(COL_DUE, ddate_col)

        # days left
#        dleft_col   = gtk.TreeViewColumn()
#        render_text = gtk.CellRendererText()
#        dleft_col.set_title(_("Days left"))
#        dleft_col.pack_start(render_text, expand=False)
#        dleft_col.add_attribute(render_text, "markup", COL_DLEFT)
#        dleft_col.set_resizable(False)
#        dleft_col.set_sort_column_id(COL_DLEFT)
#        dleft_col.set_cell_data_func(render_text, self._celldatafunction)
#        self.append_column(dleft_col)
#        self.columns.insert(COL_DLEFT, dleft_col)

        # Global treeview properties
        self.set_property("expander-column", title_col)
        self.set_property("enable-tree-lines", False)
        self.set_rules_hint(False)

    ### DRAG AND DROP ########################################################
    def on_button_press(self, widget, event):
        # Here we intercept mouse clicks on selected items so that we can
        # drag multiple items without the click selecting only one
        target = self.get_path_at_pos(int(event.x), int(event.y))
        if (target 
           and event.type == gtk.gdk.BUTTON_PRESS
           and not (event.state & (gtk.gdk.CONTROL_MASK|gtk.gdk.SHIFT_MASK))
           and self.get_selection().path_is_selected(target[0])):
               # disable selection
               self.get_selection().set_select_function(lambda *ignore: False)
               self.defer_select = target[0]
            
    def on_button_release(self, widget, event):
        # re-enable selection
        self.get_selection().set_select_function(lambda *ignore: True)
        
        target = self.get_path_at_pos(int(event.x), int(event.y))    
        if (self.defer_select and target 
           and self.defer_select == target[0]
           and not (event.x==0 and event.y==0)): # certain drag and drop 
                                                 # operations still have path
               # if user didn't drag, simulate the click previously ignored
               self.set_cursor(target[0], target[1], False)
            
        self.defer_select=False

    def on_drag_drop(self, treeview, context, selection, info, timestamp):
        self.emit_stop_by_name('drag_drop')

    def on_drag_data_get(self, treeview, context, selection, info, timestamp):
        """Extract data from the source of the DnD operation. Here the id of
        the parent task and the id of the selected task is passed to the
        destination"""
        treeselection = treeview.get_selection()
        model, paths = treeselection.get_selected_rows()
        iters = [model.get_iter(path) for path in paths]
        iter_str = ','.join([model.get_string_from_iter(iter) for iter in iters])
        selection.set('gtg/task-iter-str', 0, iter_str)
        return

    def on_drag_data_received(self, treeview, context, x, y, selection, info,\
                              timestamp):

        model          = treeview.get_model()
#        model_filter   = model.get_model()
        tasktree_model = model.get_model()

        drop_info = treeview.get_dest_row_at_pos(x, y)

        if drop_info:
            path, position = drop_info
            iter = model.get_iter(path)
            if position == gtk.TREE_VIEW_DROP_BEFORE or\
               position == gtk.TREE_VIEW_DROP_AFTER:
                # Must add the task to the parent of the task situated\
                # before/after
                # Get sibling parent
                par_iter = model.iter_parent(iter)
            else:
                # Must add task as a child of the dropped-on iter
                # Get parent
                par_iter = iter
        else:
            # Must add the task to the root
            # Parent = root => iter=None
            par_iter = None

        # Get parent iter as a TaskTreeModel iter
        if par_iter:
            par_iter_tasktree   =\
                model.convert_iter_to_child_iter(None, par_iter)
#            par_iter_tasktree =\
#                model_filter.convert_iter_to_child_iter(par_iter_filter)
        else:
            par_iter_tasktree = None

        # Get dragged iter as a TaskTreeModel iter
        iters = selection.data.split(',')
        for iter in iters:
            drag_iter = model.get_iter_from_string(iter)
            drag_iter_filter   =\
                model.convert_iter_to_child_iter(None, drag_iter)
            drag_iter_tasktree =\
                model_filter.convert_iter_to_child_iter(drag_iter_filter)
            tasktree_model.move_task(par_iter_tasktree, drag_iter_tasktree)

        self.emit_stop_by_name('drag_data_received')


class ClosedTaskTreeView(TaskTreeView):
    """TreeView for display of a list of task. Handles DnD primitives too."""

    def __init__(self):
        TaskTreeView.__init__(self)
        self._init_tree_view()

    def _init_tree_view(self):
        # Tag column
        self.tag_col = gtk.TreeViewColumn()
        render_tags = CellRendererTags()
        self.tag_col.set_title(_("Tags"))
        self.tag_col.pack_start(render_tags, expand=False)
        self.tag_col.add_attribute(render_tags, "tag_list", COL_TAGS)
        self.tag_col.set_cell_data_func(render_tags, self._celldatafunction)
        render_tags.set_property('xalign', 0.0)
        self.tag_col.set_resizable(False)
        self.append_column(self.tag_col)
        self.columns.insert(COL_TAGS, self.tag_col)

        # CLosed date column
        cdate_col    = gtk.TreeViewColumn()
        render_text  = gtk.CellRendererText()
        cdate_col.set_title(_("Closing date"))
        cdate_col.pack_start(render_text, expand=True)
        cdate_col.set_attributes(render_text, markup=COL_CDATE_STR)
        cdate_col.set_sort_column_id(COL_CDATE)
        cdate_col.set_cell_data_func(render_text, self._celldatafunction)
        self.append_column(cdate_col)
        self.columns.insert(COL_CDATE_STR, cdate_col)

        # Title column
        title_col    = gtk.TreeViewColumn()
        render_text  = gtk.CellRendererText()
        render_text.set_property("ellipsize", pango.ELLIPSIZE_END)
        title_col.set_title(_("Title"))
        title_col.pack_start(render_text, expand=True)
        title_col.set_attributes(render_text, markup=COL_LABEL)
        title_col.set_cell_data_func(render_text, self._celldatafunction)
        title_col.set_sort_column_id(COL_TITLE)
        self.append_column(title_col)
        self.columns.insert(COL_TITLE, title_col)
        self.set_search_column(COL_TITLE)
        
        self.set_show_expanders(False)

    def scroll_to_task(self, task_id):
        print "scroll to task does nothing : remove it"
#        model = self.get_model()
#        iter = model.get_iter_first()
#        while iter:
#            if model.get_value(iter, 1).get_id() == task_id:
#                break
#            iter = model.iter_next(iter)
#        self.scroll_to_cell(model.get_path(iter),
#                        self.tag_col,
#                        False)
