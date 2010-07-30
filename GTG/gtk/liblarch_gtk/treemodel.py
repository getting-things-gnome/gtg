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
import xml.sax.saxutils as saxutils

import gtk
import gobject
import pango

from GTG                              import _
from GTG.tools.logger                 import Log


COL_TID       = 0
COL_OBJ       = 1
COL_TITLE     = 2
COL_DDATE     = 3
COL_CDATE     = 4
COL_CDATE_STR = 5
COL_DLEFT     = 6
COL_TAGS      = 7
COL_LABEL     = 9
COL_SDATE     = 10
COL_DUE       = 11


#A task can have multiple parent (thus multiple paths)
#We thus define an iter which is a tuple [node,path], defining one
#and only one position in the tree
class TaskIter():
    def __init__(self,tree,node,path):
        self.__node = node
        self.__path = path
        self.__tree = tree
        
    def get_node(self):
        return self.__node
    
    def get_path(self):
        return self.__path

    def is_valid(self):
        return self.__path in self.__tree.get_paths_for_node(self.__node)

    def __str__(self):
        return "iter %s  for path %s" %(self.__node,str(self.__path))

class TaskIterStore():
    def __init__(self,tree,model):
        self.__tree = tree
        self.__model = model
        self.__store = {}

    def __key(self,nid,path):
        return str(path)

    def size(self):
        return len(self.__store)

    def get(self,nid,path):
        key = self.__key(nid,path)
        toreturn = None
#        print "get iter for node %s (toadd: %s)" %(node.get_id(),self.__model.tasks_to_add)
        if nid in self.__model.tasks_to_add:
            #This is a crude hack. If the task is in tasks_to_add, it means
            #that it was removed and should be added.
            #the fact that someone is asking for its iter means that it will
            #be added automatically anyway.
            #in order to avoid duplicate, we will only remove it from the list
            #of tasks to add
            self.__model.tasks_to_add.remove(nid)
        if nid and self.__store.has_key(key):
            stored_iter = self.__store[key]
            stored_nid = stored_iter.get_node()
            if stored_nid == nid:
                toreturn = stored_iter
            elif stored_nid:
                #We place a node on the position of a previous node.
                #we should then remove that previous node
                self.remove(stored_nid,path,all=False)
                self.__model.row_deleted(path)
        if not toreturn:
            toreturn = TaskIter(self.__tree,nid,path)
        self.__store[key] = toreturn
        return toreturn

    def remove(self,nid,path,all=True):
        if all:
            self.__store = {}
        else:
            key = self.__key(nid,path)
            if self.__store.has_key(key):
                stored_node = self.__store[key]
                if stored_node.get_node() == nid:
                    self.__store.pop(key)
                    return True
                else:
                    print "Trying to remove iter %s from path %s (thinking it was %s)"\
                            %(stored_node.get_node(),str(path),nid)
                    return False
            else:
                print "Removing inexistant path %s for node %s" %(str(path),nid)
                return False




class TreeModel(gtk.GenericTreeModel):

    def __init__(self, tree):
        gtk.GenericTreeModel.__init__(self)
        self.lock = False
        self.tree = tree
        self.value_list = []
        def get_nodeid(node):
            return node.get_id()
        self.value_list.append([str,get_nodeid])
        self.iter_store = TaskIterStore(self.tree,self)
        self.tasks_to_add = []
        self.tree.connect('node-added-inview',self.to_add_task)
        self.tree.connect('node-deleted-inview',self.remove_task)
        self.tree.connect('node-modified-inview',self.update_task)

### TREE MODEL HELPER FUNCTIONS ###############################################

#    def _count_active_subtasks_rec(self, task):
#        count = 0
#        if task.has_child():
#            for tid in task.get_children():
#                task = self.req.get_task(tid)
#                if task and task.get_status() == Task.STA_ACTIVE:
#                    count = count + 1 + self._count_active_subtasks_rec(task)
#        return count

    def  add_col(self,value):
        index = len(value)
        self.value_list.append(value)
        return index

### TREEMODEL INTERFACE ######################################################
#
    def on_get_flags(self):
#        print "on_get_flags"
        return gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
        return len(self.value_list)

    def on_get_column_type(self, n):
        if len(self.value_list) <= n:
            raise ValueError('The tree model doesnt have enough columns!')
        return self.value_list[n][0]
        
    def on_get_value(self, rowref, column):
        if not rowref:
            raise ValueError('Asking the value of an empty rowref')
        nid = rowref.get_node()
        node = self.tree.get_node(nid)
        if len(self.value_list) <= column:
            raise ValueError('The tree model doesnt have enough columns!')
        func = self.value_list[column][1]
        print "on_get_value %s %s" %(rowref,column)
        return func(node)
            


    def on_get_iter(self, path):
        #We have to return None if there's no node on that path
        iter = None
        nid = self.tree.get_node_for_path(path)
        if nid:
            rowref = self.iter_store.get(nid,path)
            if  nid in self.tasks_to_add:
                #print "WE WILL NOT ADD %s" %node.get_id()
                self.tasks_to_add.remove(nid)
            return rowref
        else:
            return None

    def on_get_path(self, rowref):
#        print "on_get_path"
        if rowref and rowref.is_valid():
            path = rowref.get_path()
            return path
        else:
            return None

    def on_iter_next(self, rowref):
#        print "on_iter_next"
        toreturn = None
        if rowref and rowref.is_valid():
            path = rowref.get_path()
            ppath = path[:-1]
            if ppath == ():
                ppath = None
            pid = self.tree.get_node_for_path(ppath)
            nid = rowref.get_node()
            next = self.tree.next_node(nid,pid=pid)
            #We have the next node. To know the path to use
            # we will find, in its paths, the one with 
            #the same root as the current node
            npaths = self.tree.get_paths_for_node(next)
            for n in npaths:
                if path[:-1] == n[:-1]:
                    toreturn = self.iter_store.get(next,n)
            if len(npaths) > 0 and not toreturn:
                print "!!!!!!!! We didn't find iter_next for %s but we have %s" %(rowref,npaths)
        return toreturn

    def on_iter_children(self, rowref):
        return self.on_iter_nth_child(rowref,0)
            

    def on_iter_has_child(self, rowref):
        if rowref and rowref.is_valid():
            nid = rowref.get_node()
            toreturn = self.tree.node_has_child(nid)
            return toreturn
        else:
            return False

    def on_iter_n_children(self, rowref):
        if rowref:
            node = rowref.get_node()
            toreturn = self.tree.node_n_children(node)
        else:
            toreturn = self.tree.node_n_children(None)
        return toreturn

    def on_iter_nth_child(self, rowref, n):
        toreturn = None
        if rowref and rowref.is_valid():
            nid = rowref.get_node()
            path = rowref.get_path()
            child = self.tree.node_nth_child(nid,n)
            if child:
                cpaths = self.tree.get_paths_for_node(child)
                for c in cpaths:
                    if c[:-1] == path:
                        toreturn = self.iter_store.get(child,c)
                if not toreturn:
                    print "PROBLEM: child %s have the path %s but parent %s has %s"\
                            %(child,cpaths,nid,path)
        return toreturn

    def on_iter_parent(self, rowref):
#        print "on_iter_parent"
        if rowref and rowref.is_valid():
            path = rowref.get_path()
            par_node = self.tree.get_node_for_path(path[:-1])
            return self.iter_store.get(par_node,path[:-1])
        else:
            return None

    def update_task(self, sender, tid):
#        # get the node and signal it's changed
#        print "tasktree update_task %s" %tid
        if self.tree.is_displayed(tid):
            node_paths = self.tree.get_paths_for_node(tid)
            for node_path in node_paths:
                node_iter = self.get_iter(node_path)
                if self.iter_is_valid(node_iter):
                    self.row_changed(node_path, node_iter)
#                    print "child_toggled 1 : %s" %my_node.get_title()
                    self.row_has_child_toggled(node_path, node_iter)
            if len(node_paths) == 0: 
                raise  ValueError("Error :! no path for node %s !" %tid)

    def to_add_task(self,sender,tid):
#        print "%s is to_add" %(tid)
        self.tasks_to_add.append(tid)
        if not self.lock and len(self.tasks_to_add) > 0:
            self.lock = True
            self.add_tasks()

    def add_tasks(self):
        #self.lock = True
        while len(self.tasks_to_add) > 0:
            tid = self.tasks_to_add.pop(0)

            run = True
            node_paths = self.tree.get_paths_for_node(tid)
            parents = self.tree.node_parents(tid)
            for pid in parents:
                #if we realize that a parent is still to add, we
                #don't insert the current task but we put it at the end
                #of the queue
                if pid in self.tasks_to_add:
                    self.tasks_to_add.append(tid)
                    run = False
#                    else:
#                        print "parent %s is displayed %s" %(pid,self.tree.is_displayed(pid))
            if run:
                for node_path in node_paths:
                    node_iter = self.get_iter(node_path)
                    if self.iter_is_valid(node_iter):
                        self.row_inserted(node_path, node_iter)
                        #following is mandatory if 
                        #we added a child task before his parent.
                        if self.tree.node_has_child(tid):
        #                    print "child_toggled 2 : %s" %task.get_title()
                            self.row_has_child_toggled(node_path,node_iter)
                for pid in parents:
                        for par_path in self.tree.get_paths_for_node(pid):
                            par_iter = self.get_iter(par_path)
    #                            print "child_toggled 3 : %s" %p.get_title()
                            if self.iter_is_valid(par_iter):
                                self.row_has_child_toggled(par_path, par_iter)
        self.lock = False

    def remove_task(self, sender, tid):
        #a task has been removed from the view. Therefore,
        # the widgets that represent it should be removed
        Log.debug("tasktree remove_task %s" %tid)
        removed = False
        node_paths = self.tree.get_paths_for_node(tid)
        for node_path in node_paths:
            Log.debug("* tasktree REMOVE %s - %s " %(tid,node_path))
            self.iter_store.remove(tid,node_path)
#            print "     remove row %s" %str(node_path)
            self.row_deleted(node_path)
            removed = True
        return removed
                    
    def move_task(self, parent_tid, child_tid):
        """Moves the task identified by child_tid under
           parent_tid, removing all the precedent parents.
           Child becomes a root task if parent_tid is None"""
        #The genealogic search has been moved to liblarch and should be
        #removed from here
        def genealogic_search(tid):
            if tid not in genealogy:
                genealogy.append(tid)
                task = self.req.get_task(tid)
                for par in task.get_parents():
                    genealogic_search(par)
        child_task = self.req.get_task(child_tid)
        current_parents = child_task.get_parents()
        genealogy = []
        if parent_tid:
            parent_task = self.req.get_task(parent_tid)
            parents_parents = parent_task.get_parents()
            for p in parents_parents:
                genealogic_search(p)

        #Avoid the typical time-traveller problem being-the-father-of-yourself
        #or the grand-father. We need some genealogic research !
        if child_tid in genealogy or parent_tid == child_tid:
            return
        #if we move a task, this task should be saved, even if new
        child_task.set_to_keep()
        # Remove old parents 
        for pid in current_parents:
            #We first remove the node from the view (to have the path)
            node_paths = self.tree.get_paths_for_node(child_task)
            for node_path in node_paths:
                self.row_deleted(node_path)
            #then, we remove the parent
            child_task.remove_parent(pid)
        #Set new parent
        if parent_tid:
            child_task.add_parent(parent_tid)
        #If we don't have a new parent, add that task to the root
        else:
            node_paths = self.tree.get_paths_for_node(child_task)
            for node_path in node_paths:
                node_iter = self.get_iter(node_path)
                if self.iter_is_valid(node_iter):
                    self.row_inserted(node_path, node_iter)
        #if we had a filter, we have to refilter after the drag-n-drop
        #This is not optimal and could be improved
        self.tree.refilter()
