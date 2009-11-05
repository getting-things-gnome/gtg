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
COL_BGCOL     = 8
COL_LABEL     = 9

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
        str)

    def __init__(self, requester):
        
        gtk.GenericTreeModel.__init__(self)
        self.req  = requester
        self.tree = Tree()
                
        # Default config
        self.bg_color_enable = True

### TREE MODEL HELPER FUNCTIONS ###############################################

    def _add_all_subtasks(self, node, task):
        if task.has_subtasks():
            node_path = self.tree.get_path_for_node(node)
            node_iter = self.get_iter(node_path)
            for c_tid in task.get_subtask_tids():
                if self.tree.has_node(c_tid):
                    c_task = self.req.get_task(c_tid)
                    c_node = TreeNode(c_tid, c_task)
                    self.tree.add_node(c_tid, c_node, node)
                    c_node_path = self.tree.get_path_for_node(c_node)
                    #if c_node_path:
                        #c_node_iter = self.get_iter(c_node_path)
                        #self.row_inserted(c_node_path, c_node_iter)
                    self._add_all_subtasks(c_node, c_task)
                    #print " - %s: adding %s as subtask." % (task.get_id(), c_tid)
        else:
            return

    def _count_active_subtasks_rec(self, task):
        count = 0
        if task.has_subtasks():
            for tid in task.get_subtask_tids():
                task = self.req.get_task(tid)
                if task.get_status() == Task.STA_ACTIVE:
                    count = count + 1 + self._count_active_subtasks_rec(task)
        return count

### TREEMODEL INTERFACE ######################################################
#
    def on_get_flags(self):
        return gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
        return len(self.column_types)

    def on_get_column_type(self, n):
        return self.column_types[n]

    def on_get_value(self, rowref, column):
        node = self.tree.get_node_for_rowref(rowref)
        if not node:
            return None
        else:
            task = node.get_obj()
        if   column == COL_TID:
            return task.get_id()
        elif column == COL_OBJ:
            return task
        elif column == COL_TITLE:
            return saxutils.escape(task.get_title())
        elif column == COL_DDATE:
            return task.get_due_date()
        elif column == COL_CDATE:
            return task.get_closed_date()
        elif column == COL_CDATE_STR:
            if task.get_status() == Task.STA_DISMISSED:
                date = "<span color='#AAAAAA'>" +\
                    task.get_closed_date() + "</span>"
            else:
                date = task.get_closed_date()
            return date
        elif column == COL_DLEFT:
            return task.get_days_left()
        elif column == COL_TAGS:
            return task.get_tags()
        elif column == COL_BGCOL:
            if self.bg_color_enable:
                return colors.background_color(task.get_tags())
            else:
                return None
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
        #print "on_get_iter: " + str(path)
        return self.tree.get_rowref_for_path(path)

    def on_get_path(self, rowref):
        #print "on_get_path: %s" % (rowref)
        return self.tree.get_path_for_rowref(rowref)

    def on_iter_next(self, rowref):
        #print "on_iter_next: %s" % (rowref)
        node        = self.tree.get_node_for_rowref(rowref)
        parent_node = node.get_parent()
        if parent_node:
            next_idx = parent_node.get_child_index(node.get_id()) + 1
            if parent_node.get_n_children()-1 < next_idx:
                return None
            else:
                return self.tree.get_rowref_for_node(\
                    parent_node.get_nth_child(next_idx))
        else:
            return None

    def on_iter_children(self, rowref):
        #print "on_iter_children: %s" % (rowref)
        if rowref:
            node = self.tree.get_node_for_rowref(rowref)
            if node and node.has_child():
                return self.tree.get_rowref_for_node(node.get_nth_child(0))
            else:
                return None
        else:
            node = self.root.get_nth_child(0)
            return self.tree.get_rowref_for_node(node)

    def on_iter_has_child(self, rowref):
        #print "on_iter_has_child: %s" % (rowref)
        node = self.tree.get_node_for_rowref(rowref)
        if node:
            return node.has_child()
        else:
            return None

    def on_iter_n_children(self, rowref):
        #print "on_iter_n_children: %s" % (rowref)
        if rowref:
            node = self.tree.get_node_for_rowref(rowref)
        else:
            node = self.tree.get_root()
        return node.get_n_children()

    def on_iter_nth_child(self, rowref, n):
        #print "on_iter_nth_child: %s %d" % (rowref, n)
        if rowref:
            node = self.tree.get_node_for_rowref(rowref)
        else:
            node = self.tree.get_root()
        nth_child = node.get_nth_child(n)
        return self.tree.get_rowref_for_node(nth_child)

    def on_iter_parent(self, rowref):
        #print "on_iter_parent: %s" % (rowref)
        node = self.tree.get_node_for_rowref(rowref)
        if node.has_parent():
            parent = node.get_parent()
            if parent == self.tree.get_root():
                return None
            else:
                return self.tree.get_rowref_for_node(parent)
        else:
            return None

    def add_task(self, tid):
        nodes = []
        # get the task
        task = self.req.get_task(tid)
        # insert the task in the tree (root)
        my_node = TreeNode(tid, task)
        self.tree.add_node(tid, my_node, None)
        node_path = self.tree.get_path_for_node(my_node)
        node_iter = self.get_iter(node_path)
        self.row_inserted(node_path, node_iter)
        nodes.append(my_node)
        # has the task parents?
        if task.has_parents():
            # get every path from parents
            par_list = task.get_parents()
            # get every paths going to each parent
            for par_tid in par_list:
                if not self.tree.has_node(par_tid):
                    #print " - %s: %s is not loaded." % (tid, par_tid)
                    continue
                else:
                    par_nodes = self.tree.get_nodes(par_tid)
                    for par_node in par_nodes:
                        my_node = TreeNode(tid, task)
                        self.tree.add_node(tid, my_node, par_node)
                        node_path = self.tree.get_path_for_node(my_node)
                        node_iter = self.get_iter(node_path)
                        self.row_inserted(node_path, node_iter)
                        nodes.append(my_node)
        # has the task children?
        for node in nodes:
            self._add_all_subtasks(node, task)
            node_path = self.tree.get_path_for_node(node)
            if node_path:
                node_iter = self.get_iter(node_path)
                self.row_has_child_toggled(node_path, node_iter)

    def remove_task(self, tid):
        # get the nodes
        nodes = self.tree.get_nodes(tid)
        removed = False
        # Remove every row of this task
        for node in nodes:
            node_path = self.tree.get_path_for_node(node)
            self.tree.remove_node(tid, node)
            self.row_deleted(node_path)
            removed = True
        return removed
                    
    def move_task(self, parent, child):
        #print "Moving %s below %s" % (child, parent)
        # Get child
        child_tid  = self.get_value(child, COL_TID)
        child_task = self.req.get_task(child_tid)
        #if we move a task, this task should be saved, even if new
        child_task.set_to_keep()
        # Get old parent
        old_par = self.iter_parent(child)
        if old_par:
            old_par_tid  = self.get_value(old_par, COL_TID)
            old_par_task = self.req.get_task(old_par_tid)
        else:
            old_par_task = None
        # Get new parent
        if parent:
            new_par_tid  = self.get_value(parent, COL_TID)
            new_par_task = self.req.get_task(new_par_tid)
        else:
            new_par_task = None
        # Remove child from old parent
        if old_par_task:
            old_par_task.remove_subtask(child_tid)
        # Remove old parent from child
        if old_par_task:
            child_task.remove_parent(old_par_tid)
        # Add child to new parent (add_subtask also add new parent to child)
        if new_par_task:
            new_par_task.add_subtask(child_tid)

    def set_bg_color(self, val):
        self.bg_color_enable = val

class TaskTreeView(gtk.TreeView):
    """TreeView for display of a list of task. Handles DnD primitives too."""

    def __init__(self, model=None):
        gtk.TreeView.__init__(self)
        self.columns = []
        self.show()

    def get_column(self, index):
        return self.columns[index]

    def get_column_index(self, col_id):
        return self.columns.index(col_id)

    def refresh(self, collapsed_rows=None):
        self.expand_all()
        self.get_model().foreach(self._refresh_func, collapsed_rows)

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

    def _init_tree_view(self):
        # Tag column
        tag_col     = gtk.TreeViewColumn()
        render_tags = CellRendererTags()
        tag_col.set_title(_("Tags"))
        tag_col.pack_start(render_tags, expand=False)
        tag_col.add_attribute(render_tags, "tag_list", COL_TAGS)
        render_tags.set_property('xalign', 0.0)
        tag_col.set_resizable(False)
        tag_col.add_attribute(render_tags, "cell-background", COL_BGCOL)
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
        title_col.add_attribute(render_text, "cell_background", COL_BGCOL)
        title_col.set_sort_column_id(COL_TITLE)
        self.append_column(title_col)
        self.columns.insert(COL_TITLE, title_col)

        # Due date column
        ddate_col   = gtk.TreeViewColumn()
        render_text = gtk.CellRendererText()
        ddate_col.set_title(_("Due date"))
        ddate_col.pack_start(render_text, expand=False)
        ddate_col.add_attribute(render_text, "markup", COL_DDATE)
        ddate_col.set_resizable(False)
        ddate_col.add_attribute(render_text, "cell_background", COL_BGCOL)
        ddate_col.set_sort_column_id(COL_DDATE)
        self.append_column(ddate_col)
        self.columns.insert(COL_DDATE, ddate_col)

        # days left
        dleft_col   = gtk.TreeViewColumn()
        render_text = gtk.CellRendererText()
        dleft_col.set_title(_("Days left"))
        dleft_col.pack_start(render_text, expand=False)
        dleft_col.add_attribute(render_text, "markup", COL_DLEFT)
        dleft_col.set_resizable(False)
        dleft_col.add_attribute(render_text, "cell_background", COL_BGCOL)
        dleft_col.set_sort_column_id(COL_DLEFT)
        self.append_column(dleft_col)
        self.columns.insert(COL_DLEFT, dleft_col)

        # Global treeview properties
        self.set_property("expander-column", title_col)
        self.set_property("enable-tree-lines", False)
        self.set_rules_hint(False)

    ### DRAG AND DROP ########################################################

    def on_drag_drop(self, treeview, context, selection, info, timestamp):
        self.emit_stop_by_name('drag_drop')

    def on_drag_data_get(self, treeview, context, selection, info, timestamp):
        """Extract data from the source of the DnD operation. Here the id of
        the parent task and the id of the selected task is passed to the
        destination"""
        treeselection = treeview.get_selection()
        model, iter = treeselection.get_selected()
        iter_str = model.get_string_from_iter(iter)
        selection.set('gtg/task-iter-str', 0, iter_str)
        return

    def on_drag_data_received(self, treeview, context, x, y, selection, info,\
                              timestamp):

        model          = treeview.get_model()
        model_filter   = model.get_model()
        tasktree_model = model_filter.get_model()

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
            par_iter_filter   =\
                model.convert_iter_to_child_iter(None, par_iter)
            par_iter_tasktree =\
                model_filter.convert_iter_to_child_iter(par_iter_filter)
        else:
            par_iter_tasktree = None

        # Get dragged iter as a TaskTreeModel iter
        drag_iter = model.get_iter_from_string(selection.data)
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
        tag_col     = gtk.TreeViewColumn()
        render_tags = CellRendererTags()
        tag_col.set_title(_("Tags"))
        tag_col.pack_start(render_tags, expand=False)
        tag_col.add_attribute(render_tags, "tag_list", COL_TAGS)
        render_tags.set_property('xalign', 0.0)
        tag_col.set_resizable(False)
        tag_col.add_attribute(render_tags, "cell-background", COL_BGCOL)
        self.append_column(tag_col)
        self.columns.insert(COL_TAGS, tag_col)

        # CLosed date column
        cdate_col    = gtk.TreeViewColumn()
        render_text  = gtk.CellRendererText()
        cdate_col.set_title(_("Closing date"))
        cdate_col.pack_start(render_text, expand=True)
        cdate_col.set_attributes(render_text, markup=COL_CDATE_STR)
        cdate_col.add_attribute(render_text, "cell_background", COL_BGCOL)
        cdate_col.set_sort_column_id(COL_CDATE)
        self.append_column(cdate_col)
        self.columns.insert(COL_CDATE_STR, cdate_col)

        # Title column
        title_col    = gtk.TreeViewColumn()
        render_text  = gtk.CellRendererText()
        render_text.set_property("ellipsize", pango.ELLIPSIZE_END)
        title_col.set_title(_("Title"))
        title_col.pack_start(render_text, expand=True)
        title_col.set_attributes(render_text, markup=COL_LABEL)
        title_col.add_attribute(render_text, "cell_background", COL_BGCOL)
        title_col.set_sort_column_id(COL_TITLE)
        self.append_column(title_col)
        self.columns.insert(COL_TITLE, title_col)
        
        self.set_show_expanders(False)
