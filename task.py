import sys, time, os
from datetime import date
import string


#This class represent a task in GTG.
class Task :
    def __init__(self, ze_id) :
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
        
    def set_text(self,texte) :
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
        if task not in self.children and task not in self.parents :
            self.children.append(task)
            #The if prevent an infinite loop
            task.add_parent(self)
    
    #Take a task object as parameter 
    def remove_subtask(self,task) :
        self.children.remove(task)
        
    def get_subtasks(self) :
        zelist = []
        for i in self.children :
            zelist.append(i)
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
        return zeli
        
    #This is a callback. The "sync" function has to be set
    def set_sync_func(self,sync) :
        self.sync_func = sync
        
    def sync(self) :
        if self.sync_func :
            self.sync_func(self.tid)
        
###########################################################################
        
#This class represent a project : a list of tasks sharing the same backend
class Project :
    def __init__(self, name) :
        self.name = name
        self.list = {}
        self.sync_func = None
        self.pid = None
        
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
            
        
    def get_task(self,ze_id) :
        return self.list[str(ze_id)]
        
    def add_task(self,task) :
        tid = task.get_id()
        self.list[str(tid)] = task
        task.set_project(self.get_pid())
        
    def new_task(self) :
        tid = self.__free_tid()
        task = Task(tid)
        self.list[str(tid)] = task
        task.set_project(self.get_pid())
        return task
    
    def delete_task(self,tid) :
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
        
        
    
