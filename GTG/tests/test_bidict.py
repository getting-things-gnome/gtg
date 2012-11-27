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

""" Tests for the BiDict class """

import unittest
import uuid

from GTG.tools.bidict import BiDict


class TestBiDict(unittest.TestCase):
    """ Tests for the BiDict object."""

    def test_add_and_gets(self):
        """ Test for the __init__, _get_by_first, _get_by_second function """
        pairs = [(uuid.uuid4(), uuid.uuid4()) for a in xrange(10)]
        bidict = BiDict(*pairs)
        for pair in pairs:
            self.assertEqual(bidict._get_by_first(pair[0]), pair[1])
            self.assertEqual(bidict._get_by_second(pair[1]), pair[0])

    def test_remove_by_first_or_second(self):
        """ Tests for removing elements from the biDict """
        pair_first = (1, 'one')
        pair_second = (2, 'two')
        bidict = BiDict(pair_first, pair_second)
        bidict._remove_by_first(pair_first[0])
        bidict._remove_by_second(pair_second[1])
        missing_first = 0
        missing_second = 0
        try:
            bidict._get_by_first(pair_first[0])
        except KeyError:
            missing_first += 1
        try:
            bidict._get_by_first(pair_second[0])
        except KeyError:
            missing_first += 1
        try:
            bidict._get_by_second(pair_first[1])
        except KeyError:
            missing_second += 1
        try:
            bidict._get_by_second(pair_second[1])
        except KeyError:
            missing_second += 1
        self.assertEqual(missing_first, 2)
        self.assertEqual(missing_second, 2)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestBiDict)
