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

from GTG                              import _
from GTG.core.tree                    import Tree, TreeNode
from GTG.tools                        import colors
from GTG.core.task                    import Task
from GTG.taskbrowser.CellRendererTags import CellRendererTags
from GTG.tools.logger                 import Log

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

#A task can have multiple parent (thus multiple paths)
#We thus define an iter which is a tuple [node,path], defining one
#and only one position in the tree
class TaskIter():
    def __init__(self,tree,node,path):
        self.__node = node
        self.__path = path
        self.__tree = tree
        
    def get_node(self):
        return self.__node
    
    def get_path(self):
        return self.__path

    def is_valid(self):
        return self.__path in self.__tree.get_paths_for_node(self.__node)

    def __str__(self):
        return "iter %s  for path %s" %(self.__node.get_id(),str(self.__path))

class TaskIterStore():
    def __init__(self,tree,model):
        self.__tree = tree
        self.__model = model
        self.__store = {}

    def __key(self,node,path):
        return str(path)

    def get(self,node,path):
        key = self.__key(node,path)
        toreturn = None
        deleted = False
        if node and self.__store.has_key(key):
            stored_iter = self.__store[key]
            stored_node = stored_iter.get_node()
            if stored_node == node:
                toreturn = stored_iter
            elif stored_node:
                self.remove(stored_node,path,all=False)
                self.__model.row_deleted(path)
                deleted = stored_node
        if not toreturn:
            toreturn = TaskIter(self.__tree,node,path)
        self.__store[key] = toreturn
        if deleted:
            self.__model.to_add_task(deleted.get_id())
#            for i in self.__store:
#                print "%s : %s" %(i,self.__store[i])
        return toreturn

    def remove(self,node,path,all=True):
        if all:
            self.__store = {}
        else:
            key = self.__key(node,path)
            if self.__store.has_key(key):
                stored_node = self.__store[key]
                if stored_node.get_node() == node:
                    self.__store.pop(key)
                    return True
                else:
                    print "Trying to remove iter %s from path %s (thinking it was %s)"\
                            %(stored_node.get_node().get_id(),str(path),node.get_id())
                    return False
            else:
                print "Removing inexistant path %s for node %s" %(str(path),node.get_id())
                return False



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

    col_len = len(column_types)

    def __init__(self, requester, config, tree=None):
        
        gtk.GenericTreeModel.__init__(self)
        self.req  = requester
        self.config = config
        if tree:
            self.tree = tree
        else:
            self.tree = self.req.get_main_tasks_tree()
        self.iter_store = TaskIterStore(self.tree,self)
        self.tasks_to_add = []
        self.tree.connect('task-added-inview',self.add_task)
        self.tree.connect('task-deleted-inview',self.remove_task)
        self.tree.connect('task-modified-inview',self.update_task)
        #need to get the GTK style for the inline preview of task content
        tempwin = gtk.Window()
        tempwin.realize()
        self.style = tempwin.get_style()
        tempwin.destroy()

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
        return self.col_len

    def on_get_column_type(self, n):
#        print "on_get_column_type %s" %n
        return self.column_types[n]

    def on_get_value(self, iter, column):
        if not iter:
            return None
        task = iter.get_node()
        if column == COL_OBJ:
            return task
        elif column == COL_DDATE:
            return task.get_due_date().to_readable_string()
        elif column == COL_DLEFT:
            return task.get_days_left()
        elif column == COL_TITLE:
            return saxutils.escape(task.get_title())
        elif column == COL_SDATE:
            return task.get_start_date().to_readable_string()
        elif column == COL_CDATE:
            return task.get_closed_date()
        elif column == COL_TID:
            return task.get_id()
        elif column == COL_CDATE_STR:
            if task.get_status() == Task.STA_DISMISSED:
                date = "<span color='#AAAAAA'>" +\
                    str(task.get_closed_date()) + "</span>"
            else:
                date = str(task.get_closed_date())
            return date
        elif column == COL_DUE:
            return task.get_due_date().to_readable_string()
        elif column == COL_TAGS:
            tags = task.get_tags()
            tags.sort(key = lambda x: x.get_name())
            return tags
        elif column == COL_LABEL:
            title = saxutils.escape(task.get_title())
            color = self.style.text[gtk.STATE_INSENSITIVE].to_string()
            if task.get_status() == Task.STA_ACTIVE:
                count = self._count_active_subtasks_rec(task)
                if count != 0:
                    title += " (%s)" % count
                
                if self.config["contents_preview_enable"]:
                	excerpt = saxutils.escape(task.get_excerpt(lines=1, \
                		strip_tags=True, strip_subtasks=True))
                	title += " <span size='small' color='%s'>%s</span>" \
                		%(color, excerpt) 
            elif task.get_status() == Task.STA_DISMISSED:
                title = "<span color='%s'>%s</span>"%(color, title)
            return title

    def on_get_iter(self, path,node=None):
#        print "on_get_iter for %s" %(str(path))
        node = self.tree.get_node_for_path(path)
#        parent = self.tree.get_node_for_path(path[:-1])
        iter = self.iter_store.get(node,path)
        return iter

    def on_get_path(self, iter):
#        print "on_get_path"
        if iter and iter.is_valid():
            node = iter.get_node()
#            paths = self.tree.get_paths_for_node(node)
            path = iter.get_path()
#            print "path of iter is correct : %s" %(path in paths)
            return path
        else:
            return None

    def on_iter_next(self, iter):
#        print "on_iter_next"
        toreturn = None
        if iter and iter.is_valid():
            path = iter.get_path()
            parent = self.tree.get_node_for_path(path[:-1])
            node = iter.get_node()
            next = self.tree.next_node(node,parent=parent)
            #We have the next node. To know the path to use
            # we will find, in its paths, the one with 
            #the same root as the current node
            npaths = self.tree.get_paths_for_node(next)
            for n in npaths:
                if path[:-1] == n[:-1]:
                    toreturn = self.iter_store.get(next,n)
        return toreturn

    def on_iter_children(self, iter):
#        print "on_iter_children"
        return self.on_iter_nth_child(iter,0)
            

    def on_iter_has_child(self, iter):
#        print "on_iter_has_child"
        if iter:
            node = iter.get_node()
            return self.tree.node_has_child(node)
        else:
            return False

    def on_iter_n_children(self, iter):
#        print "on_iter_n_children"
        if iter:
            node = iter.get_node()
            return self.tree.node_n_children(node)
        else:
            return self.tree.node_n_children(None)

    def on_iter_nth_child(self, iter, n):
        if iter:
            id = iter.get_node().get_id()
        else:
            id = None
#        print "on_iter_nth_child n=%s (iter %s)" %(n,id)
        toreturn = None
        if iter and iter.is_valid():
            node = iter.get_node()
            path = iter.get_path()
            child = self.tree.node_nth_child(node,n)
            if child:
                cpaths = self.tree.get_paths_for_node(child)
#                print "   path is %s and cpaths (%s) are %s" %(path,child.get_id(),cpaths)
                for c in cpaths:
                    if c[:-1] == path:
                        toreturn = self.iter_store.get(child,c)
                if not toreturn:
                    print "PROBLEM: child %s have the path %s but parent has %s"\
                            %(child.get_id(),cpaths,path)
        return toreturn

    def on_iter_parent(self, iter):
#        print "on_iter_parent"
        if iter and iter.is_valid():
            path = iter.get_path()
            par_node = self.tree.get_node_for_path(path[:-1])
            return self.iter_store.get(par_node,path[:-1])
        else:
            return None

    def update_task(self, sender, tid):
#        # get the node and signal it's changed
#        print "tasktree update_task %s" %tid
        if self.tree.is_displayed(tid):
            my_node = self.tree.get_node(tid)
#            print "update %s" %my_node.get_title()
            if my_node and my_node.is_loaded():
                node_paths = self.tree.get_paths_for_node(my_node)
                for node_path in node_paths:
                    node_iter = self.get_iter(node_path)
                    self.row_changed(node_path, node_iter)
#                    print "child_toggled 1 : %s" %my_node.get_title()
                    self.row_has_child_toggled(node_path, node_iter)
                if len(node_paths) == 0: 
                    print "Error :! no path for node %s !" %my_node.get_id()

    def to_add_task(self,tid):
        self.tasks_to_add.append(tid)

    def add_task(self, sender, tid):
        task = self.tree.get_node(tid)
        if task:
            node_paths = self.tree.get_paths_for_node(task)
            for node_path in node_paths:
                node_iter = self.get_iter(node_path)
                self.row_inserted(node_path, node_iter)
                #following is mandatory if 
                #we added a child task before his parent.
                if self.tree.node_has_child(task):
#                    print "child_toggled 2 : %s" %task.get_title()
                    self.row_has_child_toggled(node_path,node_iter)
            parents = self.tree.node_parents(task)
            for p in parents:
                    for par_path in self.tree.get_paths_for_node(p):
                        par_iter = self.get_iter(par_path)
#                        print "child_toggled 3 : %s" %p.get_title()
                        self.row_has_child_toggled(par_path, par_iter)
        if len(self.tasks_to_add) > 0:
            t = self.tasks_to_add.pop()
            self.add_task(None,t)

    def remove_task(self, sender, tid):
        #a task has been removed from the view. Therefore,
        # the widgets that represent it should be removed
        Log.debug("tasktree remove_task %s" %tid)
        node = self.tree.get_node(tid)
        removed = False
        node_paths = self.tree.get_paths_for_node(node)
        for node_path in node_paths:
            Log.debug("* tasktree REMOVE %s - %s " %(tid,node_path))
#            print "      remove iter %s" %tid
            self.iter_store.remove(node,node_path)
#            print "     remove row %s" %str(node_path)
            self.row_deleted(node_path)
            removed = True
        return removed
                    
    def move_task(self, parent_tid, child_tid):
        """Moves the task identified by child_tid under
           parent_tid, removing all the precedent parents.
           Child becomes a root task if parent_tid is None"""
#        print "move task %s to parent %s" %(child_tid,parent_tid)
        def genealogic_search(tid):
            if tid not in genealogy:
                genealogy.append(tid)
                task = self.req.get_task(tid)
                for par in task.get_parents():
                    genealogic_search(par)
        child_task = self.req.get_task(child_tid)
        current_parents = child_task.get_parents()
        genealogy = []
        if parent_tid:
            parent_task = self.req.get_task(parent_tid)
            parents_parents = parent_task.get_parents()
            for p in parents_parents:
                genealogic_search(p)

        #Avoid the typical time-traveller problem being-the-father-of-yourself
        #or the grand-father. We need some genealogic research !
        if child_tid in genealogy or parent_tid == child_tid:
            return
        #if we move a task, this task should be saved, even if new
        child_task.set_to_keep()
        # Remove old parents 
        for pid in current_parents:
            #We first remove the node from the view (to have the path)
            node_paths = self.tree.get_paths_for_node(child_task)
            for node_path in node_paths:
                self.row_deleted(node_path)
            #then, we remove the parent
            child_task.remove_parent(pid)
        #Set new parent
        if parent_tid:
            child_task.add_parent(parent_tid)
        #If we don't have a new parent, add that task to the root
        else:
            node_paths = self.tree.get_paths_for_node(child_task)
            for node_path in node_paths:
                node_iter = self.get_iter(node_path)
                self.row_inserted(node_path, node_iter)
        #if we had a filter, we have to refilter after the drag-n-drop
        #This is not optimal and could be improved
        self.tree.refilter()
            

class TaskTreeView(gtk.TreeView):
    """TreeView for display of a list of task. Handles DnD primitives too."""

    def __init__(self, requester):
        gtk.TreeView.__init__(self)
        self.columns = []
        self.bg_color_enable = True
        self.req = requester
        self.show()
        
    def set_bg_color(self, val):
        self.bg_color_enable = val

    def _celldatafunction(self, column, cell, model, iter):
        col = None
        if self.bg_color_enable:
            bgcolor = column.get_tree_view().get_style().base[gtk.STATE_NORMAL]
            if iter:
                value = model.get_value(iter, COL_TAGS)
                if value:
                    col = colors.background_color(value, bgcolor)
        cell.set_property("cell-background", col)

    def get_column(self, index):
        return self.columns[index]

    def get_column_index(self, col_id):
        return self.columns.index(col_id)

class ActiveTaskTreeView(TaskTreeView):
    """TreeView for display of a list of task. Handles DnD primitives too."""

    DND_TARGETS = [
        ('gtg/task-iter-str', gtk.TARGET_SAME_WIDGET, 0)
    ]

    def __init__(self, requester):
        TaskTreeView.__init__(self, requester)
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
#        tag_col.set_title(_("Tags"))
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
        tasktree_model = model.get_model()
        drop_info = treeview.get_dest_row_at_pos(x, y)
        if drop_info:
            path, position = drop_info
            iter = model.get_iter(path)
            # Must add the task to the parent of the task situated\
            # before/after 
            if position == gtk.TREE_VIEW_DROP_BEFORE or\
               position == gtk.TREE_VIEW_DROP_AFTER:
                # Get sibling parent
                destination_iter = model.iter_parent(iter)
            else:
                # Must add task as a child of the dropped-on iter
                # Get parent
                destination_iter = iter
            if destination_iter:
                destination_tid = model.get_value(destination_iter, COL_TID)
            else:
                #it means we have drag-n-dropped above the first task
                # we should consider the destination as a root then.
                destination_tid = None
        else:
            # Must add the task to the root
            # Parent = root => iter=None
            destination_tid = None

        # Get dragged iter as a TaskTreeModel iter
        iters = selection.data.split(',')
        for iter in iters:
            dragged_iter = model.get_iter_from_string(iter)
            dragged_tid = model.get_value(dragged_iter, COL_TID)
            #print "we will move %s to %s" %(dragged_tid,destination_tid)
            tasktree_model.move_task(destination_tid, dragged_tid)
        self.emit_stop_by_name('drag_data_received')


class ClosedTaskTreeView(TaskTreeView):
    """TreeView for display of a list of task. Handles DnD primitives too."""

    def __init__(self, requester):
        TaskTreeView.__init__(self, requester)
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
