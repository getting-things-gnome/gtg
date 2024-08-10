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
from uuid import uuid4, UUID

from GTG.core.saved_searches import SavedSearch, SavedSearchStore
from lxml.etree import XML


class TestSavedSearch(TestCase):


    def test_add_simple(self):
        search_id = uuid4()
        search = SavedSearch(id=search_id, name='Test Search', query='@tag1')
        store = SavedSearchStore()

        self.assertEqual(len(store.data), 0)
        store.add(search)

        self.assertEqual(len(store.data), 1)

        # We shouldn't add saved searches with the same id
        with self.assertRaises(KeyError):
            store.add(search)

        self.assertEqual(len(store.data), 1)


    def test_remove_simple(self):
        store = SavedSearchStore()
        search = SavedSearch(uuid4(), 'Some @tag', 'Looking for some tag')
        store.add(search)

        self.assertEqual(len(store.data), 1)
        store.remove(search.id)
        self.assertEqual(len(store.data), 0)

        with self.assertRaises(KeyError):
            store.remove(uuid4())


    def test_count(self):
        store = SavedSearchStore()

        search = store.new('Root search', '@tag')
        store.new('Root search 2', '@tag2')

        self.assertEqual(store.count(), 2)
        store.remove(search.id)
        self.assertEqual(store.count(), 1)


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

        self.assertEqual(store.lookup[UUID('4796b97b-3690-4e74-a056-4153061958df')].query, 'urgent')


    def test_xml_write_simple(self):

        store = SavedSearchStore()
        store.add(SavedSearch(uuid4(), 'Some @tag', 'Looking for some tag'))
        store.add(SavedSearch(uuid4(), 'Some @other @tag', 'Looking for more'))

        xml_root = store.to_xml()

        self.assertEqual(len(xml_root), 2)
