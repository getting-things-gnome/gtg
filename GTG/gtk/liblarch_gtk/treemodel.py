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


class TreeModel(gtk.GenericTreeModel):

    def __init__(self, tree):
        gtk.GenericTreeModel.__init__(self)
        self.lock = False
        self.tree = tree
        self.value_list = []
        def get_nodeid(node):
            return node.get_id()
        self.value_list.append([str,get_nodeid])
#        self.iter_store = TaskIterStore(self.tree,self)
#        self.tasks_to_add = []
        self.tree.connect('node-added-inview',self.update_task,'add')
        self.tree.connect('node-deleted-inview',self.remove_task)
        self.tree.connect('node-modified-inview',self.update_task,'update')

### TREE MODEL HELPER FUNCTIONS ###############################################

    def  add_col(self,value):
        self.value_list.append(value)
        index = self.value_list.index(value)
        return index
        
    
    def __build_rowref(self,path):
        '''The rowref is the like the path but with ancestors ID instead
        of position. This ensure that each rowref is unique and that we
        are a real tree, not an acyclic directed graphs'''
        rowref = ()
        while len(path) > 0:
            nid = self.tree.get_node_for_path(path)
            if not nid:
                rowref = None
                raise IndexError('building rowref : No node for path %s'%path)
            else:
                rowref = (nid,) + rowref
            path = path[:-1]
        return rowref
            
    def __get_nid_from_rowref(self,rowref):
        if len(rowref) <= 0:
            raise ValueError('Rowref is empty ! Returning root ?')
        nid = rowref[-1]
        return nid
        
    def __get_node_from_rowref(self,rowref):
        nid = self.__get_nid_from_rowref(rowref)
        node = self.tree.get_node(nid)
        return node
        
    def __get_path_from_rowref(self,rowref):
        path = ()
        size = len(rowref)
        while len(rowref) > 0:
            nid = rowref[0]
            rowref = rowref[1:]
            temp_list = self.tree.get_paths_for_node(nid)
            for p in temp_list:
                if p[:-1] == path :
                    path = p
        #security check
        if len(path) != size:
            raise ValueError('path %s should be of size %s' %(path,size))
        return path
            
        

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
        node = self.__get_node_from_rowref(rowref)
        if len(self.value_list) <= column:
            raise ValueError('The tree model doesnt have enough columns!')
        func = self.value_list[column][1]
        toreturn = func(node)
        return toreturn

    def on_get_iter(self, path):
        #We have to return None if there's no node on that path
        iter = None
        nid = self.tree.get_node_for_path(path)
        if nid:
            rowref = self.__build_rowref(path)
            return rowref
        else:
            return None

    def on_get_path(self, rowref):
        return self.__get_path_from_rowref(rowref)

    def on_iter_next(self, rowref):
        toreturn = None
        if rowref:
            nid = self.__get_nid_from_rowref(rowref)
            if len(rowref) > 1:
                pid = self.__get_nid_from_rowref(rowref[:-1])
                next_id = self.tree.next_node(nid,pid=pid)
            else:
                next_id = self.tree.next_node(nid)
            #We have the next node, we have to build the rowref
            if next_id:
                toreturn = rowref[:-1] + (next_id,)
        return toreturn

    def on_iter_children(self, rowref):
        #By Gtk.treeview definition, we have to return None
        #if rowref doesn't have any children
        nid = self.__get_nid_from_rowref(rowref)
        if self.tree.node_n_children(nid) > 0:
            return self.on_iter_nth_child(rowref,0)
        else:
            return None

    def on_iter_has_child(self, rowref):
        nid = self.__get_nid_from_rowref(rowref)
        return self.tree.node_has_child(nid)

    def on_iter_n_children(self, rowref):
        if rowref:
            nid = self.__get_nid_from_rowref(rowref)
        else:
            nid = None
        return self.tree.node_n_children(nid)

    def on_iter_nth_child(self, rowref, n):
        if rowref:
            nid = self.__get_nid_from_rowref(rowref)
        else:
            #if rowref == None, we use the root
            nid = None
            rowref = ()
        cid = self.tree.node_nth_child(nid,n)
        return rowref + (cid,)

    def on_iter_parent(self, rowref):
        if len(rowref) >= 1:
            return rowref[:-1]
        else:
            return None

    def update_task(self, sender, tid,data=None):
#        print "update task : %s %s" %(data,tid)
        node_paths = self.tree.get_paths_for_node(tid)
        for node_path in node_paths:
            if data == 'add':
                rowref = self.get_iter(node_path)
                self.row_inserted(node_path, rowref)
                #Toggling the parent ( FIXME: this should be done
                #on liblarch level !!!
                if self.tree.node_has_parent(tid):
                    for p in self.tree.node_parents(tid):
                        self.update_task(None,p,data='parent_update')
            else:
                rowref = self.get_iter(node_path)
                self.row_changed(node_path, rowref)
            if self.tree.node_has_child(tid):
                self.row_has_child_toggled(node_path, rowref)
        if len(node_paths) == 0: 
            raise  ValueError("Error :! no path for node %s !" %tid)
                
    def remove_task(self,sender,tid,paths=None):
        if paths:
            for p in paths:
#                print "removing task %s on %s" %(tid,str(p))
                self.row_deleted(p)
        else:
            print "we should get the path in order to delete %s" %tid
            
            
########### The following should be removed onc liblarch-gtk is working ######

#    def add_task(self,sender,tid,data=None):
#        print "add date : %s" %data
#        node_paths = self.tree.get_paths_for_node(tid)
#        for node_path in node_paths:
#            rowref = self.get_iter(node_path)
#            self.row_inserted(node_path, rowref)
#            if self.tree.node_has_child(tid):
#                self.row_has_child_toggled(node_path, rowref)
#        if len(node_paths) == 0: 
#            raise  ValueError("Error :! no path for node %s !" %tid)
#        while len(self.tasks_to_add) > 0:
#            tid = self.tasks_to_add.pop(0)

#            run = True
#            node_paths = self.tree.get_paths_for_node(tid)
#            parents = self.tree.node_parents(tid)
#            for pid in parents:
#                #if we realize that a parent is still to add, we
#                #don't insert the current task but we put it at the end
#                #of the queue
#                if pid in self.tasks_to_add:
#                    self.tasks_to_add.append(tid)
#                    run = False
##                    else:
##                        print "parent %s is displayed %s" %(pid,self.tree.is_displayed(pid))
#            if run:
#                for node_path in node_paths:
#                    node_iter = self.get_iter(node_path)
#                    if self.iter_is_valid(node_iter):
#                        self.row_inserted(node_path, node_iter)
#                        #following is mandatory if 
#                        #we added a child task before his parent.
#                        if self.tree.node_has_child(tid):
#        #                    print "child_toggled 2 : %s" %task.get_title()
#                            self.row_has_child_toggled(node_path,node_iter)
#                for pid in parents:
#                        for par_path in self.tree.get_paths_for_node(pid):
#                            par_iter = self.get_iter(par_path)
#    #                            print "child_toggled 3 : %s" %p.get_title()
#                            if self.iter_is_valid(par_iter):
#                                self.row_has_child_toggled(par_path, par_iter)
#        self.lock = False

#    def remove_task(self, sender, tid):
#        #a task has been removed from the view. Therefore,
#        # the widgets that represent it should be removed
#        Log.debug("tasktree remove_task %s" %tid)
#        print "Move task not yet implemented in liblarch_gtk"
#        removed = False
#        node_paths = self.tree.get_paths_for_node(tid)
#        for node_path in node_paths:
#            Log.debug("* tasktree REMOVE %s - %s " %(tid,node_path))
#            self.iter_store.remove(tid,node_path)
##            print "     remove row %s" %str(node_path)
#            self.row_deleted(node_path)
#            removed = True
#        return removed
                    
#    def move_task(self, parent_tid, child_tid):
#        """Moves the task identified by child_tid under
#           parent_tid, removing all the precedent parents.
#           Child becomes a root task if parent_tid is None"""
#        #The genealogic search has been moved to liblarch and should be
#        #removed from here
#        print "Move task not yet implemented in liblarch_gtk (and it shouldnot)"
#        def genealogic_search(tid):
#            if tid not in genealogy:
#                genealogy.append(tid)
#                task = self.req.get_task(tid)
#                for par in task.get_parents():
#                    genealogic_search(par)
#        child_task = self.req.get_task(child_tid)
#        current_parents = child_task.get_parents()
#        genealogy = []
#        if parent_tid:
#            parent_task = self.req.get_task(parent_tid)
#            parents_parents = parent_task.get_parents()
#            for p in parents_parents:
#                genealogic_search(p)

#        #Avoid the typical time-traveller problem being-the-father-of-yourself
#        #or the grand-father. We need some genealogic research !
#        if child_tid in genealogy or parent_tid == child_tid:
#            return
#        #if we move a task, this task should be saved, even if new
#        child_task.set_to_keep()
#        # Remove old parents 
#        for pid in current_parents:
#            #We first remove the node from the view (to have the path)
#            node_paths = self.tree.get_paths_for_node(child_task)
#            for node_path in node_paths:
#                self.row_deleted(node_path)
#            #then, we remove the parent
#            child_task.remove_parent(pid)
#        #Set new parent
#        if parent_tid:
#            child_task.add_parent(parent_tid)
#        #If we don't have a new parent, add that task to the root
#        else:
#            node_paths = self.tree.get_paths_for_node(child_task)
#            for node_path in node_paths:
#                node_iter = self.get_iter(node_path)
#                if self.iter_is_valid(node_iter):
#                    self.row_inserted(node_path, node_iter)
#        #if we had a filter, we have to refilter after the drag-n-drop
#        #This is not optimal and could be improved
#        self.tree.refilter()
