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

#This doesn't work
IDLE_ADD = False
THREAD_PROTECTION = False

import gobject
import functools
import threading

from GTG.tools.liblarch.tree import MainTree
from GTG.tools.liblarch.filteredtree import FilteredTree
from GTG.tools.liblarch.filters_bank import FiltersBank



class Tree():
    '''A thin wrapper to MainTree that adds filtering capabilities.
        It also provides a few methods to operate complex operation on the
        MainTree (e.g, move_node)
    '''


    def __init__(self):
        if THREAD_PROTECTION:
            self.thread = threading.current_thread()
            self.__tree = MainTree(thread=self.thread)
        else:
            self.__tree = MainTree()
        self.__fbank = FiltersBank(self.__tree)
        self.views = {}
        #main is a reserved name for a viewtree. It is the complete viewtree,
        #without anyfilter
        self.views['main'] = ViewTree(self,self.__tree,self.__fbank,static=True)
        if THREAD_PROTECTION:
            self.views['main'].set_thread(self.thread)

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
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not acces add_node from thread %s' %t)
            node.set_thread(self.thread)
        if IDLE_ADD:
            gobject.idle_add(self.__tree.add_node,node,parent_id)
        else:
            self.__tree.add_node(node,parent_id=parent_id)

    def del_node(self,nid,recursive=False):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not acces del_node from thread %s' %t)
        if IDLE_ADD:
            gobject.idle_add(self.__tree.remove_node,nid,recursive)
            return True
        else:
            return self.__tree.remove_node(nid,recursive=recursive)

    def refresh_node(self,nid):
        #FIXME: Transform this thread-protection code in a @decorator or in a
        #function, since it's repeated (invernizzi)
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not refres_node from thread %s' %t)
        if IDLE_ADD:
            gobject.idle_add(self.__tree.modify_node,nid)
        else:
            self.__tree.modify_node(nid)
            
    def refresh_all(self):
        for nid in self.__tree.get_all_nodes():
            self.refresh_node(nid)
        
    def move_node(self,nid,new_parent_id=None):
        """
        Move the node to a new parent (dismissing all other parents)
        use pid None to move it to the root
        """
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not move_node from thread %s' %t)
        if self.has_node(nid):
            node = self.get_node(nid)
            if IDLE_ADD:
                gobject.idle_add(node.set_parent,new_parent_id)
            else:
                node.set_parent(new_parent_id)
            toreturn = True
        else:
            toreturn = False
        return toreturn
        
    #if pid is None, nothing is done
    def add_parent(self,nid,new_parent_id=None):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not add_parent from thread %s' %t)
        if self.has_node(nid):
            node = self.get_node(nid)
            if IDLE_ADD:
                gobject.idle_add(node.add_parent,new_parent_id)
                toreturn = True
            else:
                toreturn = node.add_parent(new_parent_id)
        else:
            toreturn = False
        return toreturn

    ############ Views ############
    #The main view is the bare tree, without any filters on it.
    def get_main_view(self):
        return self.views['main']
        
    def get_viewtree(self,name=None,refresh=True):
        '''This returns a viewtree.
        If name is given and a view of that name already exists,
        that existing view is returned. Else, a view with that name
        is created. If name is None, the view is not remembered.
        If refresh is False, the view is not initialized (meaning that it 
        will probably not reflect the Tree. This is useful as an optimization
        if you plan to apply filter.
        '''
        if name and self.views.has_key(name):
            vt = self.views[name]
        else:
#            print "   -> creating new viewtree %s  - %s" %(name,self.views.keys())
            vt = ViewTree(self,self.__tree,self.__fbank,refresh=refresh)
            if THREAD_PROTECTION:
                vt.set_thread(self.thread)
            if name:
                self.views[name] = vt
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
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not add_filter from thread %s' %t)
        return self.__fbank.add_filter(filter_name,filter_func,parameters=parameters)

    def remove_filter(self,filter_name):
        """
        Remove a filter from the bank.
        Only custom filters that were added here can be removed
        Return False if the filter was not removed
        """
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not remove_filter from thread %s' %t)
        return self.__fbank.remove_filter(filter_name)

################### ViewTree #####################

class ViewTree(gobject.GObject):

    #Those are the three signals you want to catch if displaying
    #a filteredtree. The argument of all signals is the nid of the node
    __gsignal_str = (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (str, ))
    __gsignal_str2 = (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, \
                                                (str,gobject.TYPE_PYOBJECT, ))
    __gsignal_str3 = (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, \
                                                (str,gobject.TYPE_PYOBJECT,\
                                                    gobject.TYPE_PYOBJECT,  ))
    #FIXME: should we unify those signals ? They are conceptually different
    __gsignals__ = {'node-added-inview'   : __gsignal_str2,
                    'node-deleted-inview' : __gsignal_str2,
                    'node-modified-inview': __gsignal_str2,
                    'node-children-reordered': __gsignal_str3,
                    'node-added'   : __gsignal_str,
                    'node-deleted' : __gsignal_str,
                    'node-modified': __gsignal_str,}
                                            
    def __init__(self, maininterface, maintree, filters_bank,\
                                             refresh = True, static = False):
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
        self.maininterface = maininterface
        self.__maintree = maintree
        self.static = static
        self.__cllbcks = {}
        self.thread = None
        #If we are static, we directly ask the tree. No need of an
        #FilteredTree layer
        self.__ft = None
        if static:
            #Needed for the get_n_nodes with filters
#            self.__ft = FilteredTree(maintree, filters_bank, refresh = refresh)
            self.__maintree.register_callback('node-added', \
                        functools.partial(self.__emit, 'node-added'))
            self.__maintree.register_callback('node-deleted', \
                        functools.partial(self.__emit, 'node-deleted'))
            self.__maintree.register_callback('node-modified', \
                        functools.partial(self.__emit, 'node-modified'))
        else:
            self.__ft = FilteredTree(maintree, filters_bank, refresh = refresh)
            self.__ft.set_callback('added', \
                        functools.partial(self.__emit, 'node-added-inview'))
            self.__ft.set_callback('deleted', \
                        functools.partial(self.__emit, 'node-deleted-inview'))
            self.__ft.set_callback('modified', \
                        functools.partial(self.__emit, 'node-modified-inview'))
            self.__ft.set_callback('reordered', \
                        functools.partial(self.__emit, 'node-children-reordered'))
                        
    def set_thread(self,thread):
        self.thread = thread
        
    def get_basetree(self):
        return self.maininterface
            
    def __emit(self, signal_name, tid,path=None,neworder=None):
        for k in self.__cllbcks.get(signal_name,[]):
            f = self.__cllbcks[signal_name][k]
            if neworder:
                f(tid,path,neworder)
            else:
                f(tid,path)
        if signal_name.endswith('-inview'):
            self.emit(signal_name, tid,path)
        elif signal_name.endswith('-reordered'):
            self.emit(signal_name,tid,path,neworder)
        else:
            self.emit(signal_name, tid)
        
    def register_cllbck(self,event,func):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not register_cllbck from thread %s' %t)
        if not self.__cllbcks.has_key(event):
            self.__cllbcks[event] = {}
        dic = self.__cllbcks[event]
        #finding a free key
        k = 0
        while dic.has_key(k):
            k += 1
        #registering
        dic[k] = func
        #returning the key so we can later unregister a callback
        return k

    def deregister_cllbck(self,event,func):
        try:
            del self.__cllbcks[event][func]
        except KeyError:
            pass

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
            raise Exception("You should not get a static node"+\
                            " in a viewtree")
        return toreturn

    def get_root(self):
        return self.__maintree.get_root()

    def print_tree(self,string=None):
        if self.static:
            return self.__maintree.print_tree(string=string)
        else:
            return self.__ft.print_tree(string=string)

    #return a list of nid of displayed nodes
    def get_all_nodes(self):
        if self.static:
            return self.__maintree.get_all_nodes()
        else:
            return self.__ft.get_all_nodes()
        
    def refresh_all(self):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not refresh_all from thread %s' %t)
        self.__maintree.refresh_all()

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
        if not self.__ft:
            print "you cannot get_n_nodes for a static tree"
            self.__ft = FilteredTree(maintree, filters_bank, refresh = refresh)
        return self.__ft.get_n_nodes(withfilters=withfilters,\
                                    include_transparent=include_transparent)

    def get_node_for_path(self, path):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not get_node_for_path from thread %s' %t)
        return self.__ft.get_node_for_path(path)

    #If nid is none, return root path
    def get_paths_for_node(self, nid=None):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not get_paths_for_node from thread %s' %t)
        if self.static:
            return self.__maintree._paths_for_node(nid)
        else:
            return self.__ft.get_paths_for_node(nid)

    #pid is used only if nid has multiple parents.
    #if pid is none, a random parent is used.
    def next_node(self, nid,pid=None):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not next_node from thread %s' %t)
        if self.static:
            return self.__maintree.next_node(nid,pid=pid)
        else:
            return self.__ft.next_node(nid,pid)
        
    def node_has_child(self, nid):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not has_child from thread %s' %t)
        if self.static:
            toreturn = self.__maintree.get_node(nid).has_child()
        else:
            toreturn = self.__ft.node_has_child(nid)
        return toreturn

    #if nid is None, return the number of nodes at the root
    def node_n_children(self, nid=None):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not node_n_children from thread %s' %t)
        return len(self.node_all_children(nid))
        
    def node_all_children(self, nid=None):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not node_all_children from thread %s' %t)
        if self.static:
            toreturn = self.__maintree.get_node(nid).get_children()
        else:
            toreturn = self.__ft.node_all_children(nid)
        return toreturn

    def node_nth_child(self, nid, n):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not node_nth_child from thread %s' %t)
        toreturn = None
        if self.static:
            node = self.__get_static_node(nid)
            if node and node.get_n_children() > n:
                toreturn = node.get_nth_child(n)
            else:
                raise ValueError("node %s has less than %s nodes" %(nid,n))
        else:
            realn = self.__ft.node_n_children(nid)
            if realn <= n:
                raise ValueError("viewtree has %s nodes, no node %s" %(realn,n))
            toreturn = self.__ft.node_nth_child(nid,n)
        return toreturn
        
    def node_has_parent(self,nid):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not node_has_parent from thread %s' %t)
        return len(self.node_parents(nid)) > 0

    def node_parents(self, nid):
        """
        Returns displayed parents of the given node, or [] if there is no 
        parent (such as if the node is a child of the virtual root),
        or if the parent is not displayable.
        Doesn't check wheter node nid is displayed or not. (we only care about
        parents)
        """
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not node_parents from thread %s' %t)
        if self.static:
            toreturn = self.__maintree.get_node(nid).get_parents()
        else:
            toreturn = self.__ft.node_parents(nid)
        return toreturn

    def is_displayed(self,nid):
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not is_displayed from thread %s' %t)
        if self.static:
            return self.__maintree.has_child(nid)
        else:
            return self.__ft.is_displayed(nid)

    ####### Change filters #################
    def list_applied_filters(self):
        return self.__ft.list_applied_filters()
        
    def apply_filter(self,filter_name,parameters=None,\
                     reset=False,refresh=True):
        """
        Applies a new filter to the tree.
        @param filter_name: The name of an already registered filter to apply
        @param parameters: Optional parameters to pass to the filter
        @param reset : optional boolean. Should we remove other filters?
        @param refresh : should we refresh after applying this filter ?
        """
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not apply_filter from thread %s' %t)
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
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not unapply_filter from thread %s' %t)
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
        if THREAD_PROTECTION:
            t = threading.current_thread()
            if t != self.thread:
                raise Exception('! could not reset_filters from thread %s' %t)
        if self.static:
            raise Exception("WARNING: filters cannot be reset" +\
                            "on a static tree\n")
        else:
             self.__ft.reset_filters(refresh=refresh,\
                                        transparent_only=transparent_only)
        return
