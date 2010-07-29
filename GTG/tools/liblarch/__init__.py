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
        self.mainview = ViewTree(self.__tree, self.__fbank, static=True)

    ###### nodes handling ######
    def get_node(self, node_id):
        """
        return the node object defined by the Node id nid.
        raises a ValueError if the node doesn't exist in the tree
        """
        return self.__tree.get_node(node_id)

    def has_node(self, node_id):
        # TODO: docstring
        return self.__tree.has_node(node_id)

    def add_node(self, node, parent_id=None):
        # TODO: docstring
        self.__tree.add_node(node, parent_id=parent_id)

    def del_node(self, node_id):
        # TODO: docstring
        return self.__tree.remove_node(node_id)

    def refresh_node(self, node_id):
        # TODO: docstring
        # TODO: why use 'refresh' and 'modify'?
        self.__tree.modify_node(node_id)

    # TODO: this probably gives the wrong value for 'self' in move_node
    move_node = lambda self, *args: MainTree.move_node(self.__tree, *args)
    print_tree = lambda self: MainTree.print_tree(self.__tree)

    #if pid is None, nothing is done
    def add_parent(self, node_id, new_parent_id=None):
        # TODO: eliminate this shorthand
        return self.get_node(node_id).add_parent(new_parent_id)

    ############ Views ############
    #The main view is the bare tree, without any filters on it.
    def get_main_view(self):
        return self.mainview

    def get_viewtree(self,refresh=True):
        vt = ViewTree(self.__tree, self.__fbank, refresh=refresh)
        return vt

    ########### Filters bank ######
    def list_filters(self):
        """ List, by name, all available filters """
        return self.__fbank.list_filters()

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

    def remove_filter(self,filter_name):
        """
        Remove a filter from the bank.
        Only custom filters that were added here can be removed
        Return False if the filter was not removed
        """
        return self.__fbank.remove_filter(filter_name)


class ViewTree(gobject.GObject):
    #Those are the three signals you want to catch if displaying
    #a filteredtree. The argument of all signals is the nid of the node
    __gsignals__ = {'node-added-inview': (gobject.SIGNAL_RUN_FIRST, \
                                          gobject.TYPE_NONE, (str, )),
                    'node-deleted-inview': (gobject.SIGNAL_RUN_FIRST, \
                                            gobject.TYPE_NONE, (str, )),
                    'node-modified-inview': (gobject.SIGNAL_RUN_FIRST, \
                                            gobject.TYPE_NONE, (str, )),}

    def __init__(self, maintree, filters_bank, refresh=True, static=False):
        gobject.GObject.__init__(self)
        self.__maintree = maintree
        self.static = static
        #If we are static, we directly ask the tree. No need of an
        #FilteredTree layer.
        if static:
            self.__ft = maintree
        else:
            self.__ft = FilteredTree(maintree, filters_bank, refresh=refresh)
            self.__ft.connect('node-added-inview', self.__emit, 'add')
            self.__ft.connect('node-deleted-inview', self.__emit, 'del')
            self.__ft.connect('node-modified-inview', self.__emit, 'mod')

    def __emit(self,sender,tid,data=None):
        if data == 'add':
            self.emit('node-added-inview',tid)
        elif data == 'del':
            self.emit('node-deleted-inview',tid)
        elif data == 'mod':
            self.emit('node-modified-inview',tid)
        else:
            raise ValueError("Wrong signal %s" %data)

    #only by commodities
    def get_node(self,nid):
        return self.__maintree.get_node(nid)

    def __get_static_node(self,nid):
        toreturn = None
        if self.static:
            if not nid or nid == 'root':
                toreturn = self.__maintree.get_root()
            else:
                toreturn = self.__maintree.get_node(nid)
        else:
            raise Exception("Bad programmer: should not get a static node"+\
                            " in a viewtree")
        return toreturn

    def print_tree(self):
        return self.__ft.print_tree()

    #return a list of nid of displayed nodes
    def get_all_nodes(self):
        return self.__ft.get_all_nodes()

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
        if self.static and len(withfilters) > 0:
            raise Exception("WARNING: filters cannot be applied" +\
                            "to a static tree\n"+\
                     "the filter parameter of get_n_nodes will be dismissed")
        if self.static:
            return len(self.__maintree.get_all_nodes())
        else:
            return self.__ft.get_n_nodes(withfilters=withfilters,
              include_transparent=include_transparent)

    def get_node_for_path(self, path):
        return self.__ft.get_node_for_path(path)

    #If nid is none, return root path
    def get_paths_for_node(self, node_id=None):
        return self.__ft.get_paths_for_node(node_id)

    #pid is used only if nid has multiple parents.
    #if pid is none, a random parent is used.
    def next_node(self, node_id, parent_id=None):
        return self.__ft.next_node(node_id, parent_id)

    def node_has_child(self, node_id):
        toreturn = False
        if self.static:
            node = self.__get_static_node(node_id)
            toreturn = len(node._children) != 0
        else:
            toreturn = self.__ft.node_has_child(node_id)
        return toreturn

    #if nid is None, return the number of nodes at the root
    def node_n_children(self, nid=None):
        return len(self.node_all_children(nid))

    def node_all_children(self, node_id=None):
        toreturn = []
        if self.static:
            node = self.__get_static_node(node_id)
            if node:
                toreturn = node._children
        else:
            toreturn = self.__ft.node_children(node_id)
        return toreturn

    def node_nth_child(self, nid, n):
        toreturn = None
        if self.static:
            node = self.__get_static_node(nid)
            if node:
                toreturn = node.get_nth_child(n)
        else:
            toreturn = self.__ft.node_nth_child(nid,n)
        return toreturn

    def node_has_parent(self,nid):
        return len(self.node_parents(nid)) > 0

    def node_parents(self, nid):
        """
        Returns displayed parents of the given node, or [] if there is no 
        parent (such as if the node is a child of the virtual root),
        or if the parent is not displayable.
        Doesn't check wheter node nid is displayed or not. (we only care about
        parents)
        """
        toreturn = []
        if self.static:
            node = self.__get_static_node(nid)
            if node:
                toreturn = node._parents
            # don't return the ID of the root node
            try:
                toreturn.remove(self.__maintree.root.id)
            except KeyError:
                pass
        else:
            toreturn = self.__ft.node_parents(nid)
        return toreturn

    def is_displayed(self,nid):
        return self.__ft.is_displayed(nid)

    ####### Change filters #################
    def apply_filter(self, filter_name, parameters={}, reset=False,
      refresh=True):
        """
        Applies a new filter to the tree.
        @param filter_name: The name of an already registered filter to apply
        @param parameters: Optional parameters to pass to the filter
        @param reset : optional boolean. Should we remove other filters?
        @param refresh : should we refresh after applying this filter ?
        """
        if self.static:
            raise Exception("WARNING: filters cannot be applied" +\
                            "to a static tree\n")
        else:
            self.__ft.apply_filter(filter_name, parameters=parameters,
              reset=reset, refresh=refresh)

    def unapply_filter(self,filter_name,refresh=True):
        """
        Removes a filter from the tree.
        @param filter_name: The name of an already added filter to remove
        """
        if self.static:
            raise Exception("WARNING: filters cannot be unapplied" +\
                            "from a static tree\n")
        else:
            self.__ft.unapply_filter(filter_name, refresh=refresh)

    def reset_filters(self,refresh=True):
        """
        Clears all filters currently set on the tree.
        """
        if self.static:
            raise Exception("WARNING: filters cannot be reset" +\
                            "on a static tree\n")
        else:
             self.__ft.reset_filters(refresh=refresh)

