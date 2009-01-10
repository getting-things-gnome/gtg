import sys, time, os, xml.dom.minidom
import string, threading

from gtg_core   import CoreConfig
from tools import cleanxml

##This is for the awful pretty xml things
#tab = "\t"
#enter = "\n"

#todo : Backend should only provide one big "project" object and should 
#not provide get_task and stuff like that.
class Backend :
    def __init__(self,zefile,datastore,default_folder=True) :
        self.ds = datastore
        if default_folder :
            self.zefile = os.path.join(CoreConfig.DATA_DIR,zefile)
            self.filename = zefile
        else :
            self.zefile = zefile
            self.filename = zefile
        
        self.doc, self.__xmlproject = cleanxml.openxmlfile(self.zefile,"project")
        
        proj_name = "Unknown"
        if self.__xmlproject.length > 0 :
            xmlproj = self.__xmlproject[0]
            if xmlproj.hasAttribute("name") :
                proj_name = str(xmlproj.getAttribute("name"))
            
        self.project = self.ds.new_project(proj_name)
                

    def get_filename(self):
        return self.filename
        
    #This function should return a project object with all the current tasks in it.
    def get_project(self) :
        if self.__xmlproject[0] :
            subtasks = []
            #t is the xml of each task
            for t in self.__xmlproject[0].childNodes:
                cur_id = "%s" %t.getAttribute("id")
                cur_stat = "%s" %t.getAttribute("status")
                cur_task = self.ds.new_task(cur_id)
                donedate = cleanxml.readTextNode(t,"donedate")
                cur_task.set_status(cur_stat,donedate=donedate)
                #we will fill the task with its content
                cur_task.set_title(cleanxml.readTextNode(t,"title"))
                #the subtasks should be processed later, when all tasks
                #are in the project. We put all the information in a list.
                subtasks.append([cur_task,t.getElementsByTagName("subtask")])
                tasktext = t.getElementsByTagName("content")
                if len(tasktext) > 0 :
                    if tasktext[0].firstChild :
                        tas = "<content>%s</content>" %tasktext[0].firstChild.nodeValue
                        content = xml.dom.minidom.parseString(tas)
                        cur_task.set_text(content.firstChild.toxml())
                cur_task.set_due_date(cleanxml.readTextNode(t,"duedate"))
                cur_task.set_start_date(cleanxml.readTextNode(t,"startdate"))
                cur_tags = t.getAttribute("tags").replace(' ','').split(",")
                if "" in cur_tags: cur_tags.remove("")
                for tag in cur_tags: cur_task.add_tag(tag)
                #adding task to the project
                self.project.add_task(cur_task)
            #Now we can process the subtasks
            for t in subtasks :
                for s in t[1] :
                    sub = s.childNodes[0].nodeValue
                    subt = self.project.get_task(sub)
                    t[0].add_subtask(subt)
        return self.project

    def set_project(self, project):
        self.project = project
        
        
    #This function will sync the whole project
    def sync_project(self) :
        #Currently, we are not saving the tag table.
        doc = xml.dom.minidom.Document()
        p_xml = doc.createElement("project")
        p_name = self.project.get_name()
        if p_name :
            p_xml.setAttribute("name", p_name)
        doc.appendChild(p_xml)
        for tid in self.project.list_tasks():
            t = self.project.get_task(tid)
            t_xml = doc.createElement("task")
            t_xml.setAttribute("id",str(tid))
            t_xml.setAttribute("status" , t.get_status())
            tags_str = ""
            for tag in t.get_tags_name(): tags_str = tags_str + str(tag) + ","
            t_xml.setAttribute("tags"   , tags_str[:-1])
            p_xml.appendChild(t_xml)
            cleanxml.addTextNode(doc,t_xml,"title",t.get_title())
            cleanxml.addTextNode(doc,t_xml,"duedate",t.get_due_date())
            cleanxml.addTextNode(doc,t_xml,"startdate",t.get_start_date())
            cleanxml.addTextNode(doc,t_xml,"donedate",t.get_done_date())
            childs = t.get_subtasks()
            for c in childs :
                cleanxml.addTextNode(doc,t_xml,"subtask",c.get_id())
            tex = t.get_text()
            if tex :
                #We take the xml text and convert it to a string
                #but without the "<content />" 
                element = xml.dom.minidom.parseString(tex)
                temp = element.firstChild.toxml().partition("<content>")[2]
                desc = temp.partition("</content>")[0]
                #t_xml.appendChild(element.firstChild)
                cleanxml.addTextNode(doc,t_xml,"content",desc)
            #self.__write_textnode(doc,t_xml,"content",t.get_text())
        #it's maybe not optimal to open/close the file each time we sync
        # but I'm not sure that those operations are so frequent
        # might be changed in the future.
        cleanxml.savexml(self.zefile,doc)

    #It's easier to save the whole project each time we change a task
    def sync_task(self,task_id) :
        self.sync_project()
        
