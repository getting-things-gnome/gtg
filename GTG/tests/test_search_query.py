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
        self.assertEqual(parse("query"), {"word": [(True, 'query')]})

    def test_word_literal_query(self):
        self.assertEqual(parse('"query"'), {"word": [(True, 'query')]})

    def test_tag_query(self):
        self.assertEqual(parse("@gtg"), {"tag": [(True, '@gtg')]})

    def test_literal_tag_query(self):
        self.assertEqual(parse('"@gtg"'), {"word": [(True, '@gtg')]})

    def test_only_not(self):
        self.assertRaises(InvalidQuery, parse, "!not")

    def test_not_not(self):
        self.assertRaises(InvalidQuery, parse, "!not !not")

    def test_not_not_word(self):
        self.assertEqual(parse('!not !not word'), {"word": [(True, 'word')]})

    def test_not_not_not_word(self):
        self.assertEqual(parse('!not !not !not word'), {"word": [(False, 'word')]})

    def test_not_not_not_not_word(self):
        self.assertEqual(parse('!not !not !not !not word'), {"word": [(True, 'word')]})

    def test_not_word_query(self):
        self.assertEqual(parse("!not query"), {"word": [(False, 'query')]})

    def test_not_word_literal_query(self):
        self.assertEqual(parse('!not "query"'), {"word": [(False, 'query')]})

    def test_not_tag_query(self):
        self.assertEqual(parse("!not @gtg"), {"tag": [(False, '@gtg')]})

    def test_not_literal_tag_query(self):
        self.assertEqual(parse('!not "@gtg"'), {"word": [(False, '@gtg')]})

    def test_or(self):
        self.assertEqual(parse("@gtg !or @gtd"), {"or": [ {"tag": [(True, "@gtg")]}, {"tag": [(True, "@gtd")]}]} )

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
