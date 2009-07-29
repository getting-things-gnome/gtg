
import gtk
import gobject

from GTG import _
from GTG.tools import colors
from GTG.taskbrowser.CellRendererTags import CellRendererTags

COL_TID   = 0
COL_TITLE = 1
COL_DDATE = 3
COL_DLEFT = 4
COL_TAGS  = 5
COL_BGCOL = 6

class TaskTreeModel(gtk.GenericTreeModel):

    column_types = (\
        str,\
        str,\
        str,\
        str,\
        str,\
        gobject.TYPE_PYOBJECT,\
        str)

    def __init__(self, requester, tasks=None, is_tree=True):
        gtk.GenericTreeModel.__init__(self)
        self.req = requester
        self.root_tasks = []
        self.is_tree = is_tree
        if tasks:
            for tid in tasks:
                my_task = self.req.get_task(tid)
                if is_tree and not my_task.has_parents() or \
                   not is_tree:
                    self.root_tasks.append(tid)

### TREE MODEL HELPER FUNCTIONS ###############################################

    def get_n_root_tasks(self):
        return len(self.root_tasks)

    def get_nth_root_task(self, index):
        try:
            return self.root_tasks[index]
        except(IndexError):
            raise ValueError('Index is not in task list')

    def get_root_task_index(self, tid):
        return self.root_tasks.index(tid)

    def _rowref_from_path(self, task, path):
        """Return a row reference for a given treemodel path
        
         @param task : the root from which the treemodel path starts. Set it
                       to None to start from the uppest level.
         @param path : the treemodel path
        """
        if len(path) == 1:
            if task == None:
                my_tid = self.get_nth_root_task(path[0])
            else:
                my_tid = task.get_nth_subtask(path[0])
            return "/" + str(my_tid)
        else:
            if task == None:
                my_tid = self.get_nth_root_task(path[0])
            else:
                my_tid = task.get_nth_subtask(path[0])
            task = self.req.get_task(my_tid)
            path = path[1:]
            return "/" + str(my_tid) + \
                self._rowref_from_path(task, path)

    def _path_for_rowref(self, task, rowref):
        if rowref.rfind('/') == 0:
            if task:
                return (task.get_subtask_index(rowref[1:]),)
            else:
                return (self.get_root_task_index(rowref[1:]),)
        else:
            cur_tid  = rowref[1:rowref.find('/', 1)]
            cur_task = self.req.get_task(cur_tid)
            if task:
                cur_path = (task.get_subtask_index(cur_tid),)
            else:
                cur_path = (self.get_root_task_index(cur_tid),)
            rowref   = rowref[rowref.find(cur_tid)+len(cur_tid):]
            return cur_path + self._path_for_rowref(cur_task, rowref)

    def get_path_from_rowref(self, rowref):
        return self._path_for_rowref(None, rowref)

    def get_rowref_from_path(self, path):
        return self._rowref_for_path(None, path)

### TREEMODEL INTERFACE ######################################################
#
    def on_get_flags(self):
        return gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
        return len(self.column_types)

    def on_get_column_type(self, n):
        return self.column_types[n]

    def on_get_value(self, rowref, column):
        cur_tid = rowref[rowref.rfind('/')+1:]
        task    = self.req.get_task(cur_tid)
        if   column == COL_TID:
            return task.get_id()
        elif column == COL_TITLE:
            return task.get_title()
        elif column == COL_DDATE:
            return task.get_due_date()
        elif column == COL_DLEFT:
            return task.get_days_left()
        elif column == COL_TAGS:
            return task.get_tags()
        elif column == COL_BGCOL:
            return colors.background_color(task.get_tags())

    def on_get_iter(self, path):
        #print "on_get_iter: " + str(path)
        try:
            return self._rowref_from_path(None, path)
        except(ValueError):
            return None

    def on_get_path(self, rowref):
        #print "on_get_path: %s" % (rowref)
        return self.get_path_from_rowref(rowref)

    def on_iter_next(self, rowref):
        #print "on_iter_next: %s" % (rowref)
        cur_tid = rowref[rowref.rfind('/')+1:]
        if rowref.rfind('/') == 0:
            next_idx  = self.get_root_task_index(cur_tid) + 1
            if next_idx >= self.get_n_root_tasks():
                return None
            else:
                next_tid = self.get_nth_root_task(next_idx)
                return "/" + str(next_tid)
        else:
            par_rowref = rowref[:rowref.rfind('/')]
            par_tid    = par_rowref[par_rowref.rfind('/')+1:]
            par_task   = self.req.get_task(par_tid)
            #print cur_tid
            next_idx   = par_task.get_subtask_index(cur_tid) + 1
            if next_idx >= par_task.get_n_subtasks():
                return None
            else:
                next_tid  = par_task.get_nth_subtask(next_idx)
                next_task = self.req.get_task(next_tid)
                return par_rowref + "/" + str(next_task.get_id())

    def on_iter_children(self, rowref):
        #print "on_iter_children: %s" % (rowref)
        if not self.is_tree:
            return None
        if rowref:
            cur_tid = rowref[rowref.rfind('/')+1:]
            task    = self.req.get_task(cur_tid)
            if task.has_subtask():
                child_tid = task.get_nth_subtask(0)
                return rowref + "/" + str(child_tid)
            else:
                return None
        else:
            my_tid = self.get_nth_root_task(0)
            return "/" + str(my_tid)

    def on_iter_has_child(self, rowref):
        #print "on_iter_has_child: %s" % (rowref)
        if not self.is_tree:
            return False
        cur_tid = rowref[rowref.rfind('/')+1:]
        task    = self.req.get_task(cur_tid)
        return task.has_subtask()

    def on_iter_n_children(self, rowref):
        #print "on_iter_n_children: %s" % (rowref)
        if not rowref:
            return self.get_n_root_tasks()
        if not self.is_tree:
            return 0
        cur_tid = rowref[rowref.rfind('/')+1:]
        task    = self.req.get_task(cur_tid)
        return task.get_n_subtasks()

    def on_iter_nth_child(self, parent, n):
        #print "on_iter_nth_child: %s %d" % (parent, n)
        if parent:
            par_tid  = parent[parent.rfind('/')+1:]
            par_task = self.req.get_task(par_tid)
            subtask_tid = par_task.get_nth_subtask(n)
            return parent + "/" + str(subtask_tid)
        else:
            my_tid = self.get_nth_root_task(n)
            return "/" + str(my_tid)

    def on_iter_parent(self, child):
        #print "on_iter_parent: %s" % (child)
        if not self.is_tree:
            return None
        if child.rfind('/') == 0:
            return None
        else:
            par_rowref = child[:child.rfind('/')]
            return par_rowref

    def add_task(self, tid):
        print "Add task: %s" % tid
        task = self.req.get_task(tid)
        #for p in task.get_parents():
        #    print p
        
        # 1. get the task
        # 2. get every path from parents
        

    def move(self, parent, child):
        #print "Moving %s below %s" % (child, parent)
        # Get child
        child_tid  = self.get_value(child, COL_TID)
        child_task = self.req.get_task(child_tid)
        child_path = self.get_path(child)
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
        # Remove child from parent
        if old_par_task:
            old_par_task.remove_subtask(child_tid)
        else:
            self.root_tasks.remove(child_tid)
        # Remove parent from child
        if old_par_task:
            child_task.remove_parent(old_par_tid)
        # Add child to new parent
        if new_par_task:
            new_par_task.add_subtask(child_tid)
        else:
            self.root_tasks.append(child_tid)
        # Warn tree about deleted row
        self.row_deleted(child_path)
        # Warn tree about inserted row
        if new_par_task:
            new_child_index = new_par_task.get_subtask_index(child_tid)
        else:
            new_child_index = self.root_tasks.index(child_tid)
        if parent:
            new_child_path = self.get_path(parent) + (new_child_index,)
        else:
            new_child_path = (new_child_index,)
        new_child_iter = self.get_iter(new_child_path)
        self.row_inserted(new_child_path, new_child_iter)

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
        title_col.set_title(_("Title"))
        title_col.pack_start(render_text, expand=False)
        title_col.add_attribute(render_text, "markup", COL_TITLE)
        title_col.set_resizable(True)
        title_col.set_expand(True)
        #The following line seems to fix bug #317469
        #I don't understand why !!! It's voodoo !
        #Is there a Rubber Chicken With a Pulley in the Middle ?
        title_col.set_max_width(100)
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
        tasktree_model.move(par_iter_tasktree, drag_iter_tasktree)

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

        # Done date column
        ddate_col    = gtk.TreeViewColumn()
        render_text  = gtk.CellRendererText()
        ddate_col.set_title(_("Closing date"))
        ddate_col.pack_start(render_text, expand=True)
        ddate_col.set_attributes(render_text, markup=COL_DDATE)
        ddate_col.set_sort_column_id(COL_DDATE)
        ddate_col.add_attribute(render_text, "cell_background", COL_BGCOL)
        ddate_col.set_sort_column_id(COL_DDATE)
        self.append_column(ddate_col)
        self.columns.insert(COL_DDATE, ddate_col)

        # Title column
        title_col    = gtk.TreeViewColumn()
        render_text  = gtk.CellRendererText()
        title_col.set_title(_("Title"))
        title_col.pack_start(render_text, expand=True)
        title_col.set_attributes(render_text, markup=COL_TITLE)
        title_col.set_sort_column_id(COL_TITLE)
        title_col.set_expand(True)
        title_col.add_attribute(render_text, "cell_background", COL_BGCOL)
        title_col.set_sort_column_id(COL_TITLE)
        self.append_column(title_col)
        self.columns.insert(COL_TITLE, title_col)
