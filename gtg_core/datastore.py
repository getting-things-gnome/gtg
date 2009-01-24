import time
import threading
import gobject

from gtg_core   import tagstore, requester
from gtg_core.task import Task


#Only the datastore should access to the backend
DEFAULT_BACKEND = "1"
THREADING = False

class DataStore(gobject.GObject):
    __gsignals__ = { 'refresh': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                                   (str,)) }

    def __init__ (self):
        gobject.GObject.__init__(self)
        self.backends = {}
        self.tasks = {}
        self.tagstore = tagstore.TagStore()
        self.requester = requester.Requester(self)
        self.registration = {}
        
    def all_tasks(self) :
        all_tasks = []
        for key in self.backends :
            b = self.backends[key]
            tlist = b.get_tasks_list()
            all_tasks += tlist
        return all_tasks
        
    def get_task(self,tid) :
        if self.tasks.has_key(tid) :
            empty_task = self.tasks[tid]
        else :
            empty_task = self.new_task(tid,newtask=False)
        if tid and not empty_task.is_loaded() :
            uid,pid = tid.split('@') #pylint: disable-msg=W0612
            back = self.backends[pid]
            task = back.get_task(empty_task,tid)
        else :
            task = empty_task
        #If the task doesn't exist, we create it with a forced pid
        return task
        
    def delete_task(self,tid) :
        if tid and self.tasks.has_key(tid) :
            self.tasks[tid].delete()
            uid,pid = tid.split('@') #pylint: disable-msg=W0612
            back = self.backends[pid]
            back.remove_task(tid)
            self.tasks.pop(tid)
        
    #Create a new task and return it.
    #newtask should be True if you create a task
    #it should be False if you are importing an existing Task
    def new_task(self,tid=None,pid=None,newtask=False) :
        #If we don't have anything, we use the default PID
        if not pid : pid = DEFAULT_BACKEND
        #If tid, we force that tid and create a real new task
        if tid and not self.tasks.has_key(tid) :
            task = Task(tid,self.requester,newtask=newtask)
            uid,pid = tid.split('@') #pylint: disable-msg=W0612
            self.tasks[tid] = task
            return task
        #Else we create a new task in the given pid
        elif pid and self.backends.has_key(pid):
            newtid = self.backends[pid].new_task_id()
            task = Task(newtid,self.requester,newtask=newtask)
            self.tasks[newtid] = task
            task = self.backends[pid].get_task(task,newtid)
            return task
        elif tid :
            print "new_task with existing tid = bug"
            return self.tasks[tid]
        else :
            print "not possible to build the task = bug"
            return None
        
    def get_tagstore(self) :
        return self.tagstore
        
    def get_requester(self) :
        return self.requester

    def register_backend(self, dic):
        if dic.has_key("backend") :
            pid = dic["pid"]
            backend = dic["backend"]
            source = TaskSource(backend,dic,self.refresh_ui)
            self.backends[pid] = source
            #Filling the backend
#            for tid in source.get_tasks_list() :
#                task = self.new_task(tid=tid)
        else :
            print "Register a dic without backend key:  BUG"

    def unregister_backend(self, backend):
        print "unregister backend %s not implemented" %backend

    def get_all_backends(self):
        l = []
        for key in self.backends :
            l.append(self.backends[key])
        return l
        
    ## Handle the registered UI
    def register_ui(self,refresh_func) :
        rid = 1
        while self.registration.has_key(rid) :
            rid += 1
        self.registration[rid] = refresh_func
        return rid
        
    def unregister_ui(self,reg_id) :
        if self.registration.has_key(reg_id) :
            self.registration.pop(reg_id)
    
    def refresh_ui(self) :
        self.emit("refresh","1")
        #for rid in self.registration :
            #print "datastore.refresh_ui %s" %rid
            #self.registration[rid]()
        

#Task source is an transparent interface between the real backend and datastore
#Task source has also more functionnalities
class TaskSource() :
    def __init__(self,backend,parameters,refresh_cllbck) :
        self.backend = backend
        self.dic = parameters
        self.tasks = {}
        self.time = time.time()
        self.refresh = refresh_cllbck
        self.locks = {}
        self.tosleep = 0

##### The Backend interface ###############
##########################################
# All functions here are proxied from the backend itself

    def get_tasks_list(self) :
        tlist = self.backend.get_tasks_list()
        for t in tlist :
            if not self.locks.has_key(t) :
                self.locks[t] = threading.Lock()
        return tlist
        
    def get_task(self,empty_task,tid) :
        #Our thread
        def getting(empty_task,tid) :
            if THREADING :
                time.sleep(1)
                self.tosleep += 1
            self.backend.get_task(empty_task,tid)
            empty_task.set_sync_func(self.set_task)
            empty_task.set_loaded()
            self.refresh()
            #TODO : block access to the task if the thread is running
            #FIXME : do not display not fetched tasks
        ##########
        if self.tasks.has_key(tid) :
            task = self.tasks[tid]
            if task :
                empty_task = task
#            else :
#                empty_task = None
        else :
#            self.locks[tid].acquire()
#            print "lock acquired"
            #By putting the task in the dic, we say :
            #"This task is already fetched (or at least in fetching process)
            self.tasks[tid] = False
            if THREADING :
                t = threading.Thread(target=getting,args=[empty_task,tid])
                t.start()
                self.tasks[tid] = empty_task
            else :
                getting(empty_task,tid)
                self.tasks[tid] = empty_task
#            print "lock released"
#            self.locks[tid].release()
        return empty_task

    def set_task(self,task) :
        #This is foireux : imagine qu'on skipe un save et puis on quitte
#        self.tasks[task.get_id()] = task
#        diffe = time.time() - self.time
#        if diffe > 2 :
#            self.time = time.time()    
#            return self.backend.set_task(task)
#        else :
#            return True
        toreturn = self.backend.set_task(task)
        return toreturn
    
    def remove_task(self,tid) :
        self.tasks.pop(tid)
        self.locks.pop(tid)
        return self.backend.remove_task(tid)
        
    def new_task_id(self) :
        newid = self.backend.new_task_id()
        if not newid :
            k = 0
            pid = self.dic["pid"]
            newid = "%s@%s" %(k,pid)
            while self.tasks.has_key(str(newid)) :
                k += 1
                newid = "%s@%s" %(k,pid)
        if not self.locks.has_key(newid) :
            self.locks[newid] = threading.Lock()
        return newid

    def quit(self) :
        return self.backend.quit()
        
########## End of Backend interface ###########
###############################################

#Those functions are only for TaskSource
    def get_parameters(self) :
        return self.dic

