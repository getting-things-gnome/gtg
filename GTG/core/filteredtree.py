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

#from gtk import GenericTreeModel

class FilteredTree():

    def __init__(self,tree):
        self.tree = tree
        
    #### Standard tree functions
    def get_node(self,id):
        return self.tree.get_node(id)
    
    def get_root(self):
        return self.tree.get_root()


    ####TreeModel functions ##############################

    def get_node_for_path(self, path):
        #print "get_iter for path %s" %str(path)
        #We should convert the path to the base.path
        toreturn = self.tree.get_node_for_path(path)
        return toreturn

    def get_path_for_node(self, node):
        #print "get_path for node %s" %node
        #For that node, we should convert the base_path to path
        base_path = self.tree.get_path_for_node(node)
        path = base_path
        return path

    def next_node(self, node):
        #print "on_iter_next for node %s" %node
        #We should take the next good node, not the next base node
        if node:
            parent_id = node.get_parent()
            parent_node = self.tree.get_node(parent_id)
            if parent_node:
                next_idx = parent_node.get_child_index(node.get_id()) + 1
                if parent_node.get_n_children()-1 < next_idx:
                    nextnode = None
                else:
                    nextnode = parent_node.get_nth_child(next_idx)
            else:
                nextnode = None
        else:
            nextnode = None
        return nextnode

    def node_children(self, parent):
        #print "on_iter_children for parent %s" %parent
        #here, we should return only good childrens
        if parent:
            if parent.has_child():
                 child = parent.get_nth_child(0)
            else:
                child = None
        else:
            child = self.get_root().get_nth_child(0)
        return child

    def node_has_child(self, node):
        #print "on_iter_has_child for node %s" %node
        #we should say "has_good_child"
        if node:
            return node.has_child()
        else:
            return None

    def node_n_children(self, node):
        #print "on_iter_n_children for node %s" %node
        #we should return the number of "good" children
        if not node:
            node = self.get_root()
        toreturn = node.get_n_children()
        return toreturn

    def node_nth_child(self, node, n):
        #print "on_iter_nth_child for parent %s - n %s" %(parent,n)
        #we return the nth good children !
        if not node:
            node = self.get_root()
        nth_child = node.get_nth_child(n)
        return nth_child

    def node_parent(self, node):
        #print "on_iter_parent %s" %child
        #return None if we are at a Virtual root
        if node.has_parent():
            parent_id = node.get_parent()
            parent = self.tree.get_node(parent_id)
            if parent == self.tree.get_root():
                return None
            else:
                return parent
        else:
            return None


    #### Filtering methods ##########
        
    def refilter(self):
        print "refiltering"
