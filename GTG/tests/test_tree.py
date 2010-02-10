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

"""Tests for the tagstore."""

import unittest

from GTG.core.tree import Tree,TreeNode

class TestTree(unittest.TestCase):
    """Tests for `Tree`."""
    
    #build a tree. If flat, all nodes are added to the root
    #else, we build a stairs-like structure
    def _build_tree(self,nbr_of_nodes=0,flat=True):
        i = 1
        previous_node = None
        tree = Tree()
        while i <= nbr_of_nodes:
            node_name1 = '%s@1' %(i)
            node_name2 = '%s@%s' %(i,i)
            node1 = TreeNode(node_name1)
            tree.add_node(node1)
            if previous_node and not flat:
                node2 = TreeNode(node_name2)
                tree.add_node(node2,parent=previous_node)
                #previous_node.add_child(node)
                previous_node = node2
            else:
                previous_node = node1
            i+=1
        return tree
            

    def test_root(self):
        #A tree created without an argument has a root
        tree = self._build_tree(0)
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

#    def test_name_is_attribute(self):
#        # The name of the tag is also stored as an attribute.
#        tag = Tag('foo')
#        self.assertEqual('foo', tag.get_attribute('name'))

#    def test_missing_attribute_returns_none(self):
#        # If get_attribute is called for an attribute that doesn't exist, it
#        # returns None.
#        tag = Tag('whatever')
#        result = tag.get_attribute('no-such-attribute')
#        self.assertEqual(None, result)

#    def test_set_attribute_calls_save(self):
#        # Calling set_attribute calls the 'save_cllbk'.
#        save_calls = []
#        tag = Tag('whatever', lambda: save_calls.append(None))
#        tag.set_attribute('new-attribute', 'value')
#        self.assertEqual(1, len(save_calls))

#    def test_set_then_get_attribute(self):
#        # Attributes set with set_attribute can be retrieved with
#        # get_attribute.
#        tag = Tag('whatever', lambda: None)
#        tag.set_attribute('new-attribute', 'value')
#        result = tag.get_attribute('new-attribute')
#        self.assertEqual('value', result)

#    def test_set_non_str_attribute_casts_to_string(self):
#        # If the value of the attribute passed to set_attribute is not a
#        # string, it's cast to a string.
#        tag = Tag('whatever', lambda: None)
#        tag.set_attribute('new-attribute', 42)
#        result = tag.get_attribute('new-attribute')
#        self.assertEqual('42', result)

#    def test_get_all_attributes_initial(self):
#        # Initially, a Tag has only the name attribute.
#        tag = Tag('foo')
#        self.assertEqual(['name'], tag.get_all_attributes())

#    def test_get_all_attributes_after_setting(self):
#        # After attributes are set, get_all_attributes includes those
#        # attributes. The order is not guaranteed.
#        tag = Tag('foo', lambda: None)
#        tag.set_attribute('bar', 'baz')
#        self.assertEqual(set(['name', 'bar']), set(tag.get_all_attributes()))

#    def test_get_all_but_name(self):
#        # If 'butname' is True, then exclude the 'name' attribute.
#        tag = Tag('foo', lambda: None)
#        self.assertEqual([], tag.get_all_attributes(butname=True))
#        tag.set_attribute('bar', 'baz')
#        self.assertEqual(['bar'], tag.get_all_attributes(butname=True))

#    def test_str(self):
#        # str(tag) is 'Tag: <name>'
#        tag = Tag('foo')
#        self.assertEqual('Tag: foo', str(tag))

#    def test_set_name_attribute_does_nothing(self):
#        # The 'name' attribute is set by the constructor. After it is set, it
#        # cannot be changed with further calls to set_attribute.
#        tag = Tag('old', lambda: None)
#        tag.set_attribute('name', 'new')
#        self.assertEqual('old', tag.get_name())
#        self.assertEqual('old', tag.get_attribute('name'))

#    # XXX: The following tests check the current behaviour of the Tag class,
#    # but I'm not sure if they're correct behaviour. -- jml, 2009-07-17
#    def test_save_not_called_on_construction(self):
#        # The save callback isn't called by the constructor, despite the fact
#        # that it sets the name attribute.
#        save_calls = []
#        Tag('old', lambda: save_calls.append(None))
#        self.assertEqual(0, len(save_calls))

#    def test_set_name_doesnt_call_save(self):
#        # Setting the name attribute doesn't call save.
#        save_calls = []
#        tag = Tag('old', lambda: save_calls.append(None))
#        tag.set_attribute('name', 'new')
#        self.assertEqual(0, len(save_calls))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
