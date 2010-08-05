# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things Gnome! - a personal organizer for the GNOME desktop
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
import functools

from GTG.tools.liblarch.tree import MainTree
from GTG.tools.liblarch.filteredtree import FilteredTree
from GTG.tools.liblarch.filters_bank import FiltersBank



class Tree():
    '''A thin wrapper to MainTree that adds filtering capabilities.
        It also provides a few methods to operate complex operation on the
        MainTree (e.g, move_node)
    '''


    def __init__(self):
        self.__tree = MainTree()
        self.__fbank = FiltersBank(self.__tree)
        self.mainview = ViewTree(self.__tree,self.__fbank,static=True)

    ###### nodes handling ######
    def get_node(self,nid):
        """
        return the node object defined by the Node id nid.
        raises a ValueError if the node doesn't exist in the tree
        """
        return self.__tree.get_node(nid)
    
    def has_node(self,nid):
        return self.__tree.has_node(nid)

    def add_node(self,node,parent_id=None):
#        node.set_tree(self.__tree)
        self.__tree.add_node(node,parent_id=parent_id)

    def del_node(self,nid):
        return self.__tree.remove_node(nid)

    def refresh_node(self,nid):
        self.__tree.modify_node(nid)
        
    def move_node(self,nid,new_parent_id=None):
        """
        Move the node to a new parent (dismissing all other parents)
        use pid None to move it to the root
        """
        if self.has_node(nid):
            node = self.get_node(nid)
            node.set_parent(new_parent_id)
            toreturn = True
        else:
            toreturn = False
        return toreturn
        
    #if pid is None, nothing is done
    def add_parent(self,nid,new_parent_id=None):
        if self.has_node(nid):
            node = self.get_node(nid)
            toreturn = node.add_parent(new_parent_id)
        else:
            toreturn = False
        return toreturn

    ############ Views ############
    #The main view is the bare tree, without any filters on it.
    def get_main_view(self):
        return self.mainview
        
    def get_viewtree(self,refresh=True):
        vt = ViewTree(self.__tree,self.__fbank,refresh=refresh)
        return vt

    ########### Filters bank ######
    def list_filters(self):
        """ List, by name, all available filters """
        return self.__fbank.list_filters()

    def add_filter(self,filter_name,filter_func,parameters=None):
        """
        Adds a filter to the filter bank 
        @filter_name : name to give to the filter
        @filter_func : the function that will filter the nodes
        @parameters : some default parameters fot that filter
        Return True if the filter was added
        Return False if the filter_name was already in the bank
        """
        return self.__fbank.add_filter(filter_name,filter_func,parameters=parameters)

    def remove_filter(self,filter_name):
        """
        Remove a filter from the bank.
        Only custom filters that were added here can be removed
        Return False if the filter was not removed
        """
        return self.__fbank.remove_filter(filter_name)

################### ViewTree #####################

class ViewTree(gobject.GObject):

    #Those are the three signals you want to catch if displaying
    #a filteredtree. The argument of all signals is the nid of the node
    __gsignal_str = (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (str, ))
    #FIXME: should we unify those signals ? They are conceptually different
    __gsignals__ = {'node-added-inview'   : __gsignal_str,
                    'node-deleted-inview' : __gsignal_str,
                    'node-modified-inview': __gsignal_str,
                    'node-added'   : __gsignal_str,
                    'node-deleted' : __gsignal_str,
                    'node-modified': __gsignal_str,}
                                            
    def __init__(self, maintree, filters_bank, refresh = True, static = False):
        '''A ViewTree is the interface that should be used to display Tree(s).

           @param maintree: a Tree object, cointaining all the nodes
           @param filters_bank: a FiltersBank object. Filters can be added
                                dinamically to that.
           @param refresh: if True, this ViewTree is automatically refreshed
                           after applying a filter.
           @param static: if True, this is the view of the complete maintree.
                           Filters cannot be added to such a view.
        '''
        gobject.GObject.__init__(self)
        self.__maintree = maintree
        self.static = static
        #If we are static, we directly ask the tree. No need of an
        #FilteredTree layer.
        if static:
            self.__ft = maintree
            self.__ft.connect('node-added', \
                        functools.partial(self.__emit, 'node-added'))
            self.__ft.connect('node-deleted', \
                        functools.partial(self.__emit, 'node-deleted'))
            self.__ft.connect('node-modified', \
                        functools.partial(self.__emit, 'node-modified'))
        else:
            self.__ft = FilteredTree(maintree, filters_bank, refresh = refresh)
            self.__ft.connect('node-added-inview', \
                        functools.partial(self.__emit, 'node-added-inview'))
            self.__ft.connect('node-deleted-inview', \
                        functools.partial(self.__emit, 'node-deleted-inview'))
            self.__ft.connect('node-modified-inview', \
                        functools.partial(self.__emit, 'node-modified-inview'))
            
    def __emit(self, signal_name, sender, tid, data = None):
        print "emitting signal %s for node %s from %s" %(signal_name,tid,self)
        self.emit(signal_name, tid)

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

    def get_n_nodes(self,withfilters=[],include_transparent=True):
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
            return self.__ft.get_n_nodes(withfilters=withfilters,\
                                    include_transparent=include_transparent)

    def get_node_for_path(self, path):
        return self.__ft.get_node_for_path(path)

    #If nid is none, return root path
    def get_paths_for_node(self, nid=None):
        return self.__ft.get_paths_for_node(nid)

    #pid is used only if nid has multiple parents.
    #if pid is none, a random parent is used.
    def next_node(self, nid,pid=None):
        return self.__ft.next_node(nid,pid)
        
    def node_has_child(self, nid):
        toreturn = False
        if self.static:
            node = self.__get_static_node(nid)
            toreturn = node.has_child()
        else:
            toreturn = self.__ft.node_has_child(nid)
        return toreturn

    #if nid is None, return the number of nodes at the root
    def node_n_children(self, nid=None):
        return len(self.node_all_children(nid))
        
    def node_all_children(self, nid=None):
        toreturn = []
        if self.static:
            node = self.__get_static_node(nid)
            if node:
                toreturn = node.get_children() 
        else:
            toreturn = self.__ft.node_all_children(nid)
        return toreturn

    def node_nth_child(self, nid, n):
        toreturn = None
        if self.static:
            node = self.__get_static_node(nid)
            if node and node.get_n_children() > n:
                toreturn = node.get_nth_child(n)
            else:
                raise ValueError("node %s has less than %s nodes" %(nid,n))
        else:
            if self.__ft.node_n_children(nid) <= n:
                raise ValueError("viewtree has less than %s nodes" %n)
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
                toreturn = node.get_parents()
        else:
            toreturn = self.__ft.node_parents(nid)
        return toreturn

    def is_displayed(self,nid):
        return self.__ft.is_displayed(nid)

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
        if self.static:
            raise Exception("WARNING: filters cannot be applied" +\
                            "to a static tree\n")
        else:
            self.__ft.apply_filter(filter_name,parameters=parameters,\
                                    reset=reset,refresh=refresh)
        return

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
        return

    def reset_filters(self,refresh=True,transparent_only=False):
        """
        Clears all filters currently set on the tree.
        """
        if self.static:
            raise Exception("WARNING: filters cannot be reset" +\
                            "on a static tree\n")
        else:
             self.__ft.reset_filters(refresh=refresh,\
                                        transparent_only=transparent_only)
        return
