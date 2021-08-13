# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) The GTG Team
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

from GTG.core.saved_searches import SavedSearch, SavedSearchStore
from lxml.etree import Element, XML


class TestSavedSearch(TestCase):

    def test_new_simple(self):
        store = SavedSearchStore()
        search = store.new('Some @tag', 'Looking for some tag')

        # Make sure we have added a new search
        self.assertEqual(len(store.data), 1)

        # Make sure it's the same one we received
        self.assertEqual(store.lookup[search.id], search)

        # Make sure it's an instance of SavedSearch
        self.assertIsInstance(search, SavedSearch)


    def test_add_simple(self):
        search_id = uuid4()
        search = SavedSearch(id=search_id, name='Test Search', query='@tag1')
        store = SavedSearchStore()

        self.assertEqual(len(store.data), 0)
        result = store.add(search)

        self.assertEqual(len(store.data), 1)

        # We shouldn't add saved searches with the same id
        with self.assertRaises(KeyError):
            store.add(search)

        self.assertEqual(len(store.data), 1)


    def test_remove_simple(self):
        store = SavedSearchStore()
        search = store.new('Some @tag', 'Looking for some tag')

        self.assertEqual(len(store.data), 1)
        store.remove(search.id)
        self.assertEqual(len(store.data), 0)

        with self.assertRaises(KeyError):
            store.remove('000')


    def test_new_tree(self):

        store = SavedSearchStore()

        root_1 = store.new('Root search', '@tag')
        root_2 = store.new('Root search 2', '@tag2')

        child_1 = store.new('Child search 1', '@another_tag', root_1.id)
        child_2 = store.new('Child search 2', '@another_tag', root_2.id)

        child_3 = store.new('Child search 3', '@another_tag', child_2.id)

        self.assertEqual(len(store.lookup), 5)
        self.assertEqual(len(store.data), 2)
        self.assertEqual(len(root_1.children), 1)
        self.assertEqual(len(child_2.children), 1)

        with self.assertRaises(KeyError):
            store.new('An error', '@error', '000')


    def test_add_tree(self):

        store = SavedSearchStore()

        search_1 = SavedSearch(id=uuid4(), name='Test 1', query='@tag1')
        search_2 = SavedSearch(id=uuid4(), name='Test 2', query='@tag2')
        search_3 = SavedSearch(id=uuid4(), name='Test 3', query='@tag3')
        search_4 = SavedSearch(id=uuid4(), name='Test 4', query='@tag4')
        search_5 = SavedSearch(id=uuid4(), name='Test 5', query='@tag5')


        store.add(search_1)
        store.add(search_2)
        store.add(search_3, search_1.id)
        store.add(search_4, search_3.id)
        store.add(search_5, search_3.id)


    def test_remove_tree(self):
        store = SavedSearchStore()

        root_1 = store.new('Root search', '@tag')
        root_2 = store.new('Root search 2', '@tag2')

        child_1 = store.new('Child search 1', '@another_tag', root_1.id)
        child_2 = store.new('Child search 2', '@another_tag', root_2.id)

        child_3 = store.new('Child search 3', '@another_tag', child_2.id)

        self.assertEqual(len(store.lookup), 5)
        store.remove(child_3.id)

        self.assertEqual(len(store.lookup), 4)
        self.assertEqual(len(child_2.children), 0)

        store.remove(root_1.id)
        store.remove(root_2.id)

        self.assertEqual(len(store.lookup), 0)
        self.assertEqual(len(store.data), 0)


    def test_count(self):

        store = SavedSearchStore()

        root_1 = store.new('Root search', '@tag')
        root_2 = store.new('Root search 2', '@tag2')
        child_2 = store.new('Child search 2', '@another_tag', root_2.id)

        self.assertEqual(store.count(), 3)
        self.assertEqual(store.count(root_only=True), 2)

        store.remove(child_2.id)
        self.assertEqual(store.count(), 2)
        self.assertEqual(store.count(root_only=True), 2)


    def test_xml_load_simple(self):

        store = SavedSearchStore()
        xml_doc = XML('''
    <searchList>
        <savedSearch id="4796b97b-3690-4e74-a056-4153061958df" name="Urgent in tasks" query="urgent" />
        <savedSearch id="2ff11525-a209-4cd9-8f50-859592f1ee37" name="Other tasks" query="@other" />
    </searchList>
                 ''')

        store.from_xml(xml_doc)
        self.assertEqual(store.count(), 2)


    def test_xml_load_tree(self):

        store = SavedSearchStore()
        xml_doc = XML('''
    <searchList>
        <savedSearch id="4796b97b-3690-4e74-a056-4153061958df" name="Urgent in tasks" query="urgent" />
        <savedSearch id="2ff11525-a209-4cd9-8f50-859592f1ee37" name="Other tasks" query="@other" />
        <savedSearch id="89fdc73c-6776-4d65-8220-dffec1953fae" name="More tasks" query="@another" parent="Other tasks"/>
        <savedSearch id="588c9ffa-e96b-42a1-862b-8684fc09181e" name="More tasks 2" query="@yet_another" parent="More tasks 2"/>
    </searchList>
                 ''')

        store.from_xml(xml_doc)
        self.assertEqual(store.count(), 4)
        self.assertEqual(store.count(root_only=True), 2)

        self.assertEqual(store.lookup['4796b97b-3690-4e74-a056-4153061958df'].query, 'urgent')
        self.assertEqual(len(store.lookup['2ff11525-a209-4cd9-8f50-859592f1ee37'].children), 1)


    def test_xml_write_simple(self):

        store = SavedSearchStore()
        search1 = store.new('Some @tag', 'Looking for some tag')
        search2 = store.new('Some @other @tag', 'Looking for more')

        xml_root = store.to_xml()

        self.assertEqual(len(xml_root), 2)


    def test_xml_write_tree(self):

        store = SavedSearchStore()
        search1 = store.new('Some @tag', 'Looking for some tag')
        search2 = store.new('Some @other @tag', 'Looking for more')

        xml_root = store.to_xml()

        self.assertEqual(len(xml_root), 2)


    def test_parent(self):

        store = SavedSearchStore()
        search1 = store.new('Some @tag', 'Looking for some tag')
        search2 = store.new('Some @other @tag', 'Looking for more')

        self.assertEqual(len(store.lookup), 2)
        self.assertEqual(len(store.data), 2)

        store.parent(search1.id, search2.id)

        self.assertEqual(len(store.data), 1)
        self.assertEqual(len(search2.children), 1)
        self.assertEqual(len(store.lookup), 2)

        search3 = store.new('Some @other @tag', 'Looking for more')
        store.parent(search3.id, search1.id)

        self.assertEqual(len(store.data), 1)
        self.assertEqual(len(search1.children), 1)
        self.assertEqual(len(search2.children), 1)
        self.assertEqual(len(store.lookup), 3)


    def test_unparent(self):

        store = SavedSearchStore()
        search1 = store.new('Some @tag', 'Looking for some tag')
        search2 = store.new('Some @other @tag', 'Looking for more')

        self.assertEqual(len(store.lookup), 2)
        self.assertEqual(len(store.data), 2)

        store.parent(search1.id, search2.id)

        self.assertEqual(len(store.data), 1)
        self.assertEqual(len(search2.children), 1)
        self.assertEqual(len(store.lookup), 2)

        store.unparent(search1.id, search2.id)

        self.assertEqual(len(store.data), 2)
        self.assertEqual(len(search2.children), 0)
        self.assertEqual(len(store.lookup), 2)
