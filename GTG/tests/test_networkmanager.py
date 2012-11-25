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

""" Tests for Network Manager """

import unittest

from GTG.tools.networkmanager import is_connection_up


class TestNetworkManager(unittest.TestCase):
    """ Test network manager tool code """

    def test_is_connection_up_dont_throw_exception(self):
        """ is_connection_up() returns a boolean value and
        don't throw any exception """
        self.assertIn(is_connection_up(), [True, False])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
