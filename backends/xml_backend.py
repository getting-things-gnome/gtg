import sys, time, os, xml.dom.minidom
import string, threading

from task import Task, Project

#This is for the awful pretty xml things
tab = "\t"
enter = "\n"

#todo : Backend should only provide one big "project" object and should 
#not provide get_task and stuff like that.
class Backend :
    def __init__(self,zefile) :
        self.zefile = zefile
        if os.path.exists(self.zefile) :
            f = open(self.zefile,mode='r')
            doc=xml.dom.minidom.parse(self.zefile)
            self.__cleanDoc(doc,tab,enter)
            self.__xmlproject = doc.getElementsByTagName("project")
            proj_name = str(self.__xmlproject[0].getAttribute("name"))
            self.project = Project(proj_name)
        
        #the file didn't exist, create it now
        else :
            doc = xml.dom.minidom.Document()
            self.__xmlproject = doc.createElement("project")
            doc.appendChild(self.__xmlproject)
            #then we create the file
            f = open(self.zefile, mode='a+')
            f.write(doc.toxml().encode("utf-8"))
            f.close()
     
    #Those two functions are there only to be able to read prettyXML
    #Source : http://yumenokaze.free.fr/?/Informatique/Snipplet/Python/cleandom       
    def __cleanDoc(self,document,indent="",newl=""):
        node=document.documentElement
        self.__cleanNode(node,indent,newl)
 
    def __cleanNode(self,currentNode,indent,newl):
        filter=indent+newl
        if currentNode.hasChildNodes :
        #and currentNode.nodeName != "content":
            for node in currentNode.childNodes:
                if node.nodeType == 3 :
                    node.nodeValue = node.nodeValue.lstrip(filter).strip(filter)
                    if node.nodeValue == "":
                        currentNode.removeChild(node)
            for node in currentNode.childNodes:
                self.__cleanNode(node,indent,newl)
#        elif currentNode.nodeName == "content" :
        
    #This function should return a project object with all the current tasks in it.
    def get_project(self) :
        if self.__xmlproject[0] :
            #t is the xml of each task
            for t in self.__xmlproject[0].childNodes:
                cur_id = "%s" %t.getAttribute("id")
                cur_stat = "%s" %t.getAttribute("status")
                cur_task = Task(cur_id)
                donedate = self.__read_textnode(t,"donedate")
                cur_task.set_status(cur_stat,donedate=donedate)
                #we will fill the task with its content
                cur_task.set_title(self.__read_textnode(t,"title"))
                #cur_task.set_text(self.__read_textnode(t,"content"))
                tasktext = t.getElementsByTagName("content")
                if len(tasktext) > 0 :
                    #cur_task.set_text(tasktext[0].toxml())
                    tas = "<content>%s</content>" %tasktext[0].firstChild.nodeValue
                    content = xml.dom.minidom.parseString(tas)
                    cur_task.set_text(content.firstChild.toxml())
                cur_task.set_due_date(self.__read_textnode(t,"duedate"))
                cur_task.set_start_date(self.__read_textnode(t,"startdate"))
                #adding task to the project
                self.project.add_task(cur_task)
        return self.project
    
    #This is a method to read the textnode of the XML
    def __read_textnode(self,node,title) :
        n = node.getElementsByTagName(title)
        if n and n[0].hasChildNodes() :
            content = n[0].childNodes[0].nodeValue
            if content :
                return content
        return None
        
        
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
            t_xml.setAttribute("status",t.get_status())
            p_xml.appendChild(t_xml)
            self.__write_textnode(doc,t_xml,"title",t.get_title())
            self.__write_textnode(doc,t_xml,"duedate",t.get_due_date())
            self.__write_textnode(doc,t_xml,"startdate",t.get_start_date())
            self.__write_textnode(doc,t_xml,"donedate",t.get_done_date())
            tex = t.get_text()
            if tex :
                #We take the xml text and convert it to a string
                #but without the "<content />" 
                element = xml.dom.minidom.parseString(tex)
                temp = element.firstChild.toxml().partition("<content>")[2]
                desc = temp.partition("</content>")[0]
                #t_xml.appendChild(element.firstChild)
                self.__write_textnode(doc,t_xml,"content",desc)
            #self.__write_textnode(doc,t_xml,"content",t.get_text())
        #it's maybe not optimal to open/close the file each time we sync
        # but I'm not sure that those operations are so frequent
        # might be changed in the future.
        f = open(self.zefile, mode='w+')
        f.write(doc.toprettyxml(tab,enter).encode("utf-8"))
#        f.write(doc.toxml().encode("utf-8"))
        f.close()
    
#    #our own method that will print pretty xml
#    def __prettyxml(self,doc) :
#        txt = ""
#        if doc.nodeType == doc.TEXT_NODE :
#            txt += doc.toxml()
#        elif doc.nodeName == "content" :
#            txt += "\n"
#            txt += doc.toxml()
#            #txt += "\n"
#        else :
#            childs = doc.childNodes
#            if len(childs) == 1 :
#                if doc.firstChild.nodeType == doc.TEXT_NODE :
#                    txt += "\n"
#                    txt += doc.toxml()
#                    #txt += "\n"
#                else :
#                    txt += "\n"
#                    txt += "<%s>"
#                    txt += self.__prettyxml(childs[0])
#            else :
#                for n in childs :
#                    txt += self.__prettyxml(n)
#        return txt
     
    #Method to add a text node in the doc to the parent node   
    def __write_textnode(self,doc,parent,title,content) :
        if content :
            element = doc.createElement(title)
            parent.appendChild(element)
            element.appendChild(doc.createTextNode(content))

    #It's easier to save the whole project each time we change a task
    def sync_task(self,task_id) :
        self.sync_project()
        
