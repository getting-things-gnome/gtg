import os

from gtg_core   import CoreConfig, tagstore, requester
from gtg_core.task import Task,Project
#Here we import the default backend
from backends.localfile import Backend

BACKEND_COLUMN = 0
PROJ_COLUMN = 1

class DataStore:

    def __init__ (self):
        self.backends = []
        self.projects = {}
        self.cur_pid  = 1
        self.tagstore = tagstore.TagStore()
        self.requester = requester.Requester(self)
        
    #Create a new task and return it.
    #newtask should be True if you create a task
    #it should be task if you are importing an existing Task
    def new_task(self,tid,newtask=False) :
        task = Task(tid,self,newtask=newtask)
        uid,pid = tid.split('@') #pylint: disable-msg=W0612
        backend = self.projects[pid][BACKEND_COLUMN]
        task.set_sync_func(backend.sync_task)
        return task
    
    #We create a new project with a given backend
    #If the backend is None, then we use the default one
    #Default backend is localfile and we add a new one.
    def new_project(self,name,backend=None) :
        project = Project(name,self)
        if not backend :
            # Create backend
            backend   = Backend(None,self,project=project)
            backend.sync_project()
            # Register it in datastore
            self.register_backend(backend)
            
        project.set_pid(str(self.cur_pid))
        project.set_sync_func(backend.sync_project)
        self.projects[str(self.cur_pid)] = [backend, project]
        self.cur_pid = self.cur_pid + 1
        return project


    def remove_project(self, pid):
        b  = self.get_project_with_pid(pid)[0]
        self.projects.pop(pid)
        self.unregister_backend(b)
        fn = b.get_filename()
        os.remove(os.path.join(CoreConfig.DATA_DIR,fn))
        
    def get_tagstore(self) :
        return self.tagstore
        
    def get_requester(self) :
        return self.requester

    def load_data(self):
        for b in self.backends:
            b.get_project()

    def register_backend(self, backend):
        if backend != None:
            self.backends.append(backend)

    def unregister_backend(self, backend):
        if backend != None:
            self.backends.remove(backend)

    def get_all_projects(self):
        return self.projects

    def get_project_with_pid(self, pid):
        return self.projects[pid]

    def get_all_backends(self):
        return self.backends
