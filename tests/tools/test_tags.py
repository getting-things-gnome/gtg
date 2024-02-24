# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2014 - Lionel Dricot & Bertrand Rousseau
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

import unittest
from unittest import TestCase

from GTG.core.tags import extract_tags_from_text


class TestExtractTags(TestCase):
    """ extract_tags_from_text """

    def assertTags(self, text, expected_tags):
        tag_list = extract_tags_from_text(text)
        self.assertEqual(expected_tags, tag_list)

    def test_doesnt_find_empty_tag(self):
        self.assertTags("", [])

    def test_finds_tag_at_beginning(self):
        self.assertTags("@tag some other text", ["@tag"])

    def test_finds_tag_at_end(self):
        self.assertTags("some text ended with @endtag", ["@endtag"])

    def test_ignores_emails(self):
        self.assertTags(
            "no @emails allowed: invernizzi.l@gmail.com", ["@emails"])

    def test_ignores_diffs(self):
        self.assertTags("no @@diff stuff", [])

    def test_accepts_hypen_in_tag(self):
        self.assertTags("@do-this-today", ["@do-this-today"])
        self.assertTags("@con--tinuous---hypen-s", ["@con--tinuous---hypen-s"])

    def test_ignores_hypen_at_end_of_tag(self):
        self.assertTags("@hypen-at-end- some other text", ["@hypen-at-end"])
        self.assertTags("@hypen-at-end-, with comma", ["@hypen-at-end"])

    def test_accepts_dot_in_tag(self):
        self.assertTags("text @gtg-0.3", ["@gtg-0.3"])

    def test_ignores_dot_at_end_of_tag(self):
        self.assertTags("@tag.", ["@tag"])

    def test_accepts_slash_in_tag(self):
        self.assertTags("@do/this/today", ["@do/this/today"])

    def test_ignores_slash_at_end_of_tag(self):
        self.assertTags("@slash/es/", ["@slash/es"])

    def test_accepts_colon_in_tag(self):
        self.assertTags("@my:tag", ["@my:tag"])

    def ignore_colon_at_end(self):
        self.assertTags("@:a:b:c:", ["@:a:b:c"])

    def test_accepts_ampersand_in_tag(self):
        self.assertTags("@home&work", ["@home&work"])


@unittest.skip('TODO these need to move now that parse_tag_list is inside'
               ' ModifyTagsDialog')
class TestParseTagList(TestCase):
    """ parse_tag_list """

    def test_parses_positive_single_tag(self):
        self.assertEqual(parse_tag_list("tag"), [("tag", True)])
        self.assertEqual(parse_tag_list("@tag"), [("@tag", True)])

    def test_parses_postivie_tag_list(self):
        self.assertEqual(
            parse_tag_list("a b c"),
            [("a", True), ("b", True), ("c", True)],
        )
        self.assertEqual(
            parse_tag_list("@a @b @c"),
            [("@a", True), ("@b", True), ("@c", True)],
        )

    def test_parses_negative_single_tag(self):
        self.assertEqual(parse_tag_list("!tag"), [("tag", False)])
        self.assertEqual(parse_tag_list("!@tag"), [("@tag", False)])

    def test_parses_negative_tag_list(self):
        self.assertEqual(
            parse_tag_list("!a !b !c"),
            [("a", False), ("b", False), ("c", False)],
        )
        self.assertEqual(
            parse_tag_list("!@a !@b !@c"),
            [("@a", False), ("@b", False), ("@c", False)],
        )

    def test_parses_mixed_tags(self):
        self.assertEqual(
            parse_tag_list("add !remove"),
            [("add", True), ("remove", False)],
        )
        self.assertEqual(
            parse_tag_list("!remove add"),
            [("remove", False), ("add", True)],
        )
