# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personnal organizer for the GNOME desktop
# Copyright (c) 2008-2009 - Lionel Dricot & Bertrand Rousseau
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

#Functions to convert a Task object to an XML string and back
import xml.dom.minidom

from GTG.tools import cleanxml

#Take an empty task, an XML node and return a Task.
def task_from_xml(task,xmlnode) :
    cur_task = task
    cur_stat = "%s" %xmlnode.getAttribute("status")
    donedate = cleanxml.readTextNode(xmlnode,"donedate")
    cur_task.set_status(cur_stat,donedate=donedate)
    #we will fill the task with its content
    cur_task.set_title(cleanxml.readTextNode(xmlnode,"title"))
    #the subtasks
    sub_list = xmlnode.getElementsByTagName("subtask")
    for s in sub_list :
        sub_tid = s.childNodes[0].nodeValue
        cur_task.add_subtask(sub_tid)
    attr_list = xmlnode.getElementsByTagName("attribute")
    for a in attr_list:
        content = a.childNodes[0].nodeValue
        key = a.getAttribute("key")
        namespace = a.getAttribute("namespace")
        cur_task.set_attribute(key, content, namespace=namespace)
    tasktext = xmlnode.getElementsByTagName("content")
    if len(tasktext) > 0 :
        if tasktext[0].firstChild :
            tas = "<content>%s</content>" %tasktext[0].firstChild.nodeValue
            content = xml.dom.minidom.parseString(tas)
            cur_task.set_text(content.firstChild.toxml()) #pylint: disable-msg=E1103 
    cur_task.set_due_date(cleanxml.readTextNode(xmlnode,"duedate"))
    cur_task.set_start_date(cleanxml.readTextNode(xmlnode,"startdate"))
    cur_tags = xmlnode.getAttribute("tags").replace(' ','').split(",")
    if "" in cur_tags: cur_tags.remove("")
    for tag in cur_tags: cur_task.add_tag(tag)
    #Why should we sync here ? It makes no sense
    #cur_task.sync()
    
    return cur_task

#Task as parameter the doc where to put the XML node
def task_to_xml(doc,task) :
    t_xml = doc.createElement("task")
    t_xml.setAttribute("id",task.get_id())
    t_xml.setAttribute("status" , task.get_status())
    tags_str = ""
    for tag in task.get_tags_name(): 
        tags_str = tags_str + str(tag) + ","
    t_xml.setAttribute("tags", tags_str[:-1])
    cleanxml.addTextNode(doc,t_xml,"title",task.get_title())
    cleanxml.addTextNode(doc,t_xml,"duedate",task.get_due_date())
    cleanxml.addTextNode(doc,t_xml,"startdate",task.get_start_date())
    cleanxml.addTextNode(doc,t_xml,"donedate",task.get_closed_date())
    childs = task.get_subtasks_tid()
    for c in childs :
        cleanxml.addTextNode(doc,t_xml,"subtask",c)
    for a in task.attributes:
    	namespace,key=a
    	content=task.attributes[a]
    	element = doc.createElement('attribute')
    	element.setAttribute("namespace", namespace)
    	element.setAttribute("key", key)
    	element.appendChild(doc.createTextNode(content))
        t_xml.appendChild(element)
    tex = task.get_text()
    if tex :
        #We take the xml text and convert it to a string
        #but without the "<content />" 
        element = xml.dom.minidom.parseString(tex)
        temp = element.firstChild.toxml().partition("<content>")[2] #pylint: disable-msg=E1103
        desc = temp.partition("</content>")[0]
        #t_xml.appendChild(element.firstChild)
        cleanxml.addTextNode(doc,t_xml,"content",desc)
    #self.__write_textnode(doc,t_xml,"content",t.get_text())
    return t_xml
