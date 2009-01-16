import os
import uuid

from gtg_core   import CoreConfig
from tools import cleanxml, taskxml

#todo : Backend should only provide one big "project" object and should 
#not provide get_task and stuff like that.

#If a project is provided as parameter, it means that we are creating
#a new backend for this new project. It generally means that zefile will be "None"
class Backend :
    def __init__(self,zefile,datastore,default_folder=True,project=None) :
        #If zefile is None, we create a new file
        if not zefile :
            zefile = "%s.xml" %(uuid.uuid4())
        self.ds = datastore
        self.req = self.ds.get_requester()
        if default_folder :
            self.zefile = os.path.join(CoreConfig.DATA_DIR,zefile)
            self.filename = zefile
        else :
            self.zefile = zefile
            self.filename = zefile
        
        self.doc, self.xmlproj = cleanxml.openxmlfile(self.zefile,"project")
        
        proj_name = "Unknown"
        if self.xmlproj.hasAttribute("name") :
            proj_name = str(self.xmlproj.getAttribute("name"))
            
        if project :
            self.project = project
        else :
            self.project = self.ds.new_project(proj_name,backend=self)
                

    def get_filename(self):
        return self.filename
        
    #This function should return a project object with all the current tasks in it.
    def get_project(self) :
        if self.xmlproj :
            #t is the xml of each task
            for t in self.xmlproj.childNodes:
                cur_task = taskxml.task_from_xml(self.req,t)
                #The sync is done in the task_from_xml method
                #cur_task.sync()
        return self.project   
        
    #This function will sync the whole project
    def sync_project(self) :
        doc,p_xml = cleanxml.emptydoc("project")
        p_name = self.project.get_name()
        if p_name :
            p_xml.setAttribute("name", p_name)
        for tid in self.project.list_tasks():
            task = self.project.get_task(tid)
            t_xml = taskxml.task_to_xml(doc,task)
            p_xml.appendChild(t_xml)
        
        #it's maybe not optimal to open/close the file each time we sync
        # but I'm not sure that those operations are so frequent
        # might be changed in the future.
        cleanxml.savexml(self.zefile,doc)

    #It's easier to save the whole project each time we change a task
    def sync_task(self,task) : #pylint: disable-msg=W0613
        self.sync_project()
        
