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
import gobject
import functools
import inspect
import time
import random

from GTG.tools.liblarch import Tree
from GTG.tools.liblarch.tree import TreeNode
from GTG.gtk.liblarch_gtk import TreeView
from GTG.tests.signals_testing import SignalCatcher, CallbackCatcher, GobjectSignalsManager
from GTG.tests.tree_testing import TreeTester

# Prefer callbacks or signals?
USE_CALLBACKS_INSTEAD_OF_SIGNALS=True

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


    def caller_name(self):
        '''
        Returns the filename and the line of the calling function.
        Precisely, it returns the calling calling function (because
        you're calling this one).
        '''
        frame=inspect.currentframe()
        frame=frame.f_back.f_back
        code=frame.f_code
        return code.co_filename, code.co_firstlineno    

    def _assertSignal(self, generator, signal_name, function, \
                     how_many_signals = 1):
        def new(how_many_signals, error_code, *args, **kws):
            with SignalCatcher(self, generator, signal_name,\
                               how_many_signals = how_many_signals,
                               error_code = error_code)\
                    as [signal_catched_event, signal_arguments]:
                function(*args, **kws)
                signal_catched_event.wait()
                self.recorded_signals[signal_name] += signal_arguments
            return None

        # Functools.partial create something like a closure. It provides
        # several arguments by default, but additional arguments are
        # still possible
        return functools.partial(new, how_many_signals, self.caller_name())

    def _assertCallback(self, generator, signal_name, function, \
                     how_many_signals = 1):
        def new(how_many_signals, error_code, *args, **kws):
            with CallbackCatcher(self, generator, signal_name,\
                               how_many_signals = how_many_signals,
                               error_code = error_code)\
                    as [signal_catched_event, signal_arguments]:
                function(*args, **kws)
                #Ensuring there's no async signal left
                generator.flush()
                signal_catched_event.wait()
                self.recorded_signals[signal_name] += signal_arguments
            return None

        return functools.partial(new, how_many_signals, self.caller_name())

    if USE_CALLBACKS_INSTEAD_OF_SIGNALS:
        assertSignal = _assertCallback
    else:
        assertSignal = _assertSignal

    def test_assertSignal(self):
        """ Creates a fake GObject which emits N signals and test whether
        they are emitted.

        The last parameter of assertSignal(...)(33) is parameter for
        FakeGobject.emit_n_signals.
        """

        class FakeGobject(gobject.GObject):
            __gsignals__ = {'node-added-inview': (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE, [])}
            def emit_n_signals(self, n):
                while n:
                    n -= 1
                    gobject.idle_add(self.emit, 'node-added-inview')
        fake_gobject = FakeGobject() 
        self._assertSignal(fake_gobject, \
                          'node-added-inview', \
                          fake_gobject.emit_n_signals, 33)(33)

    def setUp(self):
        """Set up a dummy tree with filters and nodes.

        Construct a Tree for testing, with some filters for testing, including
        filters with parameters 'flat' and 'transparent'.  Create a collection of
        nodes with some of the properties these filters filter on.
        """
        i = 0
        #node numbers, used to check
        self.red_nodes = 0
        self.blue_nodes = 0
        self.green_nodes = 0
        #Larch, is the tree. Learn to recognize it.
        self.tree = Tree()
        self.view = self.tree.get_viewtree()
        self.tester = TreeTester(self.view)
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
        #initalize gobject signaling system
        self.gobject_signal_manager = GobjectSignalsManager()
        self.gobject_signal_manager.init_signals()
        self.recorded_signals = {'node-added-inview': [],
                                 'node-modified-inview': [],
                                 'node-deleted-inview': []}
        self.assertNodeAddedInview = functools.partial ( \
            self.assertSignal, self.view, 'node-added-inview')
        self.assertNodeModifiedInview = functools.partial ( \
            self.assertSignal, self.view, 'node-modified-inview')
        self.assertNodeDeletedInview = functools.partial ( \
            self.assertSignal, self.view, 'node-deleted-inview')

    def tearDown(self):
        try:
            self.tester.test_validity()
        finally:
            #stopping gobject main loop
            self.gobject_signal_manager.terminate_signals()
        
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
        """Test that one node can be retrieved from the tree
        """

        view = self.tree.get_viewtree()
        self.assertEqual(view.get_node_for_path(()), None)
        #we test that get node works for the last node
        node = self.tree.get_node(str(self.total-1))
        self.assertTrue(node != None)
        self.assertEqual(str(self.total-1),node.get_id())
        #and not for an non-existing node
        self.assertRaises(ValueError,self.tree.get_node,str(self.total))

    def test_add_remove_node(self):
        """ Test the adding and removal of nodes """
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('temp')
        node.add_color('blue')

        # run "self.tree.add_node(node, parent_id = '0')" and check that 
        # it generates a 'node-added-view' AND a 'node-modified-inview'
        self.assertSignal(self.view, \
                            'node-modified-inview', \
                            self.assertSignal(self.view, \
                                              'node-added-inview', \
                                          self.tree.add_node))(node, parent_id = '0')
        self.assertTrue(('temp',('0', 'temp')) in self.recorded_signals['node-added-inview'])
        self.assertTrue(('0',('0', )) in \
                     self.recorded_signals['node-modified-inview'])
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
        self.tester.test_validity()
        
    def test_modifying_node(self):
        """ Modifying a node and see if the change is reflected in filters """
        viewblue = self.tree.get_viewtree(refresh=False)
        testblue = TreeTester(viewblue)
        viewblue.apply_filter('blue')
        viewred = self.tree.get_viewtree(refresh=False)
        testred = TreeTester(viewred)
        viewred.apply_filter('red')
        node = DummyNode('temp')
        node.add_color('blue')
        #Do you see : we are modifying a child
        self.assertSignal(self.view, \
                          'node-modified-inview', \
                          self.tree.add_node, 1)(node,parent_id='0')
        self.assertTrue(('0',('0', )) in self.recorded_signals['node-modified-inview'])
        #Node is blue
        self.assertTrue(viewblue.is_displayed('temp'))
        self.assertFalse(viewred.is_displayed('temp'))
        #node is blue and red
        node.add_color('red')
        self.assertTrue(viewblue.is_displayed('temp'))
        self.assertTrue(viewred.is_displayed('temp'))
        #node is red only
        node.remove_color('blue')
        self.assertFalse(viewblue.is_displayed('temp'))
        self.assertTrue(viewred.is_displayed('temp'))
        testred.test_validity()
        testblue.test_validity()

    def test_removing_parent(self):
        """Test behavior of node when its parent goes away.

        When you remove a parent, the child nodes should be added to
        the root if they don't have any other parents.
        """
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('temp')
        node.add_color('blue')
        self.tree.add_node(node,parent_id='0')
        all_nodes = self.view.get_all_nodes()
        self.assertTrue('0' in all_nodes)
        self.assertTrue('temp' in all_nodes)
        self.assertSignal(self.view, \
                          'node-deleted-inview', \
                          self.tree.del_node, 1)('0')
#        self.assertTrue(('0',(0, )) in self.recorded_signals['node-deleted-inview'])
        all_nodes = self.view.get_all_nodes()
        self.assertFalse('0' in all_nodes)
        self.assertTrue('temp' in all_nodes)
        
    def test_adding_to_late_parent(self):
        '''Add a node to a parent not yet in the tree
        then add the parent later'''
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('child')
        self.tree.add_node(node,parent_id='futur')
        all_nodes = view.get_all_nodes()
        self.assertTrue('child' in all_nodes)
        self.assertFalse('futur' in all_nodes)
        self.assertEqual(len(view.node_parents('child')),0)
        #now inserting the parent
        node2 = DummyNode('futur')
        self.tree.add_node(node2)
        all_nodes = view.get_all_nodes()
        self.assertTrue('child' in all_nodes)
        self.assertTrue('futur' in all_nodes)
        self.assertTrue('futur' in view.node_parents('child'))
        #TODO the same test but with filters
        
    def test_adding_to_late_parent2(self):
        '''Another tricky case with late parent. This was
        a very rare but existing crash'''
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('child')
        self.tree.add_node(node)
        self.assertEqual(len(view.node_parents('child')),0)
        node2 = DummyNode('futur')
        node.add_parent('futur')
        node.modified()
        self.assertEqual(len(view.node_parents('child')),0)
        self.assertNotEqual(view.get_paths_for_node('child'),[(0,0)])
        self.tree.add_node(node2)
        self.assertTrue('futur' in view.node_parents('child'))
        
    def test_adding_to_late_parent3(self):
        '''Another tricky case with late parent. This was
        a very rare but existing crash'''
        view = self.tree.get_viewtree(refresh=True)
        view.apply_filter('red')
        node = DummyNode('child')
        node.add_color('red')
        self.tree.add_node(node)
        node2 = view.get_node('0')
        node2.remove_color('red')
        node.add_parent('0')
        node.modified()
        self.assertEqual(len(view.node_parents('child')),0)
        self.assertNotEqual(view.get_paths_for_node('child'),[('0','child')])
        node2.add_color('red')
        self.assertTrue('0' in view.node_parents('child'))
        
    def test_adding_self_parent(self):
        '''A node cannot be its own parent'''
        view = self.tree.get_viewtree(refresh=True)
        node = view.get_node('0')
        node.add_parent('0')
        self.assertEqual(len(node.get_parents()),0)
        self.assertEqual(len(node.get_children()),0)
        node.set_parent('0')
        self.assertEqual(len(node.get_parents()),0)
        self.assertEqual(len(node.get_children()),0)
        node.add_child('0')
        self.assertEqual(len(node.get_parents()),0)
        self.assertEqual(len(node.get_children()),0)
        
        
    def test_multiple_children(self):
        '''We test a node with two children.'''
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('child')
        node2 = DummyNode('child2')
        self.tree.add_node(node,parent_id='0')
        self.tree.add_node(node2,parent_id='0')
        #We first test that the childrens are both there.
        self.assertEqual(view.node_n_children('0'),2)
        self.assertEqual(view.next_node('child'),'child2')
        #We build a list of children paths
        paths = []
        paths += view.get_paths_for_node('child')
        paths += view.get_paths_for_node('child2')
        #take the paths of the parent - let's call it (X,) "
        roots = view.get_paths_for_node('0')
        #Then, (X,0) and (X,1) should be both in paths of children
        for r in roots:
            p = r + ('child',)
            self.assertTrue(p in paths)
            p = r + ('child2',)
            self.assertTrue(p in paths)
            
    def test_counting_children(self):
        '''We test the number of children, recursively or not'''
        view = self.tree.get_viewtree(refresh=True)
        zero = self.tree.get_node('0')
        zero.add_color('blue')
        node = DummyNode('child')
        node.add_color('blue')
        node2 = DummyNode('child2')
        self.assertEqual(view.node_n_children('0'),0)
        self.tree.add_node(node,parent_id='0')
        self.assertEqual(view.node_n_children('0'),1)
        self.tree.add_node(node2,parent_id='0')
        self.assertEqual(view.node_n_children('0'),2)
        self.assertEqual(view.node_n_children('0',recursive=True),2)
        node3 = DummyNode('child3')
        node3.add_color('blue')
        self.tree.add_node(node3,parent_id='child')
        self.assertEqual(view.node_n_children('0'),2)
        self.assertEqual(view.node_n_children('0',recursive=True),3)
        node4 = DummyNode('child4')
        self.tree.add_node(node4,parent_id='child3')
        self.assertEqual(view.node_n_children('0'),2)
        self.assertEqual(view.node_n_children('0',recursive=True),4)
        self.assertEqual(view.node_n_children('child'),1)
        self.assertEqual(view.node_n_children('child',recursive=True),2)
        view.apply_filter('blue')
        self.assertEqual(view.node_n_children('0'),1)
        self.assertEqual(view.node_n_children('0',recursive=True),2)
        self.assertEqual(view.node_n_children('child'),1)
        self.assertEqual(view.node_n_children('child',recursive=True),1)
        node5 = DummyNode('child5')
        self.tree.add_node(node5,parent_id='child2')
        self.tree.del_node('child4')
        self.assertEqual(view.node_n_children('0'),1)
        node2.add_color('blue')
        self.assertEqual(view.node_n_children('0',recursive=True),3)
        view.unapply_filter('blue')
        self.assertEqual(view.node_n_children('0'),2)
        self.assertEqual(view.node_n_children('0',recursive=True),4)
        self.tree.del_node('child3')
        self.assertEqual(view.node_n_children('0'),2)
        self.assertEqual(view.node_n_children('0',recursive=True),3)
        
            
    def test_clean_multiple_parents(self):
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('child')
        node2 = DummyNode('child2')
        self.tree.add_node(node,parent_id='0')
        self.tree.add_node(node2,parent_id='child')
        node.add_parent('1')
        node2.add_parent('1')
        self.assertEqual(len(view.node_parents('child')),2)
        view.apply_filter('blue')

    def test_adding_to_late_parent_with_leaf_filter(self):
        '''Add a node to a parent not yet in the tree
        then add the parent later'''
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('child')
        self.tree.add_node(node,parent_id='futur')
        all_nodes = view.get_all_nodes()
        self.assertTrue('child' in all_nodes)
        self.assertFalse('futur' in all_nodes)
        self.assertEqual(len(view.node_parents('child')),0)
        #now inserting the parent
        view.apply_filter('leaf')
        node2 = DummyNode('futur')
        self.tree.add_node(node2)
        all_nodes = view.get_all_nodes()
        self.assertTrue('child' in all_nodes)
        self.assertFalse('futur' in all_nodes)
        self.assertFalse('futur' in view.node_parents('child'))
        view.reset_filters()
        self.assertTrue(view.is_displayed('futur'))
        self.assertTrue('futur' in view.node_parents('child'))

    def test_updating_parent(self):
        node = DummyNode('child')
        node.add_color('red')
        self.tree.add_node(node,parent_id='0')
        view = self.tree.get_viewtree(refresh=False)
        view.apply_filter('red')
        self.assertEqual(view.node_parents('child'),['0'])
        path0 = view.get_paths_for_node('0')[0]
        pathchild = path0 + ('child',)
        self.assertEqual(view.get_paths_for_node('child'),[pathchild])
        node0 = view.get_node('0')
        node0.add_color('blue')
        self.assertEqual(view.node_parents('child'),['0'])
        self.assertEqual(view.get_paths_for_node('child'),[pathchild])
        node0.remove_color('red')
        self.assertEqual(view.node_parents('child'),[])
        self.assertEqual(view.get_paths_for_node('child'),[('child',)])
        node0.add_color('red')
        path0 = view.get_paths_for_node('0')[0]
        pathchild = path0 + ('child',)
        self.assertEqual(view.node_parents('child'),['0'])
        self.assertEqual(view.get_paths_for_node('child'),[pathchild])
        
    def test_addchild_with_late_parent(self):
        '''Add a child to a node which is not yet in the tree. 
        We also check with a callback that the path sent is well
        corresponding to the nid received.
        '''
        def check_path(nid,path):
            realnode = view.get_node_for_path(path)
#            self.assertEqual(nid,realnode)
        def printtree(tid,paths=None):
            treestr = ' '
            #The printtree method returns an error when the printed tree
            #is not logical. Thus, by connecting a print tree to signals,
            #the test will fail if there's any inconsistencies.
            view.print_tree(string=True)
        view = self.tree.get_viewtree(refresh=True)
        view.register_cllbck('node-modified-inview',check_path)
        view.register_cllbck('node-deleted-inview',printtree)
        node = DummyNode('child')
        node2 = DummyNode('futur')
        node3 = DummyNode('child2')
        node2.add_child('child')
        node2.add_child('child2')
        self.tree.add_node(node)
        self.tree.add_node(node3)
        all_nodes = view.get_all_nodes()
        self.assertTrue('child' in all_nodes)
        self.assertTrue('child2' in all_nodes)
        self.assertFalse('futur' in all_nodes)
        self.assertEqual(len(view.node_parents('child')),0)
        self.assertEqual(len(view.node_parents('child2')),0)
        #now inserting the parent
        view.apply_filter('leaf')
        self.tree.add_node(node2)
        all_nodes = view.get_all_nodes()
        self.assertTrue('child' in all_nodes)
        self.assertTrue('child2' in all_nodes)
        self.assertFalse('futur' in all_nodes)
        self.assertFalse('futur' in view.node_parents('child'))
        self.assertFalse('futur' in view.node_parents('child2'))
        view.reset_filters()
        self.assertTrue(view.is_displayed('futur'))
        self.assertTrue('futur' in view.node_parents('child'))
        self.assertTrue('futur' in view.node_parents('child2'))
        
    def test_addparent_with_late_child(self):
        '''Add a child not yet in the tree to a node'''
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('parent')
        node2 = DummyNode('futur')
        node.add_child('futur')
        self.tree.add_node(node)
        all_nodes = view.get_all_nodes()
        self.assertTrue('parent' in all_nodes)
        self.assertFalse('futur' in all_nodes)
        self.assertEqual(view.node_n_children('parent'),0)
        #now inserting the parent
        view.apply_filter('leaf')
        self.tree.add_node(node2)
        all_nodes = view.get_all_nodes()
        self.assertTrue('futur' in all_nodes)
        self.assertFalse('parent' in all_nodes)
        self.assertFalse('parent' in view.node_parents('futur'))
        view.reset_filters()
        self.assertTrue(view.is_displayed('parent'))
        self.assertTrue('futur' in view.node_all_children('parent'))
        
    def test_more_late_child(self):
        '''This one is trickier. We add a node with some children.
        Then, we add later a new child between the existing children.
        '''
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('parent')
        node1 = DummyNode('futur1')
        node2 = DummyNode('futur2')
        node3 = DummyNode('futur3')
        node4 = DummyNode('futur4')
        node.add_child('futur1')
        node.add_child('futur2')
        node.add_child('futur3')
        node.add_child('futur4')
        self.tree.add_node(node)
        self.tree.add_node(node1)
        #look, we miss the node 2 !
        self.tree.add_node(node3)
        self.tree.add_node(node4)
        self.assertEqual(view.node_n_children('parent'),3)
        self.tree.add_node(node2)
        self.assertEqual(view.node_n_children('parent'),4)
        
    def test_late_first_child(self):
        '''Futur2 is the child of parent
           Futur1 is both the child of parent and futur2
           Futur1 will be added later, forcing a reorganization.
        '''
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('parent')
        node1 = DummyNode('futur1')
        node2 = DummyNode('futur2')
        node.add_child('futur1')
        node.add_child('futur2')
        node2.add_child('futur1')
        self.tree.add_node(node)
        self.tree.add_node(node2)
        #Look, we didn't add futur1
        self.assertEqual(view.node_n_children('parent'),1)
        self.assertEqual(view.node_n_children('futur2'),0)
        self.assertFalse(view.is_displayed('futur1'))
        #Now we add it !
        self.tree.add_node(node1)
        self.assertEqual(view.node_n_children('parent'),2)
        self.assertEqual(view.node_n_children('futur2'),1)
        self.assertTrue(view.is_displayed('futur1'))
        
    def test_move_node_to_a_multiple_parent(self):
        view = self.tree.get_viewtree(refresh=True)
        node = self.tree.get_node('13')
        node3 = self.tree.get_node('3')
        node.add_parent('9')
        node.add_parent('10')
        self.tree.del_node('3')
        self.assertFalse(self.tree.has_node('3'))
        self.tree.add_node(node3,parent_id='13')
        self.assertEqual(len(view.get_paths_for_node('3')),3)
        self.tree.del_node('3')
        self.tree.move_node('4','13')
        self.assertEqual(len(view.get_paths_for_node('4')),3)
        
    def test_recursive_removing_parent(self):
        """Test behavior of node when its parent goes away.

        When you remove a parent recursively, all the children
        are also removed !
        """
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('temp')
        node.add_color('blue')
        self.tree.add_node(node,parent_id='0')
        all_nodes = self.view.get_all_nodes()
        self.assertTrue('0' in all_nodes)
        self.assertTrue('temp' in all_nodes)
        self.assertSignal(self.view, \
                          'node-deleted-inview', \
                          self.tree.del_node, 1)('0', recursive = True)
        self.assertTrue(('temp',('0', 'temp')) in\
                                 self.recorded_signals['node-deleted-inview'])
        all_nodes = self.view.get_all_nodes()
        self.assertFalse('0' in all_nodes)
        self.assertFalse('temp' in all_nodes)

    def test_move_node(self):
        """Test node movement from parents.

        Check that node can be moved from one node to another,
        and to root.  When moved to root, verify it has no parents.
        """
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('temp')
        node.add_color('blue')
        self.tree.add_node(node,parent_id='0')
        #Testing initial situation
        self.assertTrue(view.node_has_child('0'))
        self.assertTrue('temp' in view.node_all_children('0'))
        self.assertTrue('temp' not in view.node_all_children('1'))

        #Moving node
        self.assertSignal(self.view, \
                          'node-modified-inview', \
                          self.tree.move_node, 2)('temp','1')
#        self.assertTrue(('0',(0,)) in self.recorded_signals['node-modified-inview'])
        self.assertTrue(('1',('1',)) in self.recorded_signals['node-modified-inview'])
        self.assertTrue(view.node_has_child('1'))
        self.assertTrue('temp' in view.node_all_children('1'))
        self.assertTrue('temp' not in view.node_all_children('0'))
        #Now moving to root
        self.tree.move_node('temp')
        self.assertTrue('temp' not in view.node_all_children('1'))
        self.assertTrue('temp' not in view.node_all_children('0'))
        #temp still exist and doesn't have any parents
        all_nodes = self.mainview.get_all_nodes()
        self.assertTrue('temp' in all_nodes)
        self.assertEqual(0,len(self.mainview.node_parents('temp')))

    def test_add_parent(self):
        """Test that a node can have two parents.

        Verify that when a node with a parent gets a second parent, 
        the node can be found in both parent nodes.
        """
        view = self.tree.get_viewtree(refresh = True)
        node = DummyNode('temp')
        node.add_color('blue')
        self.assertSignal(self.view, \
                          'node-modified-inview', \
                          self.tree.add_node, 1)(node, parent_id = '0')
        #Not checking temp. Indeed, it has been added, so there should not 
        #be any modified signal
        self.assertTrue(('0',('0',)) in self.recorded_signals['node-modified-inview'])
        #Testing initial situation
        self.assertTrue(view.node_has_child('0'))
        self.assertTrue('temp' in view.node_all_children('0'))
        self.assertTrue('temp' not in view.node_all_children('1'))
        #Adding another parent
        self.assertSignal(self.view, \
                          'node-modified-inview', \
                          self.tree.add_parent, 1)('temp','1')
        self.assertTrue(('1',('1',)) in self.recorded_signals['node-modified-inview'])
        self.assertTrue(view.node_has_child('1'))
        self.assertTrue('temp' in view.node_all_children('1'))
        self.assertTrue('temp' in view.node_all_children('0'))
    
    #we try to add a task as a child of one of its grand-children.
    #Nothing should happen

    def test_cyclic_paradox(self):
        """Try to add a node as a child of one of its grand-children."""
        view = self.tree.get_main_view()
        node = DummyNode('temp')
        node.add_color('blue')
        self.tree.add_node(node,parent_id='0')
        self.tree.add_parent('0','1')
        self.assertTrue('1' in self.mainview.node_parents('0'))
        self.assertTrue('0' in self.mainview.node_parents('temp'))
        #direct circular relationship
        self.assertRaises(Exception,self.tree.add_parent,'0','temp')
        #More complex circular relationship
        self.assertRaises(Exception,self.tree.add_parent,'1','temp')
        # And then printing => if it stops, nothing ciruclar stays there
        view.print_tree(True)
        
    def test_mainview(self):
        """Verify mainview behavior

        Test that mainview is always up-to-date and raise exception when
        trying to add filters on it
        """
        self.assertRaises(Exception,self.mainview.apply_filter,'blue')
        
    #### Testing each method of the ViewTree
    
    ### Testing each method of the TreeView
    def test_viewtree_get_n_nodes(self):
        """ Test get_n_nodes() method of TreeView

        Check that retrieving counts of nodes with various filters returns
        the expected collections.
        """
        total = self.red_nodes + self.blue_nodes + self.green_nodes
        self.assertEqual(total,self.view.get_n_nodes())
        self.assertEqual(self.green_nodes,self.view.get_n_nodes(withfilters=['green']))
        self.assertEqual(total,self.mainview.get_n_nodes())
        
    def test_viewtree_get_n_nodes_with_cache(self):
        '''Testing the cache of the get_n_nodes'''
        nbr = self.green_nodes
        self.assertEqual(nbr,self.mainview.get_n_nodes(\
                            withfilters=['green'],include_transparent=False))
        node = self.tree.get_node('0')
        node.add_color('green')
        
        self.assertEqual(nbr+1,self.mainview.get_n_nodes(\
                            withfilters=['green'],include_transparent=False))
        node.remove_color('green')
        self.assertEqual(nbr,self.mainview.get_n_nodes(\
                            withfilters=['green'],include_transparent=False))
    
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
        self.assertTrue('0' in all_nodes)
        self.assertTrue('temp' in all_nodes)
        self.assertEqual(self.total+1,len(all_nodes))
        #Mainview
        self.assertTrue('0' in all_nodes2)
        self.assertTrue('temp' in all_nodes2)
        self.assertEqual(self.total+1,len(all_nodes2))
        #Removing the node
        self.tree.del_node('1')
        all_nodes = self.view.get_all_nodes()
        all_nodes2 = self.mainview.get_all_nodes()
        self.assertFalse('1' in all_nodes)
        self.assertTrue('temp' in all_nodes)
        self.assertEqual(self.total,len(all_nodes))
        #mainview
        self.assertFalse('1' in all_nodes2)
        self.assertTrue('temp' in all_nodes2)
        self.assertEqual(self.total,len(all_nodes2))
        
        
    def test_viewtree_get_node_for_path(self):
        view = self.tree.get_viewtree(refresh=True)
        #nid1 and nid2 are not always the same
        nid1 = view.get_node_for_path(('0',))
        nid2 = self.mainview.get_node_for_path(('0',))
        self.assertTrue(nid1 != None)
        self.assertTrue(nid2 != None)
        #Thus we do a mix of test.
        nid1b = view.next_node(nid1)
        path1b = view.get_paths_for_node(nid1b)
        self.assertEqual([(nid1b,)],path1b)
        #same for mainview
        nid2b = self.mainview.next_node(nid2)
        path2b = self.mainview.get_paths_for_node(nid2b)
        self.assertEqual([(nid2b,)],path2b)
        #with children
        node = DummyNode('temp')
        node.add_color('blue')
        self.tree.add_node(node,parent_id=nid1)
        self.tree.add_parent('temp',nid2)
        self.assertEqual('temp',self.mainview.get_node_for_path((nid1,'temp')))
        self.assertEqual('temp',view.get_node_for_path((nid2,'temp')))
        #Adding a child to the child
        node2 = DummyNode('temp2')
        node2.add_color('blue')
        self.tree.add_node(node2,parent_id=nid1)
        node = DummyNode('temp_child')
        node.add_color('blue')
        self.tree.add_node(node,parent_id='temp2')
        self.assertEqual('temp_child',view.get_node_for_path((nid1,'temp2','temp_child')))
        self.tree.add_parent('temp2',nid2)
        self.assertEqual('temp_child',self.mainview.get_node_for_path((nid2,'temp2','temp_child')))
        #with filters
        view.apply_filter('blue')
        pl = view.get_paths_for_node('temp2')
        for p in pl:
            pp = p + ('temp_child',)
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
            pp += (str(firstgreen+i),)
        #with filters
        view.apply_filter('green')
        pp = view.get_paths_for_node(str(firstgreen+1))[0]
        i = 1
        #Testing all the green nodes (that are in stairs)
        while i < self.green_nodes:
            returned = view.get_paths_for_node(str(firstgreen+i))[0]
            self.assertEqual(pp,returned)
            i+=1
            pp += (str(firstgreen+i),)
        
    def test_viewtree_next_node(self):
        view = self.tree.get_viewtree(refresh=True)
        """Test next_node() for TreeView.

        Add two nodes to a parent, then verify various ways of looking
        at the next node in the parent's list.
        """
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
        """Test node_has_child() for TreeView

        Verify that TreeView's node_n_children()'s return changes after
        a node is added to an empty TreeView instance.
        """
        node = DummyNode('temp')
        node.add_color('blue')
        self.assertFalse(view.node_has_child('0'))
        self.assertFalse(self.mainview.node_has_child('0'))
        #Adding the node to the tree
        self.tree.add_node(node,parent_id='0')
        self.assertTrue(view.node_has_child('0'))
        self.assertTrue(self.mainview.node_has_child('0'))
        
    def test_moving_to_future_parent(self):
        view = self.tree.get_viewtree(refresh=True)
        node = DummyNode('future_par')
        node2 = DummyNode('child')
        self.tree.add_node(node2,parent_id='0')
        self.assertTrue('child' in view.node_all_children('0'))
        node2.set_parent('future_par')
        self.assertFalse('child' in view.node_all_children('0'))
        self.assertFalse(node2.has_parent())
        self.tree.add_node(node)
        self.assertTrue('child' in view.node_all_children('future_par'))
        self.assertTrue(node2.has_parent())
    
    def test_viewtree_node_all_children(self):
        view = self.tree.get_viewtree(refresh=True)
        self.assertEqual(0,len(view.node_all_children('0')))
        """Test node_all_children() for TreeView.

        We also test node_n_children here. Nearly the same method.
        """
        #checking that 0 and 1 are in root
        self.assertTrue('0' in view.node_all_children())
        self.assertTrue('1' in view.node_all_children())
        self.assertTrue('0' in self.mainview.node_all_children())
        self.assertTrue('1' in self.mainview.node_all_children())
        node = DummyNode('temp')
        node.add_color('blue')
        #adding a new children
        self.tree.add_node(node,parent_id='0')
        self.assertEqual(1,view.node_n_children('0'))
        self.assertTrue('temp' in view.node_all_children('0'))
        self.assertEqual(1,self.mainview.node_n_children('0'))
        self.assertTrue('temp' in self.mainview.node_all_children('0'))
        #Testing with a filter
        view.apply_filter('red')
        self.assertFalse('temp' in view.node_all_children('0'))
        view.unapply_filter('red')
        #moving an existing children
        self.tree.move_node('1','0')
        self.assertEqual(2,view.node_n_children('0'))
        self.assertTrue('1' in view.node_all_children('0'))
        self.assertFalse('1' in view.node_all_children())
        self.assertEqual(2,self.mainview.node_n_children('0'))
        self.assertTrue('1' in self.mainview.node_all_children('0'))
        self.assertFalse('1' in self.mainview.node_all_children())
        #removing a node
        self.tree.del_node('temp')
        self.assertEqual(1,view.node_n_children('0'))
        self.assertFalse('temp' in view.node_all_children('0'))
        self.assertEqual(1,self.mainview.node_n_children('0'))
        self.assertFalse('temp' in self.mainview.node_all_children('0'))
        #moving a node elsewhere
        self.tree.move_node('1')
        self.assertEqual(0,view.node_n_children('0'))
        self.assertFalse('1' in view.node_all_children('0'))
        self.assertEqual(0,self.mainview.node_n_children('0'))
        self.assertFalse('1' in self.mainview.node_all_children('0'))
        #checking that '1' is back in root
        self.assertTrue('1' in view.node_all_children())
        self.assertTrue('1' in self.mainview.node_all_children())
        
    def test_viewtree_node_nth_child(self):
        """Test node_nth_child() for TreeView.

        Verify that when retrieving a given child node, that it is
        returned, except when requesting a node not in the tree or that
        is not present due being filtered out.
        """
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
        """Test node_parents() for TreeView.

        Verify that a node's parents can be retrieved, if it has any.
        Check that if a node has multiple parents, that both parents are
        returned.
        """
        #Checking that a node at the root has no parents
        self.assertEqual([],view.node_parents('0'))
        self.assertEqual([],self.mainview.node_parents('0'))
        #Adding a child
        node = DummyNode('temp')
        node.add_color('blue')
        self.tree.add_node(node,parent_id='0')
        self.assertEqual(['0'],view.node_parents('temp'))
        self.assertEqual(['0'],self.mainview.node_parents('temp'))
        #adding a second node.add_child('0')parent
        self.tree.add_parent('temp','1')
        self.assertEqual(['0','1'],view.node_parents('temp'))
        self.assertEqual(['0','1'],self.mainview.node_parents('temp'))
        #now with a filter
        view.apply_filter('blue')
        self.assertEqual([],view.node_parents('temp'))
        #if the node is not displayed, asking for parents will raise an error
        view.unapply_filter('blue')
        view.apply_filter('red')
        self.assertRaises(IndexError,view.node_parents,'temp')
        

    def test_viewtree_is_displayed(self):
        view = self.tree.get_viewtree(refresh=True)
        """Test is_displayed() for TreeView.

        Verify that a node is shown as displayed once it's been added
        to the tree, but not if an active filter should be hiding it.
        """
        node = DummyNode('temp')
        node.add_color('blue')
        self.assertFalse(view.is_displayed('temp'))
        self.assertFalse(self.mainview.is_displayed('temp'))
        #Adding the node to the tree
        self.tree.add_node(node,parent_id='0')
        self.assertTrue(view.is_displayed('temp'))
        self.assertTrue(self.mainview.is_displayed('temp'))
        view.apply_filter('blue')
        self.assertTrue(view.is_displayed('temp'))
        view.apply_filter('red')
        self.assertFalse(view.is_displayed('temp'))





############ Filters

    def test_simple_filter(self):
        view = self.tree.get_viewtree(refresh=False)
        test = TreeTester(view)
        """Test use of filters to restrict nodes shown.

        When the 'red' filter is applied, only nodes with the 'red' color
        should be returned.  Applying the 'blue' filter on top of that should
        result in no nodes, since there are no nodes with both 'red' and 'blue'.

        When two filters are applied, and the second one is removed, the
        result should be the same as if only the first one had been applied.

        When a node gains a color, check that it is filtered appropriately.

        When a displayed node is added to a non-displayed parent, it
        should still be displayed.
        """
        view.apply_filter('red')
        test.test_validity()
        self.assertEqual(self.red_nodes,view.get_n_nodes())
        self.assertEqual(self.red_nodes,view.get_n_nodes(withfilters=['red']))
        self.assertEqual(0,view.get_n_nodes(withfilters=['blue']))
        #Red nodes are all at the root
        self.assertEqual(self.red_nodes,view.node_n_children())
        #applying another filter
        view.apply_filter('green')
        test.test_validity()
        self.assertEqual(0,view.get_n_nodes())
        #unapplying the first filter
        view.unapply_filter('red')
        test.test_validity()
        self.assertEqual(self.green_nodes,view.get_n_nodes())
        self.assertEqual(self.green_nodes,view.get_n_nodes(withfilters=['green']))
        self.assertEqual(0,view.get_n_nodes(withfilters=['red']))
        #There's only one green node at the root
        self.assertEqual(1,view.node_n_children())
        #Modifying a node to make it red and green
        self.assertFalse(view.is_displayed('0'))
        node = view.get_node('0')
        node.add_color('green')
        #It should now be in the view
        self.assertTrue(view.is_displayed('0'))
        self.assertEqual(1,view.get_n_nodes(withfilters=['red']))
        self.assertEqual(2,view.node_n_children())
        #Now, we add a new node
        node = DummyNode('temp')
        node.add_color('green')
        self.tree.add_node(node)
        test.test_validity()
        #It should now be in the view
        self.assertTrue(view.is_displayed('temp'))
        self.assertEqual(3,view.node_n_children())
        #We remove it
        self.tree.del_node('temp')
        test.test_validity()
        self.assertFalse(view.is_displayed('temp'))
        self.assertEqual(2,view.node_n_children())
        #We add it again as a children of a non-displayed node
        self.tree.add_node(node,parent_id='1')
        test.test_validity()
        self.assertTrue(view.is_displayed('temp'))
        self.assertEqual(3,view.node_n_children())
        #It should not have parent
        self.assertEqual(0,len(view.node_parents('temp')))

    def test_leaf_filter(self):
        view = self.tree.get_viewtree(refresh=False)
        test = TreeTester(view)
        """Test filtering to show only the leaf nodes.

        When the 'leaf' filter is applied and a child added to a node,
        the parent node should not be present in the results.
        """
        view.apply_filter('leaf')
        total = self.red_nodes + self.blue_nodes
        self.assertEqual(total,view.get_n_nodes())
        view.apply_filter('green')
        self.assertEqual(1,view.get_n_nodes())
        nid = view.get_node_for_path(('14',))
        #Now, we add a new node
        node = DummyNode('temp')
        node.add_color('green')
        self.tree.add_node(node,parent_id='14')
        self.assertEqual(1,view.get_n_nodes())
        nid = view.get_node_for_path(('temp',))
        self.assertEqual('temp',nid)
        test.test_validity()

    #we copy/paste the test
    def test_flatleaves_filters(self):
        """We apply a leaves + flat filter and the result
        should be the same as a simple leaf filter.
        """
        view = self.tree.get_viewtree(refresh=False)
        test = TreeTester(view)
        view.apply_filter('flatleaves')
        total = self.red_nodes + self.blue_nodes
        self.assertEqual(total,view.get_n_nodes())
        view.apply_filter('green')
        self.assertEqual(1,view.get_n_nodes())
        nid = view.get_node_for_path(('14',))
        #Now, we add a new node
        node = DummyNode('temp')
        node.add_color('green')
        self.tree.add_node(node,parent_id=nid)
        self.assertEqual(1,view.get_n_nodes())
        nid = view.get_node_for_path(('temp',))
        self.assertEqual('temp',nid)
        test.test_validity()
        
    #green are stairs
    #the flat filter should make them flat
    def test_flat_filters(self):
        """Test a flat filter.
        
        Green nodes are in "stairs" (each one being the child of another)
        By applying a filter with the flat properties, we test that
        all the nodes are now seen "flately".
        """
        view = self.tree.get_viewtree(refresh=False)
        test = TreeTester(view)
        view.apply_filter('flatgreen')
        #all green nodes should be visibles
        self.assertEqual(self.green_nodes,view.get_n_nodes())
        i = 10
        nodes = []
        #we check that the paths are on the root
        while i < self.green_nodes:
            nid = view.get_node_for_path((str(i),))
            view.print_tree()
            nodes.append(nid)
            self.assertFalse(nid == None)
            #let see if a node has parent
            self.assertFalse(view.node_has_parent(nid))
            #and, of course, it cannot have children
            self.assertFalse(view.node_has_child(nid))
            i += 1
        #we check that we have seen all the nodes
        i = 10
        while i <= self.green_nodes :
            self.assertTrue(str(self.total-i) in nodes)
            i += 1
        test.test_validity()
        
    def test_transparent_filters(self):
        view = self.tree.get_viewtree(refresh=False)
        test = TreeTester(view)
        """Test excluding transparent filters

        Filters marked with the 'transparent' property should apply in get_n_nodes()
        normally, but can be turned off via the include_transparent parameter.
        """
        view.apply_filter('transgreen')
        self.assertEqual(self.green_nodes,view.get_n_nodes())
        self.assertEqual(self.total,view.get_n_nodes(include_transparent=False))
        #Now with filters in the counting
        count1 = view.get_n_nodes(withfilters=['transblue'])
        count2 = view.get_n_nodes(withfilters=['transblue'],\
                                                    include_transparent=False)
        self.assertEqual(0,count1)
        self.assertEqual(self.blue_nodes,count2)
        test.test_validity()

    def test_view_signals(self):
        view = self.tree.get_viewtree(refresh = True)
        
    def test_update_callback(self):
        '''We test the update callbacks and we check that the path
            received is well corresponding to the nid received'''
        def check_path(nid,path):
            self.assertEqual(view.get_node_for_path(path),nid)
            self.assertTrue(path in view.get_paths_for_node(nid))
        view = self.tree.get_viewtree(refresh=False)
        test = TreeTester(view)
        view.register_cllbck('node-modified-inview',check_path)
        view.register_cllbck('node-added-inview',check_path)
        view.apply_filter('leaf')
        view.unapply_filter('leaf')
        test.test_validity()
        
    def test_torture(self):
        '''This is a torture test, where we will do whatever
        we want in random order.
        '''
        view = self.tree.get_viewtree(refresh = False)
        test = TreeTester(view)
        view.reset_filters(refresh=True)
        node = DummyNode('parent')
        node.add_child('1')
        node.add_child('3')
        node.add_child('5')
        node.add_child('7')
        node.add_child('9')
        node.add_child('11')
        self.assertEqual(node.get_id(), "parent")
        self.assertFalse(view.is_displayed('parent'))
        self.tree.add_node(node)
        test.test_validity()
        self.assertEqual(view.node_n_children('parent'),6)
        self.assertEqual(node.get_id(), "parent")
        view.apply_filter('blue')
        test.test_validity()
        self.assertEqual(node.get_id(), "parent")
        self.assertFalse(view.is_displayed('parent'))
        node.add_color('blue')
        test.test_validity()
        self.assertTrue(view.is_displayed('parent'))
        self.assertEqual(view.node_n_children('parent'),3)
        
    def test_copypasting_child(self):
        view = self.tree.get_viewtree(refresh = False)
        test = TreeTester(view)
        view.apply_filter('green')
        node = DummyNode('child')
        node.add_color('green')
        node1 = DummyNode('child2')
        node1.add_color('green')
        node2 = DummyNode('parent')
        node2.add_color('green')
        self.tree.add_node(node2)
        self.tree.add_node(node,parent_id='10')
        self.tree.add_node(node1,parent_id='10')
        #We copy paste 'child' into 'parent'
        node2.add_child('child')
        test.test_validity()

    def test_speed(self):
        '''
        Performance tests. Patches that reduce performance too much are not
        acceptable
        '''
        self.tester.quit()
        BIG_NUMBER = 1000
        view = self.tree.get_viewtree(refresh = False)
        nodes_id = []
        start = time.time()
        for index in xrange(BIG_NUMBER):
            node = DummyNode("stress" + str(index))
            nodes_id.append(node.get_id())
            self.tree.add_node(node)
        end = time.time()
        print "\nADDING %d NODES: %f" % (BIG_NUMBER, end - start)

        start = time.time()
        for node_id in nodes_id:
            self.tree.refresh_node(node_id)
        end = time.time()
        print "\nUPDATING %d NODES: %f" % (BIG_NUMBER, end - start)

        start = time.time()
        for node_id in nodes_id:
            self.tree.del_node(node_id)
        end = time.time()
        print "\nDELETING %d NODES: %f" % (BIG_NUMBER, end - start)

    def test_remove_grand_grand_parent(self):
        """ Remove from tree a node which is parent of child 
        which is also parent.

        Using example tree from setUp()

        root:
             0
             1
             2
             3
             4
             5
             6
             7
             8
             9 <- We want to remove this
              10
               11
                12
                 13
                  14

        The result should be
        root:
             1
             2
             3
             4
             5
             6
             7
             8
             10
              11
               12
                13
                 14
        """

        self.tree.del_node("9")

        # Testing expected parents => (node, [parents])
        relationships = [
            (0,[]), (1,[]), (2,[]), (3,[]), (4,[]), (5,[]), (6,[]), (7,[]), (8,[]),
            (10,[]), (11,[10]), (12,[11]), (13,[12]), (14,[13]),
        ]

        for node_id, parents in relationships:
            # Convert IDs to strings
            node_id = str(node_id)
            parents = [str(parent) for parent in parents]

            self.assertEqual(self.tree.get_node(node_id).get_parents(), parents)

    def test_put_orphan_to_root(self):
        """ Put orphan (a child of deleted parent) to root,
        not to the parent of the parent

        Using example tree from setUp()

        root:
             0
             1
             2
             3
             4
             5
             6
             7
             8
             9
              10
               11
                12
                 13 <- we remove this
                  14

        The result should be
        root:
             0
             1
             2
             3
             4
             5
             6
             7
             8
             10
              11
               12
             14
        """

        self.tree.del_node("13")
        orphan_node = self.tree.get_node("14")
        self.assertEqual(orphan_node.get_parents(), [])

    def test_delete_task_randomly(self):
        """ Create a "big" number of tasks and delete them in "random" order.

        Testability is done by having always the same seed for random number generator."""

        # Fairly random number (Debian-like :-D)
        SEED_NUMBER = 4
        ADD_NODES_TO_TREE = 20
        BASE_ID = 100

        original_state = random.getstate()
        random.seed(SEED_NUMBER)

        view = self.tree.get_viewtree()
        total_count = view.get_n_nodes()

        parent_id = None
        for i in range(ADD_NODES_TO_TREE):
            node_id = str(BASE_ID + i)
            node = TreeNode(node_id, parent_id)
            self.tree.add_node(node)
            parent_id = node_id

        self.assertEqual(total_count + ADD_NODES_TO_TREE, view.get_n_nodes())

        nodes = view.get_all_nodes()
        random.shuffle(nodes)

        for node_id in nodes:
            self.tree.del_node(node_id)

        random.setstate(original_state)

    def test_add_existing_relationship(self):
        """ Add the same relationship several times.

        LibLarch should recognize that the relationship exists and do nothing. """

        view = self.tree.get_viewtree()
        count = view.get_n_nodes()

        parent_id = "parent"
        parent = DummyNode(parent_id)
        parent.add_parent("12")
        parent.add_parent("0")
        self.tree.add_node(parent)
        count += 1
        self.assertEqual(count, view.get_n_nodes())

        child_id = "child"
        child = DummyNode(child_id)
        self.tree.add_node(child)
        count += 1

        # A random number of iterations
        for i in range(20):
            child.add_parent(parent_id)

            self.assertEqual(count, view.get_n_nodes())
            self.assertEqual([parent_id], view.node_parents(child_id))
            self.assertEqual([child_id], view.node_all_children(parent_id))
            self.assertEqual(["0", "12"], sorted(view.node_parents(parent_id)))

    def test_remove_parent_of_multiple_parent_task_child(self):
        """ Remove one parent of multiple parent task child.

        The child should stay where it is, not moved to root. """

        view = self.tree.get_viewtree()

        self.tree.add_node(DummyNode("t1"))
        self.tree.add_node(DummyNode("t2"))

        node = DummyNode("t3")
        node.add_parent("t1")
        self.tree.add_node(node)

        node = DummyNode("t4")
        node.add_parent("t3")
        node.add_parent("t2")
        self.tree.add_node(node)

        node = DummyNode("t5")
        node.add_parent("t4")
        self.tree.add_node(node)

        node = DummyNode("t6")
        node.add_parent("t1")
        self.tree.add_node(node)

        self.assertEqual(["t3", "t6"], view.node_all_children("t1"))
        self.assertEqual(["t4"], view.node_all_children("t2"))
        self.assertEqual(["t3", "t2"], view.node_parents("t4"))
        self.assertEqual(["t4"], view.node_parents("t5"))

        self.tree.del_node("t3")

        self.assertEqual(["t6"], view.node_all_children("t1"))
        self.assertEqual(["t4"], view.node_all_children("t2"))
        self.assertEqual(["t2"], view.node_parents("t4"))
        self.assertEqual(["t4"], view.node_parents("t5"))

    def test_remove_parent_of_multiple_children(self):
        """ Remove parent of multiple immediate children.

        This is very basic test but sometimes it fails. """
        self.tree.add_node(DummyNode("A"))
        self.tree.add_node(DummyNode("B"), parent_id="A")
        self.tree.add_node(DummyNode("C"), parent_id="A")

        self.tree.del_node("A")

    def test_add_children_first(self):
        """ Set children of a task first and only then add it tree.

        This is the way the localfile backend works. """

        CHILDREN_NUM = 6
        children = ['%d@1' % i for i in range(1, CHILDREN_NUM+1)]
        master_id = '0@1'

        view = self.tree.get_main_view()
        # We need to access root of the tree
        tree_root = view.get_node('root')

        # Clean tree first
        for node_id in view.get_all_nodes():
            self.tree.del_node(node_id)

        self.assertEqual([], view.get_all_nodes())
        self.assertEqual([], tree_root.get_children())

        # Add master node with reference of children
        master = DummyNode(master_id)
        for child_id in children:
            master.add_child(child_id)
        self.tree.add_node(master)

        # Now add children
        for child_id in children:
            self.tree.add_node(DummyNode(child_id))

        # Check status
        self.assertEqual([master_id] + children, sorted(view.get_all_nodes()))

        # Master node
        self.assertEqual([], view.node_parents(master_id))
        self.assertEqual(children, view.node_all_children(master_id))

        # Children
        for node_id in children:
            self.assertEqual([master_id], view.node_parents(node_id))
            self.assertEqual([], view.node_all_children(node_id))

        # Check root => there should be no nodes but master
        self.assertEqual([master_id], tree_root.get_children())

    def test_maintree_print_tree(self):
        """ Test MainTree's print_tree() to string """
        view = self.tree.get_main_view()
        self.assertEqual(view.print_tree(True),
"""root
 0
 1
 2
 3
 4
 5
 6
 7
 8
 9
  10
   11
    12
     13
      14
""")
        self.tree.add_node(DummyNode('temp'), '0')
        self.assertEqual(['temp'], view.node_all_children('0'))
        self.assertEqual(view.print_tree(True),
"""root
 0
  temp
 1
 2
 3
 4
 5
 6
 7
 8
 9
  10
   11
    12
     13
      14
""")

    def test_almost_circular_dependencies(self):
        """ Have the nasty tree:
        n1
        -n2
        -n3
        --n2
        """

        a = DummyNode("a")
        b = DummyNode("b")
        c = DummyNode("c")

        a.add_child("b")
        a.add_child("c")
        c.add_child("b")

        self.tree.add_node(a)
        self.tree.add_node(b)
        self.tree.add_node(c)

    def test_remove_tasks(self):
        """ This test case is based on real code and a bug.
        have node 'a' with children 'b', 'c' and then remove
        'a' recursively. """
        a = DummyNode("a")
        b = DummyNode("b")
        c = DummyNode("c")

        a.add_child("b")
        a.add_child("c")

        self.tree.add_node(a)
        self.tree.add_node(b)
        self.tree.add_node(c)

        for node_id in ['a', 'b', 'c']:
            if self.tree.has_node(node_id):
                self.tree.del_node(node_id, True)

    def test_remove_recursively_clean(self):
        """ Test that when we have task with many subtasks,
        all will be removed and no will left in tree """
        N = 50
        prefix = "child_"

        view = self.tree.get_main_view()

        parent = DummyNode("parent")
        self.tree.add_node(parent)
        for i in range(N):
            node_id = prefix + str(i)
            self.tree.add_node(DummyNode(node_id))
            parent.add_child(node_id)

        self.tree.del_node("parent", True)

        self.assertTrue("parent" not in view.get_all_nodes())
        # No orphans are left
        for node_id in view.get_all_nodes():
            self.assertFalse(node_id.startswith(prefix))
            
    def test_queue_action_one_action(self):
        self.testvalue = 0
        def action(x):
            self.testvalue += x
        self.tree = Tree()
        self.view = self.tree.get_viewtree()
        self.tree.add_filter('blue',self.is_blue)
        self.tree.add_filter('green',self.is_green)
        self.view.apply_filter('green')
        bl = DummyNode('bl')
        bl.add_color('blue')
        gr = DummyNode('gr')
        gr.add_color('green')
        self.view.queue_action('bl',action,1)
        self.view.queue_action('gr',action,2)
        self.assertEqual(self.testvalue,0)
        self.tree.add_node(bl)
        self.assertEqual(self.testvalue,0)
        self.tree.add_node(gr)
        self.assertEqual(self.testvalue,2)
        
    def test_queue_action_multiples_actions(self):
        self.testvalue = 0
        def action(x):
            self.testvalue += x
        self.tree = Tree()
        self.view = self.tree.get_viewtree()
        self.tree.add_filter('blue',self.is_blue)
        self.tree.add_filter('green',self.is_green)
        self.view.apply_filter('green')
        bl = DummyNode('bl')
        bl.add_color('blue')
        gr = DummyNode('gr')
        gr.add_color('green')
        self.view.queue_action('bl',action,1)
        self.view.queue_action('bl',action,3)
        self.view.queue_action('gr',action,2)
        self.assertEqual(self.testvalue,0)
        self.tree.add_node(bl)
        self.assertEqual(self.testvalue,0)
        self.tree.add_node(gr)
        self.assertEqual(self.testvalue,2)
        self.view.unapply_filter('green')
        #test value should be 2 + 1 + 3 = 6
        self.assertEqual(self.testvalue,6)
        
        
    def test_recursive_count(self):
        self.value = 0
        self.view = self.tree.get_viewtree()
        def update(x,path):
            if x == '0':
                self.value = self.view.node_n_children(x,recursive=True)
        self.view.register_cllbck('node-modified-inview',update)
        a = DummyNode('a')
        b = DummyNode('b')
        c = DummyNode('c')
        d = DummyNode('d')
        d.add_color('blue')
        zero = self.tree.get_node('0')
        zero.add_color('blue')
        self.view.flush()
        self.assertEqual(self.value,0)
        self.tree.add_node(a,'0')
        self.view.flush()
        self.assertEqual(self.value,1)
        self.tree.add_node(b,'a')
        self.view.flush()
        self.assertEqual(self.value,2)
        self.tree.add_node(c,'b')
        self.view.flush()
        self.assertEqual(self.value,3)
        self.tree.add_node(d,'0')
        self.view.flush()
        self.assertEqual(self.value,4)
        self.tree.del_node('b')
        self.view.flush()
        self.assertEqual(self.value,2)
        self.view.apply_filter('blue')
        self.view.flush()
        self.assertEqual(self.value,1)     
        

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
