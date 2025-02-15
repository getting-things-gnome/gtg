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

from gi.repository import GObject

from GTG.core.base_store import StoreItem


class TestStoreItemProperties(TestCase):


    def test_init(self):
        uuid = uuid4()
        item = StoreItem(uuid)
        self.assertEqual(item.id, uuid)


    def test_children_count_default_value(self):
        item = StoreItem(uuid4())
        self.assertEqual(item.children_count, 0)
        self.assertFalse(item.has_children)


    def test_children_count_single_child(self):
        item = StoreItem(uuid4())
        item.children.append(StoreItem(uuid4))
        self.assertEqual(item.children_count, 1)
        self.assertTrue(item.has_children)


    def test_children_count_multiple_children(self):
        item = StoreItem(uuid4())
        item.children = [ StoreItem(uuid4) for _ in range(15) ]
        self.assertEqual(item.children_count, 15)
        self.assertTrue(item.has_children)



class Dummy(GObject.Object):
    """A dummy GObject that helps test bindings."""

    int_value = 0
    num_of_updates = 0

    @GObject.Property(type=int)
    def an_int(self):
        return self.int_value

    @an_int.setter
    def an_int(self,value):
        self.int_value = value
        self.num_of_updates += 1



class TestStoreItemAddChild(TestCase):


    def setUp(self):
        self.root = StoreItem(uuid4())
        self.child = StoreItem(uuid4())
        self.root.children = [ self.child ]
        self.dummy = Dummy()


    def test_add_new_child(self):
        new_item = StoreItem(uuid4())
        self.root.add_child(new_item)
        self.assertIn(new_item,self.root.children)


    def test_adding_existing_child_does_nothing(self):
        self.root.add_child(self.child)
        self.assertEqual(self.root.children,[self.child])


    def test_has_child_notification_for_first_child(self):
        self.child.bind_property('has_children',self.dummy,'an_int',GObject.BindingFlags.DEFAULT,lambda _,b: 5)
        new_item = StoreItem(uuid4())
        self.child.add_child(new_item)
        self.assertEqual(self.dummy.num_of_updates,1)


    def test_children_count_notification(self):
        self.root.bind_property('children_count',self.dummy,'an_int',GObject.BindingFlags.DEFAULT)
        new_item = StoreItem(uuid4())
        self.root.add_child(new_item)
        self.assertEqual(self.dummy.num_of_updates,1)


    def test_no_has_children_notification_for_non_first_child(self):
        self.root.bind_property('has_children',self.dummy,'an_int',GObject.BindingFlags.DEFAULT,lambda _,b: 5)
        new_item = StoreItem(uuid4())
        self.root.add_child(new_item)
        self.assertEqual(self.dummy.num_of_updates,0)


    def test_no_children_count_notification_for_existing_child(self):
        self.root.bind_property('children_count',self.dummy,'an_int',GObject.BindingFlags.DEFAULT)
        self.root.add_child(self.child)
        self.assertEqual(self.dummy.num_of_updates,0)



class TestStoreItemRemoveChild(TestCase):


    def setUp(self):
        self.root = StoreItem(uuid4())
        self.child1 = StoreItem(uuid4())
        self.child2 = StoreItem(uuid4())
        self.root.children = [ self.child1, self.child2 ]
        self.dummy = Dummy()


    def test_remove_child(self):
        self.root.remove_child(self.child1)
        self.assertNotIn(self.child1,self.root.children)


    def test_removing_non_existing_child_does_nothing(self):
        new_item = StoreItem(uuid4())
        self.root.remove_child(new_item)
        self.assertEqual(self.root.children,[self.child1,self.child2])


    def test_has_child_notification_for_last_child(self):
        self.root.bind_property('has_children',self.dummy,'an_int',GObject.BindingFlags.DEFAULT,lambda _,b: 5)
        self.root.remove_child(self.child1)
        self.root.remove_child(self.child2)
        self.assertEqual(self.dummy.num_of_updates,1)


    def test_children_count_notification(self):
        self.root.bind_property('children_count',self.dummy,'an_int',GObject.BindingFlags.DEFAULT)
        self.root.remove_child(self.child1)
        self.assertEqual(self.dummy.num_of_updates,1)


    def test_no_has_children_notification_for_non_last_child(self):
        self.root.bind_property('has_children',self.dummy,'an_int',GObject.BindingFlags.DEFAULT,lambda _,b: 5)
        self.root.remove_child(self.child2)
        self.assertEqual(self.dummy.num_of_updates,0)


    def test_no_children_count_notification_for_non_existing_child(self):
        self.root.bind_property('children_count',self.dummy,'an_int',GObject.BindingFlags.DEFAULT)
        new_item = StoreItem(uuid4())
        self.root.remove_child(new_item)
        self.assertEqual(self.dummy.num_of_updates,0)



class TestStoreItemGetAncestors(TestCase):


    def setUp(self):
        self.root = StoreItem(uuid4())

        self.children = [ StoreItem(uuid4()) for _ in range(5) ]
        self.root.children = self.children
        for c in self.children:
            c.parent = self.root

        self.grandchildren = [ StoreItem(uuid4()) for _ in range(7) ]
        self.root.children[-1].children = self.grandchildren
        for c in self.grandchildren:
            c.parent = self.root.children[-1]

        self.greatgrandchildren = [ StoreItem(uuid4()) for _ in range(2) ]
        self.root.children[-1].children[0].children = self.greatgrandchildren
        for c in self.greatgrandchildren:
            c.parent = self.root.children[-1].children[0]


    def test_default_value(self):
        item = StoreItem(uuid4())
        self.assertEqual(item.get_ancestors(),[])


    def test_root_element(self):
        self.assertEqual(self.root.get_ancestors(),[])


    def test_single_ancestor(self):
        self.assertEqual(self.children[3].get_ancestors(),[self.root])


    def test_multiple_ancestors(self):
        expected = [self.root.children[-1].children[0],self.root.children[-1],self.root]
        self.assertEqual(self.greatgrandchildren[0].get_ancestors(),expected)



class TestStoreItemIsParentableTo(TestCase):


    def setUp(self):
        self.root = StoreItem(uuid4())
        self.strangers = [ StoreItem(uuid4()) for _ in range(3) ]

        self.children = [ StoreItem(uuid4()) for _ in range(5) ]
        self.root.children = self.children
        for c in self.children:
            c.parent = self.root

        self.grandchildren = [ StoreItem(uuid4()) for _ in range(7) ]
        self.root.children[-1].children = self.grandchildren
        for c in self.grandchildren:
            c.parent = self.root.children[-1]

        self.greatgrandchildren = [ StoreItem(uuid4()) for _ in range(2) ]
        self.root.children[-1].children[0].children = self.greatgrandchildren
        for c in self.greatgrandchildren:
            c.parent = self.root.children[-1].children[0]


    def test_forbid_selfparenting(self):
        self.assertFalse(self.root.is_parentable_to(self.root))


    def test_forbid_children(self):
        self.assertFalse(self.root.is_parentable_to(self.children[0]))


    def test_forbid_distant_descendant(self):
        self.assertFalse(self.root.is_parentable_to(self.greatgrandchildren[1]))


    def test_allow_parent(self):
        self.assertTrue(self.children[1].is_parentable_to(self.root))


    def test_allow_distant_ancestor(self):
        self.assertTrue(self.greatgrandchildren[0].is_parentable_to(self.root))


    def test_allow_sibling(self):
        self.assertTrue(self.children[1].is_parentable_to(self.children[2]))


    def test_allow_other_trees(self):
        self.assertTrue(self.greatgrandchildren[0].is_parentable_to(self.strangers[2]))
