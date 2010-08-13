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

from GTG.tools.logger import Log

#PLOUM_DEBUG : COUNT_CACHING seems to be broken : write test to detect it
#Edit dynamically a tag an you will see why it is broken
COUNT_CACHING_ENABLED = True
## if FT doesn't use signals, it might be slower (but easier to debug)
FT_USE_SIGNALS = 0

class FilteredTree():

    def __init__(self,tree,filtersbank,refresh=True):
        """
        Construct a FilteredTree object on top of an existing task tree.
        @param req: The requestor object
        @param tree: The tree to filter from
        @param maintree: Whether this tree is the main tree.  The requester
        must be used to change filters against the main tree.
        """
        self.tree = tree
        #The cached Virtual Root
        self.cache_vr = []
        #The state of the tree
        #each displayed nodes is a key in the dic. The value is another dic
        #that contains the following :
        # 'paths' :  a list of the paths for that node
        # 'children' : the ordered list of childrens of that node 
        # 'parents' : the ordered list of parents 
        # if the value of one is None, it might be dynamically computed TBC
        self.cache_nodes = {}
        self.cllbcks = {}
        
        self.__updating_lock = False
        self.__updating_queue = []
        
        #filters
        #self.__flat should only be used by dynamic functions, not static one
        self.__flat = False
        self.applied_filters = []
        self.fbank = filtersbank
        
        #counting optimisation
        self.counted_nodes = []
        self.count_cache = {}
        
        #an initial refilter is always needed if we don't apply a filter
        #for performance reason, we do it only if refresh = True
        if refresh:
            self.refilter()
        
        
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
        
    #those callbacks are called instead of signals.
    def set_callback(self,event,func):
        self.cllbcks[event] = func
        
    def callback(self,event,tid,paths=None):
        func = self.cllbcks.get(event,None)
        if func:
            if not paths:
                paths = self.get_paths_for_node(tid)
            if not paths or len(paths) <= 0:
                raise Exception('cllbck %s for %s but it has no paths'%(event,tid))
            func(tid,paths)
            
    def get_node(self,id):
        """
        Retrieves the given node
        @param id: The tid of the task node
        @return: Node from the underlying tree
        """
        return self.tree.get_node(id)
        
################## External update functions ###################
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
        self.__updating_queue.append([tid,'update'])
        if not self.__updating_lock and len(self.__updating_queue) > 0:
            self.__updating_lock = True
            self.__execution_loop()

    def external_add_node(self,tid):
        if not tid:
            raise ValueError('cannot add node None')
        self.__updating_queue.append([tid,'add'])
        if not self.__updating_lock and len(self.__updating_queue) > 0:
            self.__updating_lock = True
            self.__execution_loop()
            
    def external_remove_node(self,tid):
        if not tid:
            raise ValueError('cannot remove node None')
        self.__updating_queue.append([tid,'delete'])
        if not self.__updating_lock and len(self.__updating_queue) > 0:
            self.__updating_lock = True
            self.__execution_loop()
            
            
    def __execution_loop(self):
        while len(self.__updating_queue) > 0:
            tid,action = self.__updating_queue.pop(0)
#            print "# # # %s %s popped out" %(tid,action)
#            print "       lis is %s" %self.__updating_queue
            if action == 'update':
                self.__update_node(tid)
            elif action == 'delete':
                self.__delete_node(tid)
            elif action == 'add':
                #we only add if parents are already displayed
#                toadd = False
#                for p in self.__node_parents(tid):
#                    if self.is_displayed(p):
#                        toadd =True
#                if toadd:
                self.__add_node(tid)
            else:
                raise ValueError('%s in not a valid action for the loop') %action
        self.__updating_lock = False
        
################# Static cached Filtered Tree ##################
    # Basically, our we save statically our FT in cache_vr and cache_nodes
    #All external functions get their result from that cache
    #This enforce the external state of the FT being consistent at any time !
    
    def print_tree(self,string=None):
        toprint = "displayed : %s\n" %self.get_all_nodes()
        toprint += "VR is : %s\n" %self.cache_vr
        toprint += "updating_queue is : %s" %self.__updating_queue
        if string:
            string = toprint + "\n"
        else:
            print toprint
        for rid in self.cache_vr:
            self.print_from_node(rid,string=string)
        #alternate implementation using next_node
#        if len(self.virtual_root) > 0:
#            rid = self.virtual_root[0]
#            self.__print_from_node(rid)
#            rid = self.next_node(rid)
#            while rid:
#                self.__print_from_node(rid)
#                rid = self.next_node(rid)

    #This function print the actual tree. Useful for debugging
    def print_from_node(self, nid, level=0,string=None):
        prefix = "->"*level
        paths = self.get_paths_for_node(nid)
        toprint = "%s%s    (%s) " %(prefix,nid,\
                    str(paths))
        if string:
            string += toprint
            string += "\n"
        else:
            print toprint
        level += 1
        is_good = False
        for p in paths:
            if len(p) == level:
                is_good = True
        if not is_good:
            raise Exception('theres no path of level %s' %level +\
                            'for node %s - %s' %(nid,str(paths)))
        if self.node_has_child(nid):
            nn = self.node_n_children(nid)
            n = 0
            while n < nn:
                child_id = self.node_nth_child(nid,n)
                self.print_from_node(child_id,level,string=string)
                n += 1
    
    #Those 3 functions are static except if the cache was not yet used.
    #Could it be a source of bug ?
    def get_paths_for_node(self,tid):
        toreturn = self.cache_nodes[tid]['paths']
        return toreturn
    
    def node_all_children(self,tid):
        if tid:
            toreturn = self.cache_nodes[tid]['children']
        else:
            #We consider the root node.
            toreturn = list(self.cache_vr)
        return toreturn
    
    def node_parents(self,tid):
        toreturn = self.cache_nodes[tid]['parents']
        return toreturn
    
    
    #All the following functions returns a static result based on the state 
    #of cache_vr and cache_nodes. No other information should be required.
    def get_all_nodes(self):
        """
        returns list of all displayed node keys
        """
        return self.cache_nodes.keys()
        
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
        if not include_transparent:
            #Currently, the cache only work for one filter
            if len(withfilters) == 1:
                usecache = True
            zelist = self.counted_nodes
        else:
            zelist = self.get_all_nodes()
        if len(withfilters) > 0:
            key = "".join(withfilters)
            if usecache and self.count_cache.has_key(key):
                toreturn = self.count_cache[key]
#                self.using_cache += 1
#                print "we used cache to return %s for %s" %(toreturn,key)
            else:
                for tid in zelist:
                    result = True
                    for f in withfilters:
                        filt = self.fbank.get_filter(f)
                        if filt:
                            result = result and filt.is_displayed(tid)
                    if result:
                        toreturn += 1
                if COUNT_CACHING_ENABLED and usecache:
                    self.count_cache[key] = toreturn
        else:
            toreturn = len(zelist)
        return toreturn
        
        
    #The path received is only for tasks that are displayed
    #We have to find the good node.
    def get_node_for_path(self, path):
        """
        Returns node for the given path.
        """
        #We should convert the path to the base.path
        if not path or str(path) == '()':
            return None
        p0 = path[0]
        if len(self.cache_vr) > p0:
            n1id = self.cache_vr[p0]
            pa = path[1:]
            toreturn = self.__node_for_path(n1id,pa)
        else:
            toreturn = None
        return toreturn

    def __node_for_path(self,basenode_id,path):
        if len(path) == 0:
            return basenode_id
        elif path[0] < self.node_n_children(basenode_id):
            if len(path) == 1:
                return self.node_nth_child(basenode_id,path[0])
            else:
                node_id = self.node_nth_child(basenode_id,path[0])
                path = path[1:]
                return self.__node_for_path(node_id, path)
        else:
            return None
        
    #pid is used only if nid has multiple parents.
    #if pid is none, a random parent is used.
    def next_node(self, nid,pid=None):
        """
        Returns the next sibling node, or None if there are no other siblings
        """
        #We should take the next good node, not the next base node
        toreturn = None
        if nid in self.cache_vr:
            if pid:
                raise Exception('Asking for next_node of %s'%nid+\
                        'with parent %s but node is in VR'%pid)
            i = self.cache_vr.index(nid) + 1
            if len(self.cache_vr) > i:
                nextnode_id = self.cache_vr[i]
                if self.is_displayed(nextnode_id):
                    toreturn = nextnode_id
        else:
            parents_nodes = self.node_parents(nid)
            if len(parents_nodes) >= 1:
                if pid and pid in parents_nodes:
                    parent_node = pid
                else:
                    parent_node = parents_nodes[0]
                total = self.node_n_children(parent_node)
                c = 0
                next_id = -1
                while c < total and next_id < 0:
                    child_id = self.node_nth_child(parent_node,c)
                    c += 1
                    if child_id == nid:
                        next_id = c
                if next_id >= 0 and next_id < total:
                    toreturn = self.node_nth_child(parent_node,next_id)
            else:
                raise Exception('asking for next_node of %s' %nid +\
                                'which has no parents but is not in VR')
        #check to see if our result is correct
        if toreturn and not self.is_displayed(toreturn):
            toreturn = None
            raise ValueError('next_node %s aims to return %s' %(nid,toreturn)+\
                            'but it is not displayed')
        return toreturn
    
    def node_children(self, parent):
        """
        Returns the first child node of the given parent, or None
        if the parent has no children.
        @param parent: The parent node or None to retrieve the children
        of the virtual root.
        """
        child = self.node_nth_child(parent,0)
        return child
        
    def node_has_child(self, nid):
        """
        Returns true if the given node has any children
        """
        return self.node_n_children(nid)>0
    
    def node_n_children(self,nid):
        return len(self.node_all_children(nid))
        
    def node_nth_child(self, nid, n):
        """
        Retrieves the nth child of the node.
        @param node: The parent node, or None to look at children of the
        virtual_root.
        """
        toreturn = None
        children = self.node_all_children(nid)
        if len(children) > n:
            toreturn = children[n]
        #we return None if n is too big.
#        else:
#            raise Exception('Try to get child nbr %s of %s' %(n,nid) +\
#                            'but it has only %s children' %len(children))
        return toreturn
        
    def is_displayed(self,nid):
        return self.cache_nodes.has_key(nid)
        
    def is_root(self,nid):
        return nid in self.cache_vr
        
####################### End of static state functions #######################

####################### Dynamic functions ###################################

    def __get_paths_for_node(self,tid):
        """
        Return a list of paths for a given node
        Return an empty list if no path for that Node.
        """
        toreturn = []
        if tid:
            node = self.get_node(tid)
            pars = self.__node_parents(tid)
        else:
            return [()]
        #For that node, we should convert the base_path to path
        if not node or not self.__is_displayed(tid):
            print "node %s does not exist or is not displayed : no paths" %nid
            return toreturn
#        elif node == self.get_root():
#            path = ()
#            toreturn.append(path)
#        elif tid in self.virtual_root:
        #FIXME : should not use cache VR in this function !
        elif len(pars) <= 0:
            if tid in self.cache_vr:
                ind = self.cache_vr.index(tid)
                path = (ind,)
                toreturn.append(path)
            else:
                realparents = node.get_parents()
                print "real parents of %s are : %s" %(tid,str(realparents))
                print "displayed_nodes are %s" %self.cache_nodes.keys()
                for p in realparents:
                    print "%s is displayed : %s" %(p,self.is_displayed(p))
                    print "but the truth is : %s" %self.__is_displayed(p)
                raise Exception("%s has no parent but is not in VR" %tid)
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
                    par_paths = self.__get_paths_for_node(par)
                    for par_path in par_paths:
                        path = par_path + (pos,)
                        toreturn.append(path)
            if len(toreturn) == 0:
                #if we are here, it means that we have a ghost task that 
                #is not really displayed but still here, in the tree
                #it happens sometimes when we remove a parent with children
                raise Exception('ghost position for %s' %tid +\
                                "VR : %s " %self.virtual_root)
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
        if tid and self.tree.has_node(tid):
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
            if counting_result and tid not in self.counted_nodes:
                #This is an hard custom optimisation for task counting
                #Normally, we would here reset the cache of counted tasks
                #But this slow down a lot the startup.
                #So, we update manually the cache.
                for k in self.count_cache.keys():
                    f = self.fbank.get_filter(k)
                    if f.is_displayed(tid):
                        self.count_cache[k] += 1
                self.counted_nodes.append(tid)
            elif not counting_result and tid in self.counted_nodes:
                #Removing node is less critical so we just reset the cache.
                self.count_cache = {}
                self.counted_nodes.remove(tid)
        else:
            result = False
        return result
        
#################### Update the static state ################################
        
        
    def __delete_node(self,nid):
#        print "remove node %s" %nid
        # 1. recursively delete all children, left-leaf first
        children = self.node_all_children(nid)
        oldpaths = self.get_paths_for_node(nid)
        i = len(children)
        while i > 0:
            i -= 1
            self.__delete_node(children[i])
        # 2. delete the node itself
        parents = self.node_parents(nid)
        if nid in self.cache_vr:
            #check consistency
            if len(parents) > 0:
                raise Exception('%s has parents % and is in VR'%(nid,parents))
            index = self.cache_vr.index(nid)
            print "removing node %s from the VR" %nid
            print "  -> we should update %s in the VR" %self.cache_vr[index:]
            self.cache_vr.remove(nid)
        else:
            if len(parents) <= 0:
                raise Exception('%s has no parents and is not in VR'%(nid))
            for p in parents:
                p_dic = self.cache_nodes[p]['children']
                index = p_dic.index(nid)
                p_dic.remove(nid)
                #PLOUM_DEBUG: we should update the remaining node, isn't it ?
                print "removing node %s from children of %s" %(nid,p)
                print "  -> we should update %s in children" %p_dic[index:]
        self.cache_nodes.pop(nid)
        # 3. send the signal (it means that the state is valid)
        self.callback('deleted',nid,oldpaths)
        # 4. update next_node  (PLOUM_DEBUG: this is the trickiest point)
        return True
    
    def __add_node(self,nid):
        #we only add node that really need it.
        curdis = self.is_displayed(nid)
        newdis = self.__is_displayed(nid)
        if curdis or not newdis:
            return False
#        print "add node %s" %(nid)
        #1. Add the node
        parents = self.__node_parents(nid)
        dis_parents = []
        for p in parents:
            #Check that at least some parents are displayed
            if self.is_displayed(p):
                dis_parents.append(p)
#        if len(dis_parents) == 0
#            raise Exception('node %s needs at least one displayed parent'%s)
        #1b. we add it as a child for its parents
        if len(dis_parents) > 0:
            for p in dis_parents:
                p_child = self.cache_nodes[p]['children']
                if nid not in p_child:
                    p_child.append(nid)
                else:
                    raise Exception("%s was already in children of parent %s"%(nid,p))
        else:
            if nid in self.cache_vr:
                raise Exception('%s was already in VR'%nid)
            self.cache_vr.append(nid)
         #1a. We create the node
        node_dic = {}
        #The parents have to be updated in order for get paths to work
        newpaths = self.__get_paths_for_node(nid)
        node_dic['paths'] = newpaths
        node_dic['parents'] = dis_parents
        node_dic['children'] = []  # childrens will add themselves afterward
        if self.cache_nodes.has_key(nid):
            raise Exception('%s was already a visible node when added' %nid)
        self.cache_nodes[nid] = node_dic
        #2. send the signal (it means that the state is valid)
        self.callback('added',nid,newpaths)
        #3. Add the children
        children = self.__node_all_children(nid)
        for c in children:
            #maybe the child already exists as a child of another node
            if self.is_displayed(c):
                self.cache_nodes[c]['parents'].append(nid)
                self.cache_nodes[nid]['children'].append(c)
            else:
                self.__add_node(c)
        return True
        
    
    def __update_node(self,nid):
        oldpaths = self.get_paths_for_node(nid).sort()
        newpaths = self.__get_paths_for_node(nid).sort()
        if oldpaths == newpaths:
            self.callback("modified", tid,newpaths)
        else:
            if len(oldpaths) > 0:
                self.__delete_node(nid,oldpaths)
            if len(newpaths) > 0:
                self.__add_node(nid,newpaths)
        return True
            
################# Filters functions #####################################
    
    def refilter(self):
        """
        rebuilds the tree from scratch. It should be called only when 
        the filter is changed (i.e. only filters_bank should call it).
        """
        #If we have only one flat filter, the result is flat
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
        for nid in self.tree.get_all_nodes():
            #only add root nodes (those who don't have parents)
            if self.__is_displayed(nid) and len(self.__node_parents(nid)) == 0:
                self.__add_node(nid)
        #print "*** end of refiltering ****"
        #self.print_tree()

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
            return True
        else:
            return False
    
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
