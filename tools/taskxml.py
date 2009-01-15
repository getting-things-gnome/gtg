#Functions to convert a Task object to an XML string and back
import os, xml.dom.minidom

from tools import cleanxml

#Take a requester, an XML node and return a Task.
def task_from_xml(req,xmlnode) :
    cur_id = "%s" %xmlnode.getAttribute("id")
    cur_task = req.get_task(cur_id)
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
    
    return cur_task
