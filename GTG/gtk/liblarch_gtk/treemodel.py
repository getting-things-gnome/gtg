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
DEBUG_MODEL = True
TM_USE_SIGNALS = True
TM_IDLE_ADD = True
THREAD_PROTECTION = False

import xml.sax.saxutils as saxutils

import gtk
import gobject
import pango
if DEBUG_MODEL or THREAD_PROTECTION:
    import threading

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
        if THREAD_PROTECTION:
            self.thread = threading.current_thread()

    def connect_model(self):
        if TM_USE_SIGNALS:
            self.tree.connect('node-added-inview',self.__add_task)
            self.tree.connect('node-deleted-inview',self.__remove_task)
            self.tree.connect('node-modified-inview',self.__update_task)
            self.tree.connect('node-children-reordered',self.__reorder)
        else:
            self.tree.register_cllbck('node-added-inview',self.add_task)
            self.tree.register_cllbck('node-deleted-inview',self.remove_task)
            self.tree.register_cllbck('node-modified-inview',self.update_task)
            self.tree.register_cllbck('node-children-reordered',self.reorder)

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
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not acces get_column from thread %s' %t)
        if len(self.value_list) <= n:
            raise ValueError('The tree model doesnt have enough columns!')
        return self.value_list[n][0]

    def on_get_value(self, rowref, column):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not acces get_value from thread %s' %t)
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

    def on_get_iter(self, path):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not acces get_iter from thread %s' %t)
        #We have to return None if there's no node on that path
        nid = self.tree.get_node_for_path(path)
        if nid:
            rowref = self.__build_rowref(path)
            toreturn = rowref
        else:
            toreturn = None
        if DEBUG_MODEL:
            print "on_get_iter for path %s -> %s : %s" %(path,nid,toreturn)
        return toreturn

    def on_get_path(self, rowref):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not acces get_path from thread %s' %t)
        toreturn = self.__get_path_from_rowref(rowref)
        if DEBUG_MODEL:
            print "on_get_path for %s : %s" %(str(rowref),toreturn)
        return toreturn

    def on_iter_next(self, rowref):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not acces iter_next from thread %s' %t)
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
        if DEBUG_MODEL:
            print "iter_next for %s : %s" %(str(rowref),toreturn)
#        if not toreturn:
#            print "###########  iter_next returns None for rowref %s" %str(rowref)
#            self.tree.print_tree()
#        else:
#            print "******** %s is next node of %s ********" %(toreturn,str(rowref))
        return toreturn

    def on_iter_children(self, rowref):
        #By Gtk.treeview definition, we have to return None
        #if rowref doesn't have any children
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not acces iter_children from thread %s' %t)
        nid = self.__get_nid_from_rowref(rowref)
        if self.tree.node_n_children(nid) > 0:
            toreturn = self.on_iter_nth_child(rowref,0)
        else:
            toreturn = None
        if DEBUG_MODEL:
            print "on_iter_children %s : %s" %(str(rowref),toreturn)
        return toreturn

    def on_iter_has_child(self, rowref):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not acces iter_has_child from thread %s' %t)
        nid = self.__get_nid_from_rowref(rowref)
        toreturn = self.tree.node_has_child(nid)
        if DEBUG_MODEL:
            print "on_iter_has_child %s : %s" %(str(rowref),toreturn)
        return toreturn

    def on_iter_n_children(self, rowref):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not acces iter_n_children from thread %s' %t)
        if rowref:
            nid = self.__get_nid_from_rowref(rowref)
        else:
            nid = None
        toreturn = self.tree.node_n_children(nid)
        if DEBUG_MODEL:
            print "returning iter_n_children for %s (%s) : %s" %(str(rowref),nid,toreturn)
        return toreturn

    def on_iter_nth_child(self, rowref, n):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not acces iter_nth_child from thread %s' %t)
        if rowref:
            nid = self.__get_nid_from_rowref(rowref)
        else:
            #if rowref == None, we use the root
            nid = None
            rowref = ()
        cid = self.tree.node_nth_child(nid,n)
        toreturn = rowref + (cid,)
        if DEBUG_MODEL:
            print "on iter child nbr %s for %s : %s" %(n,str(rowref),toreturn)
        return toreturn

    def on_iter_parent(self, rowref):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not acces iter_parent from thread %s' %t)
        if len(rowref) >= 1:
            toreturn = rowref[:-1]
        else:
            toreturn = None
        if DEBUG_MODEL:
            print "on iter parent %s :%s" %(str(rowref),toreturn)
        return toreturn

    def add_task(self,tid,path):
        if TM_IDLE_ADD:
            gobject.idle_add(self.__update_task,None,tid,path,'add')
        else:
            self.__update_task(None,tid,path,'add')

    def __add_task(self,sender,tid,path):
        self.__update_task(sender,tid,path,'add')

    def update_task(self, tid,path,data=None):
        if TM_IDLE_ADD:
            gobject.idle_add(self.__update_task,None,tid,path,data)
        else:
            self.__update_task(None,tid,path,data)

    def __update_task(self,sender,tid,node_path,data=None):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not update_task from thread %s' %t)
#       print "updating %s for path %s" %(tid,str(node_path))
#       print "other paths are %s" %(str(self.tree.get_paths_for_node(tid)))
        actual_tid = self.tree.get_node_for_path(node_path)
        if tid == actual_tid:
            if DEBUG_MODEL:
                print "    ! this is the update/add %s get_iter" %tid
            rowref = self.get_iter(node_path)
            if data == 'add':
                if DEBUG_MODEL:
                    print "     adding %s on path %s" %(tid,str(node_path))
                self.row_inserted(node_path, rowref)
                if len(node_path) > 1:
                    parpath = node_path[:-1]
                    parrowref = self.get_iter(parpath)
                    self.row_has_child_toggled(parpath,parrowref)
            else:
                if DEBUG_MODEL:
                    print "     modifying %s on path %s" %(tid,str(node_path))
                self.row_changed(node_path, rowref)
            if self.tree.node_has_child(tid):
                if DEBUG_MODEL:
                    print "     child toggling for %s %s" %(tid,str(node_path))
                self.row_has_child_toggled(node_path, rowref)
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
#        self.tree.print_tree()

    def remove_task(self,tid,path):
        if TM_IDLE_ADD:
            gobject.idle_add(self.__remove_task,None,tid,path)
        else:
            self.__remove_task(None,tid,path)

    def __remove_task(self,sender,tid,path):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not remove_task from thread %s' %t)
        if DEBUG_MODEL:
            print "     deleting row %s  (it's tid %s)" %(str(path),tid)
#            self.tree.print_tree()
        self.row_deleted(path)
#        print "removing %s from path %s" %(tid,str(path))
        if len(path) > 1:
            parpath = path[:-1]
            parrowref = self.get_iter(parpath)
            self.row_has_child_toggled(parpath,parrowref)
        
    def reorder(self,sender,nid,path,neworder):
        if TM_IDLE_ADD:
            gobject.idle_add(self.__reorder,None,nid,path,neworder)
        else:
            self.__reorder(None,nid,path,neworder)
            
    def __reorder(self, sender, nid,path,neworder):
        actual_nid = self.tree.get_node_for_path(path)
        if nid == actual_nid:
            if path:
                rowref = self.get_iter(path)
            else:
                rowref = None
            self.rows_reordered(path,rowref,neworder)
        else:
            raise Exception('path/node mismatch in reorder')

