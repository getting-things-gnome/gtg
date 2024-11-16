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


    def test_children_count_singel_child(self):
        item = StoreItem(uuid4())
        item.children.append(StoreItem(uuid4))
        self.assertEqual(item.children_count, 1)
        self.assertTrue(item.has_children)


    def test_children_count_multiple_children(self):
        item = StoreItem(uuid4())
        item.children = [ StoreItem(uuid4) for _ in range(15) ]
        self.assertEqual(item.children_count, 15)
        self.assertTrue(item.has_children)



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



class TestStoreItemCheckPossibleParent(TestCase):


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
        self.assertFalse(self.root.check_possible_parent(self.root))


    def test_forbid_children(self):
        self.assertFalse(self.root.check_possible_parent(self.children[0]))


    def test_forbid_distant_descendant(self):
        self.assertFalse(self.root.check_possible_parent(self.greatgrandchildren[1]))


    def test_allow_parent(self):
        self.assertTrue(self.children[1].check_possible_parent(self.root))


    def test_allow_distant_ancestor(self):
        self.assertTrue(self.greatgrandchildren[0].check_possible_parent(self.root))


    def test_allow_sibling(self):
        self.assertTrue(self.children[1].check_possible_parent(self.children[2]))


    def test_allow_other_trees(self):
        self.assertTrue(self.greatgrandchildren[0].check_possible_parent(self.strangers[2]))
