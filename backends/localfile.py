import os
import uuid

from gtg_core   import CoreConfig
from tools import cleanxml, taskxml
import time

#Return the name of the backend as it should be displayed in the UI
def get_name() :
    return "Local File"
    
#Return a description of the backend
def get_description() :
    return "Your tasks are saved in an XML file located in your HOME folder"
    
#Return a dictionnary of parameters. Keys should be strings and
#are the name of the parameter.
#Value are string with value : string, password, int, bool
#and are an information about the type of the parameter
#Currently, only string is supported
def get_parameters() :
    dic = {}
    dic["filename"] = "string"
    return dic

def get_features() :
    return {}

#Types is one of : readwrite, readonly,import,export
def get_type() :
    return "readwrite"


#The parameters dictionnary should match the dictionnary returned in 
#get_parameters. Anyway, the backend should care if one expected value is
#None or do not exist in the dictionnary.
class Backend :
    def __init__(self,parameters) :
        if parameters.has_key("filename") :
            zefile = parameters["filename"]
        #If zefile is None, we create a new file
        else :
            zefile = "%s.xml" %(uuid.uuid4())
            parameters["filename"] = zefile
        #For the day we want to open files somewhere else
        default_folder = True
        if default_folder :
            self.zefile = os.path.join(CoreConfig.DATA_DIR,zefile)
            self.filename = zefile
        else :
            self.zefile = zefile
            self.filename = zefile
        self.doc, self.xmlproj = cleanxml.openxmlfile(self.zefile,"project")


    #Return the list of the task ID available in this backend
    def get_tasks_list(self) :
        #time.sleep(4)
        tid_list = []
        for node in self.xmlproj.childNodes :
            tid_list.append(node.getAttribute("id"))
        return tid_list
    
    
    #Fill the task "task_to_fill" with the information of the task TID
    #Return True if successful, False otherwhise
    def get_task(self,task_to_fill,tid) :
        #time.sleep(4)
        for node in self.xmlproj.childNodes :
            if node.getAttribute("id") == tid :
                return taskxml.task_from_xml(task_to_fill,node)
        return task_to_fill
    
    #Save the task in the backend
    def set_task(self,task) :
        #time.sleep(4)
        tid = task.get_id()
        existing = None
        #First, we find the existing task from the treenode
        for node in self.xmlproj.childNodes :
            if node.getAttribute("id") == tid :
                existing = node
        t_xml = taskxml.task_to_xml(self.doc,task)
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
        return None
        
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
        cleanxml.savexml(self.zefile,self.doc,backup=True)
