# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things Gnome! - a personal organizer for the GNOME desktop
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
from GTG import _

class TestDates(unittest.TestCase):
    '''
    Tests for the various Date classes
    '''

    def test_get_canonical_date(self):
        '''
        Tests for "get_canonical_date"
        '''
        known_values = (("1985-03-29", "1985-03-29"), ("now", _("now")),
                        ("soon", _("soon")), ("later", _("later")), ("", ""))
        for value, result in known_values:
            date = get_canonical_date(value)
            self.assertEqual(date.__str__(), result)

def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestDates)

