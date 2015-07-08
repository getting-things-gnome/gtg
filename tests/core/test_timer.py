# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2015 - Lionel Dricot & Bertrand Rousseau
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

import datetime

from mock import patch
from unittest import TestCase

from GTG.core.timer import Timer


class Config(object):
    """Creating a mock Config
    to be able to create a Timer object later
    """
    def __init__(self):
        self.values = {'hour': '00', 'min': '00'}

    def set(self, name, value):
        self.values[name] = value

    def get(self, name):
        return self.values.get(name)


class TestTimerParser(TestCase):

    def setUp(self):
        patch.object(Timer, 'connect_to_dbus').start()
        self.timer = Timer(Config())

    def tearDown(self):
        patch.stopall()

    def test_time_parser_classic_format(self):
        self.assertEqual(self.timer.parse_time('00:00'), datetime.time(0, 0))
        self.assertEqual(self.timer.parse_time('2:40'), datetime.time(2, 40))
        self.assertEqual(self.timer.parse_time('17:30'), datetime.time(17, 30))
        self.assertEqual(self.timer.parse_time('23:59'), datetime.time(23, 59))

    def test_hours_in_range_classic_format(self):
        with self.assertRaises(ValueError):
            self.timer.parse_time('25:30')
        with self.assertRaises(ValueError):
            self.timer.parse_time('30:20')
        with self.assertRaises(ValueError):
            self.timer.parse_time('-1:20')

    def test_minutes_in_range_classic_format(self):
        with self.assertRaises(ValueError):
            self.timer.parse_time('10:80')
        with self.assertRaises(ValueError):
            self.timer.parse_time('2:-40')
        with self.assertRaises(ValueError):
            self.timer.parse_time('70:-40')

    def test_time_parser_am_pm_format(self):
        # Test without space in front of am/pm
        self.assertEqual(self.timer.parse_time('1:30pm'),
                         datetime.time(13, 30))
        self.assertEqual(self.timer.parse_time('1:30am'), datetime.time(1, 30))

        # Test with space in front of am/pm
        self.assertEqual(self.timer.parse_time('1:30 pm'),
                         datetime.time(13, 30))
        self.assertEqual(self.timer.parse_time('1:30 am'),
                         datetime.time(1, 30))

        # Test only format of HH & am/pm
        self.assertEqual(self.timer.parse_time('1am'), datetime.time(1, 0))
        self.assertEqual(self.timer.parse_time('1pm'), datetime.time(13, 0))
        self.assertEqual(self.timer.parse_time('10 am'), datetime.time(10, 0))
        self.assertEqual(self.timer.parse_time('10 pm'), datetime.time(22, 0))

    def test_time_parser_AM_PM_format(self):
        # Test without space in front of am/pm
        self.assertEqual(self.timer.parse_time('2:40PM'),
                         datetime.time(14, 40))
        self.assertEqual(self.timer.parse_time('2:40AM'), datetime.time(2, 40))

        # Test with space in front of am/pm
        self.assertEqual(self.timer.parse_time('2:40 PM'),
                         datetime.time(14, 40))
        self.assertEqual(self.timer.parse_time('2:40 AM'),
                         datetime.time(2, 40))

        # Test only format of HH & am/pm
        self.assertEqual(self.timer.parse_time('2AM'), datetime.time(2, 0))
        self.assertEqual(self.timer.parse_time('2PM'), datetime.time(14, 0))
        self.assertEqual(self.timer.parse_time('11 AM'), datetime.time(11, 0))
        self.assertEqual(self.timer.parse_time('11 PM'), datetime.time(23, 0))

    def test_12_hour_format_am_pm(self):
        self.assertEqual(self.timer.parse_time('12 am'), datetime.time(0, 0))
        self.assertEqual(self.timer.parse_time('12 pm'), datetime.time(12, 0))
        self.assertEqual(self.timer.parse_time('12:30 am'),
                         datetime.time(0, 30))
        self.assertEqual(self.timer.parse_time('12:30 pm'),
                         datetime.time(12, 30))

    def test_hours_are_in_range_am_pm_format(self):
        self.assertEqual(self.timer.parse_time("5:20"), datetime.time(5, 20))
        with self.assertRaises(ValueError):
            self.timer.parse_time('-3:20pm')
        with self.assertRaises(ValueError):
            self.timer.parse_time('25:20pm')
        with self.assertRaises(ValueError):
            self.timer.parse_time('99:20pm')
        with self.assertRaises(ValueError):
            self.timer.parse_time('-1pm')
        with self.assertRaises(ValueError):
            self.timer.parse_time('16pm')
        with self.assertRaises(ValueError):
            self.timer.parse_time('40 am')

    def test_minutes_are_in_range_am_pm_format(self):
        self.assertEqual(self.timer.parse_time('0:20'), datetime.time(0, 20))
        with self.assertRaises(ValueError):
            self.timer.parse_time('0:-20pm')
        with self.assertRaises(ValueError):
            self.timer.parse_time('0:60pm')
        with self.assertRaises(ValueError):
            self.timer.parse_time('0:80pm')

    def test_time_parser_army_time_format(self):
        self.assertEqual(self.timer.parse_time('0000'), datetime.time(0, 0))
        self.assertEqual(self.timer.parse_time('0530'), datetime.time(5, 30))
        self.assertEqual(self.timer.parse_time('1645'), datetime.time(16, 45))
        self.assertEqual(self.timer.parse_time('2000'), datetime.time(20, 0))

    def test_out_of_range_values_army_time_format(self):
        with self.assertRaises(ValueError):
            self.timer.parse_time('2500')
        with self.assertRaises(ValueError):
            self.timer.parse_time('2060')
        with self.assertRaises(ValueError):
            self.timer.parse_time('-130')
        with self.assertRaises(ValueError):
            self.timer.parse_time('15-30')
