# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
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

""" Tests for parsing searching query """

import unittest
from GTG.core.search import parse_search_query, InvalidQuery

parse = parse_search_query

class TestSearchQuery(unittest.TestCase):

    def test_word_query(self):
        self.assertEqual(parse("query"), {'q':[("word", True, 'query')]})

    def test_word_literal_query(self):
        self.assertEqual(parse('"query"'), {'q':[("word", True, 'query')]})

    def test_tag_query(self):
        self.assertEqual(parse("@gtg"), {'q': [("tag", True, '@gtg')]})

    def test_literal_tag_query(self):
        self.assertEqual(parse('"@gtg"'), {'q': [("word", True, '@gtg')]})

    def test_only_not(self):
        self.assertRaises(InvalidQuery, parse, "!not")

    def test_not_not(self):
        self.assertRaises(InvalidQuery, parse, "!not !not")

    def test_not_not_word(self):
        self.assertEqual(parse('!not !not word'), {'q': [("word", True, 'word')]})

    def test_not_not_not_word(self):
        self.assertEqual(parse('!not !not !not word'), {'q': [("word", False, 'word')]})

    def test_not_not_not_not_word(self):
        self.assertEqual(parse('!not !not !not !not word'), {'q': [("word", True, 'word')]})

    def test_not_word_query(self):
        self.assertEqual(parse("!not query"), {'q': [("word", False, 'query')]})

    def test_not_word_literal_query(self):
        self.assertEqual(parse('!not "query"'), {'q': [("word", False, 'query')]})

    def test_not_tag_query(self):
        self.assertEqual(parse("!not @gtg"), {'q': [("tag", False, '@gtg')]})

    def test_not_literal_tag_query(self):
        self.assertEqual(parse('!not "@gtg"'), {'q': [("word", False, '@gtg')]})

    def test_or(self):
        self.assertEqual(parse("@gtg !or @gtd"), {'q': [("or", True, [("tag", True, "@gtg"), ("tag", True, "@gtd")])]})

    def test_or_or(self):
        self.assertEqual(parse("@gtg !or @gtd !or @a"), {'q': [("or", True, [("tag", True, "@gtg"), ("tag", True, "@gtd"), ("tag", True, "@a")])]})

    def test_or_or_or_or_or(self):
        self.assertEqual(parse("@gtg !or @gtd !or @a !or @b !or @c"), 
            {'q': [("or", True, [("tag", True, "@gtg"), ("tag", True, "@gtd"), ("tag", True, "@a"), ("tag", True, "@b"), ("tag", True, "@c")])]})

    def test_not_or(self):
        self.assertRaises(InvalidQuery, parse, '!not !or')

    def test_not_or_word(self):
        self.assertRaises(InvalidQuery, parse, '!not !or word')

    def test_word_not_or_word(self):
        self.assertRaises(InvalidQuery, parse, 'word !not !or word')

    def test_double_or(self):
        self.assertEqual(parse("a !or b c !or d"), {'q': [
            ("or", True, [("word", True, "a"), ("word", True, "b")]),
            ("or", True, [("word", True, "c"), ("word", True, "d")])
        ]})

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
