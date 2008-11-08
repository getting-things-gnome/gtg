import sys, time, os, xml.dom.minidom
import string, threading

from task import Task, Project
#Development variables. Should be removed
zefile = "mynote.xml"


#todo : Backend should only provide one big "project" object and should 
#not provide get_task and stuff like that.
class Backend :
    def __init__(self) :
        self.project = Project("project")
        if os.path.exists(zefile) :
            f = open(zefile,mode='r')
            # sanitize the pretty XML
            doc=xml.dom.minidom.parse(zefile)
            self.__cleanDoc(doc,"\t","\n")
            self.__xmlproject = doc.getElementsByTagName("project")
        
        #the file didn't exist, create it now
        else :
            doc = xml.dom.minidom.Document()
            self.__xmlproject = doc.createElement("project")
            doc.appendChild(self.__xmlproject)
            #then we create the file
            f = open(zefile, mode='a+')
            f.write(doc.toxml().encode("utf-8"))
            f.close()
     
    #Those two functions are there only to be able to read prettyXML
    #Source : http://yumenokaze.free.fr/?/Informatique/Snipplet/Python/cleandom       
    def __cleanDoc(self,document,indent="",newl=""):
        node=document.documentElement
        self.__cleanNode(node,indent,newl)
 
    def __cleanNode(self,currentNode,indent,newl):
        filter=indent+newl
        if currentNode.hasChildNodes:
            for node in currentNode.childNodes:
                if node.nodeType == 3:
                    node.nodeValue = node.nodeValue.lstrip(filter).strip(filter)
                    if node.nodeValue == "":
                        currentNode.removeChild(node)
            for node in currentNode.childNodes:
                self.__cleanNode(node,indent,newl)
        
    #This function should return a project object with all the current tasks in it.
    def get_project(self) :
        #t is the xml of each task
        for t in self.__xmlproject[0].childNodes:
            cur_id = "%s" %t.getAttribute("id")
            cur_task = Task(cur_id)
            #we will fill the task with its content
            xtitle = t.getElementsByTagName("title")
            if xtitle[0].hasChildNodes():
                title = xtitle[0].childNodes[0].nodeValue
                cur_task.set_title(title)
            content = t.getElementsByTagName("content")
            if content[0].hasChildNodes():
                texte = content[0].childNodes[0].nodeValue
                cur_task.set_text(texte)
            #adding task to the project
            self.project.add_task(cur_task)
        return self.project
        
    #This function will sync the whole project
    def sync_project(self) :
        #Currently, we are not saving the tag table.
        doc = xml.dom.minidom.Document()
        p_xml = doc.createElement("project")
        doc.appendChild(p_xml)
        for tid in self.project.list_tasks():
            t = self.project.get_task(tid)
            t_xml = doc.createElement("task")
            t_xml.setAttribute("id",str(tid))
            p_xml.appendChild(t_xml)
            title = doc.createElement("title")
            t_xml.appendChild(title)
            title.appendChild(doc.createTextNode(t.get_title()))
            content = doc.createElement("content")
            t_xml.appendChild(content)
            content.appendChild(doc.createTextNode(t.get_text()))
        #it's maybe not optimal to open/close the file each time we sync
        # but I'm not sure that those operations are so frequent
        # might be changed in the future.
        f = open(zefile, mode='w+')
        f.write(doc.toprettyxml().encode("utf-8"))
        f.close()

    #It's easier to save the whole project each time we change a task
    def sync_task(self) :
        self.sync_project()
        
