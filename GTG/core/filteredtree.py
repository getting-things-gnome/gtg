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


# The problem we have is that, sometimes, we don't want to display all tasks.
# We want tasks to be filtered (workview, tags, …)
#
# The expected approach would be to put a gtk.TreeModelFilter above our
# TaskTree. Unfortunatly, this doesn't work because TreeModelFilter hides
# all children of hidden nodes. (unlike what we want)
#
# The solution we have found is to have a fake Tree between Tree and TaskTree
# This fake tree is called FilteredTree and will map path and nodes methods 
# to a result corresponding to the filtered tree.
#
# To be more efficient, a quick way to optimize the FilteredTree is to cache
# all answers in a dictionnary so we don't have to compute the answer 
# all the time. This is not done yet.

class FilteredTree():

    def __init__(self,req,tree):
        self.req = req
        self.tree = tree
        self.req.connect("task-added", self.__task_added)
        self.req.connect("task-modified", self.__task_modified)
        self.req.connect("task-deleted", self.__task_deleted)
        #virtual root is the list of root nodes
        #initially, they are the root nodes of the original tree
        self.virtual_root = []
        self.refilter()
        
    #### Standard tree functions
    def get_node(self,id):
        return self.tree.get_node(id)
    
    def get_root(self):
        return self.tree.get_root()
        
    def get_all_nodes(self):
        l = self.tree.get_all_nodes()
        for n in l:
            if not self.is_displayed(n):
                l.remove(n)
        return l
        
    def get_all_keys(self):
        k = []
        for n in self.get_all_nodes():
            k.append(n.get_id())
        return k
        
    ### update functions
    def __task_added(self,sender,tid):
        self.refilter()
        
    def __task_modified(self,sender,tid):
        self.refilter()
        
    def __task_deleted(self,sender,tid):
        self.refilter()
        
    ####TreeModel functions ##############################

    #The path received is only for tasks that are displayed
    #We have to find the good node.
    def get_node_for_path(self, path):
        #print "get_node for path %s" %str(path)
        #We should convert the path to the base.path
        p0 = path[0]
        if len(self.virtual_root) > p0:
            n1 = self.virtual_root[p0]
            path = path[1:]
            toreturn = self.__node_for_path(n1,path)
        else:
            toreturn = None
        return toreturn
    #done
    def __node_for_path(self,basenode,path):
        if len(path) == 0:
            return basenode
        elif path[0] < self.node_n_children(basenode):
            if len(path) == 1:
                return self.node_nth_child(basenode,path[0])
            else:
                node = self.node_nth_child(basenode,path[0])
                path = path[1:]
                return self.__node_for_path(node, path)
        else:
            return None
        

    def get_path_for_node(self, node):
        #For that node, we should convert the base_path to path
        if not node or not self.is_displayed(node):
            return None
        elif node == self.get_root():
            toreturn = ()
        elif node in self.virtual_root:
            ind = self.virtual_root.index(node)
            toreturn = (ind,)
        else:
            pos = 0
            par = self.node_parent(node)
            max = self.node_n_children(par)
            child = self.node_children(par)
            while pos < max and node != child:
                pos += 1
                child = self.node_nth_child(par,pos)
#            print "we want path for parent %s" %par.get_id()
            par_path = self.get_path_for_node(par)
            if par_path:
                toreturn = par_path + (pos,)
            else:
                print "*** Node %s not in vr" %(node.get_id())
                print "*** node is visilbe %s" %self.is_displayed(node)
                print "*** node has parent %s" %self.node_parent(node)
                print "**** node in VR: %s" %(node in self.virtual_root)
                toreturn = None
        #print "path for node %s is %s" %(node.get_id(),toreturn)
        return toreturn

    #Done
    def next_node(self, node):
        #print "on_iter_next for node %s" %node
        #We should take the next good node, not the next base node
        if node:
            if node in self.virtual_root:
                i = self.virtual_root.index(node) + 1
                if len(self.virtual_root) > i:
                    nextnode = self.virtual_root[i]
                else:
                    nextnode = None
            else:
                parent_node = self.node_parent(node)
                if parent_node:
                    next_idx = parent_node.get_child_index(node.get_id()) + 1
                    total = parent_node.get_n_children()-1
                    if total < next_idx:
                        nextnode = None
                    else:
                        nextnode = parent_node.get_nth_child(next_idx)
                        while next_idx < total and not self.is_displayed(nextnode):
                            next_idx += 1
                            nextnode = parent_node.get_nth_child(next_idx)
                else:
                    nextnode = None
        else:
            nextnode = None
        return nextnode

    #Done
    def node_children(self, parent):
        #print "on_iter_children for parent %s" %parent.get_id()
        #here, we should return only good childrens
        if parent:
            if self.node_has_child(parent):
                 child = self.node_nth_child(parent,0)
            else:
                child = None
        else:
            child = self.virtual_root[0]
        return child

    #Done
    def node_has_child(self, node):
        #print "on_iter_has_child for node %s" %node
        #we should say "has_good_child"
        if node and self.node_n_children(node)>0:
            return True
        else:
            return False

    #Done
    def node_n_children(self, node):
        #print "on_iter_n_children for node %s" %node
        #we should return the number of "good" children
        if not node:
            toreturn = len(self.virtual_root)
        else:
            n = 0
            for cid in node.get_children():
                c = self.get_node(cid)
                if self.is_displayed(c):
                    n+= 1
            toreturn = n
        return toreturn

    #Done
    def node_nth_child(self, node, n):
        #we return the nth good children !
        if not node:
            if len(self.virtual_root) > n:
                toreturn = self.virtual_root[n]
            else:
                toreturn = None
        else:
            total = node.get_n_children()
            cur = 0
            good = 0
            toreturn = None
            while good <= n and cur < total:
                curn = node.get_nth_child(cur)
                if self.is_displayed(curn):
                    if good == n:
                        toreturn = curn
                    good += 1
                cur += 1
        return toreturn

    #Done
    def node_parent(self, node):
        #return None if we are at a Virtual root
#        print "node %s in virtual_root %s" %(node.get_id(),self.virtual_root)
        if node and node in self.virtual_root:
            return None
        elif node and node.has_parent():
            parent_id = node.get_parent()
            parent = self.tree.get_node(parent_id)
            if parent == self.tree.get_root():
                return None
            else:
                return parent
        else:
            return None


    #### Filtering methods ##########
    
    def is_displayed(self,node):
        if node:
            return self.req.is_displayed(node)
        else:
            return False
        
    def refilter(self):
        self.virtual_root = []
        for n in self.tree.get_all_nodes():
            is_root = False
            if self.is_displayed(n):
                is_root = True
                if n.has_parent():
                    for par in n.get_parents():
                        p = self.get_node(par)
                        if self.is_displayed(p):
                            is_root = False
            if is_root and n not in self.virtual_root:
                self.virtual_root.append(n)
                
        print "refiltering : virtual_root is:"
        for r in self.virtual_root :
            print "root %s" %r.get_id()
