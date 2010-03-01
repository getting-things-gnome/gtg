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

The problem we have is that, sometimes, we don't want to display all tasks.
We want tasks to be filtered (workview, tags, …)

The expected approach would be to put a gtk.TreeModelFilter above our
TaskTree. Unfortunatly, this doesn't work because TreeModelFilter hides
all children of hidden nodes. (unlike what we want)

The solution we have found is to have a fake Tree between Tree and TaskTree
This fake tree is called FilteredTree and will map path and nodes methods 
to a result corresponding to the filtered tree.

Don't forget that the node are not aware that they are in a filtered tree
Use the FilteredTree methods, not directly the nodes one.
If you believe a function would be useful in a filtered tree, don't 
hesitate to make a proposition.

To be more efficient, a quick way to optimize the FilteredTree is to cache
all answers in a dictionary so we don't have to compute the answer 
all the time. This is not done yet.

Warning : this is very fragile. Calls to any GTK registered view should be
perfecly in sync with changes in the underlying model.
We definitely should develop some unit tests for this class.

Structure of the source :

 1. Standard tree functions mapping (get_node, get_all_nodes, get_all_keys)
 2. Receiving signal functions ( task-added,task-modified,task-deleted)
 3. Treemodel helper functions. To make it easy to build a treemodel on top.
 4. Filtering : is_displayed() and refilter()
 5. Changing the filters (not for the main FilteredTree)
 6. Private helpers.

"""

import gobject

class FilteredTree(gobject.GObject):

    #Those are the three signals you want to catch if displaying
    #a filteredtree. The argument of all signals is the tid of the task
    __gsignals__ = {'task-added-inview': (gobject.SIGNAL_RUN_FIRST, \
                                          gobject.TYPE_NONE, (str, )),
                    'task-deleted-inview': (gobject.SIGNAL_RUN_FIRST, \
                                            gobject.TYPE_NONE, (str, )),
                    'task-modified-inview': (gobject.SIGNAL_RUN_FIRST, \
                                            gobject.TYPE_NONE, (str, )),}

    def __init__(self,req,tree,maintree=False):
        gobject.GObject.__init__(self)
        self.is_main = maintree
        self.applied_filters = []
        self.req = req
        self.tree = tree
        self.update_count = 0
        self.add_count = 0
        self.remove_count = 0
        #virtual root is the list of root nodes
        #initially, they are the root nodes of the original tree
        self.virtual_root = []
        self.displayed_nodes = []
        #useful for temp storage :
        self.node_to_add = []
        #it looks like an initial refilter is not needed.
        #self.refilter()
        self.__reset_cache()
        #connecting
        self.req.connect("task-added", self.__task_added)
        self.req.connect("task-modified", self.__task_modified)
        self.req.connect("task-deleted", self.__task_deleted)

    def __reset_cache(self):
        self.path_for_node_cache = {}

    #### Standard tree functions
    def get_node(self,id):
        return self.tree.get_node(id)
    
    def get_root(self):
        return self.tree.get_root()
        
    def get_all_keys(self):
        return list(self.displayed_nodes)
        
    def get_all_nodes(self):
        k = []
        for n in self.get_all_nodes():
            k.append(self.get_node(n))
        return k
        
    def get_n_nodes(self):
        return len(self.displayed_nodes)
        
    ### signals functions
    def __task_added(self,sender,tid):
        todis = self.__is_displayed(tid)
        curdis = self.is_displayed(tid)
        if todis and not curdis:
            self.__add_node(tid)
        
    def __task_modified(self,sender,tid):
        todis = self.__is_displayed(tid)
        curdis = self.is_displayed(tid)
        if todis:
            #if the task was not displayed previously but now should
            #we add it.
            if not curdis:
                self.__add_node(tid)
            #There doesn't seem to be a need for calling the update_node
#            else:
#                task = self.get_node(tid)
#                inroot = self.__is_root(task)
#                self.__update_node(tid,inroot)
        else:
            #if the task was displayed previously but shouldn't be anymore
            #we remove it
            if curdis:
                self.__remove_node(tid)
        
    def __task_deleted(self,sender,tid):
        self.__remove_node(tid)
        
    ####TreeModel functions ##############################

    #The path received is only for tasks that are displayed
    #We have to find the good node.
    def get_node_for_path(self, path):
        #We should convert the path to the base.path
        if str(path) == '()':
            print "WE SHOULD RETURN ROOT NODE"
        p0 = path[0]
        if len(self.virtual_root) > p0:
            n1id = self.virtual_root[p0]
            n1 = self.get_node(n1id)
            pa = path[1:]
            toreturn = self.__node_for_path(n1,pa)
        else:
            toreturn = None
        return toreturn

    def __node_for_path(self,basenode,path):
        if len(path) == 0:
            return basenode
        elif path[0] < self.node_n_children(basenode):
            if len(path) == 1:
                return self.node_nth_child(basenode,path[0])
            else:
                node = self.node_nth_child(basenode,path[0])
                path = path[1:]
                return self.__node_for_path(node, path)
        else:
            return None

    def get_path_for_node(self, node):
        #For that node, we should convert the base_path to path
        if not node or not self.is_displayed(node.get_id()):
            return None
        #This is the cache so we don't compute it all the time
        elif self.path_for_node_cache.has_key(node):
            return self.path_for_node_cache[node]
        elif node == self.get_root():
            toreturn = ()
        elif node.get_id() in self.virtual_root:
            ind = self.virtual_root.index(node.get_id())
            toreturn = (ind,)
        #The node is not a virtual root
        else:
            pos = 0
            par = self.node_parent(node)
            max = self.node_n_children(par)
            child = self.node_children(par)
            while pos < max and node != child:
                pos += 1
                child = self.node_nth_child(par,pos)
            par_path = self.get_path_for_node(par)
            if par_path:
                toreturn = par_path + (pos,)
            else:
                print "*** Node %s not in vr and no path for parent" %(node.get_id())
                print "*** please report a bug against FilteredTree"
                toreturn = None
        #print "get_path_for_node %s is %s" %(node.get_id(),str(toreturn))
#        self.path_for_node_cache[node] = toreturn
        return toreturn

    #Done
    def next_node(self, node):
        #print "on_iter_next for node %s" %node
        #We should take the next good node, not the next base node
        if node:
            tid = node.get_id()
            if tid in self.virtual_root:
                i = self.virtual_root.index(tid) + 1
                if len(self.virtual_root) > i:
                    nextnode_id = self.virtual_root[i]
                    nextnode = self.get_node(nextnode_id)
                else:
                    nextnode = None
            else:
                parent_node = self.node_parent(node)
                if parent_node:
                    next_idx = parent_node.get_child_index(node.get_id()) + 1
                    total = parent_node.get_n_children()-1
                    if total < next_idx:
                        nextnode = None
                    else:
                        nextnode = parent_node.get_nth_child(next_idx)
                        while next_idx < total and not self.is_displayed(nextnode.get_id()):
                            next_idx += 1
                            nextnode = parent_node.get_nth_child(next_idx)
                else:
                    nextnode = None
        else:
            nextnode = None
        return nextnode

    #Done
    def node_children(self, parent):
        #print "on_iter_children for parent %s" %parent.get_id()
        #here, we should return only good childrens
        if parent:
            if self.node_has_child(parent):
                 child = self.node_nth_child(parent,0)
            else:
                #The spec says that the child can be None
                child = None
        else:
            child = self.virtual_root[0]
        return child

    #Done
    def node_has_child(self, node):
        #print "on_iter_has_child for node %s" %node
        #we should say "has_good_child"
        if node and self.node_n_children(node)>0:
            return True
        else:
            if not node:
                print "NODE IS NULL, we should maybe return True"
            return False

    #Done
    def node_n_children(self, node):
        #we should return the number of "good" children
        if not node:
            toreturn = len(self.virtual_root)
            id = 'root'
        else:
            n = 0
            for cid in node.get_children():
                if self.is_displayed(cid):
                    n+= 1
            toreturn = n
        return toreturn

    #Done
    def node_nth_child(self, node, n):
        #we return the nth good children !
        if not node:
            if len(self.virtual_root) > n:
                to_id = self.virtual_root[n]
                toreturn = self.get_node(to_id)
            else:
                toreturn = None
        else:
            total = node.get_n_children()
            cur = 0
            good = 0
            toreturn = None
            while good <= n and cur < total:
                curn = node.get_nth_child(cur)
                if curn and self.is_displayed(curn.get_id()):
                    if good == n:
                        toreturn = curn
                    good += 1
                cur += 1
        return toreturn

    #Done
    def node_parent(self, node):
        #return None if we are at a Virtual root
        tid = node.get_id()
        if node and tid in self.virtual_root:
            return None
        elif node and node.has_parent():
            parent_id = node.get_parent()
            parent = self.tree.get_node(parent_id)
            if parent == self.tree.get_root():
                return None
            elif self.is_displayed(parent_id):
                return parent
            else:
                return None
        else:
            return None


    #### Filtering methods #########
    
    # This is a public method that return True if the task is
    # currently displayed in the tree
    def is_displayed(self,tid):
        if tid:
            return tid in self.displayed_nodes
        else:
            toreturn = False
        return toreturn
    
    # This is a private method that return True if the task *should*
    # be displayed in the tree, regardless of its current status
    def __is_displayed(self,tid):
        if tid:
            result = True
            for f in self.applied_filters:
                filt = self.req.get_filter(f)
                if filt:
                    result = result and filt.is_displayed(tid)
            return result
        else:
            return False
        
    # This rebuild the tree from scratch. It should be called only when 
    # The filter is changed. (only filters_bank should call it.
    def refilter(self):
        self.update_count = 0
        self.add_count = 0
        self.remove_count = 0
        virtual_root2 = []
        to_add = []
        #First things, we list the nodes that will be
        #ultimately displayed
        for n in self.tree.get_all_nodes():
            tid = n.get_id()
            is_root = False
            if self.__is_displayed(tid):
                to_add.append(tid)
                is_root = self.__is_root(n)
            #and we care about those who will be virtual roots
            #(their parents are not displayed)
            if is_root and tid not in virtual_root2:
                virtual_root2.append(tid)
        
        #Second step, we empty the current tree as we will rebuild it
        #from scratch
        for rid in list(self.virtual_root):
            n = self.get_node(rid)
            self.__clean_from_node(n)
        self.__reset_cache()

        #Here, we reconstruct our filtered trees. It  cannot be random
        # Parents should be added before their children
        #First, we start we the nodes in the virtual root
        for nid in list(to_add):
            isroot = nid in virtual_root2
            self.__add_node(nid,isroot)
        #end of refiltering

    ####### Change filters #################
    def apply_filter(self,filter_name,parameters=None,imtherequester=False):
        if self.is_main and not imtherequester:
            print "Error : use the requester to apply a filter to the main tree"
            print "We don't do that automatically on purpose"
        else:
            if parameters:
                filt = self.req.get_filter(filter_name)
                if filt:
                    filt.set_parameters(parameters)
            if filter_name not in self.applied_filters:
                self.applied_filters.append(filter_name)
                self.refilter()
                return True
        return False
    
    def unapply_filter(self,filter_name,imtherequester=False):
        if self.is_main and not imtherequester:
            print "Error : use the requester to remove a filter to the main tree"
            print "We don't do that automatically on purpose"
        elif filter_name in self.applied_filters:
            self.applied_filters.remove(filter_name)
            self.refilter()
            return True
        return False

    def reset_filters(self,imtherequester=False):
        if self.is_main and not imtherequester:
            print "Error : use the requester to remove a filter to the main tree"
            print "We don't do that automatically on purpose"
        else:
            self.applied_filters = []
            self.refilter()

    def reset_tag_filters(self,refilter=True,imtherequester=False):
        if self.is_main and not imtherequester:
            print "Error : use the requester to remove a filter to the main tree"
            print "We don't do that automatically on purpose"
        else:
            if "notag" in self.applied_filters:
                self.applied_filters.remove('notag')
            for f in self.applied_filters:
                if f.startswith('@'):
                    self.applied_filters.remove(f)
            if refilter:
                self.refilter()

    ####### Private methods #################

    # Return True if the node should be a virtual root node
    # regardless of the current state
    def __is_root(self,n):
        is_root = True
        if n.has_parent():
            for par in n.get_parents():
                if self.__is_displayed(par):
                    is_root = False
        return is_root
    
    # Put or remove a node from the virtual root
    def __root_update(self,tid,inroot):
        if inroot:
            if tid not in self.virtual_root:
                self.virtual_root.append(tid)
        else:
            if tid in self.virtual_root:
                self.virtual_root.remove(tid)
    
    def __update_node(self,tid,inroot):
        self.update_count += 1
        self.__root_update(tid,inroot)
        self.emit("task-modified-inview", tid)
    
    def __add_node(self,tid,inroot=None):
        self.add_count += 1
        if not self.is_displayed(tid):
            node = self.get_node(tid)
            if inroot == None:
                inroot = self.__is_root(node)
            #If the parent's node is not already displayed, we wait
            if not inroot and not self.node_parent(node):
                self.node_to_add.append(tid)
            else:
                self.__root_update(tid,inroot)
                self.displayed_nodes.append(tid)
                self.emit("task-added-inview", tid)
                #We added a new node so we can check with those waiting
                if len(self.node_to_add) > 0:
                    n = self.node_to_add.pop(0)
                    #node still to add cannot be root
                    self.__add_node(n,False)
    
    def __remove_node(self,tid):
        self.remove_count += 1
        self.emit('task-deleted-inview',tid)
        self.__root_update(tid,False)
        if tid in self.displayed_nodes:
            self.displayed_nodes.remove(tid)
        self.__reset_cache()
        #Test if this is necessary
        parent = self.node_parent(self.get_node(tid))
        if parent:
            inroot = self.__is_root(parent)
            self.__update_node(parent.get_id(),inroot)
        
    #This function print the actual tree. Useful for debugging
    def __print_from_node(self, node, prefix=""):
        print prefix + node.get_id()
        prefix = prefix + "->"
        if self.node_has_child(node):
            child = self.node_children(node)
            while child:
                self._print_from_node(child,prefix)
                child = self.next_node(child)
    
    #This function removes all the nodes, leaves first.
    def __clean_from_node(self, node):
        if self.node_has_child(node):
            child = self.node_children(node)
            while child:
                self.__clean_from_node(child)
                child = self.next_node(child)
        self.__remove_node(node.get_id())
