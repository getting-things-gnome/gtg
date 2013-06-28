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

""" Tests for the TwoKeyDict class """

import unittest
import uuid

from GTG.tools.twokeydict import TwoKeyDict


class TestTwoKeyDict(unittest.TestCase):
    """ Tests for the TwoKeyDict object. """

    def test_add_and_gets(self):
        """ Test for the __init__, _get_by_first, _get_by_second function """
        triplets = [(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
                    for a in xrange(10)]
        tw_dict = TwoKeyDict(*triplets)
        for triplet in triplets:
            self.assertEqual(tw_dict._get_by_primary(triplet[0]), triplet[2])
            self.assertEqual(tw_dict._get_by_secondary(triplet[1]), triplet[2])

    def test_remove_by_first_or_second(self):
        """ Test for removing triplets form the TwoKeyDict """
        triplet_first = (1, 'I', 'one')
        triplet_second = (2, 'II', 'two')
        tw_dict = TwoKeyDict(triplet_first, triplet_second)
        tw_dict._remove_by_primary(triplet_first[0])
        tw_dict._remove_by_secondary(triplet_second[1])
        missing_first = 0
        missing_second = 0
        try:
            tw_dict._get_by_primary(triplet_first[0])
        except KeyError:
            missing_first += 1
        try:
            tw_dict._get_by_secondary(triplet_second[0])
        except KeyError:
            missing_first += 1
        try:
            tw_dict._get_by_secondary(triplet_first[1])
        except KeyError:
            missing_second += 1
        try:
            tw_dict._get_by_secondary(triplet_second[1])
        except KeyError:
            missing_second += 1
        self.assertEqual(missing_first, 2)
        self.assertEqual(missing_second, 2)
        # check for memory leaks
        dict_len = 0
        for key in tw_dict._primary_to_value.iterkeys():
            dict_len += 1
        self.assertEqual(dict_len, 0)

    def test_get_primary_and_secondary_key(self):
        """ Test for fetching the objects stored in the TwoKeyDict """
        triplets = [(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
                    for a in xrange(10)]
        tw_dict = TwoKeyDict(*triplets)
        for triplet in triplets:
            self.assertEqual(tw_dict._get_secondary_key(triplet[0]),
                             triplet[1])
            self.assertEqual(tw_dict._get_primary_key(triplet[1]),
                             triplet[0])

    def test_missing_and_then_add(self):
        # Primary
        local_id = '3ea957cb-417f-4944-be6c-02a1b0a84bd2'
        # Secondary
        remote_id = 'https://api.launchpad.net/1.0/bugs/345808'
        value = "Hello world"

        tw_dict = TwoKeyDict()
        self.assertRaises(KeyError, tw_dict._get_secondary_key, remote_id)
        tw_dict.add((local_id, remote_id, value))
        self.assertEqual(remote_id, tw_dict._get_secondary_key(local_id))


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestTwoKeyDict)
