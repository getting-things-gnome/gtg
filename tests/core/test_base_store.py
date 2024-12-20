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


class BaseStoreRemove(TestCase):


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
        self.assertEqual(removed,{ str(item.id) for item in self.tree_items })
