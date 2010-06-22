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

import gobject

from GTG.tools.larch.tree import MainTree
from GTG.tools.larch.filteredtree import FilteredTree

class Tree():
    def __init__(self):
        self.__tree = MainTree()
        self.__fbank = FiltersBank(self.__tree)

    ###### nodes handling ######
    def get_node(self,nid):
        return self.__tree.get_node(nid)
    
    def add_node(self,node,parent_id=None):
        node.set_tree(self.__tree)
        self.__tree.add_node(node,parent_id=parent_id)

    def del_node(self,nid):
        return self.__tree.remove_node(nid)

    def modify_node(self,nid):
        print "not implemented"
        return
        
    #move the node to a new parent (dismissing all other parents)
    #use pid None to move it to the root
    def move_node(self,nid,new_parent_id=None):
        print "not implemented"
        return

    #if pid is None, the rood is added but, then, 
    #all other parents are dismissed
    def add_parent(self,nid,new_parent_id=None):
        print "not implemented"
        return

    ############ Views ############
    def get_viewtree(self):
        vt = ViewTree(self.__tree,self.__fbank)
        return vt

    ########### Filters bank ######
    def list_filters(self):
    """ List, by name, all available filters """
    self.__fbank.list_filters()

    def add_filter(self,filter_name,filter_func,parameters=None):
        """
        Adds a filter to the filter bank 
        @filter_name : name to give to the filter
        @filter_func : the function that will filter the nodes
        @parameters : some default parameters fot that filter
        Return True if the filter was added
        Return False if the filter_name was already in the bank
        """
        self.__fbank.add_filter(filter_name,filter_func,parameters=parameters)

    def remove_filter(self,filter_name):
        """
        Remove a filter from the bank.
        Only custom filters that were added here can be removed
        Return False if the filter was not removed
        """
        self.__fbank.remove_filter(filter_name)

################### ViewTree #####################

class ViewTree(gobject.GObject):

    #Those are the three signals you want to catch if displaying
    #a filteredtree. The argument of all signals is the tid of the task
    __gsignals__ = {'task-added-inview': (gobject.SIGNAL_RUN_FIRST, \
                                          gobject.TYPE_NONE, (str, )),
                    'task-deleted-inview': (gobject.SIGNAL_RUN_FIRST, \
                                            gobject.TYPE_NONE, (str, )),
                    'task-modified-inview': (gobject.SIGNAL_RUN_FIRST, \
                                            gobject.TYPE_NONE, (str, )),}
                                            
    def __init(self,maintree,filters_bank):
        self.__maintree = maintree
        self.__ft = FilteredTree(maintree,filters_bank)

#    #only by commodities
#    def get_node(self,nid):
#        return self.__maintree.get_node(nid)

    def print_tree(self):
        return self.__ft.print_tree()

    #return a list of nid of displayed nodes
    def get_all_nodes(self):
        return self.__ft.get_all_nodes()

    def get_n_nodes(self,withfilters=[],transparent_filters=True):
        """
        returns quantity of displayed nodes in this tree
        if the withfilters is set, returns the quantity of nodes
        that will be displayed if we apply those filters to the current
        tree. It means that the currently applied filters are also taken into
        account.
        If transparent_filters = False, we only take into account 
        the applied filters that doesn't have the transparent parameters.
        """
        return self.__ft.get_n_nodes(withfilters=withfilters,\
                                    transparent_filters=transparent_filters)

    def get_node_for_path(self, path):
        return self.__ft.get_node_for_path(path)

    def get_paths_for_node(self, nid):

    def next_node(self, nid,pid):

    def node_has_child(self, nid):

    def node_n_children(self, nid):

    def node_nth_child(self, nid, n):

    def node_parents(self, nid):

    def is_displayed(self,nid):

    ####### Change filters #################
    def apply_filter(self,filter_name,parameters=None,\
                     reset=False,refresh=True):
        """
        Applies a new filter to the tree.
        @param filter_name: The name of an already registered filter to apply
        @param parameters: Optional parameters to pass to the filter
        @param reset : optional boolean. Should we remove other filters?
        @param refresh : should we refresh after applying this filter ?
        """

    def unapply_filter(self,filter_name,refresh=True):
        """
        Removes a filter from the tree.
        @param filter_name: The name of an already added filter to remove
        """

    def reset_filters(self,refresh=True):
        """
        Clears all filters currently set on the tree.
        """
