from gi.repository import GObject

class Requester(GObject.GObject):
    """ 
    A view on a GTG datastore.
    L{Requester} is a stateless object that simply provides a nice
    API for user interfaces to use for datastore operations.
    """ 

    def __init__(self, datastore):
        """Construct a L{Requester}."""
        GObject.GObject.__init__(self)
        self.ds = datastore
        self.__basetree = self.ds.get_tasks_tree()

    def get_tasks_tree(self):
        return self.ds.get_all_tasks()

    def get_basetree(self):
        return self.__basetree

    def has_task(self, tid):
        return self.ds.has_task(tid)

    def get_task(self, tid):
        task = self.ds.get_task(tid)
        return task

    def new_task(self, tags=None, newtask=True):
        """Create a new task.
        Note: this modifies the datastore.
        """
        task = self.ds.new_task()
        if tags:
            for t in tags:
                assert(not isinstance(t, Tag))
                task.tag_added(t)
        return task

    def delete_task(self, tid):
        """Delete the task 'tid'.
        Note: this modifies the datastore."""
        if self.has_task(tid):
            del self.ds._tasks[tid]
            return True
        else:
            return False

    def get_random_task(self):
        return self.ds.get_random_task()
