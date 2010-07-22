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
import gobject

# only uncomment this for debugging purposes
# from GTG.tools.logger import Log


class MainTree(gobject.GObject):
    """A tree of nodes."""
    # GObject signals to be emitted on node operations. The single argument of
    # each method is the ID of the node that was added, deleted or modified.
    __gsignals__ = {'node-added': (gobject.SIGNAL_RUN_FIRST, \
                                    gobject.TYPE_NONE, (str, )),
                    'node-deleted': (gobject.SIGNAL_RUN_FIRST, \
                                    gobject.TYPE_NONE, (str, )),
                    'node-modified': (gobject.SIGNAL_RUN_FIRST, \
                                    gobject.TYPE_NONE, (str, ))}

    def __init__(self, root=None):
        """Initialize a new tree.
        
        If *root* is given, it must be a TreeNode or subclass, and becomes the
        root node of the tree.
        
        """
        gobject.GObject.__init__(self)
        self.root_id = 'root'
        self.nodes = {}
        self.old_paths = {}
        self.pending_relationships = []
        if root:
            self.root = root
        else:
            self.root = RootNode()
        self.root.set_tree(self)

    def modify_node(self, nid):
        """Emit the node-modified signal."""
        self.__modified(nid)
        
    def __modified(self, nid):
        """Emit the node-modified signal."""
        if nid != 'root' and nid in self.nodes:
            self.emit("node-modified", nid)

    def __str__(self):
        """String representation."""
        return "<Tree: root = '%s'>" % (str(self.root))

    def get_node_for_path(self, path):
        """Return the ID of a node for a given *path*."""
        return self._node_for_path(None, path)

    def get_paths_for_node(self, node_id):
        """Return all unique paths to the node *node_id*."""
        return self._paths_for_node(node_id)

    def get_deleted_path(self,id):
        """Return a deleted path to the node *node_id*.
        
        A deleted path can only be requested once.
        
        """
        toreturn = None
        # TODO: don't print to the console
        print "old paths are : %s" % self.old_paths
        if self.old_paths.has_key(node_id):
            return self.old_paths.pop(node_id)

    def get_root(self):
        """Return the root node."""
        return self.root

    def set_root(self, root):
        """Set the root node."""
        self.root = root
        self.root.set_tree(self)

    def add_node(self, node, parent_id=None):
        """Add a node to the tree.
        
        If *parent_id* is given, then *node* becomes a child of the node
        with that ID. Otherwise, *node* is a child of the root node.
        
        """
        id = node.get_id()
        if self.nodes.has_key(id):
            # TODO: don't print to the console
            print "Error : A node with this id %s already exists" %id
            return False
        else:
            #We add the node
            node.set_tree(self)
            if parent_id:
                parent = self.get_node(parent_id)
                node.set_parent(parent.id)
                parent.add_child(id)
            else:
                self.root.add_child(id)
            self.nodes[id] = node
            # build the relationships that were waiting for that node
            for rel in list(self.pending_relationships):
                if id in rel:
                    self.new_relationship(rel[0],rel[1])
            self.emit("node-added", id)
            return True

    def remove_node(self, node_id, recursive=False):
        """Remove a node with ID *node_id* from the tree.
        
        If the node has any children, and *recursive* is false, they are made
        children of the root node. Otherwise all children of the node are
        also removed.
        
        If the node does not exist, nothing happens.
        
        """
        node = self.get_node(node_id)
        if not node:
            return
        if node.has_child():
            for child_id in node.get_children():
                if recursive:
                    self.remove_node(child_id, recursive=True)
                else:
                    self.break_relationship(node_id, child_id)
        if node.has_parent():
            for parent_id in node.get_parents():
                par = self.get_node(parent_id)
                par.remove_child(node_id)
        else:
            self.root.remove_child(node_id)
        self.emit("node-deleted", node_id)
        del self.nodes[node_id]

    def new_relationship(self, parent_id, child_id):
        """Create a new relationship between nodes.
        
        The node with ID *parent_id* is a parent of the node with ID *child_id*.
        If the relationship already exists, return False.
        
        """
        def genealogic_search(node_id):
            """Recursively build a list of every ancestor of a node.
            
            The result is stored in the variable genealogy.
            """
            if node_id not in genealogy:
                genealogy.append(node_id)
                if self.has_node(node_id):
                    node = self.get_node(node_id)
                    for parent_id in node.get_parents():
                        genealogic_search(parent_id)

#        Log.debug("new relationship between %s and %s" %(parent_id,child_id))
        if (parent_id, child_id) in self.pending_relationships:
            self.pending_relationships.remove((parent_id, child_id))
        success = False
        # no relationship allowed with yourself
        if parent_id == child_id:
            # TODO: throw an exception here?
            return False
        if parent_id == 0:
#            Log.debug("    -> adding %s to the root" %child_id)
            p = self.get_root()
        else:
            if self.has_node(parent_id):
                p = self.get_node(parent_id)
            else:
                p = None
        if p and self.has_node(child_id):
            c = self.get_node(child_id)
            # avoid the typical time-traveller problem (being-the-father-of-
            # yourself or the grand-father. We need some genealogic research!
            genealogy = []
            genealogic_search(parent_id)
            if child_id not in genealogy:
                if not p.has_child(child_id):
                    p.add_child(child_id)
                    success = True
                if parent_id != 'root' and not c.has_parent(parent_id):
                    c.add_parent(parent_id)
                    success = True
                # remove the root from the list of parent
                if success and parent_id != 'root' and \
                                            self.root.has_child(child_id):
                    self.root.remove_child(child_id)
#                if not success:
#                    Log.debug("  * * * * * Relationship already existing")
            else:
                # a circular relationship was found
#                Log.debug("  * * * * * Circular relationship found : undo")
                self.break_relationship(parent_id, child_id)
                raise Exception('Cannot build circular relationship bewteen'
                  'nodes %s and %s' % (parent_id, child_id))
        else:
            # at least one of the nodes is not in the tree. Save the relation
            # for later
            if (parent_id, child_id) not in self.pending_relationships:
                self.pending_relationships.append((parent_id, child_id))
            self.break_relationship(parent_id, child_id)
            # this is considered successful
            success = True
        if success:
            # emit signals
            self.__modified(parent_id)
            self.__modified(child_id)
        return success

    def break_relationship(self, parent_id, child_id):
        """Break an existing relationship.
        
        If the node *child_id* has only one parent (*parent_id*), then it is
        made a child of the root node. If the relationship did not exist,
        return False; otherwise return True.
        
        """
        success = False
        if self.has_node(parent_id) and self.has_node(child_id):
            p = self.get_node(parent_id)
            c = self.get_node(child_id)
            if p.has_child(child_id):
                p.remove_child(child_id)
                success = True
            if c.has_parent(parent_id):
                c.remove_parent(parent_id)
                success = True
                # if no more parents left, add to the root
                if not c.has_parent():
                    self.root.add_child(child_id)
        if success:
            # emit signals
            self.__modified(parent_id)
            self.__modified(child_id)
        return success

    def get_node(self, node_id=None):
        """Return the node with ID *node_id*.
        
        If *node_id* is None or the string 'root', return the root node.
        
        """
        if node_id in self.nodes:
            return self.nodes[node_id]
        elif node_id == 'root' or node_id == None:
            return self.root
        else:
            raise ValueError("Node %s is not in the tree. Wrong get_node()"
              % node_id)

    def get_all_nodes(self):
        """Return the IDs of all nodes in the tree."""
        return self.nodes.keys()

    def next_node(self, node_id, parent_id=None):
        """Return the next sibling of a node *node_id*.
        
        If there is no such sibling, return None. If the node has multiple
        parents, the siblings under parent *parent_id* will be returned.
        If *parent_id* is None in this case, a random parent is used.
        
        """
        # get the parents of node_id
        node = self.get_node(node_id)
        parent_ids = node.get_parents()
        # choose the appropriate parent
        if parent_id not in parent_ids:
            parent_id = parent_ids[0]
        parent = self.get_node(parent_id)
        # find the index of node_id under the parent
        index = parent.get_child_index(node_id)
        if len(parent.children) > index+1:
            return parent.get_nth_child(index+1)

    def is_displayed(self, node_id):
        """Alias for has_node()."""
        return self.has_node(node_id)

    def has_node(self, node_id):
        """Return True if the node with ID *node_id* is in the tree."""
        return node_id in self.nodes

    def print_tree(self):
        """Print a representation of the tree to stdout."""
        self._print_from_node(self.root)

    def visit_tree(self, pre_func=None, post_func=None):
        # TODO: docstring
        if self.root.has_child():
            for c in self.root.get_children():
                node = self.root.get_child(c)
                self._visit_node(node, pre_func, post_func)

### HELPER FUNCTION FOR TREE #################################################
#
    def _node_for_path(self, node_id, path):
        if node_id:
            node = self.get_node(node_id)
        else:
            node = self.root
        if node and path[0] < len(node.children):
            if len(path) == 1:
                return node.get_nth_child(path[0])
            else:
                node_id = node.get_nth_child(path[0])
                path = path[1:]
                return self._node_for_path(node_id, path)
        else:
            return None

    def _paths_for_node(self, nid=None):
        toreturn = []
        if nid:
            node = self.get_node(nid)
        else:
            node = self.root
        if node: 
            if node == self.root:
                toreturn = [()]
            elif not node.has_parent():
                index  = self.root.get_child_index(nid)
                toad = (index, )
                toreturn.append(toad)
            else:
                parents_id = node.get_parents()
                for pid in parents_id:
                    parent = self.get_node(pid)
                    if parent:
                        index  = parent.get_child_index(nid)
                        for p in self._paths_for_node(pid):
                            toreturn.append(p+(index,))
                else:
                    toreturn = [()]
        else:
            raise ValueError("Cannot get path for non existing node %s" %nid)
        return toreturn

    def _print_from_node(self, node, prefix=""):
        print prefix + node.id
        prefix = prefix + " "
        if node.has_child():
            for c in node.get_children():
                cur_node = node.get_child(c)
                self._print_from_node(cur_node, prefix)

    def _visit_node(self, node, pre_func=None, post_func=None):
        if pre_func:
            pre_func(node)
        if node.has_child():
            for c in node.get_children():
                cur_node = node.get_child(c)
                self._visit_node(cur_node, pre_func, post_func)
        if post_func:
            post_func(node)


class TreeNode(object):
    """A node in a Tree.
    
    Objects to be stored in tree should subclass TreeNode. TreeNode.__init__()
    MUST be called from any __init__ method of a subclass.
    
    TreeNodes are identified by IDs, which MUST be unique. Python's built-in
    id() function is used by default. However, by overriding the method
    _get_id(), subclasses can use any other scheme of IDs.
    
    """
    # new-style property for the ID. It is read-only.
    id = property(lambda self: self._get_id())

    def __init__(self, parent=None):
        """Initialize a new node."""
        self.parents = []
        self.children = []
        self.tree = None
        self.pending_relationship = []
        if parent:
            self.add_parent(parent)

    def __str__(self):
        """String representation."""
        return "<TreeNode: '%s'>" % (self.id)

    def modified(self):
        # TODO: docstring. What does this do?
        if self.tree:
            self.tree.modify_node(self.id)

    def set_tree(self, tree):
        """Affiliate the TreeNode with a Tree."""
        self.tree = tree
        for rel in list(self.pending_relationship):
            self.tree.new_relationship(rel[0], rel[1])
            self.pending_relationship.remove(rel)

    def get_tree(self):
        """Return a reference to the Tree containing this node."""
        return self.tree

    def _get_id(self):
        """Generate or return an ID for this node."""
        return id(self)

    def new_relationship(self, par, chi):
        """Create a new relationship."""
        if self.tree:
            return self.tree.new_relationship(par, chi)
        else:
            self.pending_relationship.append([par, chi])
            # it's pending, we return False
#            Log.debug("** There's still no tree, relationship is pending")
            return False

#### Parents
    def has_parent(self, parent_id=None):
        """Return True if the node has a parent.
        
        If *parent_id* is not None, return True if that node is a parent of
        this node.
        
        """
        if id:
            return id in self.parents
        else:
            return len(self.parents) > 0

    def get_parents(self):
        """Return a list of ids for parents of this node."""
        return self.parents

    def add_parent(self, parent_id):
        """Add the node with id *parent_id* as a parent of this node."""
        if parent_id not in self.parents:
            self.parents.append(parent_id)
            return self.new_relationship(parent_id, self.get_id())
        else:
            return False

    def set_parent(self, parent_id):
        """Set the node with id *parent_id* as the only parent of this node.
        
        If this node already has parents, those relationships are removed. If
        the argument *parent_id* is None, all parents are removed.
        
        """
        is_already_parent_flag = False
        for id in self.parents:
            if id != parent_id:
                assert(self.remove_parent(id) == True)
            else:
                is_already_parent_flag = True
        if parent_id and not is_already_parent_flag:
            self.add_parent(parent_id)
        elif parent_id == None:
            self.new_relationship('root', self.id)

    def remove_parent(self, parent_id):
        """Remove the node *parent_id* from this node's parents."""
        if id in self.parents:
            self.parents.remove(id)
            return self.tree.break_relationship(id,self.get_id())
        else:
            return False

#### Children
    def has_child(self, child_id=None):
        """Return True if the node has children.
        
        If *child_id* is given, return True if that node is a direct child of
        this node.
        
        """
        if id :
            return id in self.children
        else:
            return len(self.children) != 0

    def get_children(self):
        """Return a list of IDs for children of this node."""
        return self.children

    def get_nth_child(self, index):
        """Return the ID of the *index*th child of this node."""
        try:
            return self.children[index]
        except IndexError:
            raise IndexError('TreeNode has less than %d children.' % index)

    def get_child(self, child_id):
        """Return the child node with ID *child_id*.
        
        If there is no such child, None is returned.
        
        """
        if child_id in self.children:
            return self.tree.get_node(child_id)
        else:
            return None

    def get_child_index(self, child_id):
        """Return the index of the child with ID *child_id*.
        
        If there is no such child, None is returned.
        
        """
        if id in self.children:
            return self.children.index(id)
        else:
            return None

    def add_child(self, id):
        """Add the node *child_id* to this node's children.
        
        If the operation is successful, return True; otherwise return False.
        """
        if id not in self.children:
            self.children.append(id)
#            result = self.new_relationship(self.id, child_id)
#            Log.debug("new relationship : %s" % result)
#            return result
            return self.new_relationship(self.id, child_id)
        else:
#            Log.debug("%s was already in children of %s" % (child_id, self.id))
            return False

    def remove_child(self, child_id):
        """Remove the node *child_id* from this node's children."""
        if child_id in self.children:
            self.children.remove(child_id)
            return self.tree.break_relationship(self.id, child_id)
        else:
            return False

class RootNode(TreeNode):
    """A special class for trees with no data in the root node."""
    def _get_id():
        return 0

