from __future__ import with_statement
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
#
"""
FilteredTree provides a filtered view (subset) of tasks

FilteredTree
============
The problem we have is that, sometimes, we don't want to display all tasks.
We want tasks to be filtered (workview, tags, …)

The expected approach would be to put a gtk.TreeModelFilter above our
TaskTree. Unfortunately, this doesn't work because TreeModelFilter hides
all children of hidden nodes (not what we want!)

The solution we have found is to insert a fake tree between Tree and
TaskTree.  This fake tree is called FilteredTree and maps path and node
methods to a result corresponding to the filtered tree.

Note that the nodes are not aware that they are in a filtered tree.
Use the FilteredTree methods, not the node methods directly.
If you believe a function would be useful in a filtered tree, don't 
hesitate to make a proposal.

To be more efficient, a quick way to optimize the FilteredTree is to cache
all answers in a dictionary so we don't have to compute the answer 
all the time. This is not done yet.

B{Warning}: this is very fragile. Calls to any GTK registered view should be
perfecly in sync with changes in the underlying model.
We definitely should develop some unit tests for this class.

Structure of the source:

 1. Standard tree functions mapping (get_node, get_all_nodes, get_all_keys)
 2. Receiving signal functions ( task-added,task-modified,task-deleted)
 3. Treemodel helper functions. To make it easy to build a treemodel on top.
 4. Filtering : is_displayed() and refilter()
 5. Changing the filters (not for the main FilteredTree)
 6. Private helpers.

There's one main FilteredTree that you can get through the requester. This
main FilteredTree uses the filters applied throughout the requester. This
allows plugin writers to easily get the current displayed tree (main view).

You can create your own filters on top of this main FilteredTree, or you
can create your own personal FilteredTree custom view and apply your own
filters on top of it without interfering with the main view.  (This is
how the closed tasks pane is currently built.)

For custom views, the plugin writers are able to get their own
FilteredTree and apply on it the filters they want. (this is not finished
yet but in good shape).

An important point to stress is that information needs to be passed from
bottom to top, with no horizontal communication at all between views.

"""
import functools
import threading
import time
from copy import deepcopy

from GTG.tools.logger import Log

#PLOUM_DEBUG : COUNT_CACHING seems to be broken : write test to detect it
DEBUG = True
#Edit dynamically a tag an you will see why it is broken
COUNT_CACHING_ENABLED = True
## if FT doesn't use signals, it might be slower (but easier to debug)
FT_USE_SIGNALS = False

def synchronized(fun):
    def newf(*args,**kw):
        with args[0].state_lock:
            return fun(*args,**kw)
    return newf
    
#    def fwrap(function):
#        def newFunction(*args, **kw):
#            with fun.__self__.state_lock:
#                return function(*args, **kw)
#        return newFunction
#    return fwrap(fun)

class FilteredTree():

    def __init__(self,tree,filtersbank,refresh=True):
        """
        Construct a FilteredTree object on top of an existing task tree.
        @param req: The requestor object
        @param tree: The tree to filter from
        @param maintree: Whether this tree is the main tree.  The requester
        must be used to change filters against the main tree.
        """
        #The filtertree will not return anything if it has not be refreshed
        #at least once.
        self.__initialized = False
        self.tree = tree
        #The cached Virtual Root
        self.cache_vr = []
        self.tmp_vr = []
        #The state of the tree
        #each displayed nodes is a key in the dic. The value is another dic
        #that contains the following :
        # 'children' : the ordered list of childrens of that node 
        # 'parents' : the ordered list of parents 
        # if the value of one is None, it might be dynamically computed TBC
        self.state_id = 0
        self.cache_nodes = {}
        self.tmp_nodes = {}
        self.history = {}
        self.history[self.state_id] = [{},[]]
        #the list of displayed nodes if we only use non transparent filters.
        self.cache_opaque = []
        self.cache_transcount = {}
        self.cllbcks = {}
        
        self.timer = 0
        
        self.__updating_lock = threading.Lock()
        self.state_lock = threading.RLock()
        self.__updating_queue = []
        
        #filters
        #self.__flat should only be used by dynamic functions, not static one
        self.__flat = False
        self.applied_filters = []
        self.fbank = filtersbank
        
        #counting optimisation
        self.counted_nodes = {}
        self.count_cache = {}
        if DEBUG:
            self.trace = '\nDEBUG TRACE for ViewTree %s\n-------------\n\n'%self
        self.profile = {'add':[0,0],'delete':[0,0],'update':[0,0]}
        
        #End of initialisation : we connect the FT to the MainTree
        if FT_USE_SIGNALS:
            self.tree.connect("node-added", self.__task_added)
            self.tree.connect("node-modified", self.__task_modified)
            self.tree.connect("node-deleted", self.__task_deleted)
        else:
            #The None is to fake the signal sender
            self.tree.register_callback("node-added", functools.partial(\
                                                self.__task_added,None))
            self.tree.register_callback("node-modified", functools.partial(\
                                                self.__task_modified,None))
            self.tree.register_callback("node-deleted", functools.partial(\
                                                self.__task_deleted,None))
                                                
        #an initial refilter is always needed if we don't apply a filter
        #for performance reason, we do it only if refresh = True
        self.inrefresh = False
        if refresh:
            self.refilter()
            
    def get_state_id(self):
        return self.state_id
        
    #those callbacks are called instead of signals.
    def set_callback(self,event,func):
        self.cllbcks[event] = func
        
    def callback(self,event,tid,path,neworder=None):
        func = self.cllbcks.get(event,None)
        if func and self.__initialized:
#           The reordered callback might take None as arguments
            if neworder:
                func(tid,path,self.state_id,neworder)
            else:
                func(tid,path,self.state_id)
            
    def get_node(self,id):
        """
        Retrieves the given node
        @param id: The tid of the task node
        @return: Node from the underlying tree
        """
        return self.tree.get_node(id)
        
################## External update functions ###################
# Here, we catch node added/deleted/modified signal from the MainTree.
# With a queue mechanism, we ensure that only one instruction at a time
# is realized.
         ### signals functions
    def __task_added(self,sender,tid):
        todis = self.__is_displayed(tid)
        curdis = self.is_displayed(tid)
        if todis and not curdis:
            self.external_add_node(tid)
        
    def __task_modified(self,sender,tid):
        self.external_update_node(tid)

    def __task_deleted(self,sender,tid):
        self.external_remove_node(tid)

    def external_update_node(self,tid):
        if not tid:
            raise ValueError('cannot update node None')
        if self.__initialized:
            self.__updating_queue.append([tid,'update'])
            if self.__updating_lock.acquire(False) \
                                        and len(self.__updating_queue) > 0:
                self.__execution_loop()

    def external_add_node(self,tid):
        if not tid:
            raise ValueError('cannot add node None')
        if self.__initialized:
            self.__updating_queue.append([tid,'add'])
            if self.__updating_lock.acquire(False)\
                                        and len(self.__updating_queue) > 0:
                self.__execution_loop()
            
    def external_remove_node(self,tid):
        if not tid:
            raise ValueError('cannot remove node None')
        if self.__initialized:
            self.__updating_queue.append([tid,'delete'])
            if self.__updating_lock.acquire(False)\
                                        and len(self.__updating_queue) > 0:
                self.__execution_loop()
            
            
    def __execution_loop(self):
        while len(self.__updating_queue) > 0:
            tid,action = self.__updating_queue.pop(0)
#            print "# # # %s %s popped out (tree %s)" %(tid,action,self.applied_filters)
#            print "       lis is %s" %self.__updating_queue
            prof = self.profile[action]
            prof[0] += 1
            t = time.time()
            if action == 'update':
                if DEBUG:
                    self.trace += " - - External update of %s\n" %tid
                self.__update_node(tid)
            elif action == 'delete':
                if DEBUG:
                    self.trace += " - - External delete of %s\n" %tid
                self.__delete_node(tid)
            elif action == 'add':
                if DEBUG:
                    self.trace += " - - External add of %s\n" %tid
                self.__add_node(tid)
            else:
                raise ValueError('%s in not a valid action for the loop') %action
            prof[1] += time.time() - t
#            self.print_profile()
        self.__updating_lock.release()
        
    def print_profile(self):
        print "*********%s *******" %self
        for act in ['add','delete','update']:
            pr = self.profile[act]
            if pr[0] > 0:
                mean = pr[1] / (pr[0]*1.0)
                print "%s %s in %s s (%s mean)" %(pr[0],act,pr[1],mean)
        print "**************************************"
        
################# Static cached Filtered Tree ##################
    # Basically, our we save statically our FT in cache_vr and cache_nodes
    #All external functions get their result from that cache
    #This enforce the external state of the FT being consistent at any time !
    
    @synchronized
    def print_tree(self,string=False,state_id=None):
        toprint = "displayed : %s\n" %self.get_all_nodes(state_id=state_id)
        toprint += "VR is : %s\n" %self.cache_vr
        toprint += "updating_queue is : %s\n" %self.__updating_queue
        if not string:
            print toprint
        for rid in self.cache_vr:
            toprint += self.print_from_node(rid,string=string,state_id=state_id)
            toprint += '\n'
        return toprint
        #alternate implementation using next_node
#        if len(self.virtual_root) > 0:
#            rid = self.virtual_root[0]
#            self.__print_from_node(rid)
#            rid = self.next_node(rid)
#            while rid:
#                self.__print_from_node(rid)
#                rid = self.next_node(rid)

    #This function print the actual tree. Useful for debugging
    #The function also check the validity of the tree
    @synchronized
    def print_from_node(self, nid, level=0,string=None,state_id=None):
        prefix = "->"*level
        paths = self.get_paths_for_node(nid,state_id=state_id)
        toprint = "%s%s    (%s) " %(prefix,nid,\
                    str(paths))
        if not string:
            print toprint
        level += 1
        is_good = False
        for p in paths:
            if len(p) == level:
                is_good = True
        if not is_good:
            error = 'theres no path of level %s' %level +\
                            'for node %s - %s' %(nid,str(paths))
            if DEBUG:
                error += '\n\nDEBUG TRACE\n\n%s' %self.trace
            raise Exception(error)
        if self.node_has_child(nid,state_id=state_id):
            nn = self.node_n_children(nid,state_id=state_id)
            n = 0
            while n < nn:
                child_id = self.node_nth_child(nid,n,state_id=state_id)
                toprint += '\n'
                toprint += self.print_from_node(child_id,level,string=string,state_id=state_id)
                n += 1
        return toprint
    
    @synchronized
    def get_paths_for_node(self,nid,state_id=None):
        if not state_id:
            state_id = self.state_id
        nodes = self.history[state_id][0]
        vr = self.history[state_id][1]
        error = "Get path for %s\n" %nid
        if not nid:
            return [()]
        toreturn = []
        if nid and self.is_displayed(nid,state_id=state_id):
            pars = nodes[nid]['parents']
            if len(pars) == 0:
                if nid not in vr:
                    error = '%s has no parent and is not in VR\n' %nid
                    error += self.trace
                    raise Exception(error)
                index = vr.index(nid)
                toreturn.append((index,))
            else:
                for p in pars:
                    if not nodes.has_key(p):
                        raise Exception('parent %s is not in nodes %s'%(p,nodes.keys()))
                    if nid not in nodes[p]['children']:
                        error += "%s not in children of %s" %(nid,p)
                        raise Exception(error)
                    index = nodes[p]['children'].index(nid)
                    for pp in self.get_paths_for_node(p,state_id=state_id):
                        mypath = pp + (index,)
                        toreturn.append(mypath)
        return toreturn
    
#    def get_paths_for_node(self,tid):
#        if tid and self.is_displayed(tid):
#            toreturn = self.cache_nodes[tid]['paths']
#        elif not tid:
#            #root
#            toreturn = [()]
#        else:
#            toreturn = []
#        if len(toreturn) > 1:
#            for t in toreturn:
#                if len(t) <= 1:
#                    error = "Cannot return paths %s for %s\n" %(toreturn,tid)
#                    error += "%s is in VR: %s" %(tid,tid in self.cache_vr)
#                    raise Exception(error)
#        return toreturn
    
    @synchronized
    def node_all_children(self,tid,state_id=None):
        if not state_id:
            state_id = self.state_id
        nodes = self.history[state_id][0]
        vr = self.history[state_id][1]
        if tid:
            try:
                toreturn = nodes[tid]['children']
            except KeyError:
                toreturn = []
        else:
            #We consider the root node.
            toreturn = list(vr)
        return toreturn
    
    @synchronized
    def node_parents(self,tid,state_id=None):
        if not state_id:
            state_id = self.state_id
        nodes = self.history[state_id][0]
        error = "node_parents for %s\n" %tid
        if nodes.has_key(tid):
            toreturn = nodes[tid]['parents']
        else:
            error += '%s is not in the cache_nodes %s' %(tid,\
                                        self.get_all_nodes(state_id=state_id))
            raise IndexError(error)
        return toreturn
    
    
    #All the following functions returns a static result based on the state 
    #of cache_vr and cache_nodes. No other information should be required.
    @synchronized
    def get_all_nodes(self,state_id=None):
        """
        returns list of all displayed node keys
        """
        if not state_id:
            state_id = self.state_id
        nodes = self.history[state_id][0]
        return nodes.keys()
    
    @synchronized
    def get_n_nodes(self,withfilters=[],include_transparent=True):
        """
        returns quantity of displayed nodes in this tree
        if the withfilters is set, returns the quantity of nodes
        that will be displayed if we apply those filters to the current
        tree. It means that the currently applied filters are also taken into
        account.
        If include_transparent=False, we only take into account the applied filters
        that doesn't have the transparent parameters.
        """
        toreturn = 0
        usecache = False
        zelist = self.get_all_nodes()
        if not include_transparent:
            #As we don't want transparent filter, we the opaque list
            zelist = self.cache_opaque
            #Currently, the cache only work for one filter
            if len(withfilters) == 1:
                key = withfilters[0]
                if self.cache_transcount.has_key(key):
                    zelist = self.cache_transcount[key]
                    usecache = True
                
        if len(withfilters) > 0:
            key = "".join(withfilters)
            if usecache:
                toreturn = len(zelist)
#                self.using_cache += 1
                print "we used cache to return %s for %s" %(toreturn,key)
            else:
                temp_list = []
                for tid in zelist:
                    result = True
                    for f in withfilters:
                        filt = self.fbank.get_filter(f)
                        #We apply the filters in the arguments, regardless
                        #of their transparency
                        result = result and filt.is_displayed(tid)
#                        print "%s is displayed for filter %s : %s" %(tid,f,result)
                    if result:
                        temp_list.append(tid)
                        toreturn += 1
                if COUNT_CACHING_ENABLED and usecache:
                    self.cache_transcount[key] = temp_list
        else:
            toreturn = len(zelist)
#        print "get_n_nodes with filters %s = %s" %(withfilters,zelist)
#        print self.count_cache, self.counted_nodes
        return toreturn
        
        
    #The path received is only for tasks that are displayed
    #We have to find the good node.
    @synchronized
    def get_node_for_path(self, path,state_id=None):
        """
        Returns node for the given path.
        """
        if not state_id:
            state_id = self.state_id
        vr = self.history[state_id][1]
        #We should convert the path to the base.path
        if not path or str(path) == '()':
            return None
        p0 = path[0]
        if len(vr) > p0:
            n1id = vr[p0]
            pa = path[1:]
            toreturn = self.__node_for_path(n1id,pa,state_id=state_id)
        else:
            toreturn = None
        #If the node doesn't have the computed path, ignore it
        if toreturn and not self.is_displayed(toreturn,state_id=state_id):
            #This case is not acceptable
            error = "Getting node for path %s returns %s\n" %(str(path),toreturn)
            error += "But 3 is not displayed.\n"
            par = self.get_node_for_path(path[:-1],state_id=state_id)
            childrens = self.cache_nodes[par]
            error += "It should not be in childs %s of %s" %(par,childrens)
            raise Exception(error)
        elif toreturn and \
                path not in self.get_paths_for_node(toreturn,state_id=state_id):
            toreturn = None
        return toreturn

    @synchronized
    def __node_for_path(self,basenode_id,path,state_id=None):
        if len(path) == 0:
            return basenode_id
        elif path[0] < self.node_n_children(basenode_id,state_id=state_id):
            if len(path) == 1:
                toreturn = self.node_nth_child(basenode_id,path[0],state_id=state_id)
#                if toreturn and path0 not 
            else:
                node_id = self.node_nth_child(basenode_id,path[0],state_id=state_id)
                path = path[1:]
                toreturn = self.__node_for_path(node_id, path,state_id=state_id)
        else:
            toreturn = None
        return toreturn

    #pid is used only if nid has multiple parents.
    #if pid is none, a random parent is used.
    @synchronized
    def next_node(self, nid,pid=None,state_id=None):
        """
        Returns the next sibling node, or None if there are no other siblings
        """
        if not state_id:
            state_id = self.state_id
        vr = self.history[state_id][1]
        #We should take the next good node, not the next base node
        toreturn = None
        if nid in vr:
            if pid:
                print "next_node %s (par %s, state %s)" %(nid,pid,state_id)
                print "   (the current state is %s)" %self.state_id
                raise Exception('Asking for next_node of %s'%nid+\
                        'with parent %s but node is in VR'%pid)
            i = vr.index(nid) + 1
            if len(vr) > i:
                nextnode_id = vr[i]
                if self.is_displayed(nextnode_id,state_id=state_id):
                    toreturn = nextnode_id
        else:
            parents_nodes = self.node_parents(nid,state_id=state_id)
            if len(parents_nodes) >= 1:
                if pid and pid in parents_nodes:
                    parent_node = pid
                else:
                    parent_node = parents_nodes[0]
                total = self.node_n_children(parent_node,state_id=state_id)
                c = 0
                next_id = -1
                while c < total and next_id < 0:
                    child_id = self.node_nth_child(parent_node,c,state_id=state_id)
                    c += 1
                    if child_id == nid:
                        next_id = c
                if next_id >= 0 and next_id < total:
                    toreturn = self.node_nth_child(parent_node,next_id,state_id=state_id)
            else:
                raise Exception('asking for next_node of %s' %nid +\
                                'which has no parents but is not in VR')
        #check to see if our result is correct
        if toreturn and not self.is_displayed(toreturn,state_id=state_id):
            toreturn = None
            raise ValueError('next_node %s aims to return %s' %(nid,toreturn)+\
                            'but it is not displayed')
        return toreturn
    
    @synchronized
    def node_children(self, parent,state_id=None):
        """
        Returns the first child node of the given parent, or None
        if the parent has no children.
        @param parent: The parent node or None to retrieve the children
        of the virtual root.
        """
        child = self.node_nth_child(parent,0,state_id=state_id)
        return child
        
    @synchronized
    def node_has_child(self, nid,state_id=None):
        """
        Returns true if the given node has any children
        """
        return self.node_n_children(nid,state_id=state_id)>0
    
    @synchronized
    def node_n_children(self,nid,state_id=None):
        return len(self.node_all_children(nid,state_id=state_id))
    
    @synchronized
    def node_nth_child(self, nid, n,state_id=None):
        """
        Retrieves the nth child of the node.
        @param node: The parent node, or None to look at children of the
        virtual_root.
        """
        toreturn = None
        children = self.node_all_children(nid,state_id=state_id)
        if len(children) > n:
            toreturn = children[n]
        #we return None if n is too big.
        return toreturn
    
    @synchronized
    def is_displayed(self,nid,state_id=None):
        if not state_id:
            state_id = self.state_id
        nodes = self.history[state_id][0]
        return nodes.has_key(nid)
    
    @synchronized
    def is_root(self,nid,state_id=None):
        if not state_id:
            state_id = self.state_id
        vr = self.history[state_id][1]
        return nid in vr
        
####################### End of static state functions #######################

####################### Dynamic functions ###################################
# Those functions get their value from the real state of MainTree
# They don't touch the cache at all !
# Well, the get_paths_for_node touch it a bit…

    def __get_paths_for_node(self,tid):
        """
        Return a list of paths for a given node
        Return an empty list if no path for that Node.
        """
        toreturn = []
        if tid:
            node = self.get_node(tid)
            pars = []
            for p in self.__node_parents(tid):
                if self.is_displayed(p):
                    pars.append(p)
        else:
            return [()]
        #For that node, we should convert the base_path to path
        if not node or not self.__is_displayed(tid):
#            print "node %s does not exist or is not displayed : no paths" %tid
            return toreturn
        #FIXME : should not use cache VR in this function !
        elif len(pars) <= 0:
            if tid in self.cache_vr:
                ind = self.cache_vr.index(tid)
            else:
                #tid will be added to the end of cache_vr
                ind = len(self.cache_vr)
            path = (ind,)
            toreturn.append(path)
        #The node is not a virtual root
        else:
            for par in pars:
                #only takes into account the parents already added
                if self.is_displayed(par):
                    pos = -1
                    child = None
                    children = self.__node_all_children(par)
                    max = len(children)
                    while pos < max-1 and tid != child:
                        pos += 1
                        child = children[pos]
#                        if tid != child and not self.is_displayed(child):
#                            raise Exception('Child %s in not displayed'%child)
                    par_paths = self.__get_paths_for_node(par)
                    for par_path in par_paths:
                        path = par_path + (pos,)
                        toreturn.append(path)
                    node = self.get_node(par)
#                    print "children of %s are %s" %(par,children)
            if len(toreturn) == 0:
                #if we are here, it means that we have a ghost task that 
                #is not really displayed but still here, in the tree
                #it happens sometimes when we remove a parent with children
                raise Exception('ghost position for %s (par:%s) ' %(tid,pars) +\
                                "VR : %s " %self.cache_vr)
        #We cannot have a root path if there are other paths
        if len(toreturn) > 1:
            for t in toreturn:
                if len(t) <= 1:
                    error = 'Cannot have path %s for node %s'%(t,tid)
                    error += "bcause paths are %s" %toreturn
                    raise Exception(error)
        if toreturn:
            toreturn.sort()
        return toreturn

    
    def __node_all_children(self,nid):
        toreturn = []
        if not nid:
            #FIXME : maybe we should not use cache_vr
            toreturn = list(self.cache_vr)
        elif not self.__flat:
            node = self.tree.get_node(nid)
            if node:
                for cid in node.get_children():
                    if self.__is_displayed(cid):
                        toreturn.append(cid)
        return toreturn
    
    def __node_parents(self,nid):
        """
        Returns parents of the given node, or [] if there is no 
        parent (such as if the node is a child of the virtual root),
        or if the parent is not displayable.
        """
        if not nid:
            raise ValueError("requested a parent of the root")
        if not self.tree.has_node(nid):
            raise ValueError("requested a parent of a non-existing node %s"%nid)
        #return [] if we are at a Virtual root
        parents_nodes = []
        #we return only parents that are not root and displayed
        if not self.__flat :
            node = self.tree.get_node(nid)
            if node.has_parent():
                for pid in node.get_parents():
                    if self.__is_displayed(pid):
                        parents_nodes.append(pid)
        return parents_nodes

        
    def __is_displayed(self,tid):
        """
        This is a private method that return True if the task *should*
        be displayed in the tree, regardless of its current status
        """
        if tid and self.tree.has_node(tid) and not self.inrefresh:
            result = True
            counting_result = True
            cache_key = ""
            for f in self.applied_filters:
                filt = self.fbank.get_filter(f)
                cache_key += f
                if filt:
                    temp = filt.is_displayed(tid)
                    result = result and temp
                    if not filt.get_parameters('transparent'):
                        counting_result = counting_result and temp
#                print "     counting_result for %s : %s" %(f,counting_result)
            if counting_result:
                if tid not in self.cache_opaque:
                    self.cache_opaque.append(tid)
                for k in self.cache_transcount.keys():
                    f = self.fbank.get_filter(k)
                    if f and f.is_displayed(tid):
                        if f not in self.cache_transcount[k]:
                            self.cache_transcount[k].append(tid)
                    else:
                        if f in self.cache_transcount[k]:
                            self.cache_transcount[k].remove(tid)
                        
            elif not counting_result and tid in self.cache_opaque:
                self.cache_opaque.remove(tid)
                for k in self.cache_transcount.keys():
                    if tid in self.cache_transcount[k]:
                        self.cache_transcount[k].remove(tid)
            
            
            #This could be removed when performances are good
#                #This is an hard custom optimisation for task counting
#                #Normally, we would here reset the cache of counted tasks
#                #But this slow down a lot the startup.
#                #So, we update manually the cache.
#                for k in self.count_cache.keys():
#                    if tid not in self.counted_nodes[k]:
#                        f = self.fbank.get_filter(k)
#                        if f and f.is_displayed(tid):
#                            self.count_cache[k] += 1
#                        self.counted_nodes[k].append(tid)
#                    print "%s is displayed for filter %s : %s" %(tid,k,self.fbank.get_filter(k).is_displayed(tid))
#                    print tid in self.counted_nodes[k]
#            elif not counting_result: #and tid in self.counted_nodes:
#                #Removing node is less critical so we just reset the cache.
#                for k in self.count_cache.keys():
#                    if tid in self.counted_nodes[k]:
#                        self.count_cache[k] -= 1
#                        self.counted_nodes[k].remove(tid)
                        
#            print "__is_displayed %s : %s  - %s " %(tid,result,self.count_cache)
#            print counting_result
        else:
            result = False
        return result
        
#################### Update the static state ################################

    def __commit_state(self,pointless=False):
        self.state_lock.acquire(True)
        if not pointless:
            hist = []
            self.cache_nodes = deepcopy(self.tmp_nodes)
            hist.append(deepcopy(self.tmp_nodes))
            self.cache_vr = list(self.tmp_vr)
            hist.append(list(self.tmp_vr))
            self.history[self.state_id+1] = hist
        else:
            self.history[self.state_id+1] = self.history[self.state_id]
        self.state_id += 1
        self.state_lock.release()
        
    #If pars = None, we consider all the parents (or the node in the VR). 
    # Don't forget that
    # a node can be in Virtual Root only if it doesn't have any parent.
    def __delete_node(self,nid,pars=None):
        timer1 = time.time()
        self.trace += "Deleting node %s with pars %s\n" %(nid,pars)
        childrens = []
        if self.is_displayed(nid):
            complete_delete = True
            if pars:
                for p in pars:
                    self.__make_last_child(nid,p)
                    ppaths = self.get_paths_for_node(p)
                    nindex = self.cache_nodes[p]['children'].index(nid)
                    npaths = []
                    for pp in ppaths:
                        npaths.append(pp + (nindex,))
                    if len(pars) < len(self.cache_nodes[nid]['parents']):
                        complete_delete = False
            else:
                pars = list(self.cache_nodes[nid]['parents'])
                for p in pars:
                    self.__make_last_child(nid,p)
                if len(pars) == 0:
                    self.__make_last_child(nid,None)
                npaths = self.get_paths_for_node(nid)
                
            #We recursively delete children if necessary
            if complete_delete:
                childrens = list(self.cache_nodes[nid]['children'])
                childrens.reverse()
                for c in childrens:
                    self.__delete_node(c,pars=[nid])
                if nid in self.cache_vr:
                    self.tmp_vr.remove(nid)
                self.tmp_nodes.pop(nid)
                
            for p in pars:
                self.tmp_nodes[p]['children'].remove(nid)
                #removing the parents
                if self.tmp_nodes.has_key(nid):
                    self.tmp_nodes[nid]['parents'].remove(p)
            
            pa_count = 0
            pointless = False
            for pa in npaths:
                pa_count += 1
                #FIXME : no multiple signals !
                if len(npaths) > 1:
                    print "***WARNING : we send multiple delete signals for one commit"
                if pa_count > 1:
                    pointless = True
                self.__commit_state(pointless)
                self.callback('deleted',nid,pa)
                
            childrens.reverse()
            for c in childrens:
                self.__add_node(c)
            self.timer += time.time() - timer1
#            print "time spent in delete : %s" %self.timer
            return True
        else:
            return False
    
    def __add_node(self,nid,pars=None):
        #We only add node that should be displayed
        if self.__is_displayed(nid):
#            if not self.is_displayed(nid):
#                clist = self.__node_all_children(nid)
#                vr = list(self.tmp_vr)
#                print "(adding %s) will remove %s" %(nid,clist)
#                for c in clist:
#                    if c in vr:
#                        print "*** deleting %s" %c
#                        self.__delete_node(c)
        
            if not pars:
                pars = self.__node_parents(nid)
            #adding the parents
            for par in pars:
                if not self.is_displayed(par):
                    self.__add_node(par)
        
            #1. We remove the node from the VR if it has parents.
            if len(pars) > 0 and nid in self.tmp_vr:
                self.__delete_node(nid)
            
            already = self.is_displayed(nid)
            #if the node is not yet displayed, remove the children 
            #that are in the VR
#            if not already:
#                for c in self.__node_all_children(nid):
#                    if c in self.tmp_vr:
#                        self.__delete_node(c)
            
            #2. We create the node object (or take the existing one)
            if not already:
                node_dic = {}
                node_dic['parents'] = []
                node_dic['children'] = []
                self.tmp_nodes[nid] = node_dic
            else:
                node_dic = self.tmp_nodes[nid]
        
            #2. We add the node, one path at a time.
            for par in pars:
                parnode = self.tmp_nodes[par]
                if nid not in parnode['children']:
                    parnode['children'].append(nid)
                if par not in node_dic['parents']:
                    node_dic['parents'].append(par)
                parpaths = self.get_paths_for_node(par)
                ind = parnode['children'].index(nid)
                #FIXME : if a parent has multiple paths, we send 
                #multiple signals for one commit_state !
                #that's not good hacker, that's not good.
                if len(parpaths) > 1:
                    print "*** WARNING ***, multiple signals sent for one commit"
                p_count = 0
                pointless = False
                for pp in parpaths:
                    p_count += 1
                    path = pp + (ind,)
                    if p_count > 1 :
                        pointless = True
                    self.__commit_state(pointless)
                    self.callback('added',nid,path)
                
            if len(node_dic['parents']) == 0:
                if nid not in self.tmp_vr:
                    self.tmp_vr.append(nid)
                    ind = self.tmp_vr.index(nid)
                    self.__commit_state()
                    self.callback('added',nid,(ind,))
                    
            #Finally, we add the childrens of that node 
            for child in self.__node_all_children(nid):
                self.__add_node(child,pars=[nid])
            return True
        
        else:
            return False
            
    
    def __update_node(self,nid):
        curdis = self.is_displayed(nid)
        todis = self.__is_displayed(nid)
        error = "\n\n *** updating %s ****\n\n" %nid
        if curdis:
            if todis:
                node_dic = self.cache_nodes[nid]
                new_children = self.__node_all_children(nid)
                error += "Before the update : %s\n" %self.cache_nodes
                #We remove uneeded childrens
                for ch in list(node_dic['children']):
                    if ch not in new_children:
#                        self.trace += " ....removing child %s of %s\n" %(ch,nid)
                        self.__delete_node(ch,pars=[nid])
#                        self.trace += "  ...child is now :%s\n"%self.cache_nodes[ch]
                #We add new childrens that were not there
                for ch in new_children:
                    if ch not in node_dic['children']:
                        self.__add_node(ch,pars=[nid])
                        
                #CACHE_MODIF
                if len(node_dic['parents']) == 0 and nid not in self.cache_vr:
                    self.tmp_vr.append(nid)
                    self.__add_node(nid)
                if len(node_dic['parents']) > 0 and nid in self.cache_vr:
                    cllbcks = self.__remove_from_vr(nid)
                    #FIXME : not multiple signals !
                    self.__commit_state()
                    for c in cllbcks:
                        if len(cllbcks) > 1:
                            raise Exception('No multiple callbacks')
                        self.callback(*c)
                    
                #DEBUG
                error += "before signal : %s\n" %self.cache_nodes
                for p in self.cache_nodes[nid]['parents']:
                    if nid not in self.cache_nodes[p]['children']:
                        error += "%s not in childrens of %s\n" %(nid,p)
                        error += self.trace
                        raise Exception(error)
                for c in self.cache_nodes[nid]['children']:
                    if not self.cache_nodes.has_key(c) or \
                                nid not in self.cache_nodes[c]['parents']:
                        error += "%s not in parents of %s\n" %(nid,c)
                        error += self.trace
                        raise Exception(error)
                    
                for path in self.get_paths_for_node(nid):
#                    print "updating %s for %s" %(nid,str(path))
                    self.__commit_state(pointless=True)
                    self.callback('modified',nid,path)
            else:
                self.__delete_node(nid)
        elif not curdis and todis:
            self.__add_node(nid)
        
    
    #This function remove a node from the VR but
    #doesn't touche the cache_nodes.
    def __remove_from_vr(self,nid):
        index = self.tmp_vr.index(nid)
        tosend = []
        if index != (len(self.cache_vr)-1):
            neworder = range(0,len(self.cache_vr))
            self.tmp_vr.remove(nid)
            neworder.remove(index)
            self.tmp_vr.append(nid)
            neworder.append(index)
            tosend.append(['reordered',None,None,neworder])
        path = (self.tmp_vr.index(nid),)
        tosend.append(['deleted',nid,path])
        self.tmp_vr.remove(nid)
        return tosend
        
    def __make_last_child(self,nid,parent):
        if parent:
            children = self.tmp_nodes[parent]['children']
        else:
            children = self.tmp_vr
        if nid not in children:
            error = "node %s is not in children %s of parent %s\n"%(nid,children,parent)
            error += self.trace
            raise Exception(error)
        index = children.index(nid)
        if index != (len(children)-1):
            neworder = range(0,len(children))
            children.remove(nid)
            neworder.remove(index)
            children.append(nid)
            neworder.append(index)
            if parent:
                for path in self.get_paths_for_node(parent):
                    self.__commit_state()
                    self.callback('reordered',parent,path,neworder)
            else:
                self.__commit_state()
                self.callback('reordered',None,None,neworder)
    
################# Filters functions #####################################
    
    def refilter(self):
        """
        rebuilds the tree from scratch. It should be called only when 
        the filter is changed (i.e. only filters_bank should call it).
        """
        self.inrefresh = True
        self.__initialized = True
        #If we have only one flat filter, the result is flat
#        print " * * *  Start refilter * * *  * %s" %self.applied_filters
        self.__flat = False
        for f in self.applied_filters:
            filt = self.fbank.get_filter(f)
            if filt and not self.__flat:
                self.__flat = filt.is_flat()
        #First step, we empty the current tree as we will rebuild it
        #from scratch
        #we delete them left-leaf first !
        pos = len(self.cache_vr)
        while pos > 0:
            pos -= 1
            self.__delete_node(self.cache_vr[pos])
        #The cache should now be empty
        if len(self.cache_nodes) >0:
            raise Exception('cache_nodes should be empty but %s'%self.cache_nodes)
        if len(self.cache_vr) > 0:
            raise Exception('cache_vr should be empty but %s'%self.cache_vr)
        self.inrefresh = False
        for nid in self.tree.get_all_nodes():
            #only add root nodes (those who don't have parents)
            if self.__is_displayed(nid) and len(self.__node_parents(nid)) == 0:
                self.__add_node(nid)
#        print "*** end of refiltering ****"
#        self.print_tree()

    ####### Change filters #################
    def apply_filter(self,filter_name,parameters=None,\
                     reset=False,refresh=True):
        """
        Applies a new filter to the tree.  Can't be called on the main tree.
        @param filter_name: The name of an already registered filter to apply
        @param parameters: Optional parameters to pass to the filter
        @param reset : optional boolean. Should we remove other filters?
        """
        if reset:
            self.applied_filters = []
        if parameters:
            filt = self.fbank.get_filter(filter_name)
            if filt:
                filt.set_parameters(parameters)
            else:
                raise ValueError("No filter of name %s in the bank") %filter_name
        if filter_name not in self.applied_filters:
            self.applied_filters.append(filter_name)
            if refresh:
                self.refilter()
            toreturn = True
        else:
            toreturn = False
        return toreturn
    
    def unapply_filter(self,filter_name,refresh=True):
        """
        Removes a filter from the tree.  Can't be called on the main tree.
        @param filter_name: The name of an already added filter to remove
        """
        if filter_name in self.applied_filters:
            self.applied_filters.remove(filter_name)
            if refresh:
                self.refilter()
            return True
        else:
            return False

    def reset_filters(self,refresh=True,transparent_only=False):
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
                    print "bank is %s" %self.applied_filters
                    raise IndexError('Applied filter %s doesnt' %f +\
                                    'exist anymore in the bank')
        else:
            self.applied_filters = []
        if refresh:
            self.refilter()
            
    def list_applied_filters(self):
        return list(self.applied_filters)
