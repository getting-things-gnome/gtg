class DataStore:

    def __init__ (self):
        self.backends = []
        self.projects = {}
        self.tasks    = []
        self.cur_pid  = 1

    def add_task(self, task):
        self.tasks.append(task)

    def remove_task(self, task):
        self.tasks.remove(task)

    def add_project(self, project, backend):
        project.set_pid(self.cur_pid)
        p = project
        b = backend
        self.projects[str(self.cur_pid)] = [b, p]
        self.cur_pid = self.cur_pid + 1

    def remove_project(self, project):
        self.projects.pop(project.get_pid())

    def load_data(self):
        for b in self.backends:
            p = b.get_project()
            p.set_pid(str(self.cur_pid))
            p.set_sync_func(b.sync_project)
            self.projects[str(self.cur_pid)] = [b, p]
            self.tasks.append(p.list_tasks)
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

    def get_projects_for_query(self):
        pass

    def get_all_backends(self):
        return self.backends
