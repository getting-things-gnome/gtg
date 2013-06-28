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

'''
Tests for the various Date classes
'''

import unittest
from datetime import date, timedelta

from GTG import _
from GTG.tools.dates import Date


def next_month(aday, day=None):
    """ Increase month, change 2012-02-13 into 2012-03-13.
    If day is set, replace day in month as well

    @returns: updated date """
    if day is None:
        day = aday.day

    if aday.month == 12:
        return aday.replace(day=day, month=1, year=aday.year + 1)
    else:
        return aday.replace(day=day, month=aday.month + 1)


class TestDates(unittest.TestCase):
    """ Tests for the various Date classes """

    def test_parse_dates(self):
        """ Parse common numeric date """
        self.assertEqual(str(Date.parse("1985-03-29")), "1985-03-29")
        self.assertEqual(str(Date.parse("19850329")), "1985-03-29")
        self.assertEqual(str(Date.parse("1985/03/29")), "1985-03-29")

        today = date.today()
        parse_string = "%02d%02d" % (today.month, today.day)
        self.assertEqual(Date.parse(parse_string), today)

    def test_parse_fuzzy_dates(self):
        """ Parse fuzzy dates like now, soon, later, someday """
        self.assertEqual(Date.parse("now"), Date.now())
        self.assertEqual(Date.parse("soon"), Date.soon())
        self.assertEqual(Date.parse("later"), Date.someday())
        self.assertEqual(Date.parse("someday"), Date.someday())
        self.assertEqual(Date.parse(""), Date.no_date())

    def test_parse_local_fuzzy_dates(self):
        """ Parse fuzzy dates in their localized version """
        self.assertEqual(Date.parse(_("now")), Date.now())
        self.assertEqual(Date.parse(_("soon")), Date.soon())
        self.assertEqual(Date.parse(_("later")), Date.someday())
        self.assertEqual(Date.parse(_("someday")), Date.someday())
        self.assertEqual(Date.parse(""), Date.no_date())

    def test_parse_fuzzy_dates_str(self):
        """ Print fuzzy dates in localized version """
        self.assertEqual(str(Date.parse("now")), _("now"))
        self.assertEqual(str(Date.parse("soon")), _("soon"))
        self.assertEqual(str(Date.parse("later")), _("someday"))
        self.assertEqual(str(Date.parse("someday")), _("someday"))
        self.assertEqual(str(Date.parse("")), "")

    def test_parse_week_days(self):
        """ Parse name of week days and don't care about case-sensitivity """
        weekday = date.today().weekday()
        for i, day in enumerate(['Monday', 'Tuesday', 'Wednesday',
                                 'Thursday', 'Friday', 'Saturday', 'Sunday']):
            if i <= weekday:
                expected = date.today() + timedelta(7 + i - weekday)
            else:
                expected = date.today() + timedelta(i - weekday)

            self.assertEqual(Date.parse(day), expected)
            self.assertEqual(Date.parse(day.lower()), expected)
            self.assertEqual(Date.parse(day.upper()), expected)

            # Test localized version
            day = _(day)
            self.assertEqual(Date.parse(day), expected)
            self.assertEqual(Date.parse(day.lower()), expected)
            self.assertEqual(Date.parse(day.upper()), expected)

    def test_missing_year_this_year(self):
        """ Parsing %m%d have to find correct date:
        we enter a day this year """
        aday = next_month(date.today(), day=1)
        parse_string = "%02d%02d" % (aday.month, aday.day)
        self.assertEqual(Date.parse(parse_string), aday)

    def test_missing_year_next_year(self):
        """ Parsing %m%d have to find correct date:
        we enter a day the next year """
        aday = date.today()
        if aday.day == 1 and aday.month == 1:
            # not possible to add a day next year
            return

        aday = aday.replace(year=aday.year + 1, month=1, day=1)
        self.assertEqual(Date.parse("0101"), aday)

    def test_on_certain_day(self):
        """ Parse due:3 as 3rd day this month or next month
        if it is already more or already 3rd day """
        for i in range(28):
            i += 1
            aday = date.today()
            if i <= aday.day:
                aday = next_month(aday, i)
            else:
                aday = aday.replace(day=i)

            self.assertEqual(Date.parse(str(i)), aday)

    def test_prevent_regression(self):
        """ A day represented in GTG Date must be still the same """
        aday = date.today()
        self.assertEqual(Date(aday), aday)


def test_suite():
    """ Return unittests """
    return unittest.TestLoader().loadTestsFromTestCase(TestDates)
