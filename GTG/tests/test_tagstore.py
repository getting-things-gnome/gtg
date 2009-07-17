# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personnal organizer for the GNOME desktop
# Copyright (c) 2008-2009 - Lionel Dricot & Bertrand Rousseau
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

"""Tests for the tagstore."""

import unittest

from GTG.core.tagstore import Tag


class TestTag(unittest.TestCase):
    """Tests for `Tag`."""

    def test_name(self):
        tag = Tag('foo')
        self.assertEqual('foo', tag.get_name())

    def test_name_is_attribute(self):
        tag = Tag('foo')
        self.assertEqual('foo', tag.get_attribute('name'))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
