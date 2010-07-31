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
from json import dumps

import gobject

# only uncomment this for debugging purposes
# from GTG.tools.logger import Log


ROOTNODE_ID = -1


class MissingTreeError(Exception):
    """
    MissingTreeError is raised by TreeNode whenever a node ID lookup (for a
    parent or a child) is attempted, but the TreeNode is not associated with
    any tree.
    """
    pass


class PathError(Exception):
    """Exception for a malformed tree path."""
    pass


class MainTree(gobject.GObject):
    """A tree of nodes."""
    # GObject signals to be emitted on node operations. The single argument of
    # each method is the ID of the node that was added, deleted or modified.
    __gsignals__ = {
      'node-added': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (str,)),
      'node-deleted': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (str,)),
      'node-modified': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (str,)),
      }

    def __init__(self, root=None):
        """Initialize a new tree.
        
        If *root* is given, it must be a TreeNode or subclass, and becomes the
        root node of the tree. Otherwise a RootNode is created as the root.
        
        """
        gobject.GObject.__init__(self)
        self._nodes = {}
        self._pending_relationships = []
        if root is None:
            root = RootNode()
        self.set_root(root)

    ### Tree methods
    def add_node(self, node, parent_id=None):
        """Add a node to the tree.
        
        If *parent_id* is given, then *node* becomes a child of the node
        with that ID. Otherwise, *node* is a child of the root node.
        
        """
        id = node.id
        if len(self._nodes) == 0 and isinstance(self._root, RootNode):
            # using a RootNode, and this is the first node added to the tree.
            # Make sure the type of self._root.id is the same as other nodes
            try:
                hash(id)
            except TypeError:
                raise TypeError('Node IDs cannot be unhashable type %s ' %
                  type(id))
            else:
                self._root._type = type(id)
        if self.has_node(id):
            raise KeyError('MainTree already contains a node with ID %s'
              % id)
        else:
            #We add the node
            node.set_tree(self)
            if parent_id:
                parent = self.get_node(parent_id)
                node.set_parent(parent.id)
                parent.add_child(id)
            else:
                self._root.add_child(id)
            self._nodes[id] = node
            # build the relationships that were waiting for that node
            for rel in self._pending_relationships:
                if id in rel:
                    self.new_relationship(rel[0], rel[1])
            self.emit("node-added", id)
            return True

    def new_relationship(self, parent_id, child_id):
        """Create a new relationship between nodes.
        
        The node with ID *parent_id* is a parent of the node with ID *child_id*.
        If the relationship already exists, return False.
        
        """
        def is_descendant(node, target):
            """Check the ancestry of *node* for the node *target*.
            
            Return True if *target* is an ancestor of *node*, otherwise False.
            
            """
            if node.has_parent(target.id):
                # the target is a parent of the node. Circular!
                return True
            elif node.has_parent():
                # not a direct parent, but the node has other parents. Recurse
                circular = False
                for parent_id in node._parents:
                    circular = is_descendant(self.get_node(parent_id), target)
                    if circular:
                        # some level of recursion found circular. No need to
                        # continue
                        break
                return circular
            else:
                # node has no parents
                return False

#        Log.debug("new relationship between %s and %s" %(parent_id,child_id))
        success = False
        # remove this pair from the pending relationships
        if (parent_id, child_id) in self._pending_relationships:
            self._pending_relationships.remove((parent_id, child_id))
        # no relationship allowed with yourself
        if parent_id == child_id:
            # TODO: throw an exception here?
            return False
        try:
            # get the nodes we're going to relate. If they don't exist, this
            # will throw a ValueError.
            p = self.get_node(parent_id)
            c = self.get_node(child_id)
            # we've got the nodes
            # avoid the typical time-traveller problem (being-the-father-of-
            # yourself or the grand-father. We need some genealogic research!
            if is_descendant(p, c):
                # a circular relationship was found
#               Log.debug("  * * * * * Circular relationship found : undo")
                self.break_relationship(parent_id, child_id)
                raise Exception('Attempt to create circular relationship '
                  'bewteen nodes %s and %s' % (parent_id, child_id))
            # it's not circular!
            if child_id not in p._children:
                p._children.append(child_id)
                success = True
            if parent_id not in c._parents:
                c._parents.add(parent_id)
                success = True
        except ValueError, e:
            # at least one of the nodes was not in the tree, maybe because it's
            # not loaded. Save the relationship for later
            if (parent_id, child_id) not in self._pending_relationships:
                self._pending_relationships.append((parent_id, child_id))
            self.break_relationship(parent_id, child_id)
            # this is considered successful (?)
            success = True
        except:
            # pass on other exceptions
            raise
        finally:
            if success:
                # emit signals
                self._modified(parent_id)
                self._modified(child_id)
        return success

    def break_relationship(self, parent_id, child_id):
        """Break an existing relationship.
        
        If the node *child_id* has only one parent (*parent_id*), then it is
        made a child of the root node. If the relationship did not exist,
        return False; otherwise return True.
        
        """
        success = False
        try:
            # get the nodes we're going to break apart
            p = self.get_node(parent_id)
            c = self.get_node(child_id)
            # successful if both nodes recognized the relationship we are
            # breaking
            p._children.remove(child_id)
            c._parents.remove(parent_id)
            # if the child is now parentless, add it under the root
            if len(c._parents) == 0:
                c.add_parent(self._root.id)
            success = True
        except ValueError:
            # at least one of the nodes was not in the tree, or the child- or
            # parent-list of one of the nodes was incomplete.
            pass
        finally:
            if success:
                # emit signals
                self._modified(parent_id)
                self._modified(child_id)
            return success

    def get_all_nodes(self):
        """Return the IDs of all nodes in the tree."""
        return self._nodes.keys()

    def get_deleted_path(self,id):
        """Return a deleted path to the node *node_id*.
        
        A deleted path can only be requested once.
        
        """
        toreturn = None
        # TODO: don't print to the console
        print "old paths are : %s" % self.old_paths
        if self.old_paths.has_key(node_id):
            return self.old_paths.pop(node_id)

    def get_node_for_path(self, path):
        """Return the ID of a node for a given *path*.
        
        A *path* is a sequence of indices, with earlier indices being closer
        to the top of the tree. For example, the path (3,5,7) means "the
        seventh child of the fifth child of the third child of the root node".
        
        """
        path = list(path)
        path.reverse()
        return self._node_for_path(None, path)

    def get_paths_for_node(self, node_id=None):
        """Return all unique paths to the node *node_id*.
        
        See get_node_for_path() for a description of the format of paths.
        
        """
        return self._paths_for_node(node_id)

    def get_root(self):
        """Return the root node."""
        return self._root

    def get_node(self, node_id=None):
        """Return the node with ID *node_id*.
        
        If *node_id* is None or the string 'root', return the root node.
        
        """
        if node_id in self._nodes:
            return self._nodes[node_id]
        elif node_id == self._root.id or node_id == None or node_id == 'root':
            return self._root
        else:
            raise ValueError("Node %s is not in the tree. Wrong get_node()"
              % node_id)

    def has_node(self, node_id):
        """Return True if the node with ID *node_id* is in the tree."""
        return node_id in self._nodes.keys() + [self._root.id]

    def modify_node(self, node_id):
        """Emit the node-modified signal."""
        self._modified(node_id)

    def _modified(self, node_id):
        """Emit the node-modified signal for node *node_id*."""
        if node_id in self._nodes:
            self.emit("node-modified", node_id)

    def move_node(self, node_id, parent_id=None):
        """Make the node with ID *node_id* a child of *parent_id*.
        
        If *parent_id* is None, the node is made a child of the tree root.
        
        """
        if parent_id is None:
            parent_id = self._root.id
        try:
            self.get_node(node_id).set_parent(parent_id)
            return True
        except ValueError:
            return False

    def next_node(self, node_id, parent_id=None):
        """Return the next sibling of a node *node_id*.
        
        If there is no such sibling, return None. If the node has multiple
        parents, the siblings under parent *parent_id* will be returned.
        If *parent_id* is None in this case, a random parent is used.
        
        """
        # get the parents of node_id
        node = self.get_node(node_id)
        parent_ids = node._parents
        # choose the appropriate parent
        if parent_id not in parent_ids:
            parent_id = list(parent_ids)[0]
        parent = self.get_node(parent_id)
        # find the index of node_id under the parent
        index = parent.get_child_index(node_id)
        if len(parent._children) > index + 1:
            return parent._children[index + 1]

    def _node_for_path(self, node_id, path):
        """Recursive helper for get_node_for_path().
        
        Return the next node along *path*, starting from node *node_id*.
        
        """
        node = self.get_node(node_id)
        index = path.pop()
        try:
            if len(path):
                # still more path elements to use; recurse
                child_id = node._children[index]
                return self._node_for_path(child_id, path)
            else:
                # that was the last path element
                return node._children[index]
        except IndexError:
            raise PathError

    def _paths_for_node(self, node_id=None):
        """Recursive helper for get_paths_for_node().
        
        Return a list of tuples representing the paths to the node *node_id*.
        
        """
        paths = []
        for parent_id in self.get_node(node_id)._parents:
            i = self.get_node(parent_id)._children.index(node_id)
            for parent_path in self._paths_for_node(parent_id):
                paths.append(tuple(list(parent_path) + [i]))
        if not len(paths):
            paths.append(tuple())
        return paths

    def _print_from_node(self, node, prefix='`— '):
        """Helper function for print_tree()."""
        print prefix + str(node.id)
        for child_id in node._children:
            cur_node = node.get_child(child_id)
            self._print_from_node(cur_node, '  %s' % prefix)

    def remove_node(self, node_id, recursive=False):
        """Remove a node with ID *node_id* from the tree.
        
        If the node has any children, and *recursive* is false, they are made
        children of the root node. Otherwise all children of the node are
        also removed.
        
        If the node does not exist, nothing happens.
        
        """
        node = self.get_node(node_id)
        if node.has_child():
            for child_id in node._children:
                if recursive:
                    self.remove_node(child_id, recursive=True)
                else:
                    self.break_relationship(node_id, child_id)
        if node.has_parent():
            for parent_id in node._parents:
                par = self.get_node(parent_id)
                par.remove_child(node_id)
        else:
            self._root.remove_child(node_id)
        self.emit("node-deleted", node_id)
        del self._nodes[node_id]

    def set_root(self, root):
        """Set the root node of the tree to *root*."""
        # FIXME: method is unused in GTG
        self._root = root
        self._root.set_tree(self)

    def __str__(self):
        """String representation."""
        return "<Tree: root = '%s'>" % (str(self._root))

    def to_string(self):
        """Print a representation of the tree to stdout.
        
        The IDs of all nodes are printed one per line, with indentation to
        represent hierarchy.
        
        """
        self._print_from_node(self._root)

    def to_json(self, **kwargs):
        """Serialize the tree to JSON.
        
        A
        """
        def to_json_recurse(node):
            result = {}
            for child_id in node._children:
                result[child_id] = self.__to_json(self.get_node(child_id))
            return result
        return dumps({self._root.id: to_json_recurse(self._root)}, **kwargs)

    def visit_tree(self, pre_func=None, post_func=None):
        """Recursively walk the tree and call functions on every node.
        
        *pre_func* and *post_func* are callbacks which accept one argument, a
        node. *pre_func* is called on a node BEFORE its children are processed.
        *post_func* is called on a node AFTER its children are processed. No
        functions are called on the root node.
        
        """
        if self._root.has_child():
            for c in self._root._children:
                node = self._root.get_child(c)
                self._visit_node(node, pre_func, post_func)

    def _visit_node(self, node, pre_func=None, post_func=None):
        """Helper function for visit_node()."""
        if pre_func:
            pre_func(node)
        if node.has_child():
            for c in node._children:
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
    # methods are in three groups: general, parents, children
    ### General methods
    def __init__(self, parent=None):
        """Initialize a new node."""
        # new-style property for the ID. It is read-only.
        self._parents = set()
        self._children = []
        self._tree = None
        if parent:
            self.add_parent(parent)

    ### Child methods
    def add_child(self, child_id):
        """Add the node *child_id* to this node's children.
        
        If the operation is successful, return True; otherwise return False.
        
        """
        return self.tree.new_relationship(self.id, child_id)

    def add_parent(self, parent_id):
        """Add the node with id *parent_id* as a parent of this node."""
        return self.tree.new_relationship(parent_id, self.id)

    def get_child(self, child_id):
        """Return the child node with ID *child_id*.
        
        If there is no such child, None is returned.
        
        """
        if child_id in self._children:
            return self.tree.get_node(child_id)
        else:
            return None

    def get_child_index(self, child_id):
        """Return the index of the child with ID *child_id*.
        
        If there is no such child, None is returned.
        
        """
        if child_id in self._children:
            return self._children.index(child_id)
        else:
            return None

    def get_children(self):
        """Return a list of IDs for children of this node."""
        return self._children

    def get_parents(self):
        """Return a set of IDs for parents of this node."""
        return self._parents

    def _get_id(self):
        """Generate or return an ID for this node."""
        return id(self)

    def get_nth_child(self, index):
        """Return the ID of the *index*th child of this node."""
        try:
            return self._children[index]
        except IndexError:
            raise IndexError('TreeNode has less than %d children.' % index)

    def get_tree(self):
        if self._tree:
            return self._tree
        else:
            raise MissingTreeError('Node is not associated with a tree.')

    def has_child(self, child_id=None):
        """Return True if the node has children.
        
        If *child_id* is given, return True if that node is a direct child of
        this node.
        
        """
        if child_id is None:
            return len(self._children) != 0
        else:
            return child_id in self._children

    def has_parent(self, parent_id=None):
        """Return True if the node has a parent.
        
        If *parent_id* is not None, return True if that node is a parent of
        this node.
        
        """
        if parent_id:
            return parent_id in self._parents
        else:
            return len(self._parents) > 0 or (self.tree and
              self._parents == [self.tree._root.id])

    def modified(self):
        try:
            self.tree.modify_node(self.id)
        except MissingTreeError:
            pass

    def remove_child(self, child_id):
        """Remove the node *child_id* from this node's children."""
        return self.tree.break_relationship(self.id, child_id)

    def remove_parent(self, parent_id):
        """Remove the node *parent_id* from this node's parents."""
        return self.tree.break_relationship(parent_id, self.id)

    def set_parent(self, new_parent_id=None):
        """Set the node with id *parent_id* as the only parent of this node.
        
        If this node already has parents, those relationships are removed. If
        the argument *parent_id* is None, all parents are removed.
        
        """
        if new_parent_id in self._parents:
            return False
        else:
            # create the new relationship *first*
            self.tree.new_relationship(new_parent_id, self.id)
            for parent_id in self._parents.copy():
                if parent_id != new_parent_id:
                    self.tree.break_relationship(parent_id, self.id)
            return True

    def set_tree(self, tree):
        """Return a reference to the Tree containing this node."""
        self._tree = tree

    def __str__(self):
        """String representation."""
        return "<TreeNode: '%s'>" % (self.id)

    # New-style properties
    tree = property(get_tree, set_tree)
    id = property(lambda self: self._get_id())


class RootNode(TreeNode):
    """A special class for trees with no data in the root node."""
    def __init__(self, id_type=int):
        self._type = id_type
        TreeNode.__init__(self)

    ### TreeNode methods
    def add_parent(self, parent_id):
        raise NotImplementedError('Cannot add parent to RootNode.')

    def _get_id(self):
        return self._type(ROOTNODE_ID)

