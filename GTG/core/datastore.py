# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
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
from GTG.core.tree import Tree


#Only the datastore should access to the backend
DEFAULT_BACKEND = "1"
#If you want to debug a backend, it can be useful to disable the threads
#Currently, it's python threads (and not idle_add, which is not useful)
THREADING = True


class DataStore:

    def __init__(self):
        self.backends = {}
        self.open_tasks = Tree()
        self.closed_tasks = Tree()
        self.requester = requester.Requester(self)
        self.tagstore = tagstore.TagStore(self.requester)

    def all_tasks(self):
        return self.open_tasks.get_all_nodes()
#        all_tasks = []
#        #We also add tasks that are still not in a backend (because of threads)
#        tlist = self.open_tasks.get_all_nodes()
#        tlist += self.closed_tasks.get_all_nodes()
#        for task in tlist:
#            if task.is_loaded():
#                all_tasks.append(task.get_id())
#            else:
#                if task.get_status() == "Active":
##                    print "task %s is not loaded" %task.get_id()
##                    print task.get_title()
#                    self.get_task(task.get_id())
#        #print "%s tasks but we return %s" %(len(tlist),len(all_tasks))
#        return all_tasks

    def has_task(self, tid):
        return self.open_tasks.has_node(tid) or self.closed_tasks.has_node(tid)

    def get_task(self, tid):
        if self.has_task(tid):
            task = self.__internal_get_task(tid)
        else:
            task = None
        return task
#            if not task.is_loaded():
#                uid, pid = tid.split('@') #pylint: disable-msg=W0612
#                back = self.backends[pid]
#                task = back.get_task(task, tid)
#        else:
##            empty_task = self.new_task(tid, newtask=False)
#            empty_task = Task(tid, self.requester, newtask=False)
#            uid, pid = tid.split('@') #pylint: disable-msg=W0612
#            back = self.backends[pid]
#            if self.open_tasks.add_node(empty_task):
#                task = back.get_task(empty_task, tid)
#            else:
#                task = self.__internal_get_task(tid)
#        return task
#        
#        else:
#            empty_task = self.new_task(tid, newtask=False)
#        if tid and not empty_task.is_loaded():
#            uid, pid = tid.split('@') #pylint: disable-msg=W0612
#            back = self.backends[pid]
#            task = back.get_task(empty_task, tid)
#        else:
#            task = empty_task
#        return task
        
    def __internal_get_task(self, tid):
        toreturn = self.open_tasks.get_node(tid)
        if toreturn == None:
            self.closed_tasks.get_node(tid)
        #else:
            #print "error : this task doesn't exist in either tree"
            #pass
        #we return None if the task doesn't exist
        return toreturn

    def delete_task(self, tid):
        if tid and self.has_task(tid):
            self.__internal_get_task(tid).delete()
            uid, pid = tid.split('@') #pylint: disable-msg=W0612
            back = self.backends[pid]
            #Check that the task still exist. It might have been deleted
            #by its parent a few line earlier :
            if self.has_task(tid):
                self.open_tasks.remove_node(tid)
                self.closed_tasks.remove_node(tid)
            back.remove_task(tid)
            
            
    def new_task(self,pid=None):
        if not pid:
            pid = DEFAULT_BACKEND
        newtid = self.backends[pid].new_task_id()
        while self.has_task(newtid):
            print "error : tid already exists"
            newtid = self.backends[pid].new_task_id()
        task = Task(newtid, self.requester,newtask=True)
        task.set_sync_func(self.backends[pid].set_task,callsync=False)
        self.open_tasks.add_node(task)
        return task

#    #Create a new task and return it.
#    #newtask should be True if you create a task
#    #it should be False if you are importing an existing Task
#    def new_task(self, tid=None, pid=None, newtask=False):
#        #If we don't have anything, we use the default PID
#        if not pid:
#            pid = DEFAULT_BACKEND
#        #If tid, we force that tid and create a real new task
#        if tid and not self.has_task(tid):
#            print "new task for tid %s " %tid
#            task = Task(tid, self.requester, newtask=newtask)
#            uid, pid = tid.split('@') #pylint: disable-msg=W0612
#            #By default, a new task is active. We then put it in the Active tree
#            if self.open_tasks.add_node(task):
#                toreturn = task
#            else:
#                toreturn = self.get_task(tid)
#        #Else we create a new task in the given pid
#        elif not tid and pid and pid in self.backends:
#            newtid = self.backends[pid].new_task_id()
#            print "new task for newtid %s " %newtid
#            task = Task(newtid, self.requester, newtask=newtask)
#            self.open_tasks.add_node(task)
#            task = self.backends[pid].get_task(task, newtid)
#            toreturn = task
#            tid = newtid
#        elif tid:
#            print "error : task %s already exists !" %tid
#            toreturn = self.__internal_get_task(tid)
#        else:
#            print "not possible to build the task = bug"
#            toreturn = None
#        return toreturn

    def get_tagstore(self):
        return self.tagstore

    def get_requester(self):
        return self.requester
        
    def get_tasks_tree(self):
        return self.open_tasks
        
    def push_task(self,task):
        tid = task.get_id()
        if self.has_task(tid):
            print "pushing an existing task. We should care about modifications"
        else:
            uid, pid = tid.split('@')
            task.set_sync_func(self.backends[pid].set_task,callsync=False)
            self.open_tasks.add_node(task)
            task.set_loaded()
    
    def task_factory(self,tid):
        task = None
        if self.has_task(tid):
            print "error : tid already exists"
        else:
            task = Task(tid, self.requester, newtask=False)
        return task
            

    def register_backend(self, dic):
        if "backend" in dic:
            pid = dic["pid"]
            backend = dic["backend"]
            source = TaskSource(backend, dic)
            self.backends[pid] = source
            #Filling the backend
            #Doing this at start is more efficient than
            #after the GUI is launched
            backend.start_get_tasks(self.push_task,self.task_factory)
        else:
            print "Register a dic without backend key:  BUG"

    def unregister_backend(self, backend):
        print "unregister backend %s not implemented" %backend

    def get_all_backends(self):
        l = []
        for key in self.backends:
            l.append(self.backends[key])
        return l

#    def refresh_tasklist(self, task_list):
#        for tid in task_list:
#            #Just calling new_task then get_task is enough
##            self.new_task(tid=tid)
#            self.get_task(tid)

#Task source is an transparent interface between the real backend and datastore
#Task source has also more functionnalities

class TaskSource():

    def __init__(self, backend, parameters):
        self.backend = backend
        self.dic = parameters
        self.to_set = []
        self.lock = threading.Lock()
        
    ### TaskSource/bakcend mapping
    def start_get_tasks(self,push_task,task_factory):
        self.backend.start_get_tasks(push_task,task_factory)
    
    def set_task(self, task):
        if task not in self.to_set:
            self.to_set.append(task)
        if self.lock.acquire(False):
            try:
                print "set task for task %s" %task.get_id()
                self.backend.set_task(task)
            finally:
                self.to_set.remove(task)
                self.lock.release()
                if len(self.to_set) > 0:
                    self.set_task(self.to_set[0])
        else:
            print "cannot acquire lock"
    
    def remove_task(self, tid):
        return self.backend.remove_task(tid)
    
    def new_task_id(self):
        return self.backend.new_task_id()
    
    def quit(self):
        self.backend.quit()
        
    #Those functions are only for TaskSource
    def get_parameters(self):
        return self.dic
        
#        self.tasks = {}
#        self.time = time.time()
#        self.locks = lockslibrary()
#        self.tosleep = 0
#        self.backend_lock = threading.Lock()
#        self.removed = []
#        self.to_write = []
#        self.writing_lock = threading.Lock()
#        self.to_get = []
#        self.getting_lock = threading.Lock()

###### The Backend interface ###############
###########################################
## All functions here are proxied from the backend itself

#    #Then test by putting some articial sleeps in the localfile.py
#    def get_tasks_list(self, func):

#        def getall():
#            #print "acquiring lock to getall"
#            self.backend_lock.acquire()
#            try:
#                #print "acquired lock to getall"
#                tlist = self.backend.get_tasks_list()
#                for t in tlist:
#                    self.locks.create_lock(t)
#            finally:
#                self.backend_lock.release()
#            #print "releasing lock  to getall"
#            func(tlist)
#        if THREADING:
#            t = threading.Thread(target=getall)
#            t.start()
##            gobject.idle_add(getall)
#        else:
#            getall()
#        return None

#    def get_task(self, empty_task, tid):
#        #Our thread
#        def getting():
#            #self.locks.acquire(tid)
#            try:
#                while len(self.to_get) > 0:
#                    tid, empty_task = self.to_get.pop()
#                    #if self.locks.ifnotblocked(tid):
#                    self.backend.get_task(empty_task, tid)
#                    #calling sync in a thread might cause a segfault
#                    #thus callsync to false
#                    empty_task.set_sync_func(self.set_task, callsync=False)
#                    #set_loaded is a function that emits a signal.
#                    #Emiting a signal in a thread is likely to segfault
#                    #by wrapping it in idle_add, we ensure that gobject
#                    #mainloop handles the signal and not the tread itself.
#                    #it's not a problem to not know when it is executed
#                    #since it's the last instruction of the tread
#                    gobject.idle_add(empty_task.set_loaded)
#            finally:
#                #self.locks.release(tid)
#                self.getting_lock.release()
#        ##########
#        task = None
#        if tid in self.tasks:
#            task = self.tasks[tid]
#            if task:
##                print "already existing"
#                empty_task = task
#            #this might not be needed
#                #gobject.idle_add(empty_task.set_loaded)
#        #We will not try to get a removed task
#        elif tid not in self.removed:
#            #By putting the task in the dic, we say:
#            #"This task is already fetched (or at least in fetching process)
#            self.tasks[tid] = False
#            self.to_get.append([tid, empty_task])
#            if self.getting_lock.acquire(False):
## Disabling this to circumvent Bug #411420
##                if THREADING:
##                    self.locks.create_lock(tid)
##                    gobject.idle_add(getting,empty_task,tid)
##                    t = threading.Thread(target=getting)
##                    t.start()
##                else:
##                    self.locks.create_lock(tid)
##                    #getting(empty_task,tid)
##                    getting()
#                getting()
#            self.tasks[tid] = empty_task
#        return empty_task

#    #only one thread is used to write the task
#    #if this thread is not started, we start it.
#    def set_task(self, task):
#        self.to_write.append(task)
#        if self.writing_lock.acquire(False):
#            if THREADING:
##               gobject.idle_add(self.__write,task)
#                t = threading.Thread(target=self.__write)
#                t.start()
#            else:
#                self.__write()
#        return None

#    #This function, called in a thread, write to the backend.
#    #It acquires a lock to avoid multiple thread writing at the same time
#    #the lock is writing_lock
#    def __write(self):
#        try:
#            while len(self.to_write) > 0:
#                task = self.to_write.pop()
#                tid = task.get_id()
#                if tid not in self.removed:
##                    self.locks.acquire(tid)
##                    try:
##                    print self.locks.acquire(tid)
#                    self.backend.set_task(task)
##                    finally:
##                    self.locks.release(tid)
#        finally:
#            self.writing_lock.release()

#    #TODO : This has to be threaded too
#    def remove_task(self, tid):
#        self.backend_lock.acquire()
#        try:
#            if tid not in self.removed:
#                self.removed.append(tid)
#            if self.locks.acquire(tid):
#                toreturn = self.backend.remove_task(tid)
#                self.tasks.pop(tid)
#                self.locks.remove_lock(tid)
#            else:
#                toreturn = False
#        finally:
#            self.backend_lock.release()
#        return toreturn

#    #TODO: This has to be threaded too
#    def new_task_id(self):
#        newid = self.backend.new_task_id()
#        if not newid:
#            k = 0
#            pid = self.dic["pid"]
#            newid = "%s@%s" %(k, pid)
#            while str(newid) in self.tasks:
#                k += 1
#                newid = "%s@%s" %(k, pid)
#        if newid in self.removed:
#            self.removed.remove(newid)
#        self.locks.create_lock(newid)
#        return newid

#    #TODO : This has to be threaded too
#    def quit(self):
#        return self.backend.quit()

########### End of Backend interface ###########
################################################

##Those functions are only for TaskSource
#    def get_parameters(self):
#        return self.dic

##This is the lock library. Each task has a lock to avoir concurrency
##on the same task when writing/reading on/from the backend

#class lockslibrary:

#    def __init__(self):
#        self.locks = {}
#        #The lock library itself is protected by a lock to avoid deadlock
#        self.glob = threading.Lock()

#    def create_lock(self, tid):
#        self.glob.acquire()
#        try:
#            if tid not in self.locks:
#                self.locks[tid] = threading.Lock()
#        finally:
#            self.glob.release()

#    #To be removed, a lock should be acquired before !
#    #So acquire the lock before calling this function !
#    def remove_lock(self, tid):
#        if self.glob.acquire(False):
#            if tid in self.locks:
#                zelock = self.locks[tid]
#                self.locks.pop(tid)
#                zelock.release()
#            self.glob.release()
#        #else:
#        #print "This is a very rare bug : we were unable to remove the lock"
#        #But this not really a problem because the lock alone does do anything
#    def ifnotblocked(self, tid):
#        self.glob.acquire()
#        try:
#            if tid in self.locks:
#                return self.locks[tid].acquire(False)
#            else:
#                print "ifnotblock on non-existing lock %s = BUG" %tid
#        finally:
#            self.glob.release()

#    def acquire(self, tid):
#        self.glob.acquire()
#        try:
#            if tid in self.locks:
#                self.locks[tid].acquire()
#                toreturn = True
#            else:
#                toreturn = False
#        finally:
#            self.glob.release()
#        return toreturn

#    def release(self, tid):
#        if tid in self.locks:
#            self.locks[tid].release()
##        else:
##            print "removing non-existing lock = BUG"
