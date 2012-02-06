# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Liblarch
# Copyright (c) 2010-2011 - Lionel Dricot & Izidor Matušov
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
import processqueue
from GTG.tools.liblarch.treenode import TreeNode

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

        self._queue = processqueue.SyncQueue()
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
        #We copy the dict to not loop on it while it could be modified
        dic = dict(self.__cllbcks.get(event, {}))
        for func in dic.itervalues():
            func(node_id)

####### INTERFACE FOR HANDLING REQUESTS #######################################
    def add_node(self, node, parent_id=None, priority="low"):
        self._external_request(self._add_node, priority, node, parent_id)

    def remove_node(self, node_id, recursive=False):
        self._external_request(self._remove_node, True, node_id, recursive)

    def modify_node(self, node_id, priority="low"):
        self._external_request(self._modify_node, priority, node_id)

    def new_relationship(self, parent_id, child_id):
        self._external_request(self._new_relationship, False, parent_id, child_id)

    def break_relationship(self, parent_id, child_id):
        self._external_request(self._break_relationship, False, parent_id, child_id)

    def _external_request(self, request_type, priority, *args):
        """ Put the reqest into queue and in the main thread handle it """
        if priority == "high":
            self._queue.priority_push(request_type, *args)
        elif priority == "normal" or priority == "medium":
            self._queue.push(request_type, *args)
        else:
            self._queue.low_push(request_type, *args)

        #I'm really wondering what is this line about
        #It doesn't seem right nor useful, except for unit tests.
        if self._origin_thread == threading.current_thread():
            self._queue.process_queue()

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
        #updating the parent and the children is handled by the FT
        self._callback("node-added", node_id)
        
#        #The following callback is only needed in case we have a
#        #Flat filter applied.
#        for parent_id in parents_to_refresh:
#            self._callback("node-modified", parent_id)

        #this callback is really fast. No problem
#        for child_id in children_to_refresh:
#            #FIXME: why parent_id? this should be a bug!
#            #removing this doesn't affect the tests. Why is it useful?
#            self._callback("node-modified", child_id)

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
        if not path or path == ():
            return None
        node_id = path[-1]
        if path in self.get_paths_for_node(node_id):
            return node_id
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
                    for path in self.get_paths_for_node(parent_id):
                        paths.append(path + (node_id,))
                return paths
            else:
                return [(node_id,)]
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
