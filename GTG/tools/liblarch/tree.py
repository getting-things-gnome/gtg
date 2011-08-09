# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things Gnome! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2011 - Lionel Dricot & Bertrand Rousseau
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

class SyncQueue:
    """ Synchronized queue for processing requests"""

    def __init__(self, callback):
        """ Initialize synchronized queue.

        @param callback - function for processing requests"""
        self._queue = []
        self._handler = None
        self.callback = callback
        self._lock = threading.Lock()

    def push(self, *element):
        """ Add a new element to the queue.

        Schedule its processing if it is not already.  """
        self._lock.acquire()
        self._queue.append(element)

        if self._handler is None:
            self._handler = gobject.idle_add(self.callback)
        self._lock.release()

    def process(self):
        """ Return elements to process
        
        At the moment, it returns just one element. In the future more
        elements may be better to return (to speed it up).
        
        If there is no request left, disable processing. """

        self._lock.acquire()
        if len(self._queue) > 0:
            toreturn = [self._queue.pop(0)]
        else:
            toreturn = []

        if len(self._queue) == 0 and self._handler is not None:
            gobject.source_remove(self._handler)
            self._handler = None
        self._lock.release()
        return toreturn

class MainTree:
    """ Tree which stores and handle all requests """

    def __init__(self):
        """ Initialize MainTree.

        @param root - the "root" node which contains all nodes
        """

        self.nodes = {}
        self.pending_relationships = []

        self.__cllbcks = {}

        self.root_id = 'root'
        self.root = TreeNode(self.root_id)
        self.root.set_tree(self)

        self._queue = SyncQueue(self._process_queue)
        self._origin_thread = threading.current_thread()

    def __str__(self):
        return "<Tree: root = '%s'>" % self.root

    def get_root(self):
        """ Return root node """
        return self.root

####### INTERFACE FOR CALLBACKS ###############################################
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

    def _callback(self, event, node_id):
        """ Inform others about the event """
        for func in self.__cllbcks.get(event, {}).itervalues():
#            print "running %s %s" %(str(func),node_id)
            func(node_id)

####### INTERFACE FOR HANDLING REQUESTS #######################################
    def add_node(self, node, parent_id=None):
        self.external_request(self._add_node, node, parent_id)

    def remove_node(self, node_id, recursive=False):
        self.external_request(self._remove_node, node_id, recursive)

    def modify_node(self, node_id):
        self.external_request(self._modify_node, node_id)

    def new_relationship(self, parent_id, child_id):
        self.external_request(self._new_relationship, parent_id, child_id)

    def break_relationship(self, parent_id, child_id):
        self.external_request(self._break_relationship, parent_id, child_id)

    def external_request(self, request_type, *args):
        """ Put the reqest into queue and in the main thread handle it """

        self._queue.push(request_type, *args)

        if self._origin_thread == threading.current_thread():
            self._process_queue()

    def _process_queue(self):
        """ Process requests from queue """
        for action in self._queue.process():
            func = action[0]
            func(*action[1:])

        # return True to process other requests as well
        return True

    def refresh_all(self):
        """ Refresh all nodes """
        for node_id in self.nodes.keys():
            self.modify_node(node_id)

####### IMPLEMENTATION OF HANDLING REQUESTS ###################################
    def _create_relationship(self, parent_id, child_id):
        """ Create relationship without any checks """
        parent = self.nodes[parent_id]
        child = self.nodes[child_id]

        if child_id not in parent.children:
            parent.children.append(child_id)

        if parent_id not in child.parents:
            child.parents.append(parent_id)

        if child_id in self.root.children:
            self.root.children.remove(child_id)

    def _destroy_relationship(self, parent_id, child_id):
        """ Destroy relationship without any checks """
        parent = self.nodes[parent_id]
        child = self.nodes[child_id]

        if child_id in parent.children:
            parent.children.remove(child_id)

        if parent_id in child.parents:
            child.parents.remove(parent_id)

    def _is_circular_relation(self, parent_id, child_id):
        """ Would the new relation be circular?
        
        Go over every possible ancestors. If one of them is child_id,
        this would be circular relation.
        """

        visited = []
        ancestors = [parent_id]
        while ancestors != []:
            node_id = ancestors.pop(0)
            if node_id == child_id:
                return True
            
            if node_id not in self.nodes:
                continue
    
            for ancestor_id in self.nodes[node_id].parents:
                if ancestor_id not in visited:
                    ancestors.append(ancestor_id)

        return False
        
    def _add_node(self, node, parent_id):
        """ Add a node to the tree

        @param node - node to be added
        @param parent_id - parent to add or it will be add to root
        """
        node_id = node.get_id()
        if node_id in self.nodes:
            print "Error: Node '%s' already exists" % node_id
            return False

        node.set_tree(self)
        for relationship in node.pending_relationships:
            if relationship not in self.pending_relationships:
                self.pending_relationships.append(relationship)
        node.pending_relationships = []

        self.nodes[node_id] = node

        add_to_root = True
        parents_to_refresh = []
        children_to_refresh = []

        # Build pending relationships
        for rel_parent_id, rel_child_id in list(self.pending_relationships):
            # Adding as a child
            if rel_child_id == node_id and rel_parent_id in self.nodes:
                if not self._is_circular_relation(rel_parent_id, node_id):
                    self._create_relationship(rel_parent_id, node_id)
                    add_to_root = False
                    parents_to_refresh.append(rel_parent_id)
                else:
                    print "Error: Detected pending circular relationship", \
                        rel_parent_id, rel_child_id
                self.pending_relationships.remove((rel_parent_id, rel_child_id))

            # Adding as a parent
            if rel_parent_id == node_id and rel_child_id in self.nodes:
                if not self._is_circular_relation(node_id, rel_child_id):
                    self._create_relationship(node_id, rel_child_id)
                    children_to_refresh.append(rel_child_id)
                else:
                    print "Error: Detected pending circular relationship", \
                        rel_parent_id, rel_child_id
                self.pending_relationships.remove((rel_parent_id, rel_child_id))
        
        # Build relationship with given parent
        if parent_id is not None:
            if self._is_circular_relation(parent_id, node_id):
                raise Exception('Creating circular relationship between %s and %s' % \
                     (parent_id, node_id))
            if parent_id in self.nodes:
                self._create_relationship(parent_id, node_id)
                add_to_root = False
                parents_to_refresh.append(parent_id)
            else:
                self.pending_relationships.append((parent_id, node_id))

        # Add at least to root
        if add_to_root:
            self.root.children.append(node_id)

        # Send callbacks
        
        #FIXME: this callback is very slow with treemodelsort
        for parent_id in parents_to_refresh:
            self._callback("node-modified", parent_id)
            
        #FIXME: this callback is very slow with treemodelsort
        self._callback("node-added", node_id)
        
        #this callback is really fast. No problem
        for child_id in children_to_refresh:
            #FIXME: why parent_id? this should be a bug!
            #removing this doesn't affect the tests. Why is it useful?
            self._callback("node-modified", child_id)

    def _remove_node(self, node_id, recursive=False):
        """ Remove node from tree """

        if node_id not in self.nodes:
            print "*** Warning *** Trying to remove a non-existing node"
            return

        # Do not remove root node
        if node_id is None:
            return

        # Remove pending relationships with this node
        for relation in list(self.pending_relationships):
            if node_id in relation:
                self.pending_relationships.remove(relation)

        node = self.nodes[node_id]

        # Handle parents
        for parent_id in node.parents:
            self._destroy_relationship(parent_id, node_id)
            self._callback('node-modified', parent_id)

        # Handle children
        for child_id in list(node.children):
            if recursive:
                self._remove_node(child_id, True)
            else:
                self._destroy_relationship(node_id, child_id)
                self._callback('node-modified', child_id)
                if self.nodes[child_id].parents == []:
                    self.root.children.append(child_id)

        if node_id in self.root.children:
            self.root.children.remove(node_id)

        self.nodes.pop(node_id)
        self._callback('node-deleted', node_id)

    def _modify_node(self, node_id):
        """ Force update of a node """
        if node_id != self.root_id and node_id in self.nodes:
            self._callback('node-modified', node_id)

    def _new_relationship(self, parent_id, child_id):
        """ Creates a new relationship 
        
        This method is used mainly from TreeNode"""

        if (parent_id, child_id) in self.pending_relationships:
            self.pending_relationships.remove((parent_id, child_id))

        if not parent_id or not child_id or parent_id == child_id:
            return False

        if parent_id not in self.nodes or child_id not in self.nodes:
            self.pending_relationships.append((parent_id, child_id))
            return True

        if self._is_circular_relation(parent_id, child_id):
            self._destroy_relationship(parent_id, child_id)
            raise Exception('Cannot build circular relationship between %s and %s' % (parent_id, child_id))


        self._create_relationship(parent_id, child_id)

        # Remove from root when having a new relationship
        if child_id in self.root.children:
            self.root.children.remove(child_id)

        self._callback('node-modified', parent_id)
        self._callback('node-modified', child_id)

    def _break_relationship(self, parent_id, child_id):
        """ Remove a relationship

        This method is used mainly from TreeNode """
        for rel_parent, rel_child in list(self.pending_relationships):
            if rel_parent == parent_id and rel_child == child_id:
                self.pending_relationships.remove((rel_parent, rel_child))

        if not parent_id or not child_id or parent_id == child_id:
            return False

        if parent_id not in self.nodes or child_id not in self.nodes:
            return False

        self._destroy_relationship(parent_id, child_id)

        # Move to root if beak the last parent
        if self.nodes[child_id].get_parents() == []:
            self.root.add_child(child_id)

        self._callback('node-modified', parent_id)
        self._callback('node-modified', child_id)


####### INTERFACE FOR READING STATE OF TREE ###################################
    def has_node(self, node_id):
        """ Is this node_id in this tree? """
        return node_id in self.nodes

    def get_node(self, node_id=None):
        """ Return node of tree or root node of this tree """
        if node_id in self.nodes:
            return self.nodes[node_id]
        elif node_id == self.root_id or node_id is None:
            return self.root
        else:
            raise ValueError("Node %s is not in the tree" % node_id)

    def get_node_for_path(self, path):
        """ Convert path into node_id
        
        @return node_id if path is valid, None otherwise
        """
        if len(path) == 0:
            return None

        node_id = self.root_id
        for index in path:
            node = self.get_node(node_id)
            if node and 0 <= index < len(node.children):
                node_id = node.children[index]
            else:
                return None

        return node_id

    def get_paths_for_node(self, node_id):
        """ Get all paths for node_id """
        if not node_id or node_id == self.root_id:
            return [()]
        elif node_id in self.nodes:
            node = self.nodes[node_id]
            if node.has_parent():
                paths = []
                for parent_id in node.get_parents():
                    if parent_id not in self.nodes:
                        continue
                    index = parent.get_child_index(node_id)
                    for path in self.get_paths_for_node(parent_id):
                        paths.append(path + (index,))
                return paths
            else:
                index = self.root.get_child_index(node_id)
                return [(index,)]
        else:
            raise ValueError("Cannot get path for non existing node %s" % node_id)

    def get_all_nodes(self):
        """ Return list of all nodes in this tree """
        return self.nodes.keys()

    def next_node(self, node_id, parent_id=None):
        """ Return the next sibling node or None if there is none
        
        @param  node_id - we look for siblings of this node
        @param parent_id - specify which siblings should be used, 
            if task has more parents. If None, random parent will be used
        """
        if node_id is None:
            raise ValueError('node_id should be different than None')

        node = self.get_node(node_id)
        parents_id = node.get_parents()
        if len(parents_id) == 0:
            parid = self.root_id
        elif parent_id in parents_id:
            parid = parent_id
        else:
            parid = parents_id[0]

        parent = self.get_node(parid)
        if not parent:
            raise ValueError('Parent does not exist')

        index = parent.get_child_index(node_id)
        if index == None:
            error = 'children are : %s\n' %parent.get_children()
            error += 'node %s is not a child of %s' %(node_id,parid)
            raise IndexError(error)

        if parent.get_n_children() > index+1:
            return parent.get_nth_child(index+1)
        else:
            return None

    def print_tree(self, string=False):
        output = self.root_id + "\n"
        stack = [(" ", child_id) for child_id in reversed(self.root.children)]

        while stack != []:
            prefix, node_id = stack.pop()
            output += prefix + node_id + "\n"
            prefix += " "
            for child_id in reversed(self.nodes[node_id].get_children()):
                stack.append((prefix, child_id))

        if string:
            return output
        else:
            print output,

class TreeNode:
    """ Object just for a single node in Tree """
# FIXME maybe add a lock which prevents changing root at the wrong moment,
# updating children, etc

    def __init__(self, node_id, parent=None):
        """ Initializes node

        @param node_id - unique identifier of node (str)
        @param parent - node_id of parent
        """
        self.node_id = node_id

        self.parents = []
        self.children = []

        self.tree = None
        self.pending_relationships = []

        if parent:
            self.add_parent(parent)

    def __str__(self):
        return "<TreeNode: '%s'>" % (self.node_id)

    def get_id(self):
        """ Return node_id """
        return self.node_id
        
    def modified(self):
        """ Force to update node (because it has changed) """
        if self.tree:
            self.tree.modify_node(self.node_id)

    def set_tree(self, tree):
        """ Set tree which is should contain this node.
        
        This method should be called only from MainTree. It is not
        part of public interface. """
        self.tree = tree

    def get_tree(self):
        """ Return associated tree with this node """
        return self.tree

    def new_relationship(self, parent_id, child_id):
        """ Create new relationship or save it for later if there is no tree """
        if self.tree:
            self.tree.new_relationship(parent_id, child_id)
        else:
            self.pending_relationships.append((parent_id, child_id))

####### Parents ###############################################################
    def add_parent(self, parent_id):
        """ Add a new parent """
        if parent_id not in self.parents:
            self.parents.append(parent_id)
            self.new_relationship(parent_id, self.node_id)

    def set_parent(self, parent_id):
        """ Remove other parents and set this parent as only parent """
        is_already_parent_flag = False
        for node_id in self.parents:
            if node_id != parent_id:
                self.remove_parent(node_id)
            else:
                is_already_parent_flag = True

        if parent_id and not is_already_parent_flag:
            self.add_parent(parent_id)

    def remove_parent(self, parent_id):
        """ Remove parent """
        if parent_id in self.parents:
            self.parents.remove(parent_id)
            self.tree.break_relationship(parent_id, self.node_id)

    def has_parent(self, parent_id=None):
        """ Has parent/parents?

        @param parent_id - None => has any parent?
            not None => has this parent?
        """
        if parent_id:
            return self.tree.has_node(parent_id) and parent_id in self.parents
        else:
            return len(self.parents) > 0

    def get_parents(self):
        """ Return parents of node """
        parents = []
        if self.tree:
            for parent_id in self.parents:
                if self.tree.has_node(parent_id):
                    parents.append(parent_id)

        return parents

####### Children ##############################################################
    def add_child(self, child_id):
        """ Add a children to node """
        if child_id not in self.children:
            self.children.append(child_id)
            self.new_relationship(self.node_id, child_id)
        else:
            print "%s was already in children of %s" % (child_id, self.node_id)

    def has_child(self, child_id=None):
        """ Has child/children?

        @param child_id - None => has any child?
            not None => has this child?
        """
        if child_id:
            return child_id in self.children
        else:
            return bool(self.children)

    def get_children(self):
        """ Return children of nodes """
        children = []
        if self.tree:
            for child_id in self.children:
                if self.tree.has_node(child_id):
                    children.append(child_id)

        return children

    def get_n_children(self):
        """ Return count of children """
        return len(self.get_children())

    def get_nth_child(self, index):
        """ Return nth child """
        try:
            return self.children[index]
        except(IndexError):
            raise ValueError("Requested non-existing child")

    def get_child_index(self, node_id):
        if node_id in self.children:
            return self.children.index(node_id)
        else:
            return None
