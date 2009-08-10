
import gtk
import gobject

from GTG import _
from GTG.core.task     import Task
from GTG.tools         import colors
from GTG.taskbrowser.CellRendererTags import CellRendererTags

COL_ID    = 0
COL_NAME  = 1
COL_LABEL = 2
COL_OBJ   = 3
COL_COLOR = 4
COL_COUNT = 5
COL_SEP   = 6

class TagTreeModel(gtk.GenericTreeModel):

    column_types = (str,\
                    str,\
                    str,\
                    gobject.TYPE_PYOBJECT,\
                    str,\
                    str,\
                    bool)

    def __init__(self, requester):
        gtk.GenericTreeModel.__init__(self)
        self.req  = requester
        self.tree = self.req.get_tag_tree()
        self.workable_only = False

### MODEL METHODS ############################################################

    def update_tags_for_task(self, tid):
        task = self.req.get_task(tid)
        for t in task.get_tags():
            path = self.tree.get_path_for_node(t)
            iter = self.get_iter(path)
            self.row_changed(path, iter)

    def set_workable_only(self, val):
        self.workable_only = val

### TREEMODEL INTERFACE ######################################################
#
    def on_get_flags(self):
        return gtk.TREE_MODEL_ITERS_PERSIST|gtk.TREE_MODEL_LIST_ONLY

    def on_get_n_columns(self):
        return len(self.column_types)

    def on_get_column_type(self, n):
        return self.column_types[n]

    def on_get_iter(self, path):
        #print "on_get_iter: %s" % str(path)
        return self.tree.get_rowref_for_path(path)

    def on_get_path(self, rowref):
        #print "on_get_path: %s" % rowref
        return self.tree.get_path_for_rowref(rowref)

    def on_get_value(self, rowref, column):
        #print "on_get_value: %s" % rowref
        tag = self.tree.get_node_for_rowref(rowref)
        if   column == COL_ID:
            return tag.get_name()
        if   column == COL_NAME:
            return tag.get_name()[1:]
        if   column == COL_LABEL:
            if tag.get_attribute("label"):
                return tag.get_attribute("label")
            else:
                if tag.get_attribute("nonworkview"):
                    nwv = eval(tag.get_attribute("nonworkview"))
                else:
                    nwv = False
                if nwv:
                    return "<span color='#AAAAAA'>%s</span>"\
                         % tag.get_name()[1:]
                else:
                    return tag.get_name()[1:]
        if   column == COL_OBJ:
            return tag
        elif column == COL_COLOR:
            return task.get_attribute("color")
        elif column == COL_COUNT:
            sp_id = tag.get_attribute("special")
            if not sp_id:
                count = len(self.req.get_active_tasks_list(\
                       tags=[tag], workable=self.workable_only))
                return  count
            else:
                if sp_id == "all":
                    return len(self.req.get_active_tasks_list(\
                        workable=self.workable_only))
                elif sp_id == "notag":
                    return len(self.req.get_active_tasks_list(\
                        workable=self.workable_only, notag_only=True))
                else:
                    return 0
        elif column == COL_SEP:
            sp_id = tag.get_attribute("special")
            if not sp_id:
                return False
            else:
                if sp_id == "sep":
                    return True

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
            if node.has_child():
                return self.tree.get_rowref_for_node(node.get_nth_child(0))
            else:
                return None
        else:
            node = self.root.get_nth_child(0)
            return self.tree.get_rowref_for_node(node)

    def on_iter_has_child(self, rowref):
        #print "on_iter_has_child: %s" % (rowref)
        node = self.tree.get_node_for_rowref(rowref)
        return node.has_child()

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
            node = self.tree.get_node_from_rowref(rowref)
        else:
            node = self.tree.get_root()
        nth_child = node.get_nth_child(n)
        return self.tree.get_rowref_for_node(nth_child)

    def on_iter_parent(self, rowref):
        #print "on_iter_parent: %s" % (rowref)
        node = self.tree.get_node_from_rowref(rowref)
        if node.has_parent():
            parent = node.get_parent()
            return self.tree.get_rowref_for_node(parent)
        else:
            return None

    def add_tag(self, tname, tag):
        root      = self.tree.get_root()
        root.add_child(tname, tag)
        tag.set_parent(root)
        tag_index = root.get_child_index(tname)
        tag_path  = (tag_index,)
        tag_iter  = self.get_iter(tag_path)
        self.row_inserted(tag_path, tag_iter)
#
#    def remove_task(self, tid):
#        # get the task
#        task = self.req.get_task(tid)
#        # Remove every row of this task
#        if task.has_parents():
#            # get every paths leading to this task
#            path_list = self._get_paths_for_task(task)
#            # remove every path
#            for task_path in path_list:
#                self.row_deleted(task_path)
#        if tid in self.root_tasks:
#            task_index = self._get_root_task_index(tid)
#            task_path  = (task_index,)
#            task_iter  = self.get_iter(task_path)
#            self.row_deleted(task_path)
#            self.root_tasks.remove(tid)
#                    
#    def move_task(self, parent, child):
#        #print "Moving %s below %s" % (child, parent)
#        # Get child
#        child_tid  = self.get_value(child, COL_TID)
#        child_task = self.req.get_task(child_tid)
#        child_path = self.get_path(child)
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
#        # Remove child from old parent
#        if old_par_task:
#            old_par_task.remove_subtask(child_tid)
#        else:
#            self.root_tasks.remove(child_tid)
#        # Remove old parent from child
#        if old_par_task:
#            child_task.remove_parent(old_par_tid)
#        # Add child to new parent (add_subtask also add new parent to child)
#        if new_par_task:
#            new_par_task.add_subtask(child_tid)
#        else:
#            self.root_tasks.append(child_tid)
#        # Warn tree about deleted row
#        self.row_deleted(child_path)
#        # Warn tree about inserted row
#        if new_par_task:
#            new_child_index = new_par_task.get_subtask_index(child_tid)
#        else:
#            new_child_index = self._get_root_task_index(child_tid)
#        if parent:
#            new_child_path = self.get_path(parent) + (new_child_index,)
#        else:
#            new_child_path = (new_child_index,)
#        new_child_iter = self.get_iter(new_child_path)
#        self.row_inserted(new_child_path, new_child_iter)

class TagTreeView(gtk.TreeView):
    """TreeView for display of a list of task. Handles DnD primitives too."""

    DND_TARGETS = [
        ('gtg/task-iter-str', gtk.TARGET_SAME_WIDGET, 0)
    ]

    def __init__(self):
        gtk.TreeView.__init__(self)
        self.show()
        self._init_tree_view()

        # Drag and drop
#        self.enable_model_drag_source(\
#            gtk.gdk.BUTTON1_MASK,
#            self.DND_TARGETS,
#            gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_MOVE)
#        self.enable_model_drag_dest(\
#            self.DND_TARGETS,
#            gtk.gdk.ACTION_DEFAULT)
# 
#        self.drag_source_set(\
#            gtk.gdk.BUTTON1_MASK,
#            self.DND_TARGETS,
#            gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_MOVE)
#
#        self.drag_dest_set(\
#            gtk.DEST_DEFAULT_ALL,
#            self.DND_TARGETS,
#            gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_MOVE)
#
#        self.connect('drag_drop', self.on_drag_drop)
#        self.connect('drag_data_get', self.on_drag_data_get)
#        self.connect('drag_data_received', self.on_drag_data_received)

    def refresh(self):
        self.get_model().foreach(self._refresh_func)

    def _refresh_func(self, model, path, iter, user_data=None):
        model.row_changed(path, iter)

    def _tag_separator_filter(self, model, itera, user_data=None):
        return self.get_model().get_value(itera, COL_SEP)

    def _init_tree_view(self):
        
         # Tag column
        tag_col      = gtk.TreeViewColumn()
        render_text  = gtk.CellRendererText()
        render_count = gtk.CellRendererText()
        render_tags  = CellRendererTags()
        tag_col.set_title(_("Tags"))
        tag_col.set_clickable(False)
        tag_col.pack_start(render_tags, expand=False)
        tag_col.set_attributes(render_tags, tag=COL_OBJ)
        tag_col.pack_start(render_text, expand=True)
        tag_col.set_attributes(render_text, markup=COL_LABEL)
        tag_col.pack_end(render_count, expand=False)
        tag_col.set_attributes(render_count, markup=COL_COUNT)
        render_count.set_property("foreground", "#888a85")
        render_count.set_property('xalign', 1.0)
        render_tags.set_property('ypad', 3)
        render_text.set_property('ypad', 3)
        render_count.set_property('xpad', 3)
        render_count.set_property('ypad', 3)
        tag_col.set_sort_column_id(-1)
        tag_col.set_expand(True)
        self.append_column(tag_col)

        # Global treeview properties
        self.set_row_separator_func(self._tag_separator_filter)
        self.set_headers_visible(False)

    ### DRAG AND DROP ########################################################

#    def on_drag_drop(self, treeview, context, selection, info, timestamp):
#        self.emit_stop_by_name('drag_drop')
#
#    def on_drag_data_get(self, treeview, context, selection, info, timestamp):
#        """Extract data from the source of the DnD operation. Here the id of
#        the parent task and the id of the selected task is passed to the
#        destination"""
#        treeselection = treeview.get_selection()
#        model, iter = treeselection.get_selected()
#        iter_str = model.get_string_from_iter(iter)
#        selection.set('gtg/task-iter-str', 0, iter_str)
#        return
#
#    def on_drag_data_received(self, treeview, context, x, y, selection, info,\
#                              timestamp):
#
#        model          = treeview.get_model()
#        model_filter   = model.get_model()
#        tasktree_model = model_filter.get_model()
#
#        drop_info = treeview.get_dest_row_at_pos(x, y)
#
#        if drop_info:
#            path, position = drop_info
#            iter = model.get_iter(path)
#            if position == gtk.TREE_VIEW_DROP_BEFORE or\
#               position == gtk.TREE_VIEW_DROP_AFTER:
#                # Must add the task to the parent of the task situated\
#                # before/after
#                # Get sibling parent
#                par_iter = model.iter_parent(iter)
#            else:
#                # Must add task as a child of the dropped-on iter
#                # Get parent
#                par_iter = iter
#        else:
#            # Must add the task to the root
#            # Parent = root => iter=None
#            par_iter = None
#
#        # Get parent iter as a TaskTreeModel iter
#        if par_iter:
#            par_iter_filter   =\
#                model.convert_iter_to_child_iter(None, par_iter)
#            par_iter_tasktree =\
#                model_filter.convert_iter_to_child_iter(par_iter_filter)
#        else:
#            par_iter_tasktree = None
#
#        # Get dragged iter as a TaskTreeModel iter
#        drag_iter = model.get_iter_from_string(selection.data)
#        drag_iter_filter   =\
#            model.convert_iter_to_child_iter(None, drag_iter)
#        drag_iter_tasktree =\
#            model_filter.convert_iter_to_child_iter(drag_iter_filter)
#        tasktree_model.move_task(par_iter_tasktree, drag_iter_tasktree)
#
#        self.emit_stop_by_name('drag_data_received')
