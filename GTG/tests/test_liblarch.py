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

from GTG.tools.liblarch import Tree
from GTG.tools.liblarch.tree import TreeNode


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

class TestLibLarch(unittest.TestCase):
    """Tests for `Tree`."""


    def setUp(self):
        i = 0
        #node numbers, used to check
        self.red_nodes = 0
        self.blue_nodes = 0
        self.green_nodes = 0
        #Larch, is the tree. Learn to recognize it.
        self.tree = Tree()
        self.view = self.tree.get_viewtree()
        self.mainview = self.tree.get_main_view()
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
        self.total = self.red_nodes + self.blue_nodes + self.green_nodes
    ####Filters
    def is_blue(self,node,parameters=None):
        return node.has_color('blue')
    def is_green(self,node,parameters=None):
        return node.has_color('green')
    def is_red(self,node,parameters=None):
        return node.has_color('red')
        
    #### Testing nodes movements in the tree
    #### We test by counting nodes that meet some criterias

    def test_add_remove_node(self):
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('temp')
        node.add_color('blue')
        self.tree.add_node(node,parent_id=str(0))
        shouldbe = self.blue_nodes + 1
        total = self.red_nodes + self.blue_nodes + self.green_nodes
        #Testing that the blue node count has increased
        self.assertEqual(total+1,view.get_n_nodes())
        self.assertEqual(shouldbe,view.get_n_nodes(withfilters=['blue']))
        #also comparing with another view
        self.assertEqual(total+1,self.view.get_n_nodes())
        self.assertEqual(shouldbe,self.view.get_n_nodes(withfilters=['blue']))
        self.tree.del_node('temp')
        #Testing that it goes back to normal
        self.assertEqual(total,view.get_n_nodes())
        self.assertEqual(self.blue_nodes,view.get_n_nodes(withfilters=['blue']))
        #also comparing with another view
        self.assertEqual(total,self.view.get_n_nodes())
        self.assertEqual(self.blue_nodes,self.view.get_n_nodes(withfilters=['blue']))
    
    #When you remove a parent, the child nodes should be added to the root if
    #they don't have any other parents
    def test_removing_parent(self):
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('temp')
        node.add_color('blue')
        self.tree.add_node(node,parent_id='0')
        all_nodes = self.view.get_all_nodes()
        self.assert_('0' in all_nodes)
        self.assert_('temp' in all_nodes)
        self.tree.del_node('0')
        all_nodes = self.view.get_all_nodes()
        self.failIf('0' in all_nodes)
        self.assert_('temp' in all_nodes)
        
    def test_move_node(self):
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('temp')
        node.add_color('blue')
        self.tree.add_node(node,parent_id='0')
        #Testing initial situation
        self.assert_(view.node_has_child('0'))
        self.assert_('temp' in view.node_all_children('0'))
        self.assert_('temp' not in view.node_all_children('1'))
        #Moving node
        self.tree.move_node('temp','1')
        self.assert_(view.node_has_child('1'))
        self.assert_('temp' in view.node_all_children('1'))
        self.assert_('temp' not in view.node_all_children('0'))
        #Now moving to root
        self.tree.move_node('temp')
        self.assert_('temp' not in view.node_all_children('1'))
        self.assert_('temp' not in view.node_all_children('0'))
        #temp still exist and doesn't have any parents
        all_nodes = self.mainview.get_all_nodes()
        self.assert_('temp' in all_nodes)
        self.assertEqual(0,len(self.mainview.node_parents('temp')))
        
#    def test_add_parent(self):
    
    #we try to add a task as a child of one of its grand-children.
    #Nothing should happen
#    def test_cyclic_paradox(self):
        
    def test_mainview(self):
        #we should test that mainview is always up-to-date
        #and raise exception when trying to add filters on it
        #TODO
        pass
        
    #### Testing each method of the ViewTree
    
    def test_viewtree_get_n_nodes(self):
        total = self.red_nodes + self.blue_nodes + self.green_nodes
        self.assertEqual(total,self.view.get_n_nodes())
        self.assertEqual(self.green_nodes,self.view.get_n_nodes(withfilters=['green']))
        #TODO: test after applying a filter on the view
        #TODO : do the same test on the mainview
        
    
    def test_viewtree_get_all_nodes(self):
        all_nodes = self.view.get_all_nodes()
        self.assertEqual(True,'0' in all_nodes)
        self.assertEqual(False,'tmp' in all_nodes)
        self.assertEqual(self.total,len(all_nodes))
        node = DummyNode('temp')
        node.add_color('blue')
        self.tree.add_node(node,parent_id=str(0))
        all_nodes = self.view.get_all_nodes()
        self.assert_('0' in all_nodes)
        self.assert_('temp' in all_nodes)
        self.assertEqual(self.total+1,len(all_nodes))
        self.tree.del_node('1')
        all_nodes = self.view.get_all_nodes()
        self.failIf('1' in all_nodes)
        self.assert_('temp' in all_nodes)
        self.assertEqual(self.total,len(all_nodes))
        #TODO: test after applying a filter on the view
        #TODO : do the same test on the mainview
        
        
#    def test_viewtree_get_node_for_path(self):
#    def test_viewtree_get_paths_for_node(self):
#    def test_viewtree_next_node(self):
    def test_viewtree_node_has_child(self):
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('temp')
        node.add_color('blue')
        self.failIf(view.node_has_child('0'))
        self.tree.add_node(node,parent_id='0')
        self.assert_(view.node_has_child('0'))
        #TODO: test after applying a filter on the view
        #TODO : do the same test on the mainview
    
#    def test_viewtree_node_n_children(self):

    def test_viewtree_node_all_children(self):
        view = self.tree.get_viewtree(refresh=True)
        self.assertEqual(0,len(view.node_all_children('0')))
        #checking that 0 and 1 are in root
        self.assert_('0' in view.node_all_children())
        self.assert_('1' in view.node_all_children())
        node = DummyNode('temp')
        node.add_color('blue')
        #adding a new children
        self.tree.add_node(node,parent_id='0')
        self.assertEqual(1,len(view.node_all_children('0')))
        self.assert_('temp' in view.node_all_children('0'))
        #moving an existing children
        self.tree.move_node('1','0')
        self.assertEqual(2,len(view.node_all_children('0')))
        self.assert_('1' in view.node_all_children('0'))
        self.failIf('1' in view.node_all_children())
        #removing a node
        self.tree.del_node('temp')
        self.assertEqual(1,len(view.node_all_children('0')))
        self.failIf('temp' in view.node_all_children('0'))
        #moving a node elsewhere
        self.tree.move_node('1')
        self.assertEqual(0,len(view.node_all_children('0')))
        self.failIf('1' in view.node_all_children('0'))
        #checking that '1' is back in root
        self.assert_('1' in view.node_all_children())
        
    
#    def test_viewtree_node_nth_child(self):
#    def test_viewtree_node_parents(self):
#    def test_viewtree_is_displayed(self):
        
    

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
