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
DEBUG_MODEL = False
TM_IDLE_ADD = True
THREAD_PROTECTION = False

#I believe that the correct setup should be : 
# signals = False
# idle_add = True (to only have the call in the gtk.mainloop)
#thread_protection = True

import xml.sax.saxutils as saxutils

import gtk
import gobject
import pango
if DEBUG_MODEL or THREAD_PROTECTION:
    import threading

from GTG                              import _
from GTG.tools.logger                 import Log

PRIORITY = gobject.PRIORITY_HIGH

def threadsafe(fun):
    def newf(*args,**kw):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != args[0].thread:
                raise Exception('! could not acces %s from thread %s' \
                                                        %(fun.__name__,t))
        return fun(*args,**kw)
    return newf

class TreeModel(gtk.GenericTreeModel):

    def __init__(self, tree):
        gtk.GenericTreeModel.__init__(self)
        self.lock = False
        self.tree = tree
        self.state_id = 0
        self.value_list = []
        def get_nodeid(node):
            return node.get_id()
        self.value_list.append([str,get_nodeid])
        if THREAD_PROTECTION:
            self.thread = threading.current_thread()

    @threadsafe
    def connect_model(self):
        self.tree.register_cllbck('node-added-inview',self.add_task)
        self.tree.register_cllbck('node-deleted-inview',self.remove_task)
        self.tree.register_cllbck('node-modified-inview',self.update_task)
        self.tree.register_cllbck('node-children-reordered',self.reorder)
        self.state_id = self.tree.get_state_id()
        
        
#### function called by other threads. Those are the only not threadsafe-
#### decorated methods

    def add_task(self,tid,path,state_id):
#        if DEBUG_MODEL:
#            print "receiving add_task %s to state %s (current:%s)" \
#                                            %(tid,state_id,self.state_id)
        gobject.idle_add(self.__update_task,None,tid,path,state_id,'add',\
                                            priority=PRIORITY)

    def update_task(self, tid,path,state_id,data=None):
        gobject.idle_add(self.__update_task,None,tid,path,state_id,\
                                    data,priority=PRIORITY)
                                    
    def remove_task(self,tid,path,state_id):
        gobject.idle_add(self.__remove_task,None,tid,path,state_id,\
                                            priority=PRIORITY)
                                            
    def reorder(self,nid,path,neworder,state_id):
        gobject.idle_add(self.__reorder,None,nid,path,neworder,state_id,\
                                            priority=PRIORITY)

### TREE MODEL HELPER FUNCTIONS ###############################################

    @threadsafe
    def  add_col(self,value):
        self.value_list.append(value)
        index = self.value_list.index(value)
        return index

    @threadsafe
    def __build_rowref(self,path):
        '''The rowref is the like the path but with ancestors ID instead
        of position. This ensure that each rowref is unique and that we
        are a real tree, not an acyclic directed graphs'''
        rowref = ()
        while len(path) > 0:
            nid = self.tree.get_node_for_path(path,state_id=self.state_id)
            if not nid:
                rowref = None
                raise IndexError('building rowref : No node for path %s'%path)
            else:
                rowref = (nid,) + rowref
            path = path[:-1]
        return rowref

    @threadsafe
    def __get_nid_from_rowref(self,rowref):
        if len(rowref) <= 0:
            raise ValueError('Rowref is empty ! Returning root ?')
        nid = rowref[-1]
        return nid

    @threadsafe
    def __get_node_from_rowref(self,rowref):
        nid = self.__get_nid_from_rowref(rowref)
        node = self.tree.get_node(nid)
        return node

    @threadsafe
    def __get_path_from_rowref(self,rowref):
        path = ()
        size = len(rowref)
        while len(rowref) > 0:
            nid = rowref[0]
            rowref = rowref[1:]
            temp_list = self.tree.get_paths_for_node(nid,state_id=self.state_id)
            for p in temp_list:
                if p[:-1] == path :
                    path = p
        #security check
        if len(path) != size:
            raise ValueError('path %s should be of size %s' %(path,size))
        return path



### TREEMODEL INTERFACE ######################################################
#
    @threadsafe
    def on_get_flags(self):
#        print "on_get_flags"
        return gtk.TREE_MODEL_ITERS_PERSIST

    @threadsafe
    def on_get_n_columns(self):
        return len(self.value_list)

    @threadsafe
    def on_get_column_type(self, n):
        if len(self.value_list) <= n:
            raise ValueError('The tree model doesnt have enough columns!')
        return self.value_list[n][0]

    @threadsafe
    def on_get_value(self, rowref, column):
        if not rowref:
            raise ValueError('Asking the value of an empty rowref')
        node = self.__get_node_from_rowref(rowref)
        if len(self.value_list) <= column:
            raise ValueError('The tree model doesnt have enough columns!')
        func = self.value_list[column][1]
        toreturn = func(node)
#        if DEBUG_MODEL:
#            print "get_value  for %s %s : %s" %(str(rowref),column,toreturn)
        return toreturn

    @threadsafe
    def on_get_iter(self, path):
        #We have to return None if there's no node on that path
        nid = self.tree.get_node_for_path(path,state_id=self.state_id)
        if nid:
            rowref = self.__build_rowref(path)
            toreturn = rowref
        else:
            toreturn = None
        if DEBUG_MODEL:
            print "on_get_iter for path %s (state %s) -> %s : %s" %(path,self.state_id,nid,toreturn)
        return toreturn

    @threadsafe
    def on_get_path(self, rowref):
        toreturn = self.__get_path_from_rowref(rowref)
        if DEBUG_MODEL:
            print "on_get_path for %s : %s" %(str(rowref),toreturn)
        return toreturn

    @threadsafe
    def on_iter_next(self, rowref):
        toreturn = None
        if rowref:
            nid = self.__get_nid_from_rowref(rowref)
            if len(rowref) > 1:
                pid = self.__get_nid_from_rowref(rowref[:-1])
                next_id = self.tree.next_node(nid,pid=pid,state_id=self.state_id)
            else:
                next_id = self.tree.next_node(nid,state_id=self.state_id)
            #We have the next node, we have to build the rowref
            if next_id:
                toreturn = rowref[:-1] + (next_id,)
        if DEBUG_MODEL:
            print "iter_next for %s : %s" %(str(rowref),toreturn)
#        if not toreturn:
#            print "###########  iter_next returns None for rowref %s" %str(rowref)
#            self.tree.print_tree()
#        else:
#            print "******** %s is next node of %s ********" %(toreturn,str(rowref))
        return toreturn

    @threadsafe
    def on_iter_children(self, rowref):
        #By Gtk.treeview definition, we have to return None
        #if rowref doesn't have any children
        nid = self.__get_nid_from_rowref(rowref)
        if self.tree.node_n_children(nid,state_id=self.state_id) > 0:
            toreturn = self.on_iter_nth_child(rowref,0)
        else:
            toreturn = None
        if DEBUG_MODEL:
            print "on_iter_children %s (state %s): %s" %(str(rowref),self.state_id,toreturn)
            print self.tree.print_tree(string=True,state_id=self.state_id)
        return toreturn

    @threadsafe
    def on_iter_has_child(self, rowref):
        nid = self.__get_nid_from_rowref(rowref)
        toreturn = self.tree.node_has_child(nid,state_id=self.state_id)
        if DEBUG_MODEL:
            print "on_iter_has_child %s : %s (state %s)" %(str(rowref),toreturn,self.state_id)
        return toreturn

    @threadsafe
    def on_iter_n_children(self, rowref):
        if rowref:
            nid = self.__get_nid_from_rowref(rowref)
        else:
            nid = None
        toreturn = self.tree.node_n_children(nid,state_id=self.state_id)
        if DEBUG_MODEL:
            print "returning iter_n_children for %s (%s) : %s (state %s)" %(str(rowref),nid,toreturn,self.state_id)
        return toreturn

    @threadsafe
    def on_iter_nth_child(self, rowref, n):
        if rowref:
            nid = self.__get_nid_from_rowref(rowref)
        else:
            #if rowref == None, we use the root
            nid = None
            rowref = ()
        cid = self.tree.node_nth_child(nid,n,state_id=self.state_id)
        toreturn = rowref + (cid,)
        if DEBUG_MODEL:
            print "on iter child nbr %s for %s : %s (state %s)" %(n,str(rowref),toreturn,self.state_id)
        return toreturn

    @threadsafe
    def on_iter_parent(self, rowref):
        if len(rowref) >= 1:
            toreturn = rowref[:-1]
        else:
            toreturn = None
        if DEBUG_MODEL:
            print "on iter parent %s :%s" %(str(rowref),toreturn)
        return toreturn

    @threadsafe
    def __update_task(self,sender,tid,node_path,state_id,data=None):
#        print "other paths are %s" %(str(self.tree.get_paths_for_node(tid)))
        actual_tid = self.tree.get_node_for_path(node_path,state_id=state_id)
        if tid == actual_tid:
            if DEBUG_MODEL:
                print "    ! this is the update/add %s get_iter" %tid
#            self.state_id = state_id
            if data == 'add':
                if DEBUG_MODEL:
                    print "     adding %s on path %s" %(tid,str(node_path))
                if self.state_id != state_id - 1:
                    print "We are at state %s and want to go directly to %s"\
                                                     %(self.state_id,state_id)
                self.state_id = state_id
                rowref = self.get_iter(node_path)
                self.row_func('inserted',node_path, rowref)
                if len(node_path) > 1:
                    parpath = node_path[:-1]
                    parrowref = self.get_iter(parpath)
                    if DEBUG_MODEL:
                        print "*** child toggled for parent %s" %str(parpath)
                    self.row_func('child_toggled',parpath,parrowref)
            else:
                if DEBUG_MODEL:
                    print "     modifying %s on path %s" %(tid,str(node_path))
                if self.state_id != state_id:
                    print "we send node-modified for state %s at %s" %(state_id,self.state_id)
                self.state_id = state_id
                rowref = self.get_iter(node_path)
                self.row_func('changed',node_path, rowref)
            if self.tree.node_has_child(tid,state_id=state_id):
                if DEBUG_MODEL:
                    print "     child toggling for %s %s" %(tid,str(node_path))
                self.row_func('child_toggled',node_path, rowref)
        else:
            raise ValueError("%s path for %s is supposed" %(data,tid) +\
                    "to be %s, the one of %s "%(node_path, actual_tid))
#                print "************"
#                print "path for %s is supposed to be %s "%(tid,node_path)
#                print "but in fact, tid for that path is %s" %actual_tid
#                print "and paths are %s" %str(self.tree.get_paths_for_node(tid))
#                print "and paths for real are %s" %str(self.tree.get_paths_for_node(actual_tid))
#                self.tree.print_tree()
#        print " = ============================="
#        self.tree.print_tree()%(tid,state_id,self.state_id)

    @threadsafe
    def __remove_task(self,sender,tid,path,state_id):
        if DEBUG_MODEL:
            print "     deleting row %s  (it's tid %s)" %(str(path),tid)
        if self.state_id != state_id - 1:
                print "We are at state %s and want to go directly to %s"\
                                                     %(self.state_id,state_id)
        self.state_id = state_id
        self.row_func('delete',path)
#        print "removing %s from path %s" %(tid,str(path))
        if len(path) > 1:
            parpath = path[:-1]
            parrowref = self.get_iter(parpath)
            self.row_func('child_toggled',parpath,parrowref)
           
    @threadsafe 
    def __reorder(self, sender, nid,path,neworder,state_id):
        if self.state_id != state_id - 1:
                print "We are at state %s and want to go directly to %s"\
                                                     %(self.state_id,state_id)
        self.state_id = state_id
        actual_nid = self.tree.get_node_for_path(path,state_id=state_id)
        if nid == actual_nid:
            if path:
                rowref = self.get_iter(path)
            else:
                rowref = None
            self.row_func('reordered',path,rowref,neworder)
        else:
            raise Exception('path/node mismatch in reorder')
            
    #This function send the signals to the treeview
    @threadsafe
    def row_func(self,func,*args):
        if func == 'delete':
            f = self.row_deleted
        elif func == "child_toggled":
            f = self.row_has_child_toggled
        elif func == 'inserted':
            f = self.row_inserted
        elif func == 'changed':
            f = self.row_changed
        elif func == 'reordered':
            f = self.rows_reordered
        f(*args)
        

