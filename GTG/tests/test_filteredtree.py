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
        self.tree = Tree()
        self.tree.add_filter('blue',self.is_blue)
        self.tree.add_filter('green',self.is_green)
        self.tree.add_filter('red',self.is_red)
        #first, we add some red nodes at the root
        while i < 5:
            node = DummyNode(str(i))
            node.add_color('red')
            self.tree.add_node(node)
            i += 1
            self.red_nodes += 1
        #then, we add some blue nodes also at the root
        while i < 10:
            node = DummyNode(str(i))
            node.add_color('blue')
            self.tree.add_node(node)
            i+=1
            self.blue_nodes += 1
        #finally, we add some green nodes as children of the last nodes
        while i < 15:
            node = DummyNode(str(i))
            node.add_color('green')
            self.tree.add_node(node,parent_id=str(i-1))
            i+=1
            self.green_nodes += 1
    ####Filters
    def is_blue(self,node,parameters=None):
        return node.has_color('blue')
    def is_green(self,node,parameters=None):
        return node.has_color('green')
    def is_red(self,node,parameters=None):
        return node.has_color('red')

    def test_viewtree_n_nodes(self):
        view = self.tree.get_viewtree(refresh=True)
        total = self.red_nodes + self.blue_nodes + self.green_nodes
        self.assertEqual(total,view.get_n_nodes())
        self.assertEqual(self.green_nodes,view.get_n_nodes(withfilters=['green']))

    def test_add_remove_node(self):
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('temp')
        node.add_color('blue')
        self.tree.add_node(node,parent_id=str(0))
        shouldbe = self.blue_nodes + 1
        total = self.red_nodes + self.blue_nodes + self.green_nodes
        self.assertEqual(total+1,view.get_n_nodes())
        self.assertEqual(shouldbe,view.get_n_nodes(withfilters=['blue']))
        self.tree.del_node('temp')
        self.assertEqual(total,view.get_n_nodes())
        self.assertEqual(self.blue_nodes,view.get_n_nodes(withfilters=['blue']))

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
