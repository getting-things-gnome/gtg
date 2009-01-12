#Requester is a pure View object. It will not do anything but it will
#be used by any Interface to handle the requests to the datastore

PROJ_COLUMN = 1

class Requester :
    def __init__(self,datastore) :
        self.ds = datastore
        self.tagstore = self.ds.get_tagstore()
        
    ############## Projects #######################
    ###############################################
    
    #This method will return  a list 3-tuple :
    #pid : the pid of the project
    #name : the name of the project
    #nbr : the number of active tasks in this project
    def get_projects(self) :
        l = []
        projects = self.ds.get_all_projects()
        for p_key in projects:
            d = {}
            p = projects[p_key][PROJ_COLUMN]
            d["pid"] = p_key
            d["name"] = p.get_name()
            d["nbr"] = len(p.active_tasks())
            l.append(d)
            
        return l
            
    
    ############### Tags ##########################
    ###############################################    
    #Not used currently because it returns every tag that was ever used
    def get_all_tags(self):
        return self.tagstore.get_all_tags()
        
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
    
    
