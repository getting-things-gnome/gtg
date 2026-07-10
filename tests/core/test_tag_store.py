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

from GTG.core.tags import Tag, TagStore
from lxml.etree import XML


class TestTagStore(TestCase):


    def test_new(self):
        store = TagStore()
        tag = store.new('My_tag')

        self.assertEqual(len(store.data), 1)
        self.assertEqual(store.lookup[tag.id], tag)
        self.assertIsInstance(tag, Tag)

        tag2 = store.new('@a_tag')
        self.assertEqual(len(store.data), 2)
        self.assertEqual(tag2.name, 'a_tag')

    def test_new_keeps_root_tags_sorted(self):
        store = TagStore()
        store.new('zulu')
        store.new('Alpha')
        store.new('bravo')

        names = [store.model.get_item(i).name for i in range(store.model.get_n_items())]
        self.assertEqual(names, ['Alpha', 'bravo', 'zulu'])

    def test_new_keeps_child_tags_sorted(self):
        store = TagStore()
        parent = store.new('parent')
        store.model_expand(parent)
        store.new('zulu', parent.id)
        store.new('Alpha', parent.id)
        store.new('bravo', parent.id)

        children = store.tid_to_children_model[parent.id]
        names = [children.get_item(i).name for i in range(children.get_n_items())]
        self.assertEqual(names, ['Alpha', 'bravo', 'zulu'])


    def test_xml_load_simple(self):
        store = TagStore()
        xml_doc = XML('''
        <taglist>
            <tag id="e2503866-3ebb-4ede-9e72-ff0afa1c2e74" name="to_pay"/>
            <tag id="df4db599-63f8-4fc8-9f3d-5454dcadfd78" name="money" icon="😗️"/>
        </taglist>
            ''')

        store.from_xml(xml_doc)
        self.assertEqual(store.count(), 2)


    def test_xml_load_tree(self):
        store = TagStore()
        xml_doc = XML('''
        <taglist>
            <tag id="e2503866-3ebb-4ede-9e72-ff0afa1c2e74" name="to_pay"/>
            <tag id="df4db599-63f8-4fc8-9f3d-5454dcadfd78" name="money" icon="😗️"/>
            <tag id="ef4db599-73f8-4fc8-9f3d-5454dcadfd78" name="errands" color="767BDC" parent="df4db599-63f8-4fc8-9f3d-5454dcadfd78"/>
        </taglist>
            ''')

        store.from_xml(xml_doc)
        self.assertEqual(store.count(), 3)
        self.assertEqual(store.count(root_only=True), 2)


    def test_xml_load_tree_with_old_parent_naming(self):
        store = TagStore()
        xml_doc = XML('''
        <taglist>
            <tag id="df4db599-63f8-4fc8-9f3d-5454dcadfd78" name="money"/>
            <tag id="ef4db599-73f8-4fc8-9f3d-5454dcadfd78" name="errands" parent="money"/>
        </taglist>
            ''')

        store.from_xml(xml_doc)
        self.assertIs(store.find("errands").parent,store.find("money"))


    def test_xml_load_bad(self):
        store = TagStore()
        xml_doc = XML('''
        <taglist>
            <tag id="e2503866-3ebb-4ede-9e72-ff0afa1c2e74" name="to_pay"/>
            <tag id="df4db599-63f8-4fc8-9f3d-5454dcadfd78" name="money" icon="😗️" parent="lol"/>
        </taglist>
            ''')

        store.from_xml(xml_doc)
        self.assertEqual(store.count(), 2)


    def test_xml_write_simple(self):
        store = TagStore()
        store.new('My_tag')
        tag2 = store.new('My_tag2')
        tag3 = store.new('My_tag3', tag2.id)

        tag2.color = '555557575353'
        tag3.icon = '😅️'

        xml_root = store.to_xml()

        self.assertEqual(len(xml_root), 3)


    def test_xml_write_tree(self):
        store = TagStore()
        store.new('My_tag')
        tag2 = store.new('My_tag2')
        tag3 = store.new('My_tag3', tag2.id)

        tag2.color = '555557575353'
        tag3.icon = '😅️'

        xml_root = store.to_xml()

        self.assertEqual(len(xml_root), 3)


    def test_random_color(self):
        tag_store = TagStore()

        color1 = tag_store.generate_color()
        color2 = tag_store.generate_color()
        color3 = tag_store.generate_color()

        self.assertEqual(len(tag_store.used_colors), 3)
        self.assertNotEqual(color1, color2)
        self.assertNotEqual(color2, color3)
        self.assertNotEqual(color3, color1)
