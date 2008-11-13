class DataStore:

    def __init__ (self):
        self.backends = []
        self.projects = {}
        self.tasks    = []

    def add_task(self, task):
        self.tasks.append(task)

    def remove_task(self, task):
        self.tasks.remove(task)

    def add_project(self, project):
        self.projects.append(project)

    def remove_project(self, project):
        self.projects.remove(project)

    def load_data(self):
        i = 1
        for b in self.backends:
            p = b.get_project()
            p.set_pid(str(i))
            p.set_sync_func(b.sync_project)
            self.projects[str(i)] = [b, p]
            self.tasks.append(p.list_tasks)
            i=i+1

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
