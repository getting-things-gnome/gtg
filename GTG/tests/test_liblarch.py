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

import gtk

from GTG.tools.liblarch import Tree
from GTG.tools.liblarch.tree import TreeNode
from GTG.gtk.liblarch_gtk import TreeView


#This is a dummy treenode that only have one properties: a color
class DummyNode(TreeNode):
    def __init__(self,tid):
        TreeNode.__init__(self, tid)
        self.colors = []

    def add_color(self,color):
        if color not in self.colors:
            self.colors.append(color)
        self.modified()

    def has_color(self,color):
        return color in self.colors

    def remove_color(self,color):
        if color in self.colors:
            self.colors.remove(color)
        self.modified()

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
        self.tree.add_filter('leaf',self.is_leaf)
        param = {}
        param['flat'] = True
        self.tree.add_filter('flatgreen',self.is_green,parameters=param)
        self.tree.add_filter('flatleaves',self.is_leaf,parameters=param)
        param = {}
        param['transparent'] = True
        self.tree.add_filter('transblue',self.is_blue,parameters=param)
        self.tree.add_filter('transgreen',self.is_green,parameters=param)
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
        # (stairs-like configuration)
        while i < 15:
            node = DummyNode(str(i))
            node.add_color('green')
            self.tree.add_node(node,parent_id=str(i-1))
            i+=1
            self.green_nodes += 1
        self.total = self.red_nodes + self.blue_nodes + self.green_nodes
        ################now testing the GTK treeview ##################
        #The columns description:
        desc = {}
        col = {}
        col['title'] = "Node name"
        render_text = gtk.CellRendererText()
        col['renderer'] = ['markup',render_text]
        def get_node_name(node):
            return node.get_id()
        col['value'] = [str,get_node_name]
        desc['titles'] = col
        treeview = TreeView(self.view,desc)
        
    ####Filters
    def is_blue(self,node,parameters=None):
        return node.has_color('blue')
    def is_green(self,node,parameters=None):
        return node.has_color('green')
    def is_red(self,node,parameters=None):
        return node.has_color('red')
    def is_leaf(self,node,parameters=None):
        return not node.has_child()
        
        
    #### Testing nodes movements in the tree
    #### We test by counting nodes that meet some criterias
    
    def test_get_node(self):
        #we test that get node works for the last node
        node = self.tree.get_node(str(self.total-1))
        self.assert_(node != None)
        self.assertEqual(str(self.total-1),node.get_id())
        #and not for an non-existing node
        self.assertRaises(ValueError,self.tree.get_node,str(self.total))

    def test_add_remove_node(self):
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('temp')
        node.add_color('blue')
        self.tree.add_node(node,parent_id='0')
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
        
    def test_modifying_node(self):
        viewblue = self.tree.get_viewtree(refresh=False)
        viewblue.apply_filter('blue')
        viewred = self.tree.get_viewtree(refresh=False)
        viewred.apply_filter('red')
        node = DummyNode('temp')
        node.add_color('blue')
        #Do you see : we are modifying a child
        self.tree.add_node(node,parent_id='0')
        #Node is blue
        self.assert_(viewblue.is_displayed('temp'))
        self.failIf(viewred.is_displayed('temp'))
        #node is blue and red
        node.add_color('red')
        self.assert_(viewblue.is_displayed('temp'))
        self.assert_(viewred.is_displayed('temp'))
        #node is red only
        node.remove_color('blue')
        self.failIf(viewblue.is_displayed('temp'))
        self.assert_(viewred.is_displayed('temp'))


    
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
        
    def test_add_parent(self):
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('temp')
        node.add_color('blue')
        self.tree.add_node(node,parent_id='0')
        #Testing initial situation
        self.assert_(view.node_has_child('0'))
        self.assert_('temp' in view.node_all_children('0'))
        self.assert_('temp' not in view.node_all_children('1'))
        #Adding another parent
        self.tree.add_parent('temp','1')
        self.assert_(view.node_has_child('1'))
        self.assert_('temp' in view.node_all_children('1'))
        self.assert_('temp' in view.node_all_children('0'))
    
    #we try to add a task as a child of one of its grand-children.
    #Nothing should happen
    def test_cyclic_paradox(self):
        node = DummyNode('temp')
        node.add_color('blue')
        self.tree.add_node(node,parent_id='0')
        self.tree.add_parent('0','1')
        self.assert_('1' in self.mainview.node_parents('0'))
        self.assert_('0' in self.mainview.node_parents('temp'))
        #direct circular relationship
        self.assertRaises(Exception,self.tree.add_parent,'0','temp')
        #More complex circular relationship
        self.assertRaises(Exception,self.tree.add_parent,'1','temp')
        
    def test_mainview(self):
        #we should test that mainview is always up-to-date
        #and raise exception when trying to add filters on it
        self.assertRaises(Exception,self.mainview.apply_filter,'blue')
        
    #### Testing each method of the ViewTree
    
    def test_viewtree_get_n_nodes(self):
        total = self.red_nodes + self.blue_nodes + self.green_nodes
        self.assertEqual(total,self.view.get_n_nodes())
        self.assertEqual(self.green_nodes,self.view.get_n_nodes(withfilters=['green']))
        self.assertEqual(total,self.mainview.get_n_nodes())
        
    
    def test_viewtree_get_all_nodes(self):
        all_nodes = self.view.get_all_nodes()
        all_nodes2 = self.mainview.get_all_nodes()
        self.assertEqual(True,'0' in all_nodes)
        self.assertEqual(False,'tmp' in all_nodes)
        self.assertEqual(self.total,len(all_nodes))
        #Mainview
        self.assertEqual(True,'0' in all_nodes2)
        self.assertEqual(False,'tmp' in all_nodes2)
        self.assertEqual(self.total,len(all_nodes2))
        #adding a node
        node = DummyNode('temp')
        node.add_color('blue')
        self.tree.add_node(node,parent_id=str(0))
        all_nodes = self.view.get_all_nodes()
        all_nodes2 = self.mainview.get_all_nodes()
        self.assert_('0' in all_nodes)
        self.assert_('temp' in all_nodes)
        self.assertEqual(self.total+1,len(all_nodes))
        #Mainview
        self.assert_('0' in all_nodes2)
        self.assert_('temp' in all_nodes2)
        self.assertEqual(self.total+1,len(all_nodes2))
        #Removing the node
        self.tree.del_node('1')
        all_nodes = self.view.get_all_nodes()
        all_nodes2 = self.mainview.get_all_nodes()
        self.failIf('1' in all_nodes)
        self.assert_('temp' in all_nodes)
        self.assertEqual(self.total,len(all_nodes))
        #mainview
        self.failIf('1' in all_nodes2)
        self.assert_('temp' in all_nodes2)
        self.assertEqual(self.total,len(all_nodes2))
        
        
    def test_viewtree_get_node_for_path(self):
        view = self.tree.get_viewtree(refresh=True)
        #nid1 and nid2 are not always the same
        nid1 = view.get_node_for_path((0,))
        nid2 = self.mainview.get_node_for_path((0,))
        #Thus we do a mix of test.
        nid1b = view.next_node(nid1)
        path1b = view.get_paths_for_node(nid1b)
        self.assertEqual([(1,)],path1b)
        #same for mainview
        nid2b = self.mainview.next_node(nid2)
        path2b = self.mainview.get_paths_for_node(nid2b)
        self.assertEqual([(1,)],path2b)
        #with children
        node = DummyNode('temp')
        node.add_color('blue')
        self.tree.add_node(node,parent_id=nid1)
        self.tree.add_parent('temp',nid2)
        self. assertEqual('temp',view.get_node_for_path((0,0)))
        self. assertEqual('temp',self.mainview.get_node_for_path((0,0)))
        #Adding a child to the child
        node2 = DummyNode('temp2')
        node2.add_color('blue')
        self.tree.add_node(node2,parent_id=nid1)
        node = DummyNode('temp_child')
        node.add_color('blue')
        self.tree.add_node(node,parent_id='temp2')
        self.assertEqual('temp_child',view.get_node_for_path((0,1,0)))
        self.tree.add_parent('temp2',nid2)
        self.assertEqual('temp_child',self.mainview.get_node_for_path((0,1,0)))
        #with filters
        view.apply_filter('blue')
        pl = view.get_paths_for_node('temp2')
        for p in pl:
            pp = p + (0,)
            self.assertEqual('temp_child',view.get_node_for_path(pp))
        
    def test_viewtree_get_paths_for_node(self):
        view = self.tree.get_viewtree(refresh=True)
        #testing the root path
        self.assertEqual([()],view.get_paths_for_node())
        self.assertEqual([()],self.mainview.get_paths_for_node())
        #with children
        #the first blue node is:
        firstgreen = self.red_nodes + self.blue_nodes - 1
        pp = view.get_paths_for_node(str(firstgreen))[0]
        i = 0
        #Testing all the green nodes (that are in stairs)
        while i < self.green_nodes:
            returned = view.get_paths_for_node(str(firstgreen+i))[0]
            self.assertEqual(pp,returned)
            i+=1
            pp += (0,)
        #with filters
        view.apply_filter('green')
        pp = view.get_paths_for_node(str(firstgreen+1))[0]
        i = 1
        #Testing all the green nodes (that are in stairs)
        while i < self.green_nodes:
            returned = view.get_paths_for_node(str(firstgreen+i))[0]
            self.assertEqual(pp,returned)
            i+=1
            pp += (0,)
        
    def test_viewtree_next_node(self):
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('temp')
        node.add_color('blue')
        node.add_color('green')
        self.tree.add_node(node,parent_id='0')
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('temp2')
        node.add_color('red')
        self.tree.add_node(node,parent_id='0')
        #we give the pid
        self.assertEqual('temp2',view.next_node('temp',pid='0'))
        self.assertEqual('temp2',self.mainview.next_node('temp',pid='0'))
        #or we give not (should be the same here because only one parent)
        self.assertEqual('temp2',view.next_node('temp'))
        self.assertEqual('temp2',self.mainview.next_node('temp'))
        #next node for last node.
        self.assertEqual(None,view.next_node('temp2'))
        self.assertEqual(None,self.mainview.next_node('temp2'))
        #with filters, temp should not have any next node
        view.apply_filter('blue',refresh=False)
        view.apply_filter('green')
        self.assertEqual(None,view.next_node('temp'))

    def test_viewtree_node_has_child(self):
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('temp')
        node.add_color('blue')
        self.failIf(view.node_has_child('0'))
        self.failIf(self.mainview.node_has_child('0'))
        #Adding the node to the tree
        self.tree.add_node(node,parent_id='0')
        self.assert_(view.node_has_child('0'))
        self.assert_(self.mainview.node_has_child('0'))
    
    #We also test node_n_children here. Nearly the same method
    def test_viewtree_node_all_children(self):
        view = self.tree.get_viewtree(refresh=True)
        self.assertEqual(0,len(view.node_all_children('0')))
        #checking that 0 and 1 are in root
        self.assert_('0' in view.node_all_children())
        self.assert_('1' in view.node_all_children())
        self.assert_('0' in self.mainview.node_all_children())
        self.assert_('1' in self.mainview.node_all_children())
        node = DummyNode('temp')
        node.add_color('blue')
        #adding a new children
        self.tree.add_node(node,parent_id='0')
        self.assertEqual(1,view.node_n_children('0'))
        self.assert_('temp' in view.node_all_children('0'))
        self.assertEqual(1,self.mainview.node_n_children('0'))
        self.assert_('temp' in self.mainview.node_all_children('0'))
        #Testing with a filter
        view.apply_filter('red')
        self.failIf('temp' in view.node_all_children('0'))
        view.unapply_filter('red')
        #moving an existing children
        self.tree.move_node('1','0')
        self.assertEqual(2,view.node_n_children('0'))
        self.assert_('1' in view.node_all_children('0'))
        self.failIf('1' in view.node_all_children())
        self.assertEqual(2,self.mainview.node_n_children('0'))
        self.assert_('1' in self.mainview.node_all_children('0'))
        self.failIf('1' in self.mainview.node_all_children())
        #removing a node
        self.tree.del_node('temp')
        self.assertEqual(1,view.node_n_children('0'))
        self.failIf('temp' in view.node_all_children('0'))
        self.assertEqual(1,self.mainview.node_n_children('0'))
        self.failIf('temp' in self.mainview.node_all_children('0'))
        #moving a node elsewhere
        self.tree.move_node('1')
        self.assertEqual(0,view.node_n_children('0'))
        self.failIf('1' in view.node_all_children('0'))
        self.assertEqual(0,self.mainview.node_n_children('0'))
        self.failIf('1' in self.mainview.node_all_children('0'))
        #checking that '1' is back in root
        self.assert_('1' in view.node_all_children())
        self.assert_('1' in self.mainview.node_all_children())
        
    
    def test_viewtree_node_nth_child(self):
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('temp')
        node.add_color('blue')
        #Asking for a child that doesn't exist should raise an exception
        self.assertRaises(ValueError,view.node_nth_child,'0',0)
        self.assertRaises(ValueError,self.mainview.node_nth_child,'0',0)
        #Adding the node to the tree
        self.tree.add_node(node,parent_id='0')
        self.assertEqual('temp',view.node_nth_child('0',0))
        self.assertEqual('temp',self.mainview.node_nth_child('0',0))
        #Now with a filter
        view.apply_filter('red')
        self.assertRaises(ValueError,view.node_nth_child,'0',0)
        
        
    def test_viewtree_node_parents(self):
        view = self.tree.get_viewtree(refresh=True)
        #Checking that a node at the root has no parents
        self.assertEqual([],view.node_parents('0'))
        self.assertEqual([],self.mainview.node_parents('0'))
        #Adding a child
        node = DummyNode('temp')
        node.add_color('blue')
        self.tree.add_node(node,parent_id='0')
        self.assertEqual(['0'],view.node_parents('temp'))
        self.assertEqual(['0'],self.mainview.node_parents('temp'))
        #adding a second parent
        self.tree.add_parent('temp','1')
        self.assertEqual(['0','1'],view.node_parents('temp'))
        self.assertEqual(['0','1'],self.mainview.node_parents('temp'))
        #now with a filter
        view.apply_filter('blue')
        self.assertEqual([],view.node_parents('temp'))
        #if the node is not displayed, that should not change the parents
        view.unapply_filter('blue')
        view.apply_filter('red')
        self.assertEqual(['0','1'],view.node_parents('temp'))
        

    def test_viewtree_is_displayed(self):
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('temp')
        node.add_color('blue')
        self.failIf(view.is_displayed('temp'))
        self.failIf(self.mainview.is_displayed('temp'))
        #Adding the node to the tree
        self.tree.add_node(node,parent_id='0')
        self.assert_(view.is_displayed('temp'))
        self.assert_(self.mainview.is_displayed('temp'))
        view.apply_filter('blue')
        self.assert_(view.is_displayed('temp'))
        view.apply_filter('red')
        self.failIf(view.is_displayed('temp'))



############ Filters

    def test_simple_filter(self):
        view = self.tree.get_viewtree(refresh=False)
        view.apply_filter('red')
        self.assertEqual(self.red_nodes,view.get_n_nodes())
        self.assertEqual(self.red_nodes,view.get_n_nodes(withfilters=['red']))
        self.assertEqual(0,view.get_n_nodes(withfilters=['blue']))
        #Red nodes are all at the root
        self.assertEqual(self.red_nodes,view.node_n_children())
        #applying another filter
        view.apply_filter('green')
        self.assertEqual(0,view.get_n_nodes())
        #unapplying the first filter
        view.unapply_filter('red')
        self.assertEqual(self.green_nodes,view.get_n_nodes())
        self.assertEqual(self.green_nodes,view.get_n_nodes(withfilters=['green']))
        self.assertEqual(0,view.get_n_nodes(withfilters=['red']))
        #There's only one green node at the root
        self.assertEqual(1,view.node_n_children())
        #Modifying a node to make it red and green
        self.failIf(view.is_displayed('0'))
        node = view.get_node('0')
        node.add_color('green')
        #It should now be in the view
        self.assert_(view.is_displayed('0'))
        self.assertEqual(1,view.get_n_nodes(withfilters=['red']))
        self.assertEqual(2,view.node_n_children())
        #Now, we add a new node
        node = DummyNode('temp')
        node.add_color('green')
        self.tree.add_node(node)
        #It should now be in the view
        self.assert_(view.is_displayed('temp'))
        self.assertEqual(3,view.node_n_children())
        #We remove it
        self.tree.del_node('temp')
        self.failIf(view.is_displayed('temp'))
        self.assertEqual(2,view.node_n_children())
        #We add it again as a children of a non-displayed node
        self.tree.add_node(node,parent_id='1')
        self.assert_(view.is_displayed('temp'))
        self.assertEqual(3,view.node_n_children())
        #It should not have parent
        self.assertEqual(0,len(view.node_parents('temp')))

    def test_leaf_filter(self):
        view = self.tree.get_viewtree(refresh=False)
        view.apply_filter('leaf')
        total = self.red_nodes + self.blue_nodes
        self.assertEqual(total,view.get_n_nodes())
        view.apply_filter('green')
        self.assertEqual(1,view.get_n_nodes())
        nid = view.get_node_for_path((0,))
        #Now, we add a new node
        node = DummyNode('temp')
        node.add_color('green')
        self.tree.add_node(node,parent_id=nid)
        self.assertEqual(1,view.get_n_nodes())
        nid = view.get_node_for_path((0,))
        self.assertEqual('temp',nid)

    #we copy/paste the test
    def test_flatleaves_filters(self):
        view = self.tree.get_viewtree(refresh=False)
        view.apply_filter('flatleaves')
        total = self.red_nodes + self.blue_nodes
        self.assertEqual(total,view.get_n_nodes())
        view.apply_filter('green')
        self.assertEqual(1,view.get_n_nodes())
        nid = view.get_node_for_path((0,))
        #Now, we add a new node
        node = DummyNode('temp')
        node.add_color('green')
        self.tree.add_node(node,parent_id=nid)
        self.assertEqual(1,view.get_n_nodes())
        nid = view.get_node_for_path((0,))
        self.assertEqual('temp',nid)
        
    #green are stairs
    #the flat filter should make them flat
    def test_flat_filters(self):
        view = self.tree.get_viewtree(refresh=False)
        view.apply_filter('flatgreen')
        #all green nodes should be visibles
        self.assertEqual(self.green_nodes,view.get_n_nodes())
        i = 0
        nodes = []
        #we check that the paths are on the root
        while i < self.green_nodes:
            nid = view.get_node_for_path((i,))
            nodes.append(nid)
            self.failIf(nid == None)
            #let see if a node has parent
            self.failIf(view.node_has_parent(nid))
            #and, of course, it cannot have children
            self.failIf(view.node_has_child(nid))
            i += 1
        #we check that we have seen all the nodes
        i = 1
        while i <= self.green_nodes :
            self.assert_(str(self.total-i) in nodes)
            i += 1
        
    def test_transparent_filters(self):
        view = self.tree.get_viewtree(refresh=False)
        view.apply_filter('transgreen')
        self.assertEqual(self.green_nodes,view.get_n_nodes())
        self.assertEqual(self.total,view.get_n_nodes(include_transparent=False))
        #Now with filters in the counting
        count1 = view.get_n_nodes(withfilters=['transblue'])
        count2 = view.get_n_nodes(withfilters=['transblue'],\
                                                    include_transparent=False)
        self.assertEqual(0,count1)
        self.assertEqual(self.blue_nodes,count2)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
