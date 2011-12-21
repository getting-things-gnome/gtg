# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
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

'''
Tests for the SortedDict class
'''

import unittest

from GTG.tools.sorted_dict import SortedDict

class TestSortedDict(unittest.TestCase):
    '''
    Tests for the SortedDict object.
    '''

    def test_adding(self):
        """ Just add several items and make sure it is correct order
        Tupples:
          * key
          * weight - to sort by
          * some string - some information to carry
        """
        N = 100
        items = [(N - i - 1, i, "something not important") for i in range(N)]

        sd = SortedDict(0, 1)
        for item in reversed(items):
            sd.sorted_insert(item)

        # Test access by key
        for item in items:
            self.assertEqual(sd[item[0]], item)

        # Test the position (same as weight)
        for item in items:
            self.assertEqual(sd.get_index(item), item[1])

    def test_popping(self):
        """ Pop items from SortedDict and be sure they are removed """
        sd = SortedDict(0, 0, *[(i,) for i in range(10)])

        keys = range(10)
        for k in [0, 9, 1, 4, 2, 3, 7, 5, 8, 6]:
            keys.remove(k)
            self.assertEqual(sd.pop_by_key(k), (k,))
            self.assertEqual(sd.keys(), keys)

        self.assertEqual(sd, {})

def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestSortedDict)
