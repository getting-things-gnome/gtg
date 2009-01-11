#Requester is a pure View object. It will not do anything but it will
#be used by any Interface to handle the requests to the datastore

class Requester :
    def __init__(self,datastore) :
        self.ds = datastore
        self.tagstore = self.ds.get_tagstore()
        
    #Not used currently because it returns every tag that was ever used
    def get_all_tags(self):
        return self.tagstore.get_all_tags()
        
    #return only tags that are currently used in a task
    #FIXME it should be only active and visible tasks
    def get_used_tags(self) :
        l = []
        projects = self.ds.get_all_projects()
        for p in projects :
            for tid in projects[p][1].list_tasks():
                t = projects[p][1].get_task(tid)
                for tag in t.get_tags() :
                    if tag not in l: l.append(tag)
        return l
    
