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

"""Tests for the tagstore."""

import unittest

from GTG.tools.larch import Tree
from GTG.tools.larch.tree import TreeNode


#This is a dummy treenode that only have one properties: a color
class DummyNode(TreeNode):
    def __init__(self,tid):
        TreeNode.__init__(self, tid)
        self.colors = []

    def add_color(self,color):
        if color not in self.colors:
            self.colors.append(color)

    def has_color(self,color):
        return color in self.colors

    def remove_color(self,color):
        if color in self.colors:
            self.colors.pop(color)

class TestFilteredTree(unittest.TestCase):
    """Tests for `Tree`."""


    def setUp(self):
        i = 0
        #node numbers, used to check
        self.red_nodes = 0
        self.blue_nodes = 0
        self.green_nodes = 0
        #Larch, is the tree. Learn to recognize it.
        self.tree = Larch()
        #first, we add some red nodes at the root
        while i < 5:
            node = DummyNode(i)
            node.add_color('red')
            self.tree.add_node(node)
            i += 1
            self.red_nodes += 1
        #then, we add some blue nodes also at the root
        while i < 10:
            node = DummyNode(i)
            node.add_color('blue')
            self.tree.add_node(node)
            i+=1
            self.blue_nodes += 1
        #finally, we add some green nodes as children of the last nodes
        while i < 15:
            node = DummyNode(i)
            node.add_color('green')
            self.tree.add_node(node,parent=i-1)
            i+=1
            self.green_nodes += 1


    def test_root(self):
        #A tree created without an argument has a root
        root = tree.get_root()
        self.assertEqual('root', root.get_id())
        
    def test_add_node(self):
        #Add a node to a tree the retrieve it with its id.
        tree = self._build_tree(1)
        get = tree.get_node('1@1')
        self.assertEqual('1@1',get.get_id())
        
    def test_remove_node(self):
        #Add a node to a tree the retrieve it with its id.
        tree = self._build_tree(1)
        tree.remove_node('1@1')
        get = tree.get_node('1@1')
        self.assertEqual(None,get)
        
    def test_all_nodes(self):
        #you can retrieve all nodes, the tree being flat or not
        tree1 = self._build_tree(4)
        tree2 = self._build_tree(4,flat=False)
        flat = len(tree1.get_all_nodes())
        stair = len(tree2.get_all_nodes())
        self.assertEqual(4,flat)
        #not flat have n + n - 1 nodes
        self.assertEqual(7,stair)
        
    def test_parent(self):
        tree = self._build_tree(4,flat=False)
        #tree.print_tree()
        mynode = tree.get_node('3@3')
        self.assertEqual(True,mynode.has_parent())
        p = mynode.get_parents()[0]
        par = tree.get_node(p)
        self.assertEqual('2@2',par.get_id())
        
    def test_get_path(self):
        tree = self._build_tree(4,flat=False)
        mynode = tree.get_node('2@2')
        node_path = tree.get_path_for_node(mynode)
        self.assertEqual((0,0),node_path)
        mynode = tree.get_node('2@1')
        node_path = tree.get_path_for_node(mynode)
        self.assertEqual((1,),node_path)
        
    def test_visit(self):
        self.counter = 0
        self.counter2 = 0
        def pre(node):
            self.counter += 1
        def post(node):
            self.counter2 += 1
        tree = self._build_tree(4,flat=False)
        tree.visit_tree(pre_func=pre,post_func=post)
        self.assertEqual(7,self.counter)
        self.assertEqual(7,self.counter2)
        
    def test_get_node(self):
        tree = self._build_tree(4,flat=False)
        node1 = tree.get_node('3@1')
        node2 = tree.get_node('3@3')
        znode1 = tree.get_node_for_path((2,))
        znode2 = tree.get_node_for_path((0,0,0))
        self.assertEqual(node1,znode1)
        self.assertEqual(node2,znode2)



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
