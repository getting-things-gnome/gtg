# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
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

import gtk

class TreeModel(gtk.TreeStore):
    """ Local copy of showed tree """

    def __init__(self, tree, types):
        """ Initializes parent and create list of columns. The first colum
        is node_id of node """

        self.types = [[str, lambda node: node.get_id()]] + types
        only_types = [python_type for python_type, access_method in self.types]

        gtk.TreeStore.__init__(self, *only_types)
        self.tree = tree

    def connect_model(self):
        """ Register "signals", callbacks from liblarch.
        
        Also asks for the current status by providing add_task callback.
        We are able to connect to liblarch tree on the fly. """

        self.tree.register_cllbck('node-added-inview',self.add_task)
        self.tree.register_cllbck('node-deleted-inview',self.remove_task)
        self.tree.register_cllbck('node-modified-inview',self.update_task)
        self.tree.register_cllbck('node-children-reordered',self.reorder_nodes)

        # Request the current state
        self.tree.get_current_state()

    def my_get_iter(self, path):
        """ Because we sort the TreeStore, paths in the treestore are
        not the same as paths in the FilteredTree. We do the  conversion here"""
        iter = self.get_iter_root()
        if path == () or not iter:
            return None
        else:
            #The following code is ugly. Yuk!
            #We just wanted to convert a node path like (node1,node2,)
            #to an iterator.
            #don't look at it! Ploum, DS2011          
            current_nid = self.get_value(iter,0)
            depth = 0
            while iter and current_nid != str(path[-1]):
                in_the_path = path[depth]
                while iter and current_nid != str(in_the_path):
                    iter = self.iter_next(iter)
                    if iter:
                        current_nid = self.get_value(iter,0)
                if depth+1 < len(path):
                    depth += 1
                    iter = self.iter_children(iter)
                    if iter:
                        current_nid = self.get_value(iter,0)
                    else:
                        #we didn't find the iter, let's return none
                        return None
                else:
                    break
            return iter

    def print_tree(self):
        """ Print TreeStore as Tree into console """

        def push_to_stack(stack, level, iterator):
            """ Macro which adds a new element into stack if it is possible """
            if iterator is not None:
                stack.append((level, iterator))

        stack = []
        push_to_stack(stack, 0, self.get_iter_first())

        print "+"*50
        print "Treemodel print_tree: "
        while stack != []:
            level, iterator = stack.pop()

            print "=>"*level, self.get_value(iterator, 0)

            push_to_stack(stack, level, self.iter_next(iterator))
            push_to_stack(stack, level+1, self.iter_children(iterator))
        print "+"*50

### INTERFACE TO LIBLARCH #####################################################

    def add_task(self, node_id, path):
        """ Add new instance of node_id to position described at path.

        @param node_id: identification of task
        @param path: identification of position
        """
        node = self.tree.get_node(node_id)

        # Build a new row
        row = []
        for python_type, access_method in self.types:
            value = access_method(node)
            row.append(value)

        # Find position to add task
        iter_path = path[:-1]

        iterator = self.my_get_iter(iter_path)
        it = self.insert(iterator, -1, row)
        
#        print "adding task %s to path %s" %(node_id,str(path))

        # Show the new task if possible
#        self.row_has_child_toggled(self.get_path(it), it)

    def remove_task(self, node_id, path):
        """ Remove instance of node.

        @param node_id: identification of task
        @param path: identification of position
        """
        it = self.my_get_iter(path)
        if not it:
            raise Exception("Trying to remove node %s with no iterator"%node_id)
        actual_node_id = self.get_value(it, 0)
        assert actual_node_id == node_id
        self.remove(it)

    def update_task(self, node_id, path):
        """ Update instance of node by rebuilding the row.

        @param node_id: identification of task
        @param path: identification of position
        """
        node = self.tree.get_node(node_id)
        iterator = self.my_get_iter(path)

        for column_num, (python_type, access_method) in enumerate(self.types):
            value = access_method(node)
            self.set_value(iterator, column_num, value)
#        print "node %s has been updated on path %s" %(node_id,str(path))

    def reorder_nodes(self, node_id, path, neworder):
        """ Reorder nodes.
        
        This is deprecated signal. In the past it was useful for reordering
        showed nodes of tree. It was possible to delete just the last
        element and therefore every element must be moved to the last position
        and then deleted.

        @param node_id: identification of root node
        @param path: identification of poistion of root node
        @param neworder: new order of children of root node
        """

        if path is not None:
            it = self.my_get_iter(path)
        else:
            it = None
        self.reorder(it, neworder)
        self.print_tree()
