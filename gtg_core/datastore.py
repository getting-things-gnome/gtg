import os

from gtg_core   import CoreConfig, tagstore, requester
from gtg_core.task import Task
#Here we import the default backend
#from backends.localfile import Backend

#BACKEND_COLUMN = 0
#PROJ_COLUMN = 1

#Only the datastore should access to the backend

class DataStore:

    def __init__ (self):
        self.backends = {}
        self.tasks = {}
        self.tagstore = tagstore.TagStore()
        self.requester = requester.Requester(self)
        
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
        if tid :
            uid,pid = tid.split('@') #pylint: disable-msg=W0612
            back = self.backends[pid]
            task = back.get_task(empty_task,tid)
        else :
            task = empty_task
        #If the task doesn't exist, we create it with a forced pid
        return task
        
    def delete_task(self,tid) :
        if tid and self.tasks.has_key(tid) :
            uid,pid = tid.split('@') #pylint: disable-msg=W0612
            back = self.backends[pid]
            back.remove_task(tid)
            self.tasks.pop(tid)
        
    #Create a new task and return it.
    #newtask should be True if you create a task
    #it should be task if you are importing an existing Task
    def new_task(self,tid,newtask=False) :
        #FIXME : we should also handle the case where tid = None
        #And create a real new task
        if not self.tasks.has_key(tid) :
            task = Task(tid,self.requester,newtask=newtask)
            uid,pid = tid.split('@') #pylint: disable-msg=W0612
            backend = self.backends[pid]
            task.set_sync_func(backend.set_task)
            self.tasks[tid] = task
            return task
        else :
            print "new_task with existing tid = bug"
            return self.tasks[tid]
        
    def get_tagstore(self) :
        return self.tagstore
        
    def get_requester(self) :
        return self.requester

    def register_backend(self, backend,dic):
        pid = dic["pid"]
        source = TaskSource(backend,dic)
        if backend != None:
            self.backends[pid] = source

    def unregister_backend(self, backend):
        print "unregister backend not implemented"
#        if backend != None:
#            self.backends.remove(backend)

    def get_all_backends(self):
        l = []
        for key in self.backends :
            l.append(self.backends[key])
        return l
        

#Task source is an transparent interface between the real backend and datastore
#Task source has also more functionnalities
class TaskSource() :
    def __init__(self,backend,parameters) :
        self.backend = backend
        self.dic = parameters
        self.tasks = {}

##### The Backend interface ###############
##########################################
# All functions here are proxied from the backend itself

    def get_tasks_list(self) :
        return self.backend.get_tasks_list()
        
    def get_task(self,empty_task,tid) :
        if self.tasks.has_key(tid) :
            task = self.tasks[tid]
        else :
            task = self.backend.get_task(empty_task,tid)
            self.tasks[tid] = task
        return task

    def set_task(self,task) :
        print "sync task %s" %task.get_id()
        self.tasks[task.get_id()] = task
        return self.backend.set_task(task)
    
    def remove_task(self,tid) :
        self.tasks.pop(tid)
        return self.backend.remove_task(tid)
        
    def new_task_id(self) :
        return self.backend.new_task_id()

    def quit(self) :
        return self.backend.quit()
        
########## End of Backend interface ###########
###############################################

#Those functions are only for TaskSource
    def get_parameters(self) :
        return self.dic

        
    #We create a new project with a given backend
    #If the backend is None, then we use the default one
    #Default backend is localfile and we add a new one.
#    def new_project(self,name,backend=None) :
#        print "datastore : new_project not implemented"
#        project = Project(name,self)
#        if not backend :
#            # Create backend
#            backend   = Backend(None,self,project=project)
#            backend.sync_project()
#            # Register it in datastore
#            self.register_backend(backend)
#            
#        project.set_pid(str(self.cur_pid))
#        project.set_sync_func(backend.sync_project)
#        self.projects[str(self.cur_pid)] = [backend, project]
#        self.cur_pid = self.cur_pid + 1
#        return project


#    def remove_project(self, pid):
#        print "datastore : remove_project not implemented"
#        b  = self.get_project_with_pid(pid)[0]
#        self.projects.pop(pid)
#        self.unregister_backend(b)
#        fn = b.get_filename()
#        os.remove(os.path.join(CoreConfig.DATA_DIR,fn))
#    def get_all_projects(self):
#        print "datastore : get_all_projects not implemented"
#        #return self.projects

#    def get_project_with_pid(self, pid):
#        print "datastore : get_project_with_pid not implemented"
#        #return self.projects[pid]
