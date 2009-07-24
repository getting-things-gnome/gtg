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


import threading
import gobject
import time

from GTG.core      import tagstore, requester
from GTG.core.task import Task


#Only the datastore should access to the backend
DEFAULT_BACKEND = "1"
#If you want to debug a backend, it can be useful to disable the threads
THREADING = True

class DataStore(gobject.GObject):
    __gsignals__ = { 'refresh': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                                   (str,)) }

    def __init__ (self):
        gobject.GObject.__init__(self)
        self.backends = {}
        self.tasks = {}
        self.tagstore = tagstore.TagStore()
        self.requester = requester.Requester(self)
        
    def all_tasks(self) :
        all_tasks = []
        #Call this only when we want to force a refresh
#        for key in self.backends :
#            b = self.backends[key]
#            tlist = b.get_tasks_list()
#            all_tasks += tlist
        #We also add tasks that are still not in a backend (because of threads)
        tlist = self.tasks.keys()
        for t in tlist :
            task = self.tasks[t]
            if task.is_loaded() :
                all_tasks.append(t)
        return all_tasks

    def has_task(self,tid) :
        return self.tasks.has_key(tid)
        
    def get_task(self,tid) :
        if self.tasks.has_key(tid) :
            empty_task = self.tasks[tid]
        else :
            empty_task = self.new_task(tid,newtask=False)
        if tid and not empty_task.is_loaded() :
            uid,pid = tid.split('@') #pylint: disable-msg=W0612
            back = self.backends[pid]
            task = back.get_task(empty_task,tid)
        else :
            task = empty_task
        #If the task doesn't exist, we create it with a forced pid
        return task
        
    def delete_task(self,tid) :
        if tid and self.tasks.has_key(tid) :
            self.tasks[tid].delete()
            uid,pid = tid.split('@') #pylint: disable-msg=W0612
            back = self.backends[pid]
            #self.locks.acquire(tid)
            #Check that the task still exist. It might have been deleted
            #by its parent a few line earlier :
            if self.tasks.has_key(tid) :
                self.tasks.pop(tid)
            back.remove_task(tid)
            #The following line should not be necessary
            #self.locks.release(tid)
        
    #Create a new task and return it.
    #newtask should be True if you create a task
    #it should be False if you are importing an existing Task
    def new_task(self,tid=None,pid=None,newtask=False) :
        #If we don't have anything, we use the default PID
        if not pid : pid = DEFAULT_BACKEND
        #If tid, we force that tid and create a real new task
        if tid and not self.tasks.has_key(tid) :
            task = Task(tid,self.requester,newtask=newtask)
            uid,pid = tid.split('@') #pylint: disable-msg=W0612
            self.tasks[tid] = task
            return task
        #Else we create a new task in the given pid
        elif not tid and pid and self.backends.has_key(pid):
            newtid = self.backends[pid].new_task_id()
            task = Task(newtid,self.requester,newtask=newtask)
            self.tasks[newtid] = task
            task = self.backends[pid].get_task(task,newtid)
            return task
        elif tid :
            return self.tasks[tid]
        else :
            print "not possible to build the task = bug"
            return None
        
    def get_tagstore(self) :
        return self.tagstore
        
    def get_requester(self) :
        return self.requester

    def register_backend(self, dic):
        if dic.has_key("backend") :
            pid = dic["pid"]
            backend = dic["backend"]
            source = TaskSource(backend,dic,self.refresh_ui)
            self.backends[pid] = source
            #Filling the backend
            #Doing this at start is more efficient than after the GUI is launched
            source.get_tasks_list(func=self.refresh_tasklist)
            
        else:
            print "Register a dic without backend key:  BUG"

    def unregister_backend(self, backend):
        print "unregister backend %s not implemented" %backend

    def get_all_backends(self):
        l = []
        for key in self.backends :
            l.append(self.backends[key])
        return l
    
    def refresh_ui(self) :
        #print "refresh %s" %self.tasks
        self.emit("refresh","1")
        
    def refresh_tasklist(self,task_list) :
        for tid in task_list :
            #Just calling new_task then get_task is enough
            self.new_task(tid=tid)
            self.get_task(tid)

#Task source is an transparent interface between the real backend and datastore
#Task source has also more functionnalities
class TaskSource() :
    def __init__(self,backend,parameters,refresh_cllbck) :
        self.backend = backend
        self.dic = parameters
        self.tasks = {}
        self.time = time.time()
        self.refresh = refresh_cllbck
        self.locks = lockslibrary()
        self.tosleep = 0
        self.backend_lock = threading.Lock()
        self.removed = []

##### The Backend interface ###############
##########################################
# All functions here are proxied from the backend itself

    #Then test by putting some articial sleeps in the localfile.py
    def get_tasks_list(self,func) :
        def getall() :
            #print "acquiring lock to getall" 
            self.backend_lock.acquire()
            try :
                #print "acquired lock to getall" 
                tlist = self.backend.get_tasks_list()
                for t in tlist :
                    self.locks.create_lock(t)
            finally :
                self.backend_lock.release()
            #print "releasing lock  to getall" 
            func(tlist)
        t = threading.Thread(target=getall)
        t.start()
        #getall()
        return None
        
    def get_task(self,empty_task,tid) :
        #Our thread
        def getting(empty_task,tid) :
            self.locks.acquire(tid)
            try :
                #if self.locks.ifnotblocked(tid) :
                self.backend.get_task(empty_task,tid)
                empty_task.set_sync_func(self.set_task)
                empty_task.set_loaded()
            finally :
                self.locks.release(tid)
            self.refresh()
        ##########
        if self.tasks.has_key(tid) :
            task = self.tasks[tid]
            if task :
                empty_task = task
        #We will not try to get a removed task
        elif tid not in self.removed :
            #By putting the task in the dic, we say :
            #"This task is already fetched (or at least in fetching process)
            self.tasks[tid] = False
            if THREADING :
                self.locks.create_lock(tid)
                t = threading.Thread(target=getting,args=[empty_task,tid])
                t.start()
                self.tasks[tid] = empty_task
            else :
                getting(empty_task,tid)
                self.tasks[tid] = empty_task
        return empty_task

    def set_task(self,task) :
        #This is foireux : imagine qu'on skipe un save et puis on quitte
#        self.tasks[task.get_id()] = task
#        diffe = time.time() - self.time
#        if diffe > 2 :
#            self.time = time.time()    
#            return self.backend.set_task(task)
#        else :
#            return True
        t = threading.Thread(target=self.__write,args=[task])
        t.start()
        return None
    
    #This function, called in a thread, write to the backend.
    #It acquires a lock to avoid multiple thread writing the same task
    def __write(self,task) :
        tid = task.get_id()
        if tid not in self.removed :
            self.locks.acquire(tid)
            try :
                self.backend.set_task(task)
            finally :
                self.locks.release(tid)
    
    #TODO : This has to be threaded too
    def remove_task(self,tid) :
        self.backend_lock.acquire()
        try :
            if tid not in self.removed :
                self.removed.append(tid)
            if self.locks.acquire(tid) :
                toreturn = self.backend.remove_task(tid)
                self.tasks.pop(tid)
                self.locks.remove_lock(tid)
            else :
                toreturn = False
        finally :
            self.backend_lock.release()
        return toreturn
    
    #TODO: This has to be threaded too
    def new_task_id(self) :
        newid = self.backend.new_task_id()
        if not newid :
            k = 0
            pid = self.dic["pid"]
            newid = "%s@%s" %(k,pid)
            while self.tasks.has_key(str(newid)) :
                k += 1
                newid = "%s@%s" %(k,pid)
        if newid in self.removed :
            self.removed.remove(newid)
        self.locks.create_lock(newid)
        return newid
    
    #TODO : This has to be threaded too
    def quit(self) :
        return self.backend.quit()
        
########## End of Backend interface ###########
###############################################

#Those functions are only for TaskSource
    def get_parameters(self) :
        return self.dic
        

#This is the lock library. Each task has a lock to avoir concurrency 
#on the same task when writing/reading on/from the backend
class lockslibrary :
    def __init__(self) :
        self.locks = {}
        #The lock library itself is protected by a lock to avoid deadlock
        self.glob = threading.Lock()
        
    def create_lock(self,tid) :
        self.glob.acquire()
        try :
            if not self.locks.has_key(tid) :
                self.locks[tid] = threading.Lock()
        finally :
            self.glob.release()
        
    
    #To be removed, a lock should be acquired before !
    #So acquire the lock before calling this function !
    def remove_lock(self,tid) :
        if self.glob.acquire(False) :
            if self.locks.has_key(tid) :
                zelock = self.locks[tid]
                self.locks.pop(tid)
                zelock.release()
            self.glob.release()
        #else :
        #print "This is a very rare bug : we were unable to remove the lock"
        #But this not really a problem because the lock alone does do anything
        
    def ifnotblocked(self,tid) :
        self.glob.acquire()
        try :
            if self.locks.has_key(tid) :
                return self.locks[tid].acquire(False)
            else :
                print "ifnotblock on non-existing lock %s = BUG" %tid
        finally :
            self.glob.release()
        
    def acquire(self,tid) :
        self.glob.acquire()
        try :
            if self.locks.has_key(tid) :
                self.locks[tid].acquire()
                toreturn = True
            else :
                toreturn = False
        finally :
            self.glob.release()
        return toreturn
        
    def release(self,tid) :
        if self.locks.has_key(tid) :
            self.locks[tid].release()
#        else :
#            print "removing non-existing lock = BUG"
        
