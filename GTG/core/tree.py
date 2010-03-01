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

class Tree():

    def __init__(self, root=None):
        self.root_id = 'root'
        self.nodes = {}
        self.pending_relationships = []
        if root:
            self.root = root
        else:
            self.root = TreeNode(id=self.root_id)
        self.root.set_tree(self)

    def __str__(self):
        return "<Tree: root = '%s'>" % (str(self.root))

    def get_node_for_path(self, path):
        return self._node_for_path(self.root,path)

    def get_path_for_node(self, node):
        return self._path_for_node(node)

    def get_root(self):
        return self.root

    def set_root(self, root):
        self.root = root
        self.root.set_tree(self)

    #We add a node. By default, it's a child of the root
    def add_node(self, node, parent=None):
        #print "*************adding node %s %s" %(node, parent)
        id = node.get_id()
        if self.nodes.get(id):
            print "Error : A node with this id %s already exists" %id
            return False
        else:
            #We add the node
            node.set_tree(self)
            if parent:#    
                node.set_parent(parent)
                parent.add_child(id)
            else:
                self.root.add_child(id)
            self.nodes[id] = node
            #build the relationships that were waiting for that node
            for rel in list(self.pending_relationships):
                if id in rel:
                    self.new_relationship(rel[0],rel[1])
            return True

    #this will remove a node and all his children
    #does nothing if the node doesn't exist
    def remove_node(self, id):
        node = self.get_node(id)
        if not node :
            return
        else:
            if node.has_child():
                for c_id in node.get_children():
                    self.remove_node(c_id)
            if node.has_parent():
                for p_id in node.get_parents():
                    par = self.get_node(p_id)
                    par.remove_child(id)
            else:
                self.root.remove_child(id)
            self.nodes.pop(id)
        
    #create a new relationship between nodes if it doesn't already exist
    #return False if nothing was done
    def new_relationship(self,parent_id,child_id):
        #print "new relationship between %s and %s" %(parent_id,child_id)
        if [parent_id,child_id] in self.pending_relationships:
            self.pending_relationships.remove([parent_id,child_id])
        toreturn = False
        #no relationship allowed with yourself
        if parent_id != child_id:
            p = self.get_node(parent_id)
            c = self.get_node(child_id)
            if p and c :
                #no circular relationship allowed
                if not p.has_parent(child_id) and not c.has_child(parent_id):
                    if not p.has_child(child_id):
                        p.add_child(child_id)
                        toreturn = True
                    if not c.has_parent(parent_id):
                        #print "creating the %s - %s relation" %(parent_id,child_id)
                        c.add_parent(p)
                        toreturn = True
                        #removing the root from the list of parent
                        if self.root.has_child(child_id):
                            self.root.remove_child(child_id)
                else:
                    #a circular relationship was found
                    #undo everything
                    self.break_relationship(parent_id,child_id)
                    toreturn = False
            else:
                #at least one of the node is not loaded. Save the relation for later
                #undo everything
                self.break_relationship(parent_id,child_id)
                #save it for later
                if [parent_id,child_id] not in self.pending_relationships:
                    self.pending_relationships.append([parent_id,child_id])
                toreturn = True
        return toreturn
    
    #break an existing relationship. The child is added to the root
    #return False if the relationship didn't exist    
    def break_relationship(self,parent_id,child_id):
        toreturn = False
        p = self.get_node(parent_id)
        c = self.get_node(child_id)
        if p and c :
            if p.has_child(child_id):
                p.remove_child(child_id)
                toreturn = True
            if c.has_parent(parent_id):
                c.remove_parent(parent_id)
                toreturn = True
                #if no more parent left, adding to the root
                if not c.has_parent():
                    self.root.add_child(child_id)
        return toreturn
            
    #Trying to make a function that bypass the weirdiness of lists
    def get_node(self,id):
        return self.nodes.get(id)
            
    def get_all_keys(self):
        return list(self.nodes.keys())
            
    def get_all_nodes(self):
        li = []
        for k in self.nodes.keys():
            no = self.get_node(k)
            if no:
                li.append(no)
        return li

    def has_node(self, id):
        return (self.nodes.get(id) != None)

    def print_tree(self):
        self._print_from_node(self.root)

    def visit_tree(self, pre_func=None, post_func=None):
        if self.root.has_child():
            for c in self.root.get_children():
                node = self.root.get_child(c)
                self._visit_node(node, pre_func, post_func)

### HELPER FUNCTION FOR TREE #################################################
#
    def _node_for_path(self,node,path):
        if path[0] < node.get_n_children():
            if len(path) == 1:
                return node.get_nth_child(path[0])
            else:
                node = node.get_nth_child(path[0])
                path = path[1:]
                return self._node_for_path(node, path)
        else:
            return None

    def _path_for_node(self, node):
        if node: 
            if node == self.root:
                toreturn = ()
            elif not node.has_parent():
                index  = self.root.get_child_index(node.get_id())
                toreturn = self._path_for_node(self.root) + (index, )
            else:
                #FIXME : no multiparent support here
                parent_id = node.get_parent()
                parent = self.get_node(parent_id)
                index  = parent.get_child_index(node.get_id())
                toreturn = self._path_for_node(parent) + (index, )
        else:
            toreturn = None
        return toreturn

    def _print_from_node(self, node, prefix=""):
        print prefix + node.id
        prefix = prefix + " "
        if node.has_child():
            for c in node.get_children():
                cur_node = node.get_child(c)
                self._print_from_node(cur_node, prefix)

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

    def __init__(self, id, tree=None, parent=None):
        self.parents   = []
        self.id       = id
        self.children      = []
        self.tree = tree
        self.pending_relationship = []
        if parent:
            self.add_parent(parent)

    def __str__(self):
        return "<TreeNode: '%s'>" % (self.id)
        
    def set_tree(self,tree):
        self.tree = tree
        for rel in list(self.pending_relationship):
            self.tree.new_relationship(rel[0],rel[1])
            self.pending_relationship.remove(rel)
            
    def get_tree(self):
        return self.tree

    def get_id(self):
        return self.id
        
    
    def new_relationship(self,par,chi):
        if self.tree:
            self.tree.new_relationship(par,chi)
        else:
            self.pending_relationship.append([par,chi])
        
        
##### Parents

    def has_parent(self,id=None):
        if id:
            return id in self.parents
        else:
            return len(self.parents) > 0
    
    #this one return only one parent.
    #useful for tree where we know that there is only one
    def get_parent(self):
        #we should throw an error if there are multiples parents
        if len(self.parents) > 1:
            print "Warning : get_parent will return one random parent because \
                    there are multiple parents."
        if self.has_parent():
            return self.parents[0]
        else:
            return None
    def get_parents(self):
        return list(self.parents)

    def add_parent(self, par):
#        root = self.tree.get_root()
#        print "removing root node has parent"
#        self.tree.break_relationship(root.get_id(),self.get_id())
        id = par.get_id()
        if id not in self.parents:
            self.parents.append(id)
            return self.new_relationship(id,self.get_id())
        else:
            return False
    
    #set_parent means that we remove all other parents
    def set_parent(self,par):
        if par:
            for i in self.parents:
                if i != par:
                    self.remove_parent(i)
            self.add_parent(par)
            
    def remove_parent(self,id):
        if id in self.parents:
            self.parents.remove(id)
            self.tree.break_relationship(id,self.get_id())
            
###### Children

    def has_child(self,id=None):
        if id :
            return id in self.children
        else:
            return len(self.children) != 0

    def get_children(self):
        return list(self.children)

    def get_n_children(self):
        return len(self.children)

    def get_nth_child(self, index):
        try:
            id = self.children[index]
            return self.tree.get_node(id)
        except(IndexError):
            raise ValueError("Index is not in the children list")

    def get_child(self, id):
        if id in self.children:
            return self.tree.get_node(id)
        else:
            return None

    def get_child_index(self, id):
        return self.children.index(id)

    #return True if the child was added correctly. False otherwise
    #takes the id of the child as parameter.
    #if the child is not already in the tree, the relation is anyway "saved"
    def add_child(self, id):
        self.children.append(id)
        return self.new_relationship(self.get_id(),id)

    def remove_child(self, id):
        if id in self.children:
            self.children.remove(id)
            self.tree.break_relationship(self.get_id(),id)
            return True
        else:
            return False

        
    def change_id(self,newid):
        oldid = self.id
        self.id = newid
        for p in self.parents:
            par = self.tree.get(p)
            par.remove_child(oldid)
            par.add_child(self.id)
        for c in self.get_children():
            c.add_parent(newid)
            c.remove_parent(oldid)
