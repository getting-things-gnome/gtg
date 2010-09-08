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
Tests for the various Date classes
'''

import unittest

from GTG.tools.dates import get_canonical_date

class TestDates(unittest.TestCase):
    '''
    Tests for the various Date classes
    '''

    def test_get_canonical_date(self):
        '''
        Tests for "get_canonical_date"
        '''
        for str in ["1985-03-29", "now", "soon", "later", ""]:
            date = get_canonical_date(str)
            self.assertEqual(date.__str__(), str)

def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestDates)

