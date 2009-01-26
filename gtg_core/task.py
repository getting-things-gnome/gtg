from datetime import date
import xml.dom.minidom

from tools.listes import *
from tools.dates import *

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
        self.closed_date = None
        self.due_date = None
        self.start_date = None
        self.parents = []
        #The list of children tid
        self.children = []
        self.can_be_deleted = newtask
        # tags
        self.tags = []
        self.req = requester
        #If we don't have a newtask, we will have to load it.
        self.loaded = newtask
                
    def is_loaded(self) :
        return self.loaded
        
    def set_loaded(self) :
        self.loaded = True
    
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
        self.sync()
        
    def set_status(self,status,donedate=None) :
        self.can_be_deleted = False
        if status :
            self.status = status
            #If Done, we set the done date
            if status in ["Done","Dismiss"] :
                #to the specified date (if any)
                if donedate :
                    self.closed_date = donedate
                #or to today
                else : 
                    self.closed_date = date.today()
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
        
    def set_due_date(self,fulldate) :
        if fulldate :
            self.due_date = strtodate(fulldate)
            for child in self.get_subtasks() :
                child.set_due_date(fulldate)
        else :
            self.due_date = None
        
    #Due date return the most urgent date of all parents
    def get_due_date(self) :
        if self.due_date :
            zedate = self.due_date
        else :
            zedate = date.max
        for par in self.get_parents() :
            #Here we compare with the parent's due date
            pardate_str = self.req.get_task(par).get_due_date()
            if pardate_str :
                pardate = strtodate(pardate_str)
                if pardate and zedate > pardate :
                    zedate = pardate
        if zedate == date.max :
            return ''
        else :
            return str(zedate)

    def set_start_date(self,fulldate) :
        if fulldate :
            self.start_date = strtodate(fulldate)
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
            
    def get_closed_date(self) :
        if self.closed_date :
            return str(self.closed_date)
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
            #Except for due date because a child always has to be due
            #before its parent
            task.set_due_date(self.get_due_date())
            if task.can_be_deleted :
                task.set_start_date(self.get_start_date())
                for t in self.get_tags() :
                    task.add_tag(t.get_name())
    
    #Return the task added as a subtask
    def new_subtask(self) :
        uid,pid = self.get_id().split('@') #pylint: disable-msg=W0612
        subt = self.req.new_task(pid=pid,newtask=True)
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
        if tid and tid not in self.children and tid not in self.parents :
            self.parents.append(tid)
            self.sync()
            task = self.req.get_task(tid)
            task.add_subtask(self.get_id())
            task.sync()
            
    #Take a tid as parameter
    def remove_parent(self,tid) :
        if tid and tid in self.parents:
            self.parents.remove(tid)
            self.sync()
            parent = self.req.get_task(tid)
            if parent :
                parent.remove_subtask(self.get_id())
                parent.sync()
    
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
    #This method is called by the datastore and should not be called directly
    #Use the requester
    def delete(self) :
        for i in self.get_parents() :
            task = self.req.get_task(i)
            task.remove_subtask(self.get_id())
        for task in self.get_subtasks() :
            task.remove_parent(self.get_id())
        #then we remove effectively the task
        #self.req.delete_task(self.get_id())
        
    #This is a callback. The "sync" function has to be set
    def set_sync_func(self,sync) :
        self.sync_func = sync
        
    def sync(self) :
        if self.sync_func :
            self.sync_func(self)
            
            
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

