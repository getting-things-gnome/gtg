import sys, time, os
from datetime import date
import string
import xml.dom.minidom


#This class represent a task in GTG.
class Task :
    def __init__(self, ze_id, newtask=False) :
        #the id of this task in the project
        #tid is a string ! (we have to choose a type and stick to it)
        self.tid = str(ze_id)
        self.content = ""
        #self.content = "<content>Press Escape or close this task to save it</content>"
        self.sync_func = None
        self.title = "My new task"
        #available status are : Active - Done - Dismiss - Deleted
        self.status = "Active"
        self.done_date = None
        self.due_date = None
        self.start_date = None
        self.parents = []
        self.children = []
        self.new_task_func = None
        self.can_be_deleted = newtask
        # tags
        self.tags = []
        
    def set_project(self,pid) :
        tid = self.get_id()
        result = tid.split('@')
        self.tid = "%s@%s" %(result[0],pid)
                
    def get_id(self) :
        return str(self.tid)
        
    def get_title(self) :
        return self.title
    
    def set_title(self,title) :
        #We should check for other task with the same title
        #In that case, we should add a number (like Tomboy does)
        if title :
            self.title = title.strip('\t\n')
        else :
            self.title = "(no title task)"
        
    def set_status(self,status,donedate=None) :
        self.can_be_deleted = False
        if status :
            self.status = status
            #If Done, we set the done date
            if status == "Done" :
                #to the specified date (if any)
                if donedate :
                    self.done_date = donedate
                #or to today
                else : 
                    self.done_date = date.today()
        
    def get_status(self) :
        return self.status
        
    #function to convert a string of the form XXXX-XX-XX
    #to a date (where X are integer)
    def __strtodate(self,stri) :
        if stri :
            y,m,d = stri.split('-')
            if y and m and d :
                return date(int(y),int(m),int(d))
        return None
        
    def set_due_date(self,fulldate) :
        if fulldate :
            self.due_date = self.__strtodate(fulldate)
        else :
            self.due_date = None
        
    def get_due_date(self) :
        if self.due_date :
            return str(self.due_date)
        else :
            return ''
            
    def set_start_date(self,fulldate) :
        if fulldate :
            self.start_date = self.__strtodate(fulldate)
        else :
            self.start_date = None
        
    def get_start_date(self) :
        if self.start_date :
            return str(self.start_date)
        else :
            return ''
            
    def get_done_date(self) :
        if self.done_date :
            return str(self.done_date)
        else :
            return ''
    
    def get_days_left(self) :
        if self.due_date :
            difference = self.due_date - date.today()
            return difference.days
        else :
            return None
        
    def get_text(self) :
        #defensive programmtion to avoid returning None
        if self.content :
            return str(self.content)
        else :
            return ""
    
    """
    get_excerpt return the beginning of the content of the task.
    If "lines" is provided and different than 0, it return the number X
    of line (or the whole content if it contains less lines)
    If "char" is provided, it returns the X first chars of content (or the 
    whole contents if it contains less char)
    If both char and lines are provided, the shorter one is returned.
    If none of them are provided (or if they are 0), this function is equivalent
    to get_text with with all XML stripped down.
    Warning : all markup informations are stripped down. Empty lines are also
    removed
    """
    def get_excerpt(self,lines=0,char=0) :
        #defensive programmtion to avoid returning None
        if self.content :
            element = xml.dom.minidom.parseString(self.content)
            txt = self.__strip_content(element)
            txt = txt.strip()
            #We keep the desired number of lines
            if lines > 0 :
                liste = txt.splitlines()
                for i in liste :
                    if i.strip() == "" :
                        liste.remove(i)
                to_keep = liste[:lines]
                txt = '\n'.join(to_keep)
            #We keep the desired number of char
            if char > 0 :
                txt = txt[:char]
            return txt
        else :
            return ""
            
    def __strip_content(self,element) :
        txt = ""
        if element :
            for n in element.childNodes :
                if n.nodeType == n.ELEMENT_NODE :
                    txt+= self.__strip_content(n)
                elif n.nodeType == n.TEXT_NODE :
                    txt += n.nodeValue
        return txt
        
    def set_text(self,texte) :
        self.can_be_deleted = False
        if texte != "<content/>" :
            #defensive programmation to filter bad formatted tasks
            if not texte.startswith("<content>") :
                texte = "<content>%s" %texte
            if not texte.endswith("</content>") :
                texte = "%s</content>" %texte
            self.content = str(texte)
        else :
            self.content = ''
    
    #Take a task object as parameter
    def add_subtask(self,task) :
        self.can_be_deleted = False
        #The if prevent an infinite loop
        if task not in self.children and task not in self.parents :
            self.children.append(task)
            task.add_parent(self)
            #now we set inherited attributes only if it's a new task
            if task.can_be_deleted :
                task.set_due_date(self.get_due_date())
                task.set_start_date(self.get_start_date())
                for t in self.get_tags() :
                    task.add_tag(t)
    
    #Return the task added as a subtask
    def new_subtask(self) :
        subt = self.new_task_func()
        self.add_subtask(subt)
        return subt
    
    #Take a task object as parameter 
    def remove_subtask(self,task) :
        if task in self.children :
            self.children.remove(task)
            if task.can_be_deleted :
                task.delete()
            else :
                task.remove_parent(self)
                self.sync()
            
    def remove_subtask_tid(self,tid) :
        st = self.get_subtask_tid(tid)
        if st :
            self.remove_subtask(st)
    
    def get_subtask_tid(self,tid) :
        to_ret = None
        for i in self.children :
            if i.get_id() == tid :
                to_ret = i
        return to_ret
    
    def get_subtasks(self) :
        zelist = []
        for i in self.children :
            zelist.append(i)
        return zelist
    
    def get_subtasks_tid(self) :
        zelist = []
        for i in self.children :
            zelist.append(i.get_id())
        return zelist
        
    #Take a task object as parameter
    def add_parent(self,task) :
        if task not in self.children and task not in self.parents :
            self.parents.append(task)
            #The if prevent an infinite loop
            task.add_subtask(self)
            
    #Take a task object as parameter
    def remove_parent(self,task) :
        self.parents.remove(task)
    
    def get_parents(self):
        zelist = []
        for i in self.parents :
            zelist.append(i)
        return zelist
 
    #Return true is the task has parent
    #If tag is provided, return True only
    #if the parent has this particular tag
    def has_parents(self,tag=None):
        #The "all tag" argument
        if tag and len(self.parents)!=0 :
            a = 0
            for p in self.parents :
                a+= p.has_tags(tag)
            return a
        else :
            return len(self.parents)!=0
       
    #Method called before the task is deleted
    def delete(self) :
        for i in self.get_parents() :
            i.remove_subtask(self)
        for j in self.get_subtasks() :
            j.remove_parent(self)
        #then we remove effectively the task
        self.purge(self.get_id())
        
    def set_delete_func(self,func) :
        self.purge = func
        
    #This is a callback
    def set_newtask_func(self,newtask) :
        self.new_task_func = newtask
        
    #This is a callback. The "sync" function has to be set
    def set_sync_func(self,sync) :
        self.sync_func = sync
        
    def sync(self) :
        if self.sync_func :
            self.sync_func(self.tid)
    def get_tags(self):
        #Return a copy of the list of tags. Not the original object.
        l = []
        for t in self.tags :
            l.append(t)
        return l

    def add_tag(self, t):
        #Do not add the same tag twice
        if not t in self.tags :
            self.tags.append(t)

    def remove_tag(self, t):
        if t in self.tags :
            self.tags.remove(t)

    def has_tags(self, tag_list):
        #We want to see if the task has no tags
        if tag_list == [None] :
            return self.tags == []
        elif tag_list == [] or tag_list == None:
            return True
        else :
            for my_tag in tag_list:
                if my_tag in self.tags: return True
        return False

    def __str__(self):
        s = ""
        s = s + "Task Object\n"
        s = s + "Title:  " + self.title + "\n"
        s = s + "Id:     " + self.tid + "\n"
        s = s + "Status: " + self.status + "\n"
        s = s + "Tags:   "  + str(self.tags)
        return s
        
###########################################################################
        
#This class represent a project : a list of tasks sharing the same backend
class Project :
    def __init__(self, name) :
        self.name = name
        self.list = {}
        self.sync_func = None
        self.pid = None
        self.tagstore = None
        
    def set_pid(self,pid) :
        self.pid = pid 
        for tid in self.list_tasks() :
            t = self.list.pop(tid)
            #We must inform the tasks of our pid
            t.set_project(pid)
            #then we re-add the task
            self.add_task(t)
        
    def get_pid(self) :
        return self.pid
    
    def set_name(self,name) :
        self.name = name
    
    def get_name(self) :
        return self.name
        
    def set_tagstore(self,store) :
        self.tagstore = store
        
    def list_tasks(self):
        result = self.list.keys()
        #we must ensure that we not return a None
        if not result :
            result = []
        return result
        
    def active_tasks(self) :
        return self.__list_by_status(["Active"])
        
    def unactive_tasks(self) :
        return self.__list_by_status(["Done","Dismissed"])
    
    def __list_by_status(self,status) :
        result = []
        for st in status :
            for tid in self.list.keys() :
                if self.get_task(tid).get_status() == st :
                    result.append(tid)
        return result
            
        
    def get_task(self,ze_id) :
        return self.list[str(ze_id)]
        
    def add_task(self,task) :
        tid = task.get_id()
        self.list[str(tid)] = task
        task.set_project(self.get_pid())
        task.set_newtask_func(self.new_task)
        task.set_delete_func(self.purge_task)
        #task.set_tagstore(self.tagstore)
        
    def new_task(self) :
        tid = self.__free_tid()
        task = Task(tid,newtask=True)
        self.add_task(task)
        return task
    
    def delete_task(self,tid) :
        self.list[tid].delete()
    
    def purge_task(self,tid) :
        del self.list[tid]
        self.sync()
    
    def __free_tid(self) :
        k = 0
        pid = self.get_pid()
        kk = "%s@%s" %(k,pid)
        while self.list.has_key(str(kk)) :
            k += 1
            kk = "%s@%s" %(k,pid)
        return str(kk)
        
    #This is a callback. The "sync" function has to be set
    def set_sync_func(self,sync) :
        self.sync_func = sync
        
    def sync(self) :
        self.sync_func()
        
        
    
