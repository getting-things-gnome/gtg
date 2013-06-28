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

""" Tests for search filter """

import unittest
from GTG.core.search import search_filter
from GTG.tools.dates import Date

d = Date.parse


class FakeTask:

    def __init__(self, title="", body="", tags=[], due_date=""):
        self.title = title
        self.body = body
        self.tags = tags
        self.due_date = Date.parse(due_date)

    def get_title(self):
        return self.title

    def get_excerpt(self, strip_tags=False):
        return self.body

    def get_tags_name(self):
        return self.tags

    def get_due_date(self):
        return self.due_date


class TestSearchFilter(unittest.TestCase):

    def test_empty(self):
        self.assertFalse(search_filter(FakeTask()))

    def test_single_tag(self):
        task = FakeTask(tags=['@a'])

        self.assertTrue(search_filter(task, {"q": [("tag", True, "@a")]}))
        self.assertFalse(search_filter(task, {"q": [("tag", True, "@b")]}))
        self.assertFalse(search_filter(task, {"q": [("tag", True, "@n")]}))

    def test_double_tag(self):
        p = {"q": [("tag", True, "@a"), ("tag", True, "@b")]}

        self.assertTrue(search_filter(FakeTask(tags=['@a', '@b']), p))
        self.assertTrue(search_filter(FakeTask(tags=['@b', '@a']), p))
        self.assertTrue(search_filter(FakeTask(tags=['@b', '@a', '@a']), p))
        self.assertTrue(search_filter(
            FakeTask(tags=['@b', '@a', '@c', '@d']), p))
        self.assertTrue(search_filter(
            FakeTask(tags=['@b', 'search', '@a']), p))
        self.assertTrue(search_filter(
            FakeTask(tags=['gtg-tags-all', '@b', 'search', '@a']), p))
        self.assertTrue(search_filter(FakeTask(tags=['gtg-tags-all',
                                                     'gtg-tags-none',
                                                     '@b', 'search',
                                                     '@a']), p))

        self.assertFalse(search_filter(FakeTask(tags=['@n', '@b']), p))
        self.assertFalse(search_filter(FakeTask(tags=['@b', '@n']), p))
        self.assertFalse(search_filter(FakeTask(tags=['@a']), p))
        self.assertFalse(search_filter(FakeTask(tags=['@b']), p))
        self.assertFalse(search_filter(
            FakeTask(tags=['@b', '@b', '@c', '@d']), p))
        self.assertFalse(search_filter(
            FakeTask(tags=['@b', 'search', '@d']), p))
        self.assertFalse(search_filter(
            FakeTask(tags=['gtg-tags-all', '@g', 'search', '@a']), p))
        self.assertFalse(search_filter(FakeTask(tags=['gtg-tags-all',
                                                      'gtg-tags-none',
                                                      '@@b',
                                                      'search', '@a']), p))

    def test_simple_tag_or(self):
        task = FakeTask(tags=['@a', '@b'])

        self.assertTrue(search_filter(task,
                                      {"q": [('or', True,
                                            [("tag", True, "@a"),
                                             ("tag", True, "@b")])]}))
        self.assertTrue(search_filter(task,
                                      {"q": [('or', True,
                                            [("tag", True, "@a"),
                                             ("tag", True, "@n")])]}))
        self.assertTrue(search_filter(task,
                                      {"q": [('or', True,
                                            [("tag", True, "@n"),
                                             ("tag", True, "@b")])]}))
        self.assertFalse(search_filter(task,
                                       {"q": [('or', True,
                                             [("tag", True, "@n"),
                                              ("tag", True, "@n")])]}))

    def test_simple_word_in_title(self):
        task = FakeTask(title="GTG is the best ToDo manager for GNOME")

        # Test the lowercasing
        self.assertTrue(search_filter(task, {'q': [("word", True, 'GTG')]}))
        self.assertTrue(search_filter(task, {'q': [("word", True, 'gtg')]}))
        self.assertTrue(search_filter(task, {'q': [("word", True, 'GtG')]}))
        self.assertTrue(search_filter(task, {'q': [("word", True, 'Gtg')]}))
        self.assertTrue(search_filter(task, {'q': [("word", True, 'gTg')]}))

        self.assertTrue(search_filter(task, {'q': [("word", True, 'GTG')]}))
        self.assertTrue(search_filter(task, {'q': [("word", True, 'is')]}))
        self.assertTrue(search_filter(task, {'q': [("word", True, 'the')]}))
        self.assertTrue(search_filter(task, {'q': [("word", True, 'best')]}))
        self.assertTrue(search_filter(task, {'q': [("word", True, 'todo')]}))
        self.assertTrue(search_filter(task,
                                      {'q': [("word", True, 'manager')]}))
        self.assertTrue(search_filter(task, {'q': [("word", True, 'for')]}))
        self.assertTrue(search_filter(task, {'q': [("word", True, 'GNOME')]}))

        # test literals
        self.assertTrue(search_filter(task, {'q': [("word", True, 'GTG is')]})
                        )
        self.assertTrue(search_filter(task,
                                      {'q': [("word", True, 'for GNOME')]}))
        self.assertTrue(search_filter(task,
                                      {'q': [("word", False, 'GTG for GNOME')]
                                       }))
        self.assertFalse(search_filter(task,
                                       {'q': [("word", True, 'GTG for GNOME')]
                                        }))

    def test_simple_before(self):
        v = FakeTask(due_date="2012-02-14")

        self.assertTrue(search_filter(v,
                                      {'q': [("before", True, d('2022-01-01'))
                                             ]}))
        self.assertTrue(search_filter(v,
                                      {'q': [("before", True, d('2012-03-01'))
                                             ]}))
        self.assertTrue(search_filter(v,
                                      {'q': [("before", True, d('2012-02-20'))
                                             ]}))
        self.assertTrue(search_filter(v,
                                      {'q': [("before", True, d('2012-02-15'))
                                             ]}))
        self.assertFalse(search_filter(v,
                                       {'q': [("before", True, d('2012-02-14'))
                                              ]}))
        self.assertFalse(search_filter(v,
                                       {'q': [("before", True, d('2012-02-13'))
                                              ]}))
        self.assertFalse(search_filter(v,
                                       {'q': [("before", True, d('2000-01-01')
                                               )]}))

        self.assertFalse(search_filter(v,
                                       {'q': [("before", False, d('2012-03-01'
                                                                  ))]}))
        self.assertTrue(search_filter(v,
                                      {'q': [("before", False, d('2012-02-14')
                                              )]}))
        self.assertTrue(search_filter(v,
                                      {'q': [("before", False, d('2002-02-20')
                                              )]}))

    def test_simple_after(self):
        t = FakeTask(due_date="2012-06-01")

        self.assertTrue(search_filter(t,
                                      {'q': [("after", True, d('2002-01-01'))]
                                       }))
        self.assertTrue(search_filter(t,
                                      {'q': [("after", True, d('2012-05-30'))]
                                       }))
        self.assertFalse(search_filter(t,
                                       {'q': [("after", True, d('2013-02-20'))
                                              ]}))
        self.assertTrue(search_filter(t,
                                      {'q': [("after", False, d('2022-02-15'))
                                             ]}))

    def test_dates(self):
        self.assertTrue(search_filter(FakeTask(due_date="today"),
                                      {'q': [("today", True)]}))
        self.assertTrue(search_filter(FakeTask(due_date="tomorrow"),
                                      {'q': [("tomorrow", True)]}))
        self.assertTrue(search_filter(FakeTask(due_date=""),
                                      {'q': [("nodate", True)]}))
        self.assertTrue(search_filter(FakeTask(due_date="now"),
                                      {'q': [("now", True)]}))
        self.assertTrue(search_filter(FakeTask(due_date="soon"),
                                      {'q': [("soon", True)]}))
        self.assertTrue(search_filter(FakeTask(due_date="someday"),
                                      {'q': [("someday", True)]}))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
