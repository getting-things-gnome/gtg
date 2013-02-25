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

""" Tests for extract_tags_from_text """

import unittest
from GTG.tools.tags import extract_tags_from_text as tags


class TestExtractTags(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(tags(""), [])

    def test_tag_at_beginning(self):
        self.assertEqual(tags("@tag some other text"), ["@tag"])

    def test_tag_at_end(self):
        self.assertEqual(tags("some text ended with @endtag"), ["@endtag"])

    def test_hypen_in_tag(self):
        self.assertEqual(
            tags("@tag, @my-tag, bla bla @do-this-today,\
                 it has @con--tinuous---hypen-s-"),
            ["@tag", "@my-tag", "@do-this-today", "@con--tinuous---hypen-s"])

        self.assertEqual(tags("@hypen-at-end- some other text"),
                         ["@hypen-at-end"])
        self.assertEqual(tags("@hypen-at-end-, with comma"), ["@hypen-at-end"]
                         )

    def test_dot(self):
        self.assertEqual(tags("text @gtg-0.3"), ["@gtg-0.3"])
        self.assertEqual(
            tags("@tag., @my.tag, bla bla @do.this.today,\
                 also contains @hy-pen-.s"),
            ["@tag", "@my.tag", "@do.this.today", "@hy-pen-.s"])

    def test_slash(self):
        self.assertEqual(
            tags("@tag/, @my/tag, bla bla @do/this/today/,\
                 @hy-p-/ens with @slash/es/"),
            ["@tag", "@my/tag", "@do/this/today", "@hy-p-/ens", "@slash/es"])

    def test_colon(self):
        self.assertEqual(
            tags("@tag:, @my:tag, bla bla @do:this:today:, @co:l-on/s-,\
                 @:dot/s:, with @com,mas"),
            ["@tag", "@my:tag", "@do:this:today", "@co:l-on/s", "@:dot/s",
             "@com"])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
