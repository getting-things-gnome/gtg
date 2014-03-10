# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2014 - Lionel Dricot & Bertrand Rousseau
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

from unittest import TestCase

from GTG.tools.urlregex import match


class TestURLRegex(TestCase):
    """ URL Regex """

    def test_allows_ampersand_in_anchor(self):
        # Reproducer for https://bugs.launchpad.net/gtg/+bug/1023555
        url = "http://test.com/#hi&there"
        matched_url = match(url).group(0)
        self.assertEqual(url, matched_url)
