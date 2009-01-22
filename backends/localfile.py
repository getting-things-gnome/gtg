import os
import uuid

from gtg_core   import CoreConfig
from tools import cleanxml, taskxml

#Return the name of the backend as it should be displayed in the UI
def get_name() :
    return "backend name"
    
#Return a description of the backend
def get_description() :
    return "description"
    
#Return a dictionnary of parameters. Keys should be strings and
#are the name of the parameter.
#Value are string with value : string, password, int, bool
#and are an information about the type of the parameter
def get_parameters() :
    return {}

def get_features() :
    return {}

def get_type() :
    return "readwrite"


#The parameters dictionnary should match the dictionnary returned in 
#get_parameters. Anyway, the backend should care if one expected value is
#None or do not exist in the dictionnary.
class Backend :
    def __init__(self,parameters) :
        zefile = parameters["filename"]
        #If zefile is None, we create a new file
        if not zefile :
            zefile = "%s.xml" %(uuid.uuid4())
        if default_folder :
            self.zefile = os.path.join(CoreConfig.DATA_DIR,zefile)
            self.filename = zefile
        else :
            self.zefile = zefile
            self.filename = zefile
        self.doc, self.xmlproj = cleanxml.openxmlfile(self.zefile,"project")


    #Return the list of the task ID available in this backend
    def get_tasks_list(self) :
        tid_list = []
        for node in self.xmlproj.childNodes :
            tid_list.append(node.getAttribute("id"))
    
    
    #Fill the task "task_to_fill" with the information of the task TID
    #Return True if successful, False otherwhise
    def get_task(self,task_to_fill,tid) :
        for node in self.xmlproj.childNodes :
            if node.getAttribute("id") == tid :
                return taskxml.task_from_xml(task_to_fill,node)
        return False
    
    #Save the task in the backend
    def set_task(self,task) :
        tid = task.get_id()
        existing = None
        #First, we find the existing task from the treenode
        for node in self.xmlproj.childNodes :
            if node.getAttribute("id") == tid :
                existing = node
        t_xml = taskxml.task_to_xml(doc,task)
        #We then replace the existing node
        if existing :
            self.xmlproj.replaceChild(t_xml,existing)
        #If the node doesn't exist, we create it
        # (it might not be the case in all backends
        else :
            self.xmlproj.appendChild(t_xml)
        #In this particular backend, we write all the tasks
        #This is inherent to the XML file backend
        cleanxml.savexml(self.zefile,self.doc)
        return True
        
    #Completely remove the task with ID = tid
    def remove_task(self,tid) :
        for node in self.xmlproj.childNodes :
            if node.getAttribute("id") == tid :
                self.xmlproj.removeChild(node)
        cleanxml.savexml(self.zefile,self.doc)

    #Return an available ID for a new task so that a task with this ID
    #can be saved with set_task later.
    #If None, then GTG will create a new ID by itself
    #The ID cannot contain the character "@"
    def new_task_id(self) :
        return None

    #Called when GTG quit or disconnect the backend
    #You might pass here.
    def quit(self) :
        cleanxml.savexml(self.zefile,self.doc)
        
        
        
        
        
        
        
        
        

#    def __init__(self,parameters,datastore,default_folder=True,project=None) :
#        zefile = parameters["filename"]
#        #If zefile is None, we create a new file
#        if not zefile :
#            zefile = "%s.xml" %(uuid.uuid4())
#        self.ds = datastore
#        self.req = self.ds.get_requester()
#        if default_folder :
#            self.zefile = os.path.join(CoreConfig.DATA_DIR,zefile)
#            self.filename = zefile
#        else :
#            self.zefile = zefile
#            self.filename = zefile
#        
#        self.doc, self.xmlproj = cleanxml.openxmlfile(self.zefile,"project")
#        
#        proj_name = "Unknown"
#        if self.xmlproj.hasAttribute("name") :
#            proj_name = str(self.xmlproj.getAttribute("name"))
#            
#        if project :
#            self.project = project
#        else :
#            self.project = self.ds.new_project(proj_name,backend=self)
#                

#    def get_filename(self):
#        return self.filename
        
#    #This function should return a project object with all the current tasks in it.
#    def get_project(self) :
#        if self.xmlproj :
#            #t is the xml of each task
#            for t in self.xmlproj.childNodes:
#                cur_task = taskxml.task_from_xml(self.req,t)
#                #The sync is done in the task_from_xml method
#                #cur_task.sync()
#        return self.project   
#        
#    #This function will sync the whole project
#    def sync_project(self) :
#        doc,p_xml = cleanxml.emptydoc("project")
#        p_name = self.project.get_name()
#        if p_name :
#            p_xml.setAttribute("name", p_name)
#        for tid in self.project.list_tasks():
#            task = self.project.get_task(tid)
#            t_xml = taskxml.task_to_xml(doc,task)
#            p_xml.appendChild(t_xml)
#        
#        #it's maybe not optimal to open/close the file each time we sync
#        # but I'm not sure that those operations are so frequent
#        # might be changed in the future.
#        cleanxml.savexml(self.zefile,doc)

#    #It's easier to save the whole project each time we change a task
#    def sync_task(self,task) : #pylint: disable-msg=W0613
#        self.sync_project()
        
