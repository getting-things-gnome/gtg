# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things Gnome! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2010 - Lionel Dricot & Bertrand Rousseau
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

# FIXME lock should be used just for MainTree and TreeNode
# FIXME make sure public interface is not called from each other (prevent deadlock)

from GTG.tools.logger import Log
import threading
import gobject


class SyncQueue:
    def __init__(self, callback):
        self._queue = []
        self._handler = None
        self.callback = callback
        self._lock = threading.Lock()

    def push(self, *element):
        self._lock.acquire()
        self._queue.append(element)

        if self._handler is None:
            self._handler = gobject.idle_add(self.callback)
        self._lock.release()

    def process(self):
        """ Get slice of the queue and process it """
        self._lock.acquire()
        if len(self._queue) > 0:
            toreturn = [self._queue.pop(0)]
        else:
            toreturn = []

        if len(self._queue) == 0:
            gobject.source_remove(self._handler)
            self._handler = None
        self._lock.release()
        return toreturn
        
class MainTree:
    """Stores all nodes"""

    def __init__(self, root=None):
        self.nodes = {}
        self.old_paths = {}
        self.pending_relationships = []

        self.__cllbcks = {}

        self.root_id = 'root'
        if root:
            self.root = root
        else:
            self.root = TreeNode(self.root_id)
        self.root.set_tree(self)

        self._queue = SyncQueue(self._process_queue)
        self._execution_lock = threading.Lock()

        self._origin_thread = threading.current_thread()

    def __str__(self):
        return "<Tree: root = '%s'>" % (str(self.root))

####### PUBLIC INTERFACE ######################################################

    def register_callback(self, event, func):
        """ Store function and return unique key which can be used to
        unregister the callback later """

        if not self.__cllbcks.has_key(event):
            self.__cllbcks[event] = {}

        callbacks = self.__cllbcks[event]
        key = 0
        while callbacks.has_key(key):
            key += 1

        callbacks[key] = func
        return key

    def deregister_callback(self, event, key):
        """ Remove the callback identifed by key (from register_cllbck) """
        try:
            del self.__cllbcks[event][key]
        except KeyError:
            pass

    def get_root(self):
        return self.root

    def set_root(self, root):
# FIXME change root_id?
        self.root = root
        self.root.set_tree(self)

    def get_node_for_path(self, path):
        return self._node_for_path(None,path)

    def get_paths_for_node(self, node_id):
        return self._paths_for_node(node_id)

    def get_deleted_path(self,node_id):
        """ Deleted path can be requested only once """
# FIXME do i need this?
        if self.old_paths.has_key(node_id):
            return self.old_paths.pop(node_id)
        else:
            return None

    def add_node(self, node_id, parent_id=None):
        self.external_request(self._add_node, node_id, parent_id)

    def remove_node(self, node_id, recursive=False):
        self.external_request(self._remove_node, node_id, recursive)

    def modify_node(self, node_id):
        self.external_request(self.__modified, node_id)

    def new_relationship(self, parent_id, child_id, refresh_nodes=True):
        self._new_relationship(parent_id, child_id, refresh_nodes)
        #self._external_request(self._new_relationship, parent_id, child_id, refresh_nodes)

    def break_relationship(self, parent_id, child_id):
        self._break_relationship(parent_id, child_id)
        #self._external_request(self._break_relationship, parent_id, child_id)

    def external_request(self, request_type, *args):
        self._queue.push(request_type, *args)

        if self._origin_thread == threading.current_thread():
            self._process_queue()

    def _process_queue(self):
        # FIXME Why execution lock is problem?
        #if not self._execution_lock.acquire(False):
        #   return True

        for action in self._queue.process():
            func = action[0]
            func(*action[1:])

        #elf._execution_lock.release()
        return True

    def _add_node(self, node, parent_id=None):
        """ Add a node (TreeNode) to the tree.

        If parent_id is None, it's a child of the root"""
#FIXME change return codes to Exceptions?
        node_id = node.get_id()
        if self.nodes.has_key(node_id):
            print "Error : A node with this id %s already exists" % node_id
            return False

        #We add the node
        node.set_tree(self)
        if not parent_id:
            parent_id = 'root'
        #we build the relationship before adding the node !
        #That's crucial, else, the node will exist while
        #children might not be yet aware of the relationship
        self._new_relationship(parent_id, node_id)
        self.nodes[node_id] = node
        #build the relationships that were waiting for that node
        for rel in list(self.pending_relationships):
            if node_id in rel:
                self._new_relationship(rel[0],rel[1],refresh_nodes=False)
        self.callback("node-added", node_id)
#FIXME shouldnt be switched?
        return True

    def refresh_all(self):
        # FIXME needed to add .keys()
        for node_id in self.nodes.keys():
            self.modify_node(node_id)

#FIXME rewrite this function
#FIXME should this method public
    #this will remove a node but not his children
    #if recursive: will also remove children and children of childrens
    #does nothing if the node doesn't exist
    def _remove_node(self, node_id,recursive=False):
        if self.has_node(node_id):
            node = self.get_node(node_id)
    #        paths = self.get_paths_for_node(node)
            if not node :
                return
            else:
                #By removing the node early, we avoid unnecessary 
                #update of that node
                self.nodes.pop(node_id)
                if node.has_child():
                    for c_id in node.get_children():
# FIXME test this use case:
# i will recurively remove sub-tree and then add the same nodes. I guess, they 
# will have the relationship already there (without adding)
                        if not recursive:
                            self._break_relationship(node_id,c_id)
                        else:
                            self.remove_node(c_id,recursive=recursive)
                if node.has_parent():
                    for p_id in node.get_parents():
                        par = self.get_node(p_id)
                        par.internal_remove_child(node_id)
                else:
                    self.root.remove_child(node_id)
                self.callback("node-deleted", node_id)
        else:
            print "*** Warning *** Trying to remove a non-existing node"
            
        
#FIXME rewrite this function
#FIXME should this method public
# FIXME WRITE method
    #create a new relationship between nodes if it doesn't already exist
    #return False if nothing was done
    def _new_relationship(self,parent_id,child_id,refresh_nodes=True):
        def genealogic_search(node_id):
            """ Builds a list of every ancestor of a node. It is used to
            prevent cyclic dependencies. """

            if node_id not in genealogy:
                genealogy.append(node_id)
                if self.has_node(node_id):
                    node = self.get_node(node_id)
                    for par in node.get_parents():
                        genealogic_search(par)

        Log.debug("new relationship between %s and %s" %(parent_id,child_id))

        if [parent_id,child_id] in self.pending_relationships:
            self.pending_relationships.remove([parent_id,child_id])

        toreturn = False
        #no relationship allowed with yourself
        if parent_id != child_id:
#FIXME hardcoded value => use self.root_id
            if parent_id == 'root':
#                Log.debug("    -> adding %s to the root" %child_id)
                p = self.get_root()
            else:
                if self.has_node(parent_id):
                    p = self.get_node(parent_id)
                else:
                    p = None

            if p and self.has_node(child_id):
                c = self.get_node(child_id)
                #Avoid the typical time-traveller problem 
                #being-the-father-of-yourself or the grand-father.
                #We need some genealogic research !
                genealogy = []
                genealogic_search(parent_id)
                if child_id not in genealogy:
                    if not p.has_child(child_id):
                        #print "adding child %s to %s" %(child_id,parent_id)
                        p.internal_add_child(child_id)
                        toreturn = True
                    if parent_id != 'root' and not c.has_parent(parent_id):
                        #print "adding parent %s to %s" %(parent_id,child_id)
                        c.internal_add_parent(parent_id)
                        toreturn = True
                    #removing the root from the list of parent
                    if toreturn and parent_id != 'root' and \
                                                self.root.has_child(child_id):
                        self.root.remove_child(child_id)
                    if not toreturn:
                        Log.debug("  * * * * * Relationship already existing")
                else:
                    #FIXME There was an unreachable code, I moved exception lower
                    # FIXME discuss what should be consitent state after detecting circular relationship. The current behavior? Or should remove the last added thing? (I am not sure)
                    #a circular relationship was found
                    #undo everything
                    Log.debug("  * * * * * Circular relationship found : undo")
                    self._break_relationship(parent_id,child_id)
                    toreturn = False
                    raise Exception("Cannot build circular relationship"+\
                                    "between %s and %s" %(parent_id,child_id))
            else:
                #at least one of the node is not loaded. Save the relation for later
                #undo everything
#                print "breaking relation %s %s" %(parent_id,child_id)
                self._break_relationship(parent_id,child_id)
                #save it for later
                if [parent_id,child_id] not in self.pending_relationships:
                    self.pending_relationships.append([parent_id,child_id])
                toreturn = False

        if refresh_nodes and toreturn:
            if parent_id != 'root':
                self.__modified(parent_id)
            self.__modified(child_id)

        return toreturn
    
#FIXME rewrite this function
#FIXME should this method public
# FIXME WRITE method
    #break an existing relationship. The child is added to the root
    #return False if the relationship didn't exist    
    def _break_relationship(self,parent_id,child_id):
        toreturn = False
        if self.has_node(parent_id):
            p = self.get_node(parent_id)
            if p.has_child(child_id):
                ret = p.remove_child(child_id)
                toreturn = True
        if self.has_node(child_id):
            c = self.get_node(child_id)
            if c.has_parent(parent_id):
                c.internal_remove_parent(parent_id)
                toreturn = True
                #if no more parent left, adding to the root
            if not c.has_parent() and c not in self.root.get_children():
                self.root.add_child(child_id)
        if toreturn:
            self.__modified(parent_id)
            self.__modified(child_id)
        return toreturn
            
#FIXME rewrite this function
#FIXME should this method public
    #Trying to make a function that bypass the weirdiness of lists
    def get_node(self, node_id=None):
        toreturn = None
        if node_id in self.nodes:
            toreturn = self.nodes[node_id]
        elif node_id == 'root' or node_id == None:
            toreturn = self.root
        else:
            raise ValueError("Node %s is not in the tree. Wrong get_node()" % node_id)
        return toreturn
            
    def get_all_nodes(self):
        return list(self.nodes.keys())
    
#FIXME rewrite this function
#FIXME should this method public
    #parent_id is used only if node_id has multiple parents.
    #if parent_id is none, a random parent is used.
    def next_node(self,node_id,parent_id=None):
        """
        Returns the next sibling node, or None if there are no other siblings
        """
        #We should take the next good node, not the next base node
        if not node_id:
            raise ValueError('node_id should be different than None')
        toreturn = None
        node = self.get_node(node_id)
        parents_id = node.get_parents()
        if len(parents_id) == 0:
            parid = 'root'
        elif parent_id in parents_id:
            parid = parent_id
        else:
            parid = parents_id[0]
        parent = self.get_node(parid)
        if not parent:
            parent = self.root
        index = parent.get_child_index(node_id)
        if index == None:
            error = 'children are : %s\n' %parent.get_children()
            error += 'node %s is not a child of %s' %(node_id,parid)
            raise IndexError(error)
        if parent.get_n_children() > index+1:
            toreturn = parent.get_nth_child(index+1)
        return toreturn

#FIXME rewrite this function
#FIXME should this method public
#FIXME wtf? shouldnt it be somewhere different?
    def is_displayed(self, node_id):
        return self.has_node(node_id)

#FIXME rewrite this function
#FIXME should this method public
    def has_node(self, node_id):
        return (node_id in self.nodes)

#FIXME rewrite this function
#FIXME should this method public
    def print_tree(self,string=None):
        if string:
            print "print_tree with string is not implemented in tree.py"
        self._print_from_node(self.root)

#FIXME rewrite this function
#FIXME should this method public
    def visit_tree(self, pre_func=None, post_func=None):
        if self.root.has_child():
            for c in self.root.get_children():
                node = self.root.get_child(c)
                self._visit_node(node, pre_func, post_func)

####### PRIVATE METHODS #######################################################
        
    def callback(self, event, node_id):
        """ Inform others about the event. """
# FIXME MAKE this private => prepend _
        for func in self.__cllbcks.get(event, {}).itervalues():
            func(node_id)
        
    def __modified(self, node_id):
# FIXME why two underscores?
        if node_id != 'root' and node_id in self.nodes:
            self.callback("node-modified", node_id)

#FIXME rewrite this function
    def _node_for_path(self,node_id,path):
        if node_id:
            node = self.get_node(node_id)
        else:
            node = self.root

        if node and path and path[0] < node.get_n_children():
            if len(path) == 1:
                return node.get_nth_child(path[0])
            else:
                node_id = node.get_nth_child(path[0])
                path = path[1:]
                return self._node_for_path(node_id, path)
        else:
            return None

#FIXME rewrite this function
#FIXME added paretn_id
    def _paths_for_node(self, node_id=None):
        toreturn = []
        if node_id:
            node = self.get_node(node_id)
        else:
            node = self.root
        if node: 
            if node == self.root:
                toreturn = [()]
            elif not node.has_parent():
                index  = self.root.get_child_index(node_id)
                toad = (index, )
                toreturn.append(toad)
            else:
                parents_id = node.get_parents()


# FIXME i am not able to determine path for children if I dont know the whole path (parent can also be multiparent child... It will be really problematic!!!!

                for parent_id in parents_id:
                    parent = self.get_node(parent_id)
                    #print parent
                    if parent:
                        index  = parent.get_child_index(node_id)
                        for p in self._paths_for_node(parent_id):
                            toreturn.append(p+(index,))
# FIXME I am not sure why there is this code. I guess, the author wanted to handle the state when there is no parent. But how it is possible, that this bug wasnt discovered before? Does anybody use this function? FIXME
                #else:
                #    toreturn = [()]
        else:
            raise ValueError("Cannot get path for non existing node %s" %node_id)
        return toreturn

#FIXME rewrite this function
    def _print_from_node(self, node, prefix=""):
        print prefix + node.node_id
        prefix = prefix + " "
        if node.has_child():
            for c in node.get_children():
                cur_node = node.get_child(c)
                self._print_from_node(cur_node, prefix)

#FIXME rewrite this function
    def _visit_node(self, node, pre_func=None, post_func=None):
        if pre_func:
            pre_func(node)
        if node.has_child():
            for c in node.get_children():
                cur_node = node.get_child(c)
                self._visit_node(cur_node, pre_func, post_func)
        if post_func:
            post_func(node)


class TreeNode():
    """A single node of a tree"""

    def __init__(self, node_id, parent=None):
        self.node_id = node_id

        self.parents = []
        self.children = []

        self.tree = None
        self.pending_relationship = []

        if parent:
            self.add_parent(parent)

    def __str__(self):
        return "<TreeNode: '%s'>" % (self.node_id)
        
    def modified(self):
        #FIXME : we should maybe have
        # a directional recursive update
        if self.tree:
            #then the task
#            print "modify for %s sent to the tree" %self.id
            self.tree.modify_node(self.node_id)
#FIXME exception if not tree
#FIXME maybe add a special decorator @mustBeInTree
        
    def set_tree(self, tree):
        self.tree = tree
        for rel in list(self.pending_relationship):
            self.tree.new_relationship(rel[0],rel[1])
            self.pending_relationship.remove(rel)
        # WTF? Why to remove relationship, why not immediately? should it be run in different thread? Or better said, will more than one thread work on it? FIXME
            
    def get_tree(self):
        return self.tree

    def get_id(self):
        return self.node_id
    
    def new_relationship(self,par,chi):
        if self.tree:
            return self.tree.new_relationship(par,chi)
        else:
            self.pending_relationship.append([par,chi])
            #it's pending, we return False
            Log.debug("** There's still no tree, relationship is pending")
            return False
        
        
##### Parents

    def has_parent(self,node_id=None):
        # FIXME get rid of has_node function
        if node_id:
            toreturn = self.tree.has_node(node_id) and (node_id in self.parents)
        else:
            toreturn = len(self.parents) > 0
        return toreturn
    
    #this one return only one parent.
    #useful for tree where we know that there is only one
    def get_parent(self):
# FIXME get rid of has_parent() => transform it to _has_parent
        #we should throw an error if there are multiples parents
        if len(self.parents) > 1 :
            print "Warning: get_parent will return one random parent for task %s because there are multiple parents." %(self.get_id())
            print "Get_parent is deprecated. Please use get_parents instead"
        if self.has_parent():
            return self.parents[0]
        else:
            return None

    def get_parents(self):
#FIXME  shouldnt this be just
# return self.parents?
        '''
        Return a list of parent ids
        '''
        toreturn = []
        if self.tree:
            for p in self.parents:
                if self.tree.has_node(p):
                    toreturn.append(p)
        return toreturn

    def add_parent(self, parent_id):
        self.external_request(self.internal_add_parent, parent_id)

    def internal_add_parent(self, parent_id):
        if parent_id not in self.parents:
            self.parents.append(parent_id)
#FIXME two times the same relationship
            toreturn = self.new_relationship(parent_id, self.get_id())
        else:
            toreturn = False
        return toreturn
    
    #set_parent means that we remove all other parents
    #if parent_id is None, we will remove all parents, thus being on the root.
    def set_parent(self,parent_id):
#this has some optimization to do not remove parent if it is not necessary
        self.external_request(self.internal_set_parent, parent_id)

    def internal_set_parent(self, parent_id):
        is_already_parent_flag = False
        for i in self.parents:
            if i != parent_id:
                self.remove_parent(i)
            else:
                is_already_parent_flag = True
        if parent_id and not is_already_parent_flag:
            self.add_parent(parent_id)

            
    def remove_parent(self,node_id):
        self.external_request(self.internal_remove_parent, node_id)

    def internal_remove_parent(self, node_id):
        if node_id in self.parents:
            self.parents.remove(node_id)
            ret = self.tree.break_relationship(node_id,self.get_id())
            return ret
        else:
            return False
            
###### Children

    def has_child(self,node_id=None):
        if node_id :
            return node_id in self.children
        else:
            return bool(self.children)

    def get_children(self):
        return list(self.children)

    def get_n_children(self):
        return len(self.children)

    def get_nth_child(self, index):
        try:
            return self.children[index]
        except(IndexError):
            raise ValueError("Index is not in the children list")

    def get_child(self, node_id):
        if self.tree == None:
            raise Exception('task %s has not tree !' % self.node_id)
        if self.tree and self.tree.has_node(node_id) and node_id in self.children:
            return self.tree.get_node(node_id)
        else:
            return None

    def get_child_index(self, node_id):
        if node_id in self.children:
            return self.children.index(node_id)
        else:
            return None

    #return True if the child was added correctly. False otherwise
    #takes the node_id of the child as parameter.
    #if the child is not already in the tree, the relation is anyway "saved"
    def add_child(self, node_id):
        self.external_request(self.internal_add_child, node_id)

    def internal_add_child(self, node_id):
        if node_id not in self.children:
            self.children.append(node_id)
            toreturn = self.new_relationship(self.get_id(),node_id)
        else:
            Log.debug("%s was already in children of %s" %(node_id,self.get_id()))
            toreturn = False
        return toreturn

    def remove_child(self, node_id):
        self.external_request(self.internal_remove_child, node_id)

    def internal_remove_child(self, node_id):
        if node_id in self.children:
            self.children.remove(node_id)
            if self.tree:
                ret = self.tree.break_relationship(self.get_id(),node_id)
            return ret
        else:
            return False

    def external_request(self, func, *params):
        if self.tree:
            self.tree.external_request(func, *params)
        else:
            func(*params)
        
    def change_id(self,newid):
        oldid = self.node_id
        self.node_id = newid
        for p in self.parents:
            par = self.tree.get(p)
            par.remove_child(oldid)
            par.add_child(self.node_id)
        for c in self.get_children():
            c.add_parent(newid)
            c.remove_parent(oldid)
