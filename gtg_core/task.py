from datetime import date
import xml.dom.minidom

from tools.listes import *

#This class represent a task in GTG.
#You should never create a Task directly. Use the datastore.new_task() function.
class Task :
    def __init__(self, ze_id, requester, newtask=False) :
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
        #The list of children tid
        self.children = []
        #callbacks
        self.new_task_func = None
        self.purge = None
        
        self.can_be_deleted = newtask
        # tags
        self.tags = []
        self.req = requester
        
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
        self.sync()
        
    def get_status(self) :
        return self.status
        
    #A task is workable if all children are done/deleted/dismiss
    def is_workable(self) :
        workable = True
        for c in self.get_subtasks() :
            if c.get_status() == "Active" :
                workable = False
        return workable
        
    #function to convert a string of the form YYYY-MM-DD
    #to a date
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
            
    def is_started(self) :
        if self.start_date :
            difference = date.today() - self.start_date
            return difference.days >= 0
        else :
            return True
            
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
                    txt += self.__strip_content(n)
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
    def add_subtask(self,tid) :
        self.can_be_deleted = False
        #The if prevent an infinite loop
        if tid not in self.children and tid not in self.parents :
            self.children.append(tid)
            task = self.req.get_task(tid)
            task.add_parent(self.get_id())
            #now we set inherited attributes only if it's a new task
            if task.can_be_deleted :
                task.set_due_date(self.get_due_date())
                task.set_start_date(self.get_start_date())
                for t in self.get_tags() :
                    task.add_tag(t.get_name())
    
    #Return the task added as a subtask
    def new_subtask(self) :
        subt = self.new_task_func()
        self.add_subtask(subt.get_id())
        return subt
            
    def remove_subtask(self,tid) :
        if tid in self.children :
            self.children.remove(tid)
            task = self.req.get_task(tid)
            if task.can_be_deleted :
                task.delete()
            else :
                task.remove_parent(self.get_id())
                self.sync()
    
    def get_subtasks(self) :
        zelist = []
        for i in self.children :
            zelist.append(self.req.get_task(i))
        return zelist
    
    def get_subtasks_tid(self) :
        return returnlist(self.children)
        
        
    #add and remove parents are private
    #Only the task itself can play with it's parent
    
    #Take a tid object as parameter
    def add_parent(self,tid) :
        #The if prevent a loop
        if tid not in self.children and tid not in self.parents :
            self.parents.append(tid)
            task = self.req.get_task(tid)
            task.add_subtask(self.get_id())
            
    #Take a tid as parameter
    def remove_parent(self,tid) :
        self.parents.remove(tid)
    
    def get_parents(self):
        return returnlist(self.parents)
 
    #Return true is the task has parent
    #If tag is provided, return True only
    #if the parent has this particular tag
    def has_parents(self,tag=None):
        #The "all tag" argument
        if tag and len(self.parents)!=0 :
            a = 0
            for tid in self.parents :
                p = self.req.get_task(tid)
                a += p.has_tags(tag)
            to_return = a
        else :
            to_return = len(self.parents)!=0
        return to_return
       
    #Method called before the task is deleted
    def delete(self) :
        for i in self.get_parents() :
            task = self.req.get_task(i)
            task.remove_subtask(self.get_id())
        for j in self.get_subtasks() :
            task = self.req.get_task(j)
            task.remove_parent(self.get_id())
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
            
            
    ######## Tag functions ##############
    #####################################
        
    def get_tags_name(self):
        #Return a copy of the list of tags. Not the original object.
        l = []
        for t in self.tags :
            name = t.get_name()
            l.append(name)
        return l
        
    #return a copy of the list of tag objects
    def get_tags(self) :
        return returnlist(self.tags)

    #This function add tag by name
    def add_tag(self, tagname):
        t = self.req.new_tag(tagname)
        #Do not add the same tag twice
        if not t in self.tags :
            self.tags.append(t)
            
    #remove by tagname
    def remove_tag(self, tagname):
        t = self.req.get_tag(tagname)
        if t in self.tags :
            self.tags.remove(t)

    #tag_list is a list of tagnames
    #return true if at least of the list is in the task
    def has_tags(self, tag_list=None,notag_only=False):
        #We want to see if the task has no tags
        if notag_only :
            return self.tags == []
        #Here, the user ask for the "empty" tag
        #And virtually every task has it.
        elif tag_list == [] or tag_list == None:
            return True
        elif tag_list :
            for tag in tag_list:
                if tag in self.tags: return True
        else :
            #Well, if we don't filter on tags or notag, it's true, of course
            return True
        return False
        
    #return the color of one tag that have a color defined
    #Yes, the choosen color is a bit random in case of multiple colored tags
    def get_color(self) :
        color = None
        for t in self.get_tags() :
            c = t.get_attribute("color")
            if c :
                color = c
        return color

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
#You should never create a Project directly. Use the datastore.new_project() function.
class Project :
    def __init__(self, name,datastore) :
        self.name = name
        self.list = {}
        self.sync_func = None
        self.pid = None
        self.datastore = datastore
        
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
            
    #Will return None if the project doesn't have this task
    def get_task(self,ze_id) :
        if self.list.has_key(ze_id) :
            return self.list[str(ze_id)]
        else :
            return None
        
    def add_task(self,task) :
        tid = task.get_id()
        if not self.list.has_key(tid) :
            self.list[str(tid)] = task
            task.set_project(self.get_pid())
            task.set_newtask_func(self.new_task)
            task.set_delete_func(self.purge_task)
        else :
            print task
        
    def new_task(self) :
        tid = self.__free_tid()
        task = self.datastore.new_task(tid,newtask=True)
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
        
        
    
