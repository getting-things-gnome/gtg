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

""" Tests for parsing searching query """

import unittest
from GTG.core.search import parse_search_query, InvalidQuery
from GTG.tools.dates import Date

parse = parse_search_query
d = Date.parse


class TestSearchQuery(unittest.TestCase):

    def test_word_query(self):
        self.assertEqual(parse("query"),
                         {'q': [("word", True, 'query')]})

    def test_word_literal_query(self):
        self.assertEqual(parse('"query"'),
                         {'q': [("word", True, 'query')]})

    def test_tag_query(self):
        self.assertEqual(parse("@gtg"),
                         {'q': [("tag", True, '@gtg')]})

    def test_literal_tag_query(self):
        self.assertEqual(parse('"@gtg"'),
                         {'q': [("word", True, '@gtg')]})

    def test_only_not(self):
        self.assertRaises(InvalidQuery, parse, "!not")

    def test_not_not(self):
        self.assertRaises(InvalidQuery, parse, "!not !not")

    def test_not_not_word(self):
        self.assertEqual(parse('!not !not word'),
                         {'q': [("word", True, 'word')]})

    def test_not_not_not_word(self):
        self.assertEqual(parse('!not !not !not word'),
                         {'q': [("word", False, 'word')]})

    def test_not_not_not_not_word(self):
        self.assertEqual(parse('!not !not !not !not word'),
                         {'q': [("word", True, 'word')]})

    def test_not_word_query(self):
        self.assertEqual(parse("!not query"),
                         {'q': [("word", False, 'query')]})

    def test_not_word_literal_query(self):
        self.assertEqual(parse('!not "query"'),
                         {'q': [("word", False, 'query')]})

    def test_not_tag_query(self):
        self.assertEqual(parse("!not @gtg"),
                         {'q': [("tag", False, '@gtg')]})

    def test_not_literal_tag_query(self):
        self.assertEqual(parse('!not "@gtg"'),
                         {'q': [("word", False, '@gtg')]})

    def test_or(self):
        self.assertEqual(parse("@gtg !or @gtd"),
                         {'q': [("or", True, [("tag", True, "@gtg"),
                        ("tag", True, "@gtd")])]})

    def test_or_or(self):
        self.assertEqual(parse("@gtg !or @gtd !or @a"),
                         {'q': [("or", True, [("tag", True, "@gtg"),
                        ("tag", True, "@gtd"), ("tag", True, "@a")])]})

    def test_or_or_or_or_or(self):
        self.assertEqual(parse("@gtg !or @gtd !or @a !or @b !or @c"),
                         {'q': [("or", True, [
                                 ("tag", True, "@gtg"), ("tag", True, "@gtd"),
                        ("tag", True, "@a"), ("tag", True, "@b"),
                             ("tag", True, "@c"),
                         ])]})

    def test_not_or(self):
        self.assertRaises(InvalidQuery, parse, '!not !or')

    def test_not_or_word(self):
        self.assertRaises(InvalidQuery, parse, '!not !or word')

    def test_word_not_or_word(self):
        self.assertRaises(InvalidQuery, parse, 'word !not !or word')

    def test_double_or(self):
        self.assertEqual(parse("a !or b c !or d"), {'q': [
            ("or", True, [("word", True, "a"), ("word", True, "b")]),
            ("or", True, [("word", True, "c"), ("word", True, "d")]),
        ]})

    def test_after(self):
        self.assertEqual(parse("!after 2012-02-14"),
                         {'q': [('after', True, d('2012-02-14'))]})
        self.assertEqual(parse("!after tomorrow"),
                         {'q': [('after', True, d('tomorrow'))]})
        self.assertEqual(parse("!after today"),
                         {'q': [('after', True, d('today'))]})
        self.assertEqual(parse('!after "next month"'),
                         {'q': [('after', True, d('next month'))]})

        # Test other things as well
        self.assertEqual(parse("!after tomorrow @gtg"),
                         {'q': [('after', True, d('tomorrow')),
                                ('tag', True, '@gtg')]})
        self.assertEqual(parse("!after tomorrow !not @gtg"),
                         {'q': [('after', True, d('tomorrow')),
                                ('tag', False, '@gtg')]})
        self.assertEqual(parse("!after tomorrow mytask"),
                         {'q': [('after', True, d('tomorrow')),
                                ('word', True, 'mytask')]})
        self.assertEqual(parse("!after tomorrow !not mytask"),
                         {'q': [('after', True, d('tomorrow')),
                                ('word', False, 'mytask')]})

        # Test whitespace
        self.assertEqual(parse("!after                        today       "),
                         {'q': [('after', True, d('today'))]})

        # Test nondate information
        self.assertRaises(InvalidQuery, parse, "!after non-date-information")

        # Missing date
        self.assertRaises(InvalidQuery, parse, "!after")
        self.assertRaises(InvalidQuery, parse, "!after !after")
        self.assertRaises(InvalidQuery, parse, "!after @now")
        self.assertRaises(InvalidQuery, parse, "!not !after")

        # Not after "The End of the World" :-)
        self.assertEqual(parse("!not !after 2012-12-21"),
                         {'q': [('after', False, d('2012-12-21'))]})

    def test_before(self):
        self.assertEqual(parse("!before 2000-01-01"),
                         {'q': [('before', True, d('2000-01-01'))]})
        self.assertEqual(parse("!before tomorrow"),
                         {'q': [('before', True, d('tomorrow'))]})
        self.assertEqual(parse('!before "next month"'),
                         {'q': [('before', True, d('next month'))]})

        # Test other things as well
        self.assertEqual(parse("@gtg !before tomorrow @gtg"),
                         {'q': [('tag', True, '@gtg'),
                                ('before', True, d('tomorrow')),
                        ('tag', True, '@gtg')]})
        self.assertEqual(parse("!before tomorrow !not @gtg"),
                         {'q': [('before', True, d('tomorrow')),
                                ('tag', False, '@gtg')]})
        self.assertEqual(parse("!before tomorrow mytask"),
                         {'q': [('before', True, d('tomorrow')),
                                ('word', True, 'mytask')]})
        self.assertEqual(parse("!before tomorrow !not mytask"),
                         {'q': [('before', True, d('tomorrow')),
                        ('word', False, 'mytask')]})

        # Test whitespace
        self.assertEqual(parse("!before                        today       "),
                         {'q': [('before', True, d('today'))]})

        # Test nondate information
        self.assertRaises(InvalidQuery, parse, "!before non-date-information")

        # Missing date
        self.assertRaises(InvalidQuery, parse, "!before")
        self.assertRaises(InvalidQuery, parse, "!before !before")
        self.assertRaises(InvalidQuery, parse, "!before @now")
        self.assertRaises(InvalidQuery, parse, "!not !before")

    def test_dates(self):
        self.assertEqual(parse('!today'), {'q': [('today', True)]})
        self.assertEqual(parse('!tomorrow'), {'q': [('tomorrow', True)]})
        self.assertEqual(parse('!nodate'), {'q': [('nodate', True)]})
        self.assertEqual(parse('!now'), {'q': [('now', True)]})
        self.assertEqual(parse('!soon'), {'q': [('soon', True)]})
        self.assertEqual(parse('!someday'), {'q': [('someday', True)]})

        self.assertEqual(parse('!not !today'),
                         {'q': [('today', False)]})
        self.assertEqual(parse('word !today'),
                         {'q': [('word', True, 'word'), ('today', True)]})


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
