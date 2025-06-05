# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2024 - the GTG contributors
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

from unittest import TestCase
from uuid import uuid4

from GTG.core.base_store import StoreItem, BaseStore


class TestBaseStoreRemove(TestCase):


    def setUp(self):
        self.store = BaseStore()

        # add a simple item
        self.simple_item = StoreItem(uuid4())
        self.store.add(self.simple_item)

        # add a tree
        self.tree_items = [ StoreItem(uuid4()) for _ in range(12) ]
        self.store.add(self.tree_items[0])
        for item in self.tree_items[1:4]:
            self.store.add(item,parent_id=self.tree_items[0].id)
        for item in self.tree_items[4:7]:
            self.store.add(item,parent_id=self.tree_items[3].id)
        for item in self.tree_items[7:]:
            self.store.add(item,parent_id=self.tree_items[5].id)


    def test_remove_singel_item(self):
        self.store.remove(self.simple_item.id)
        self.assertEqual(self.store.count(), 12)


    def test_remove_tree(self):
        self.store.remove(self.tree_items[0].id)
        self.assertEqual(self.store.count(), 1)


    def test_remove_child_item(self):
        child_id = self.tree_items[1].id
        self.store.remove(child_id)
        self.assertEqual(self.store.count(), 12)
        self.assertTrue(self.tree_items[1] not in self.tree_items[0].children)


    def test_signals(self):
        removed = set()
        def on_remove(obj,s):
            removed.add(s)
        self.store.connect('removed',on_remove)
        self.store.remove(self.tree_items[0].id)
        self.assertEqual(removed,set(self.tree_items))



class TestBaseStoreParent(TestCase):


    def setUp(self):
        self.store = BaseStore()

        self.root1 = StoreItem(uuid4())
        self.root2 = StoreItem(uuid4())
        self.child = StoreItem(uuid4())
        self.invalid_id = uuid4()

        self.store.add(self.root1)
        self.store.add(self.root2)
        self.store.add(self.child,parent_id=self.root1.id)


    def test_parent_is_set(self):
        self.store.parent(self.root2.id,self.root1.id)
        self.assertEqual(self.root2.parent,self.root1)


    def test_children_list_is_updated(self):
        self.store.parent(self.root2.id,self.root1.id)
        self.assertTrue(self.root2 in self.root1.children)


    def test_root_elements_are_updated(self):
        self.store.parent(self.root2.id,self.root1.id)
        self.assertEqual(self.store.count(root_only=True),1)


    def test_invalid_item_id_raises_exception(self):
        with self.assertRaises(KeyError):
            self.store.parent(self.invalid_id,self.root1.id)


    def test_invalid_item_id_does_not_update_children(self):
        try:
            self.store.parent(self.invalid_id,self.root1.id)
        except KeyError:
            pass
        self.assertTrue(self.invalid_id not in self.root1.children)


    def test_invalid_parent_id_raises_exception(self):
        with self.assertRaises(KeyError):
            self.store.parent(self.root1.id,self.invalid_id)


    def test_invalid_parent_id_does_not_update_parent(self):
        try:
            self.store.parent(self.root1.id,self.invalid_id)
        except KeyError:
            pass
        self.assertEqual(self.root1.parent,None)


    def test_invalid_parent_id_does_not_update_root_elements(self):
        try:
            self.store.parent(self.root1.id,self.invalid_id)
        except KeyError:
            pass
        self.assertEqual(self.store.count(root_only=True),2)



class TestBaseStoreUnparent(TestCase):


    def setUp(self):
        self.store = BaseStore()

        self.root = StoreItem(uuid4())
        self.child1 = StoreItem(uuid4())
        self.child2 = StoreItem(uuid4())
        self.invalid_id = uuid4()

        self.store.add(self.root)
        self.store.add(self.child1,parent_id=self.root.id)
        self.store.add(self.child2,parent_id=self.root.id)


    def test_parent_is_unset(self):
        self.store.unparent(self.child1.id)
        self.assertIsNone(self.child1.parent)


    def test_children_list_is_updated(self):
        self.store.unparent(self.child1.id)
        self.assertEqual(self.root.children,[self.child2])


    def test_list_of_roots_is_updated(self):
        self.store.unparent(self.child2.id)
        self.assertIn(self.child2,self.store.data)


    def test_invalid_item_id_raises_exception(self):
        with self.assertRaises(KeyError):
            self.store.unparent(self.invalid_id)


    def test_unparenting_root_element_has_no_effect(self):
        self.store.unparent(self.root.id)
        self.assertEqual(self.store.data,[self.root])
