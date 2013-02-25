# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 - Lionel Dricot & Bertrand Rousseau
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

"""Tests for the tags"""

import unittest

from GTG.core.tag import Tag, Set_Name_Attribute_Error
from GTG.core.datastore import DataStore

from GTG.tests.signals_testing import GobjectSignalsManager


class TestTag(unittest.TestCase):
    """Tests for `Tag`."""

    def setUp(self):
        ds = DataStore()
        self.req = ds.get_requester()
        # initalize gobject signaling system
        self.gobject_signal_manager = GobjectSignalsManager()
        self.gobject_signal_manager.init_signals()
        # refresh the viewtree for tasks
        tt = self.req.get_tasks_tree()
        tt.reset_filters()

    def tearDown(self):
#        finally:
        # stopping gobject main loop
        self.gobject_signal_manager.terminate_signals()

    def test_name(self):
        # The first argument to the Tag constructor is the name, which you can
        # get with get_name().
        tag = Tag('foo', self.req)
        self.assertEqual('foo', tag.get_name())

    def test_name_is_attribute(self):
        # The name of the tag is also stored as an attribute.
        tag = Tag('foo', self.req)
        self.assertEqual('foo', tag.get_attribute('name'))

    def test_missing_attribute_returns_none(self):
        # If get_attribute is called for an attribute that doesn't exist, it
        # returns None.
        tag = Tag('whatever', self.req)
        result = tag.get_attribute('no-such-attribute')
        self.assertEqual(None, result)

    def test_set_then_get_attribute(self):
        # Attributes set with set_attribute can be retrieved with
        # get_attribute.
        tag = Tag('whatever', self.req)
        tag.set_attribute('new-attribute', 'value')
        result = tag.get_attribute('new-attribute')
        self.assertEqual('value', result)

    def test_set_non_str_attribute_casts_to_string(self):
        # If the value of the attribute passed to set_attribute is not a
        # string, it's cast to a string.
        tag = Tag('whatever', self.req)
        tag.set_attribute('new-attribute', 42)
        result = tag.get_attribute('new-attribute')
        self.assertEqual('42', result)

    def test_get_all_attributes_initial(self):
        # Initially, a Tag has only the name attribute.
        tag = Tag('foo', self.req)
        self.assertEqual(['name'], tag.get_all_attributes())

    def test_get_all_attributes_after_setting(self):
        # After attributes are set, get_all_attributes includes those
        # attributes. The order is not guaranteed.
        tag = Tag('foo', self.req)
        tag.set_attribute('bar', 'baz')
        self.assertEqual(set(['name', 'bar']), set(tag.get_all_attributes()))

    def test_get_all_but_name(self):
        # If 'butname' is True, then exclude the 'name' attribute.
        tag = Tag('foo', self.req)
        self.assertEqual([], tag.get_all_attributes(butname=True))
        tag.set_attribute('bar', 'baz')
        self.assertEqual(['bar'], tag.get_all_attributes(butname=True))

    def test_str(self):
        # str(tag) is 'Tag: <name>'
        tag = Tag('foo', self.req)
        self.assertEqual('Tag: foo', str(tag))

    def test_set_name_attribute_does_nothing(self):
        # The 'name' attribute is set by the constructor. After it is set, it
        # cannot be changed with further calls to set_attribute.
        tag = Tag('old', self.req)
        try:
            tag.set_attribute('name', 'new')
        except Set_Name_Attribute_Error:
            pass
        self.assertEqual('old', tag.get_name())
        self.assertEqual('old', tag.get_attribute('name'))

    # XXX: The following tests check the current behaviour of the Tag class,
    # but I'm not sure if they're correct behaviour. -- jml, 2009-07-17
    def test_save_not_called_on_construction(self):
        # The save callback isn't called by the constructor, despite the fact
        # that it sets the name attribute.
        save_calls = []
        Tag('old', self.req)
        self.assertEqual(0, len(save_calls))

    def test_set_name_doesnt_call_save(self):
        # Setting the name attribute doesn't call save.
        save_calls = []
        tag = Tag('old', self.req)
        try:
            tag.set_attribute('name', 'new')
        except Set_Name_Attribute_Error:
            pass
        self.assertEqual(0, len(save_calls))

    def test_intask_counting_after_rename(self):
        '''We test that the task counting for tags work
        even after tag renaming (stuttering tag bug)'''
        t = self.req.new_task(tags=['@testtag'])
        t.modified()
        tag = self.req.get_tag('@testtag')
        self.assertEqual(tag.get_active_tasks_count(), 1)
        t.rename_tag('@testtag', '@test')
        tag2 = self.req.get_tag('@test')
        self.assertEqual(tag2.get_active_tasks_count(), 1)
        self.assertEqual(tag.get_active_tasks_count(), 0)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestTag)
