import gtk
from GTG import tools.colors

class TaskTreeModel(gtk.GenericTreeModel):

    COL_OBJ   = 0
    COL_TITLE = 1
    COL_DDATE = 3
    COL_DLEFT = 4
    COL_TAGS  = 5
    COL_BGCOL = 6

    column_types = gtk.TreeStore(gobject.TYPE_PYOBJECT, \
                                 str,                   \
                                 str,                   \
                                 str,                   \
                                 str,                   \
                                 gobject.TYPE_PYOBJECT, \
                                 str)

    def __init__(self, tasks=None):
        gtk.GenericTreeModel.__init__(self)
        self.tasks = tasks

    def __task_for_tm_path(self, task, tm_path):
        if len(tm_path) == 1: return task.get_nth_child(tm_path[0])
        else:
            task    = task.get_nth_child(tm_path[0])
            tm_path = tm_path[1:]
            return self.__task_for_tm_path(task, tm_path)

    def set_tree(self, mtree):
        self.tree = mtree

### TREEMODEL INTERFACE ######################################################
#
    def on_get_flags(self):
        return gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
        return len(self.column_types)

    def on_get_column_type(self, n):
        return self.column_types[n]




    def on_get_value(self, rowref, column):
        task = self.tree.get_task_from_path(rowref)
        if   column == self.COL_OBJ:
            return task
        elif column == self.COL_TITLE:
            return task.get_title()
        elif column == self.COL_DDATE:
            return task.get_due_date()
        elif column == self.COL_DLEFT:
            return task.get_day_left()
        elif column == self.COL_TAGS:
            return task.get_tags()
        elif column == self.COL_BGCOL:
            return colors.background_color(task.get_tags())

    def on_get_iter(self, tm_path):
        task = self.__task_for_tm_path(self.tree.get_root(), tm_path)
        return task.path

    def on_get_path(self, rowref):
        task = self.tree.get_task_from_path(rowref)
        return self.tree.get_tree_path_for_task(task)

    def on_iter_next(self, rowref):
        #print "on_iter_next: %s" % (rowref)
        task        = self.tree.get_task_from_path(rowref)
        parent_task = task.get_parent()
        if parent_task:
            next_idx    = parent_task.get_child_index(task) + 1
            if parent_task.get_n_children()-1 < next_idx: return None
            else: return parent_task.get_nth_child(next_idx).path
        else: return None

    def on_iter_children(self, rowref):
        #print "on_iter_children: %s" % (rowref)
        if rowref:
            task = self.tree.get_task_from_path(rowref)
            if task.has_child(): return task.get_nth_child(0).path
            else               : return None
        else:
            self.root.get_nth_child(0).path

    def on_iter_has_child(self, rowref):
        #print "on_iter_has_child: %s" % (rowref)
        task = self.tree.get_task_from_path(rowref)
        return task.has_child()

    def on_iter_n_children(self, rowref):
        #print "on_iter_n_children: %s" % (rowref)
        if rowref: task = self.tree.get_task_from_path(rowref)
        else     : task = self.tree.get_root()
        return task.get_n_children()
        

    def on_iter_nth_child(self, parent, n):
        #print "on_iter_nth_child: %s %d" % (parent, n)
        if parent:
            task = self.tree.get_task_from_path(parent)
        else:
            task = self.tree.get_root()
        return task.get_nth_child(n).path

    def on_iter_parent(self, child):
        #print "on_iter_parent: %s" % (child)
        task = self.tree.get_task_from_path(child)
        if task.has_parent(): return task.get_parent().path
        else                : return None
