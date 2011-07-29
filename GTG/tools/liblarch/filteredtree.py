from __future__ import with_statement
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
#

class FilteredTree():
    # FIXME comment of class
    # describe cache and Virtual Root

    def __init__(self, tree, filtersbank, refresh=True):
        """ Construct a layer where filters could by applied

        @param tree: Original tree to filter.
        @param filtersbank: Filter bank which stores filters
        @param refresh: Requests all nodes in the beginning? Additional
            filters can be added and refresh can be done later

        _flat defines whether only nodes without children can be shown. For example WorkView filter.
        """

        self.cllbcks = {}

        # Cache
        self.nodes = {}
        self.root_id = None
#FIXME: this is just for printing
        self.root_id = 'root'
        self.nodes[self.root_id] = {'parents': [], 'children': []}

        # Connect to signals from MainTree
        self.tree = tree
        self.tree.register_callback("node-added", self.__external_modify)
        self.tree.register_callback("node-modified", self.__external_modify)
        self.tree.register_callback("node-deleted", self.__external_modify)

        # Filters
        self.__flat = False
        self.applied_filters = []
        self.fbank = filtersbank

        if refresh:
            self.refilter()

    def set_callback(self, event, func):
        """ Register a callback for an event.

        It is possible to have just one callback for event.
        @param event: one of added, modified, deleted, reordered
        @param func: callback function
        """
        self.cllbcks[event] = func
        
    def callback(self, event, node_id, path, neworder=None):
        """ Run a callback.

        To call callback, the object must be initialized and function exists.

        @param event: one of added, modified, deleted, reordered
        @param node_id: node_id parameter for callback function
        @param path: path parameter for callback function
        @param neworder: neworder parameter for reorder callback function
        """
        func = self.cllbcks.get(event, None)
        if func:
            if neworder:
                func(node_id, path, neworder)
            else:
                func(node_id, path)

#### EXTERNAL MODIFICATION ####################################################
    def __external_modify(self, node_id):
        # First thing is to find all nodes to update
        need_update = [node_id]
        visited = []

        # Go up
        queue = [node_id]
        while queue != []:
            node_id = queue.pop(0)
            visited.append(node_id)

            if node_id in self.nodes:
                for parent_id in self.nodes[node_id]['parents']:
                    if parent_id not in visited and not self.is_node_okay(parent_id):
                        need_update.insert(0, parent_id)
                        queue.append(parent_id)

            for parent_id in self.__node_parents(node_id):
                if parent_id not in visited and not self.is_node_okay(parent_id):
                    need_update.insert(0, parent_id)
                    queue.append(parent_id)

        # Go down
        queue = [node_id]
        while queue != []:
            node_id = queue.pop(0)
            visited.append(node_id)

            if node_id in self.nodes:
                for child_id in self.nodes[node_id]['children']:
                    if child_id not in visited and not self.is_node_okay(child_id):
                        need_update.append(child_id)
                        queue.append(child_id)

            for child_id in self.__node_children(node_id):
                if child_id not in visited and not self.is_node_okay(child_id):
                    need_update.append(child_id)
                    queue.append(child_id)

        for node_id in need_update:
            self.update_node(node_id)

        #self.test_validity()

    def is_node_okay(self, node_id):
        # Root is always okay :-)
        if node_id == self.root_id:
            return True

        current_display = self.is_displayed(node_id)
        new_display = self.__is_displayed(node_id)
        if current_display and new_display:

            current_parents = self.nodes[node_id]['parents']
            new_parents = self.__node_parents(node_id)
            return current_parents == new_parents
        else:
            return False

        return current_parents == new_parents
        
    def update_node(self, node_id):
        current_display = self.is_displayed(node_id)
        new_display = self.__is_displayed(node_id)

        if not current_display and not new_display:
            # Nothing to do
            return False
        elif not current_display and new_display:
            action = 'added'
        elif current_display and not new_display:
            action = 'deleted'
        else:
            action = 'modified'

        # Create node info for new node
        if action == 'added':
            self.nodes[node_id] = {'parents':[], 'children':[]}

        # Make sure parents are okay if we adding or updating
        if action == 'added' or action == 'modified':
            current_parents = self.nodes[node_id]['parents']
            new_parents = self.__node_parents(node_id)
            self.nodes[node_id]['parents'] = new_parents

            remove_from = list(set(current_parents) - set(new_parents))
            add_to = list(set(new_parents) - set(current_parents))

            for parent_id in remove_from:
                self.send_remove_tree(node_id, parent_id)
                self.nodes[parent_id]['children'].remove(node_id)

            for parent_id in add_to:
                self.nodes[parent_id]['children'].append(node_id)
                self.send_add_tree(node_id, parent_id)

        elif action == 'deleted':
            for child_id in reversed(self.nodes[node_id]['children']):
                self.send_remove_tree(child_id, node_id)
                self.nodes[child_id]['parents'].remove(node_id)

        if action in ['modified', 'deleted']:
            for path in self.get_paths_for_node(node_id):
                self.callback(action, node_id, path)

        if action == 'deleted':
            # Remove node from cache
            for parent_id in self.nodes[node_id]['parents']:
                self.nodes[parent_id]['children'].remove(node_id)
            del self.nodes[node_id]

    def send_add_tree(self, node_id, parent_id):
        paths = self.get_paths_for_node(parent_id)
        index = self.nodes[parent_id]['children'].index(node_id)
        queue = [(node_id, (index, ))]

        while queue != []:
            node_id, relative_path = queue.pop(0)

            for start_path in paths:
                path = start_path + relative_path
                self.callback('added', node_id, path)

            for index, child_id in enumerate(self.nodes[node_id]['children']):
                queue.append((child_id, relative_path + (index,)))

    def send_remove_tree(self, node_id, parent_id):
        paths = self.get_paths_for_node(parent_id)
        index = self.nodes[parent_id]['children'].index(node_id)
        stack = [(node_id, (index, ), True)]

        while stack != []:
            node_id, relative_path, first_time = stack.pop()

            if first_time:
                stack.append((node_id, relative_path, False))
                for index, child_id in enumerate(self.nodes[node_id]['children']):
                    stack.append((child_id, relative_path + (index,), True))

            else:
                for start_path in paths:
                    path = start_path + relative_path
                    self.callback('deleted', node_id, path)

    def test_validity(self):
        for node_id in self.nodes:
            for parent_id in self.nodes[node_id]['parents']:
                assert node_id in self.nodes[parent_id]['children']

            if self.nodes[node_id]['parents'] == []:
                assert node_id == self.root_id

            for parent_id in self.nodes[node_id]['children']:
                assert node_id in self.nodes[parent_id]['parents']


#### OTHER ####################################################################
    def refilter(self):
        # Find out it there is at least one flat filter
        self.__flat = False
        for filter_name in self.applied_filters:
            filt = self.fbank.get_filter(filter_name)
            if filt and not self.__flat:
                self.__flat = filt.is_flat()

        # Clean the tree
        for node_id in reversed(self.nodes[self.root_id]['children']):
            self.send_remove_tree(node_id, self.root_id)

        self.nodes = {}
        self.nodes[self.root_id] = {'parents': [], 'children': []}

        # Build tree again
# FIXME do not ignore __flat
        root_node = self.tree.get_root()
        queue = root_node.get_children()
#FIXME special call

        while queue != []:
            node_id = queue.pop(0)
            self.update_node(node_id)

            node = self.tree.get_node(node_id)
            for child_id in node.get_children():
                queue.append(child_id)

    def __is_displayed(self, node_id):
        """ Should be node displayed regardless of its current status? """
        if node_id and self.tree.has_node(node_id):
            for filter_name in self.applied_filters:
                filt = self.fbank.get_filter(filter_name)
                if filt:
                    can_be_displayed = filt.is_displayed(node_id)
                    if not can_be_displayed:
                        return False
            return True
        else:
            return False

    def is_displayed(self, node_id):
        """ Is the node displayed at the moment? """

        return node_id in self.nodes

    def __node_children(self, node_id):
        if node_id == self.root_id:
            raise Exception("Requesting children for root node")

        if not self.__flat:
            if self.tree.has_node(node_id):
                node = self.tree.get_node(node_id)
            else:
                node = None
        else:
            node = None

        if not node:
            return []

        toreturn = []
        for child_id in node.get_children():
            if self.__is_displayed(child_id):
                toreturn.append(child_id)

        return toreturn

    def __node_parents(self, node_id):
        """ Returns parents of the given node, or [] if there is no 
        parent (such as if the node is a child of the virtual root),
        or if the parent is not displayable.
        """
        # FIXME comment
        if node_id == self.root_id:
            raise ValueError("Requested a parent of the root node")

        parents_nodes = []
        #we return only parents that are not root and displayed
        if not self.__flat :
            if self.tree.has_node(node_id):
                node = self.tree.get_node(node_id)
                for parent_id in node.get_parents():
                    if self.__is_displayed(parent_id):
                        parents_nodes.append(parent_id)

        # Add to root if it is an orphan
        if parents_nodes == []:
            parents_nodes = [self.root_id]

        return parents_nodes

    def get_paths_for_node(self, node_id):
        if node_id == self.root_id or not self.is_displayed(node_id):
            return [()]
        else:
            toreturn = []
            for parent_id in self.nodes[node_id]['parents']:
                if parent_id not in self.nodes:
                    raise Exception("Parent %s does not exists" % parent_id)
                if node_id not in self.nodes[parent_id]['children']:
                    raise Exception("%s is not children of %s" % (node_id, parent_id))
                index = self.nodes[parent_id]['children'].index(node_id)

                for parent_path in self.get_paths_for_node(parent_id):
                    mypath = parent_path + (index,)
                    toreturn.append(mypath)

            return toreturn

    def print_tree(self, string=False):
        """ Representation of tree in FilteredTree
        
        @param string: if set, instead of printing, return string for printing.
        """

        stack = [(self.root_id, "")]

        output = "_"*30 + "\n" + "FilteredTree cache\n" + "_"*30 + "\n"

        while stack != []:
            node_id, prefix = stack.pop()

            output += prefix + str(node_id) + '\n'

            for child_id in reversed(self.nodes[node_id]['children']):
                stack.append((child_id, prefix+" "))

        output += "_"*30 + "\n"

        if string:
            return output
        else:
            print output

    def get_all_nodes(self):
        nodes = list(self.nodes.keys())
        nodes.remove(self.root_id)
        return nodes

    def get_n_nodes(self, withfilters=[], include_transparent=True):
        """
        returns quantity of displayed nodes in this tree
        if the withfilters is set, returns the quantity of nodes
        that will be displayed if we apply those filters to the current
        tree. It means that the currently applied filters are also taken into
        account.
        If include_transparent=False, we only take into account the applied filters
        that doesn't have the transparent parameters.
        """
#FIXME docstring
# FIXME this implementation is the most naive

        if withfilters == [] and include_transparent:
            # Use current cache
            return len(self.nodes) - 1
        elif withfilters != [] and include_transparent:
            # Filter on the current nodes

            filters = []
            for filter_name in withfilters:
                filt = self.fbank.get_filter(filter_name)
                if filt:
                    filters.append(filt)

            total_count = 0
            for node_id in self.nodes:
                if node_id == self.root_id:
                    continue

                displayed = True
                for filt in filters:
                    displayed = filt.is_displayed(node_id)
                    if not displayed:
                        break
                
                if displayed:
                    total_count += 1

            return total_count
        else:
            # Recompute every node

            # 1st step: build list of filters
            filters = []
            for filter_name in self.applied_filters:
                filt = self.fbank.get_filter(filter_name)
                if not filt:
                    continue

                # Skip transparent filters if needed
                transparent = filt.get_parameters('transparent')
                if not include_transparent and transparent:
                    continue

                filters.append(filt)

            for filter_name in withfilters:
                filt = self.fbank.get_filter(filter_name)
                if filt:
                    filters.append(filt)

            total_count = 0
            for node_id in self.tree.get_all_nodes():
                displayed = True
                for filt in filters:
                    displayed = filt.is_displayed(node_id)
                    if not displayed:
                        break
                
                if displayed:
                    total_count += 1

            return total_count

    def get_node_for_path(self, path):
        if not path or path == ():
            return None

        node_id = self.root_id
        for index in path:
            if 0 <= index < len(self.nodes[node_id]['children']):
                node_id = self.nodes[node_id]['children'][index]
            else:
                return None

        return node_id

    def next_node(self, node_id, parent_id):
        if node_id == self.root_id:
            raise Exception("Calling next_node on the root node")

        if node_id not in self.nodes:
            raise Exception("Node %s is not displayed" % node_id)

        parents = self.nodes[node_id]['parents']
        if not parent_id:
            parent_id = parents[0]
        elif parent_id not in parents:
            raise Exception("Node %s does not have parent %s" % (node_id, parent_id))

        index = self.nodes[parent_id]['children'].index(node_id)
        if index+1 < len(self.nodes[parent_id]['children']):
            return self.nodes[parent_id]['children'][index+1]
        else:
            return None

    def node_all_children(self, node_id=None):
        if node_id is None:
            node_id = self.root_id
        return list(self.nodes[node_id]['children'])

    def node_has_child(self, node_id):
        return len(self.nodes[node_id]['children']) > 0

    def node_n_children(self, node_id):
        return len(self.nodes[node_id]['children'])

    def node_nth_child(self, node_id, n):
        return self.nodes[node_id]['children'][n]

    def node_parents(self, node_id):
        if node_id not in self.nodes:
            raise IndexError('Node %s is not displayed' % node_id)
        parents = list(self.nodes[node_id]['parents'])
        if self.root_id in parents:
            parents.remove(self.root_id)
        return parents

    def get_current_state(self):
        """ Allows to connect LibLarch widget on fly to FilteredTree
        
        Sends 'added' signal/callback for every nodes that is currently
        in FilteredTree. After that, FilteredTree and TreeModel are
        in the same state
        """
        for node_id in self.nodes[self.root_id]['children']:
            self.send_add_tree(node_id, self.root_id)

#### FILTERS ##################################################################
    def list_applied_filters(self):
        return list(self.applied_filters)

    def apply_filter(self, filter_name, parameters=None, \
                    reset=None, refresh=None):
        """ Apply a new filter to the tree.

        @param filter_name: The name of an registrered filter from filters_bank
        @param parameters: Optional parameters to pass to the filter
        @param reset: Should other filters be removed?
        @param refresh: Should be refereshed the whole tree?
                (performance optimization)
        """
        if reset:
            self.applied_filters = []

        if parameters:
            filt = self.fbank.get_filter(filter_name)
            if filt:
                filt.set_parameters(parameters)
            else:
                raise ValueError("No filter of name %s in the bank" % filter_name)

        if filter_name not in self.applied_filters:
            self.applied_filters.append(filter_name)
            if refresh:
                self.refilter()
            toreturn = True
        else:
            toreturn = False

        return toreturn

    def unapply_filter(self, filter_name, refresh=True):
        """ Removes a filter from the tree.

        @param filter_name: The name of an already added filter to remove
        @param refresh: Should be refereshed the whole tree?
                (performance optimization)
        """
        if filter_name in self.applied_filters:
            self.applied_filters.remove(filter_name)
            if refresh:
                self.refilter()
            return True
        else:
            return False

    def reset_filters(self, refresh=True, transparent_only=False):
        """
        Clears all filters currently set on the tree.  Can't be called on 
        the main tree.
        Remove only transparents filters if transparent_only is True
        """
        if transparent_only:
            for f in list(self.applied_filters):
                filt = self.fbank.get_filter(f)
                if filt:
                    if filt.get_parameters('transparent'):
                        self.applied_filters.remove(f)
                else:
                    print "bank is %s" % self.applied_filters
                    raise IndexError('Applied filter %s doesnt' %f +\
                                    'exist anymore in the bank')
        else:
            self.applied_filters = []
        if refresh:
            self.refilter()
