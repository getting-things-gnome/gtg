import gtk
import gobject
from GTG.tools import colors

class TaskTreeModel(gtk.GenericTreeModel):

    COL_TID   = 0
    COL_TITLE = 1
    COL_DDATE = 3
    COL_DLEFT = 4
    COL_TAGS  = 5
    COL_BGCOL = 6

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
        for tid in tasks:
            my_task = self.req.get_task(tid)
            if is_tree and not my_task.has_parents() or \
               not is_tree:
                self.root_tasks.append(tid)

    def get_n_root_tasks(self):
        return len(self.root_tasks)

    def get_nth_root_task(self, index):
        return self.root_tasks[index]

    def get_root_task_index(self, tid):
        return self.root_tasks.index(tid)

    def rowref_from_path(self, task, path):
        """Return a row reference for a given treemodel path
        
         @param task    : the root from which the treemodel path starts. Set it
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
                self.rowref_from_path(task, path)

    def path_for_rowref(self, task, rowref):
        if rowref.rfind('/') == 0:
            if task == None:
                return (self.get_root_task_index(rowref[1:]),)
            else:
                return (task.get_subtask_index(rowref[1:]),)
        else:
            cur_tid  = rowref[1:rowref.find('/', 1)]
            task     = self.req.get_task(cur_tid)
            cur_path = (task.get_subtask_index(rowref[1:]),)
            rowref   = rowref[rowref.find(cur_tid)+len(cur_tid):]
            return cur_path + self.path_for_rowref(task, rowref)

    def get_path_from_rowref(self, rowref):
        return self.path_for_rowref(None, rowref)

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
        if   column == self.COL_TID:
            return task.get_id()
        elif column == self.COL_TITLE:
            return task.get_title()
        elif column == self.COL_DDATE:
            return task.get_due_date()
        elif column == self.COL_DLEFT:
            return task.get_days_left()
        elif column == self.COL_TAGS:
            return task.get_tags()
        elif column == self.COL_BGCOL:
            return colors.background_color(task.get_tags())

    def on_get_iter(self, path):
        #print "on_get_iter: " + str(path)
        return self.rowref_from_path(None, path)

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
