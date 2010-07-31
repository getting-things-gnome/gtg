# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2010- Lionel Dricot & Bertrand Rousseau
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
"""Liblarch tree library

Liblarch implements a tree (more precisely, a directed acyclic graph (DAG))
data structure for general use, as well as the concept of tree filters.

A tree filter is a...

The View...

"""
import gobject

from GTG.tools.liblarch.tree import MainTree
from GTG.tools.liblarch.filteredtree import FilteredTree
from GTG.tools.liblarch.filters_bank import FiltersBank


class Tree():
    """The main tree class."""
    # TODO: complete docstring
    def __init__(self):
        # TODO: docstring
        self.__tree = MainTree()
        self.__fbank = FiltersBank()
        self._main_view = ViewTree(self.__tree)

    def add_parent(self, node_id, new_parent_id=None):
        # FIXME: this shorthand only used in the test suite
        return self.get_node(node_id).add_parent(new_parent_id)

    def add_filter(self, filter_name, filter_func, parameters={}):
        """
        Adds a filter to the filter bank 
        @filter_name : name to give to the filter
        @filter_func : the function that will filter the nodes
        @parameters : some default parameters fot that filter
        Return True if the filter was added
        Return False if the filter_name was already in the bank
        """
        return self.__fbank.add_filter(filter_name, filter_func,
          parameters=parameters)

    def add_node(self, node, parent_id=None):
        # TODO: docstring
        self.__tree.add_node(node, parent_id=parent_id)

    def delete_node(self, node_id):
        # TODO: docstring
        return self.__tree.delete_node(node_id)

    def get_node(self, node_id):
        """
        return the node object defined by the Node id nid.
        raises a ValueError if the node doesn't exist in the tree
        """
        return self.__tree.get_node(node_id)

    def get_view(self, main=False, refresh=True):
        """Return a ViewTree on the contents of the current tree.
        
        If *main* is False, a ViewTree is returned that supports filtering.
        Otherwise, the ViewTree is unfiltered.
        
        For a filtered ViewTree, *refresh* determines whether the tree
        contents are automatically updated after any change to the applied
        filters.
        
        """
        if main:
            return self._main_view
        else:
            return ViewTree(self.__tree, self.__fbank, refresh=refresh)

    def list_filters(self):
        """ List, by name, all available filters """
        return self.__fbank.list_filters()

    move_node = lambda self, *args: MainTree.move_node(self.__tree, *args)

    def refresh_node(self, node_id):
        # TODO: docstring
        # TODO: why use 'refresh' and 'modify'?
        self.__tree.modify_node(node_id)

    def remove_filter(self,filter_name):
        """
        Remove a filter from the bank.
        Only custom filters that were added here can be removed
        Return False if the filter was not removed
        """
        return self.__fbank.remove_filter(filter_name)


class FilteredTreeError(Exception):
    """Raised by a ViewTree when inappropriate actions are attempted."""
    pass


class UnfilteredTreeError(Exception):
    """Raised by a ViewTree when inappropriate actions are attempted."""
    pass


class ViewTree(gobject.GObject):
    """Views on the data in a tree.
    
    A
    """
    #Those are the three signals you want to catch if displaying
    #a filteredtree. The argument of all signals is the nid of the node
    __gsignals__ = {
      'node-added-inview': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
        (str,)),
      'node-deleted-inview': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
        (str,)),
      'node-modified-inview': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
        (str,)),
      }

    # these methods can be called on self._tree whether it is a MainTree or
    # a FilteredTree. They are handled by __getattr__()
    _passthrough = [
      'get_node',
      'get_all_nodes',
      'get_node_for_path',
      'get_paths_for_node',
      'get_root',
      'next_node',
      'to_string',
      'to_json',
      ]

    def __init__(self, tree, filters_bank=None, refresh=True):
        gobject.GObject.__init__(self)
        self.filtered = (filters_bank is not None)
        if self.filtered:
            ft = FilteredTree(tree, filters_bank, refresh=refresh)
            ft.connect('node-added-inview', self.__emit, 'add')
            ft.connect('node-deleted-inview', self.__emit, 'del')
            ft.connect('node-modified-inview', self.__emit, 'mod')
            self._tree = ft
        else:
            self._tree = tree

    def apply_filter(self, filter_name, parameters={}, reset=False,
      refresh=True):
        """
        Applies a new filter to the tree.
        @param filter_name: The name of an already registered filter to apply
        @param parameters: Optional parameters to pass to the filter
        @param reset : optional boolean. Should we remove other filters?
        @param refresh : should we refresh after applying this filter ?
        """
        try:
            self._tree.apply_filter(filter_name, parameters=parameters,
              reset=reset, refresh=refresh)
        except AttributeError:
            raise UnfilteredTreeError, 'Cannot apply filters on an unfiltered'\
              ' tree.'

    def __emit(self,sender,tid,data=None):
        if data == 'add':
            self.emit('node-added-inview',tid)
        elif data == 'del':
            self.emit('node-deleted-inview',tid)
        elif data == 'mod':
            self.emit('node-modified-inview',tid)
        else:
            raise ValueError("Wrong signal %s" %data)

    def get_n_nodes(self, withfilters=[], include_transparent=True):
        """
        returns quantity of displayed nodes in this tree
        if the withfilters is set, returns the quantity of nodes
        that will be displayed if we apply those filters to the current
        tree. It means that the currently applied filters are also taken into
        account.
        If include_transparent = False, we only take into account 
        the applied filters that doesn't have the transparent parameters.
        """
        if not self.filtered and len(withfilters):
            raise UnfilteredTreeError, 'Filters cannot be applied to an '\
              'unfiltered tree.'
        elif self.filtered:
            return self._tree.get_n_nodes(withfilters=withfilters,
              include_transparent=include_transparent)
        else:
            return len(self._tree.get_all_nodes())

    def __getattr__(self, name):
        """Easier than writing many wrapper methods."""
        if name in self._passthrough:
            return getattr(self._tree, name)
        else:
            raise AttributeError

    def node_children(self, node_id=None):
        if self.filtered:
            return self._tree.node_children(node_id)
        else:
            return self._tree.get_node(node_id).get_children()

    def node_nth_child(self, node_id, n):
        if self.filtered:
            return self._tree.node_nth_child(node_id, n)
        else:
            return self._tree.get_node(node_id).get_nth_child(n)

    def node_parents(self, node_id):
        """
        Returns displayed parents of the given node, or [] if there is no 
        parent (such as if the node is a child of the virtual root),
        or if the parent is not displayable.
        Doesn't check wheter node nid is displayed or not. (we only care about
        parents)
        """
        if self.filtered:
            return self._tree.node_parents(node_id)
        else:
            result = self._tree.get_node(node_id).get_parents()
            # don't return the ID of the root node
            try:
                result.remove(self._tree.get_root().id)
            except KeyError:
                pass
            return result

    def node_is_displayed(self, node_id):
        if self.filtered:
            return self._tree.node_is_displayed(node_id)
        else:
            raise UnfilteredTreeError

    def reset_filters(self, refresh=True):
        """
        Clears all filters currently set on the tree.
        """
        try:
            self._tree.reset_filters(refresh=refresh)
        except AttributeError:
            raise UnfilteredTreeError, 'Cannot reset filters of an unfiltered'\
              ' tree.'

    def unapply_filter(self, filter_name, refresh=True):
        """
        Removes a filter from the tree.
        @param filter_name: The name of an already added filter to remove
        """
        try:
            self._tree.unapply_filter(filter_name, refresh=refresh)
        except AttributeError:
            raise UnfilteredTreeError, 'Cannot unapply filters from an '\
              'unfiltered tree.'

