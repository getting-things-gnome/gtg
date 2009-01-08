import os
from gtg_core   import CoreConfig, tagstore

class DataStore:

    def __init__ (self):
        self.backends = []
        self.projects = {}
        self.tasks    = []
        self.cur_pid  = 1
#        self.tags     = []
        self.tagstore = tagstore.TagStore()

#    def add_task(self, task):
#        print "add_task called"
#        self.tasks.append(task)

    def remove_task(self, task):
        self.tasks.remove(task)

    #p = project
    #b = backend
    def add_project(self, p, b):
        p.set_pid(str(self.cur_pid))
        p.set_tagstore(self.tagstore)
        self.projects[str(self.cur_pid)] = [b, p]
        self.cur_pid = self.cur_pid + 1

    def remove_project(self, project):
        pid = project.get_pid()
        b  = self.get_project_with_pid(pid)[0]
        self.projects.pop(pid)
        self.unregister_backend(b)
        fn = b.get_filename()
        os.remove(os.path.join(CoreConfig.DATA_DIR,fn))
        
    def get_tagstore(self) :
        return self.tagstore

    def load_data(self):
        for b in self.backends:
            p = b.get_project()
            p.set_pid(str(self.cur_pid))
            p.set_sync_func(b.sync_project)
            self.projects[str(self.cur_pid)] = [b, p]
            tid_list = p.list_tasks()
            self.tasks.append(tid_list)
#            for t in tid_list:
#                for tag in p.get_task(t).get_tags_name():
#                    if tag not in self.tags: self.tags.append(tag)
            self.cur_pid=self.cur_pid+1

    def register_backend(self, backend):
        if backend!=None:
            self.backends.append(backend)

    def unregister_backend(self, backend):
        if backend!=None:
            self.backends.remove(backend)

    def get_tasks_for_query(self):
        pass

    def get_all_tasks(self):
        return self.tasks

    def get_all_projects(self):
        return self.projects
    
    def get_all_tags(self):
        return self.tagstore.get_all_tags_name()

    def reload_tags(self):
        print "reload_tags called"
#        self.tags = []
#        for p in self.projects:
#            for tid in self.projects[p][1].list_tasks():
#                for tag in self.projects[p][1].get_task(tid).get_tags():
#                    if tag not in self.tags: self.tags.append(tag)

    def get_project_with_pid(self, pid):
        return self.projects[pid]

    def get_projects_for_query(self):
        pass

    def get_all_backends(self):
        return self.backends
