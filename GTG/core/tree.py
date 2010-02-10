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
        if root:
            self.root = root
        else:
            self.root = TreeNode(id=self.root_id)
        self.root.set_tree(self)

    def __str__(self):
        return "<Tree: root = '%s'>" % (str(self.root))

    def get_rowref_for_path(self, path):
        return self._rowref_for_path(self.root, path)

    def get_path_for_rowref(self, rowref):
        return self._path_for_rowref(self.root, rowref)

    def get_node_for_rowref(self, rowref):
        return self._node_for_rowref(self.root, rowref)

    def get_rowref_for_node(self, node):
        return self._rowref_for_node(node)

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
            print "Error : A node with this idea already exists"
        else:
            #We add the node
            node.set_tree(self)
            if parent:
                node.set_parent(parent)
                parent.add_child(node)
            else:
                self.root.add_child(node)
            self.nodes[id] = node

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
        toreturn = False
        p = self.get_node(parent_id)
        c = self.get_node(child_id)
        if p and c:
            if not p.has_child(child_id):
                p.add_child(c)
                toreturn = True
            if not c.has_parent(parent_id):
                c.add_parent(p)
                toreturn = True
                #removing the root from the list of parent
                if c.has_parent(self.root.get_id()):
                    c.remove_parent(self.root.get_id())
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
                    self.root.add_child(c)
        return toreturn
            
    #Trying to make a function that bypass the weirdiness of lists
    def get_node(self,id):
        if id in self.nodes :
            return self.nodes[id]
        else:
            return None
            
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
        return id in self.nodes.keys()

    def print_tree(self):
        self._print_from_node(self.root)

    def visit_tree(self, pre_func=None, post_func=None):
        if self.root.has_child():
            for c in self.root.get_children():
                node = self.root.get_child(c)
                self._visit_node(node, pre_func, post_func)

### HELPER FUNCTION FOR TREE #################################################
#
    def _rowref_for_path(self, node, path):
        if path[0] < node.get_n_children():
            if len(path) == 1:
                return "/" + str(node.get_nth_child(path[0]).get_id())
            else:
                node = node.get_nth_child(path[0])
                path = path[1:]
                c_path = self._rowref_for_path(node, path)
                if c_path:
                    return "/" + str(node.get_id()) + str(c_path)
                else:
                    return None
        else:
            return None

    def _path_for_rowref(self, node, rowref):
        if rowref.rfind('/') == 0:
            return (node.get_child_index(rowref[1:]), )
        else:
            cur_id   = rowref[1:rowref.find('/', 1)]
            cur_node = node.get_child(cur_id)
            cur_path = (node.get_child_index(cur_id), )
            rowref   = rowref[rowref.find(cur_id)+len(cur_id):]
            return cur_path + self._path_for_rowref(cur_node, rowref)

    def _node_for_rowref(self, node, rowref):
        #print "_node_for_rowref: %s" % rowref
        if rowref == '':
            return self.root
        elif rowref.rfind('/') == 0:
            return node.get_child(rowref[1:])
        else:
            cur_id   = rowref[1:rowref.find('/', 1)]
            cur_node = node.get_child(cur_id)
            rowref   = rowref[rowref.find(cur_id)+len(cur_id):]
            return self._node_for_rowref(cur_node, rowref)

    def _rowref_for_node(self, node):
        if not node.has_parent():
            return ""
        else:
            #Fixme : no multi parent support here
            parent_id = node.get_parent()
            parent = self.get_node(parent_id)
            return self._rowref_for_node(parent) + "/" + str(node.get_id())

    def _path_for_node(self, node):
        if node: 
            if node == self.root:
                return ()
            elif not node.has_parent():
                index  = self.root.get_child_index(node.get_id())
                return self._path_for_node(self.root) + (index, )
            else:
                #FIXME : no multiparent support here
                parent_id = node.get_parent()
                parent = self.get_node(parent_id)
                index  = parent.get_child_index(node.get_id())
                return self._path_for_node(parent) + (index, )
        return None

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
        if parent:
            self.add_parent(parent)

    def __str__(self):
        return "<TreeNode: '%s'>" % (self.id)
        
    def set_tree(self,tree):
        self.tree = tree
    def get_tree(self):
        return self.tree

    def get_id(self):
        return self.id
        
        
##### Parents

    def has_parent(self,id=None):
        if id:
            return id in self.parents
        else:
            return len(self.parents) > 0
    
    #this one return only one parent.
    #useful for tree where we know that there is only one
    def get_parent(self):
        if self.has_parent():
            return self.parents[0]
        else:
            return None
    def get_parents(self):
        return list(self.parents)

    def add_parent(self, par):
        id = par.get_id()
        self.parents.append(id)
        self.tree.new_relationship(id,self.get_id())
    
    #set_parent means that we remove all other parents
    def set_parent(self,par):
        if par:
            for i in self.parents:
                self.remove_parent(i)
            self.add_parent(par)
            
    def remove_parent(id):
        if id in self.parents():
            self.parents.pop(id)
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
        id = self.children[index]
        return self.tree.get_node(id)

    def get_child(self, id):
        if id in self.children:
            return self.tree.get_node(id)
        else:
            return None

    def get_child_index(self, id):
        return self.children.index(id)

    def add_child(self, child):
        id = child.get_id()
        self.children.append(id)
        self.tree.new_relationship(self.get_id(),id)

    def remove_child(self, id):
        if id in self.children:
            self.children.remove(id)
            self.tree.new_relationship(self.get_id(),id)

        
    def change_id(self,newid):
        oldid = self.id
        self.id = newid
        for p in self.parents:
            par = self.tree.get(p)
            par.remove_child(oldid)
            par.add_child(self)
        for c in self.get_children():
            c.add_parent(newid)
            c.remove_parent(oldid)
