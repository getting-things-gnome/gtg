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


# The problem we have is that, sometimes, we don't want to display all tasks.
# We want tasks to be filtered (workview, tags, …)
#
# The expected approach would be to put a gtk.TreeModelFilter above our
# TaskTree. Unfortunatly, this doesn't work because TreeModelFilter hides
# all children of hidden nodes. (unlike what we want)
#
# The solution we have found is to have a fake Tree between Tree and TaskTree
# This fake tree is called FilteredTree and will map path and nodes methods 
# to a result corresponding to the filtered tree.
#
# To be more efficient, a quick way to optimize the FilteredTree is to cache
# all answers in a dictionnary so we don't have to compute the answer 
# all the time. This is not done yet.
#
# Warning : this is very fragile. Calls to any GTK registered view should be
# perfecly in sync with changes in the underlying model.
# We definitely should develop some unit tests for this class.

# Structure of the source :
#
# 1) Standard tree functions mapping (get_node, get_all_nodes, get_all_keys)
# 2) Receiving signal functions ( task-added,task-modified,task-deleted)
# 3) Treemodel helper functions. To make it easy to build a treemodel on top.
# 4) Filtering : is_displayed() and refilter()
# 5) Changing the filters (not for the main FilteredTree)
# 6) Private helpers.

class FilteredTree():

    def __init__(self,req,tree,maintree=False):
        self.is_main = maintree
        self.applied_filters = []
        self.req = req
        self.tree = tree
        #virtual root is the list of root nodes
        #initially, they are the root nodes of the original tree
        self.virtual_root = []
        self.registered_views = []
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
        
    #add here your view if you want to keep informed about changes in the tree
    #the view have to implement the following functions:
    #update_task(tid)
    #add_task(tid)
    #remove_task(tid)
    def register_view(self,treemodel):
        if treemodel not in self.registered_views:
            self.registered_views.append(treemodel)
        
    #### Standard tree functions
    def get_node(self,id):
        return self.tree.get_node(id)
    
    def get_root(self):
        return self.tree.get_root()
        
    def get_all_nodes(self):
        l = self.tree.get_all_nodes()
        for n in l:
            if not self.is_displayed(n):
                l.remove(n)
        return l
        
    def get_all_keys(self):
        k = []
        for n in self.get_all_nodes():
            k.append(n.get_id())
        return k
        
    def get_n_nodes(self):
        return len(self.displayed_nodes)
        
    ### signals functions
    def __task_added(self,sender,tid):
#        print "task added signal"
        node = self.get_node(tid)
        todis = self.__is_displayed(node)
        curdis = self.is_displayed(node)
        if todis and not curdis:
            isroot = self.__is_root(node)
            self.__add_node(node,isroot)
        
    def __task_modified(self,sender,tid):
#        print   "task modified signal for %s" %tid
        node = self.get_node(tid)
        todis = self.__is_displayed(node)
        curdis = self.is_displayed(node)
        if todis:
            isroot = self.__is_root(node)
            #if the task was not displayed previously but now should
            #we add it.
            if not curdis:
                self.__add_node(node,isroot)
            #There doesn't seem to be a need for calling the update_node
            #else:
            #    print "calling update node for %s (root:%s)" %(tid,isroot)
            #    self.__update_node(node,isroot)
        else:
            #if the task was displayed previously but shouldn't be anymore
            #we remove it
            if curdis:
                self.__remove_node(node)
        
    def __task_deleted(self,sender,tid):
#        print "task deleted signal"
        node = self.get_node(tid)
        self.__remove_node(node)
        
    ####TreeModel functions ##############################

    #The path received is only for tasks that are displayed
    #We have to find the good node.
    def get_node_for_path(self, path):
        #We should convert the path to the base.path
        if str(path) == '()':
            print "WE SHOULD RETURN ROOT NODE"
        p0 = path[0]
        if len(self.virtual_root) > p0:
            n1 = self.virtual_root[p0]
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
        if not node or not self.is_displayed(node):
            return None
        #This is the cache so we don't compute it all the time
        elif self.path_for_node_cache.has_key(node):
            return self.path_for_node_cache[node]
        elif node == self.get_root():
            toreturn = ()
        elif node in self.virtual_root:
            ind = self.virtual_root.index(node)
            toreturn = (ind,)
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
            if node in self.virtual_root:
                i = self.virtual_root.index(node) + 1
                if len(self.virtual_root) > i:
                    nextnode = self.virtual_root[i]
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
                        while next_idx < total and not self.is_displayed(nextnode):
                            next_idx += 1
                            nextnode = parent_node.get_nth_child(next_idx)
                else:
                    nextnode = None
            if nextnode:
                id = nextnode.get_id()
            else:
                id = None
#            print "### Nextnode of %s is %s"%(node.get_id(),id)
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
                c = self.get_node(cid)
                if self.is_displayed(c):
                    n+= 1
            toreturn = n
            id = node.get_id()
#        print "on_iter_n_children for node %s : %s" %(id,toreturn)
        return toreturn

    #Done
    def node_nth_child(self, node, n):
        #we return the nth good children !
        if not node:
            if len(self.virtual_root) > n:
                toreturn = self.virtual_root[n]
            else:
                toreturn = None
        else:
            total = node.get_n_children()
            cur = 0
            good = 0
            toreturn = None
            while good <= n and cur < total:
                curn = node.get_nth_child(cur)
                if self.is_displayed(curn):
                    if good == n:
                        toreturn = curn
                    good += 1
                cur += 1
#            print "** %s is the %s th child of %s" %(toreturn.get_id(),n,node.get_id())
        return toreturn

    #Done
    def node_parent(self, node):
        #return None if we are at a Virtual root
#        print "node %s in virtual_root %s" %(node.get_id(),self.virtual_root)
        if node and node in self.virtual_root:
            return None
        elif node and node.has_parent():
            parent_id = node.get_parent()
            parent = self.tree.get_node(parent_id)
            if parent == self.tree.get_root():
                return None
            elif self.is_displayed(parent):
                return parent
            else:
                return None
        else:
            return None


    #### Filtering methods #########
    
    # This is a public method that return True if the task is
    # currently displayed in the tree
    def is_displayed(self,node):
        if node:
            tid = node.get_id()
            return tid in self.displayed_nodes
        else:
            toreturn = False
        return toreturn
    
    # This is a private method that return True if the task *should*
    # be displayed in the tree, regardless of its current status
    def __is_displayed(self,node):
        if node:
            #If we are the main tree, we take the main filters from the bank
            if self.is_main:
                return self.req.is_displayed(node)
            else:
                result = True
                for f in self.applied_filters:
                    filt = self.req.get_filter(f)
                    if filt:
                        result = result and filt.is_displayed(node)
                return result
        else:
            return False
        
    # This rebuild the tree from scratch. It should be called only when 
    # The filter is changed. (only filters_bank should call it.
    def refilter(self):
#        print "######### Starting refilter"
        virtual_root2 = []
        to_add = []
        #First things, we list the nodes that will be
        #ultimately displayed
        for n in self.tree.get_all_nodes():
            is_root = False
            if self.__is_displayed(n):
                to_add.append(n)
                is_root = self.__is_root(n)
            #and we care about those who will be virtual roots
            #(their parents are not displayed)
            if is_root and n not in virtual_root2:
                virtual_root2.append(n)
        
        #Second step, we empty the current tree as we will rebuild it
        #from scratch
        for r in list(self.virtual_root):
            self.__clean_from_node(r)
        self.__reset_cache()

        #Here, we reconstruct our filtered trees. It  cannot be random
        # Parents should be added before their children
        #First, we start we the nodes in the virtual root
        for n in list(to_add):
            isroot = n in virtual_root2
            self.__add_node(n,isroot)
#            if isroot:
#                self.__add_node(n,isroot)
#                to_add.remove(n)
#        #Now, we add other nodes. We add a node only if its parent
#        #is already added.
#        pos = 0
#        while len(to_add) > 0:
#            if pos >= len(to_add):
#                print "This should not happen: to_add is not emptied !"
#                pos = 0
#            n = to_add[pos]
#            if self.node_parent(n):
#                self.__add_node(n,False)
#                to_add.remove(n)
#                pos = 0
#            else:
#                pos += 1
        #end of refiltering
        
    ####### Change filters #################
    
    # FIXME : parameters handling,avoid code duplication, check if the filter exists
    def apply_filter(self,filter_name,parameters=None):
        if self.is_main:
            print "Error : use the requester to apply a filter to the main tree"
            print "We don't do that automatically on purpose"
        elif filter_name not in self.applied_filters:
            self.applied_filters.append(filter_name)
    
    def unapply_filter(self,filter_name):
        if self.is_main:
            print "Error : use the requester to remove a filter to the main tree"
            print "We don't do that automatically on purpose"
        elif filter_name in self.applied_filters:
            self.applied_filters.remove(filter_name)
        
    ####### Private methods #################
    
    # Return True if the node should be a virtual root node
    # regardless of the current state
    def __is_root(self,n):
        is_root = True
        if n.has_parent():
            for par in n.get_parents():
                p = self.get_node(par)
                if self.__is_displayed(p):
                    is_root = False
        return is_root
    
    # Put or remove a node from the virtual root
    def __root_update(self,node,inroot):
        if inroot:
            if node not in self.virtual_root:
                self.virtual_root.append(node)
        else:
            if node in self.virtual_root:
                self.virtual_root.remove(node)
    
    def __update_node(self,node,inroot):
        self.__root_update(node,inroot)
        tid = node.get_id()
#        print "### update_node %s (inroot=%s)" %(tid,inroot)
        for r in self.registered_views:
            r.update_task(tid)
    
    def __add_node(self,node,inroot):
        #print "### add_node %s" %node.get_id()
        tid = node.get_id()
        if not self.is_displayed(node):
            #If the parent's node is not already displayed, we wait
            if not inroot and not self.node_parent(node):
                self.node_to_add.append(node)
            else:
                self.__root_update(node,inroot)
                self.displayed_nodes.append(tid)
                for r in self.registered_views:
                    r.add_task(tid)
                #We added a new node so we can check with those waiting
                if len(self.node_to_add) > 0:
                    n = self.node_to_add.pop(0)
                    #node still to add cannot be root
                    self.__add_node(n,False)
    
    def __remove_node(self,node):
        tid = node.get_id()
        for r in self.registered_views:
                removed = r.remove_task(tid)
        self.__root_update(node,False)
        if tid in self.displayed_nodes:
            self.displayed_nodes.remove(tid)
        self.__reset_cache()
        parent = self.node_parent(node)
        if parent:
            inroot = self.__is_root(parent)
            self.__update_node(parent,inroot)
        
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
        self.__remove_node(node)

