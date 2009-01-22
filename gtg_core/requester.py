from tools.listes import *
#Requester is a pure View object. It will not do anything but it will
#be used by any Interface to handle the requests to the datastore

BACKEND_COLUMN = 0
PROJ_COLUMN    = 1

#There could be multiple requester. It means that a requester should never
#Hold any data except a reference to its datastore.
class Requester :
    def __init__(self,datastore) :
        self.ds = datastore
        
        
    ############## Tasks ##########################
    ###############################################
    
    #Get the task with the given pid
    #If the task doesn't exist, we create it and force the pid
    def get_task(self,tid) :
        #FIXME
        print "requester : get_task not implemented"
#        task = None
#        if tid :
#            uid,pid = tid.split('@') #pylint: disable-msg=W0612
#            proj = self.ds.get_all_projects()[pid][PROJ_COLUMN]
#            task = proj.get_task(tid)
#            #If the task doesn't exist, we create it with a forced pid
#            if not task :
#                task = self.ds.new_task(tid,newtask=False)
#                #Adding the task to its project
#                proj.add_task(task)
#        return task
        
    #Pid is the project in which the new task will be created
    #MODIFICATION class (the data will be modified)
    def new_task(self,pid,tags=None) :
        #FIXME
        print "requester : new_task not implemented"
#        task = self.ds.get_all_projects()[pid][PROJ_COLUMN].new_task()
#        if tags :
#            for t in tags :
#                task.add_tag(t.get_name())
#        return task
        
#    # Return a new Task object with a forced tid. Used only for import
#    def new_imported_task(self,tid) :
#        
#        return task
        
    #MODIFICATION class (the data will be modified)
    def delete_task(self,tid) :
        #FIXME
        print "requester : delete_task not implemented"
#        pr = self.get_project_from_uid(tid)
#        pr.delete_task(tid)
        
    #Return a list of active tasks tid
    # projects = []. All the tasks will belong to one of those project
    # If none, all tasks are eligible
    #
    # tags = []. All tasks will have at least one of those tags.
    # If None, all tasks are eligible
    #
    # Status = [] : a list of status to choose from
    # available status are : Active - Done - Dismiss - Deleted
    # If none, all tasks are eligible
    #
    # notag_only : if True, only tasks without tags are selected
    #
    # started_only : if True, only tasks with an already passed started date are selected
    # (task with no startdate are considered as started)
    #
    # is_root : if True, only tasks that have no parent in the current selection
    # are eligible. If False, all tasks are eligible
    def get_tasks_list(self,tags=None, status=["Active"],notag_only=False,\
                                started_only=True,is_root=False) :
        l_tasks = []
        #TODO : ds.all_tasks
        print "requester.get_taks_list : ds.all_tasks not implemented"
        for tid in self.ds.all_tasks() :
            task = self.get_task(tid)
            #This is status filtering
            if not task.get_status() in status :
                task = None
            #This is tag filtering
            #If we still have a task and we need to filter tags
            #(if tags is None, this test is skipped)
            if task and tags :
                if not task.has_tags(tags) :
                    task = None
                #Checking here the is_root because it has sense only with tags
                elif is_root and task.has_parents(tag=tags) :
                    task = None
            #If tags = [], we still check the is_root
            elif task and is_root :
                if task.has_parents() : task = None
            #Now checking if it has no tag
            if task and notag_only :
                if not task.has_tags(notag_only=notag_only) :
                    task = None
            #This is started filtering
            if task and started_only :
                if not task.is_started() :
                    task = None
                    
            #If we still have a task, we return it
            if task :
                l_tasks.append(tid)
        return l_tasks
        
    #Workable means that the task have no pending subtasks and can be done directly
    def get_active_tasks_list(self,tags=None,notag_only=False,\
                            started_only=True,is_root=False,workable=False) :
        l_tasks = []
        if workable :
            temp_tasks = self.get_active_tasks_list(tags=tags, notag_only=notag_only,\
                                started_only=True,is_root=False,workable=False)
            for tid in temp_tasks :
                t = self.get_task(tid)
                if t.is_workable() :
                    l_tasks.append(tid)
            return l_tasks
        else :
            active = ["Active"]
            temp_tasks = self.get_tasks_list(tags=tags,status=active,\
                 notag_only=notag_only,started_only=started_only,is_root=is_root)
            for t in temp_tasks :
                l_tasks.append(t)
            return l_tasks
        
    def get_closed_tasks_list(self,tags=None,notag_only=False,\
                            started_only=True,is_root=False) :
        closed = ["Done","Dismiss","Deleted"]
        return self.get_tasks_list(tags=tags,status=closed,\
                 notag_only=notag_only,started_only=started_only,is_root=is_root)
                 
        
    ############## Projects #######################
    ###############################################
    
    #This method will return  a list 3-tuple :
    #pid : the pid of the project
    #name : the name of the project
    #nbr : the number of active tasks in this project
    def get_projects(self) :
        print "requester : get_projects to remove"
#        l = []
#        projects = self.ds.get_all_projects()
#        for p_key in projects:
#            d = {}
#            p = projects[p_key][PROJ_COLUMN]
#            d["pid"] = p_key
#            d["name"] = p.get_name()
#            d["nbr"] = len(p.active_tasks())
#            l.append(d)  
#        return l
    
    #MODIFICATION class (the data will be modified)
    def remove_project(self,pid) :
        print "requester : remove_project to remove"
#        self.ds.remove_project(pid)
        
    def get_projects_list(self) :
        print "requester : get_projects_list"
#        return self.ds.get_all_projects().keys()
        
    def get_project_from_pid(self,pid) :
        print "requester : get_project_from_pid"
#        projects = self.ds.get_all_projects()
#        return projects[pid][PROJ_COLUMN]
        
    def get_project_from_uid(self,uid) :
        print "requester : get_project_from_uid"
#        tid,pid = uid.split('@') #pylint: disable-msg=W0612
#        project = self.ds.get_all_projects()[pid][PROJ_COLUMN]
#        return project
    
    def get_backend_from_uid(self,uid) :
        print "requester : get_backend_from_uid"
#        tid,pid = uid.split('@') #pylint: disable-msg=W0612
#        backend = self.ds.get_all_projects()[pid][BACKEND_COLUMN]
#        return backend
    
    ############### Tags ##########################
    ###############################################    
    
    
    #MODIFICATION
    def new_tag(self,tagname) :
        return self.ds.get_tagstore().new_tag(tagname)
        
    def get_tag(self,tagname) :
        return self.ds.get_tagstore().get_tag(tagname)
    
    #Not used currently because it returns every tag that was ever used
    def get_all_tags(self):
        return returnlist(self.ds.get_tagstore().get_all_tags())
        
    def get_notag_tag(self) :
        return self.ds.get_tagstore().get_notag_tag()
    def get_alltag_tag(self) :
        return self.ds.get_tagstore().get_alltag_tag()
        
        
    #return only tags that are currently used in a task
    #FIXME it should be only active and visible tasks
    def get_used_tags(self) :
        l = []
        projects = self.ds.get_all_projects()
        for p in projects :
            for tid in projects[p][PROJ_COLUMN].list_tasks():
                t = projects[p][PROJ_COLUMN].get_task(tid)
                for tag in t.get_tags() :
                    if tag not in l: l.append(tag)
        return l
    
    
