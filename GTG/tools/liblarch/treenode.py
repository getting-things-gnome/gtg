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

class TreeNode:
    """ Object just for a single node in Tree """
    def __init__(self, node_id, parent=None):
        """ Initializes node

        @param node_id - unique identifier of node (str)
        @param parent - node_id of parent
        """
        self.node_id = node_id
        
        self.parents_enabled = True
        self.children_enabled = True
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
        
    def modified(self,priority="low"):
        """ Force to update node (because it has changed) """
        if self.tree:
            self.tree.modify_node(self.node_id,priority=priority)

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
    def set_parents_enabled(self,bol):
        if not bol:
            for p in self.get_parents():
                self.remove_parent(p)
        self.parents_enabled = bol
        
    def has_parents_enabled(self):
        return self.parents_enabled

    def add_parent(self, parent_id):
        """ Add a new parent """
        if parent_id != self.get_id() and self.parents_enabled \
                                      and parent_id not in self.parents:
            if not self.tree:
                self.pending_relationships.append((parent_id, self.get_id()))
            elif not self.tree.has_node(parent_id):
                self.tree.pending_relationships.append((parent_id, self.get_id()))
            else:
                par = self.tree.get_node(parent_id)
                if par.has_children_enabled():
                    self.parents.append(parent_id)
                    self.new_relationship(parent_id, self.node_id)

    def set_parent(self, parent_id):
        """ Remove other parents and set this parent as only parent """
        if parent_id != self.get_id() and self.parents_enabled:
            is_already_parent_flag = False
            if not self.tree:
                self.pending_relationships.append((parent_id, self.get_id()))
            elif not self.tree.has_node(parent_id):
                for p in self.get_parents():
                    self.tree.break_relationship(p,self.get_id())
                self.tree.pending_relationships.append((parent_id, self.get_id()))
            else:
                par = self.tree.get_node(parent_id)
                if par.has_children_enabled():
                    for node_id in self.parents:
                        if node_id != parent_id:
                            self.remove_parent(node_id)
                        else:
                            is_already_parent_flag = True
                    if parent_id and not is_already_parent_flag:
                        self.add_parent(parent_id)

    def remove_parent(self, parent_id):
        """ Remove parent """
        if self.parents_enabled and parent_id in self.parents:
            self.parents.remove(parent_id)
            self.tree.break_relationship(parent_id, self.node_id)

    def has_parent(self, parent_id=None):
        """ Has parent/parents?

        @param parent_id - None => has any parent?
            not None => has this parent?
        """
        if self.parents_enabled:
            if parent_id:
                return self.tree.has_node(parent_id) and parent_id in self.parents
            else:
                return len(self.parents) > 0
        else:
            return False

    def get_parents(self):
        """ Return parents of node """
        parents = []
        if self.parents_enabled and self.tree:
            for parent_id in self.parents:
                if self.tree.has_node(parent_id):
                    parents.append(parent_id)

        return parents

####### Children ##############################################################
    def set_children_enabled(self,bol):
        if not bol:
            for c in self.get_children():
                self.tree.break_relationship(self.get_id(),c)
        self.children_enabled = bol
        
    def has_children_enabled(self):
        return self.children_enabled
        
    def add_child(self, child_id):
        """ Add a children to node """
        if self.children_enabled and child_id != self.get_id():
            if child_id not in self.children:
                if not self.tree:
                    self.pending_relationships.append((self.get_id(), child_id))
                elif not self.tree.has_node(child_id):
                    self.tree.pending_relationships.append((self.get_id(), child_id))
                else:
                    child = self.tree.get_node(child_id)
                    if child.has_parents_enabled():
                        self.children.append(child_id)
                        self.new_relationship(self.node_id, child_id)
            else:
                print "%s was already in children of %s" % (child_id, self.node_id)

    def has_child(self, child_id=None):
        """ Has child/children?

        @param child_id - None => has any child?
            not None => has this child?
        """
        if self.children_enabled:
            if child_id:
                return child_id in self.children
            else:
                return bool(self.children)
        else:
            return False

    def get_children(self):
        """ Return children of nodes """
        children = []
        if self.children_enabled and self.tree:
            for child_id in self.children:
                if self.tree.has_node(child_id):
                    children.append(child_id)

        return children

    def get_n_children(self):
        """ Return count of children """
        if self.children_enabled:
            return len(self.get_children())
        else:
            return 0

    def get_nth_child(self, index):
        """ Return nth child """
        try:
            return self.children[index]
        except(IndexError):
            raise ValueError("Requested non-existing child")

    def get_child_index(self, node_id):
        if self.children_enabled and node_id in self.children:
            return self.children.index(node_id)
        else:
            return None
