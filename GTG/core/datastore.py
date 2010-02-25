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
        return self.open_tasks.get_all_keys()

    def has_task(self, tid):
        return self.open_tasks.has_node(tid) or self.closed_tasks.has_node(tid)

    def get_task(self, tid):
        uid, pid = tid.split('@')
        if self.has_task(tid):
            task = self.__internal_get_task(tid)
        else:
            #print "no task %s" %tid
            task = None
        return task
        
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
        self.open_tasks.add_node(task)
        task.set_sync_func(self.backends[pid].set_task,callsync=False)
        return task

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
            self.open_tasks.add_node(task)
            task.set_loaded()
            task.set_sync_func(self.backends[pid].set_task,callsync=False)
    
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
            source.start_get_tasks(self.push_task,self.task_factory)
        else:
            print "Register a dic without backend key:  BUG"

    def unregister_backend(self, backend):
        print "unregister backend %s not implemented" %backend

    def get_all_backends(self):
        l = []
        for key in self.backends:
            l.append(self.backends[key])
        return l

#Task source is an transparent interface between the real backend and datastore
#Task source has also more functionnalities

class TaskSource():

    def __init__(self, backend, parameters):
        self.backend = backend
        self.dic = parameters
        self.to_set = []
        self.to_remove = []
        self.lock = threading.Lock()
        self.count_set = 0
        
    ### TaskSource/bakcend mapping
    def start_get_tasks(self,push_task,task_factory):
        func = self.backend.start_get_tasks
        t = threading.Thread(target=func,args=(push_task,task_factory))
        t.start()
    
    def set_task(self, task):
        tid = task.get_id()
        self.count_set += 1
        print "setting task %s (%s sets)" %(tid,self.count_set)
        if task not in self.to_set and tid not in self.to_remove:
            self.to_set.append(task)
        if self.lock.acquire(False):
            func = self.setting_thread
            t = threading.Thread(target=func)
            t.start()
#        else:
#            print "cannot acquire lock : not a problem, just for debug purpose"
            
    def setting_thread(self):
        try:
            while len(self.to_set) > 0:
                t = self.to_set.pop(0)
                tid = t.get_id()
                if tid not in self.to_remove:
#                    self.count_set += 1
#                    print "setting task %s (%s sets)" %(tid,self.count_set)
                    self.backend.set_task(t)
            while len(self.to_remove) > 0:
                tid = self.to_remove.pop(0)
                self.backend.remove_task(tid)
        finally:
            self.lock.release()
    
    def remove_task(self, tid):
        if tid not in self.to_remove:
            self.to_remove.append(tid)
        if self.lock.acquire(False):
            func = self.setting_thread
            t = threading.Thread(target=func)
            t.start()
    
    def new_task_id(self):
        return self.backend.new_task_id()
    
    def quit(self):
        self.backend.quit()
        
    #Those functions are only for TaskSource
    def get_parameters(self):
        return self.dic
