# -----------------------------------------------------------------------------
# Gettings Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2021 - the GTG contributors
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
import GTG.core.urlregex as urlregex


class TestUrlregex(TestCase):
    def test_search_does_not_include_preceeding_whitespace(self):
        match = urlregex.search("This snippet contains an url with whitespace"
            "before it:  https://wiki.gnome.org/Apps/GTG/")
        self.assertEqual(list(match)[0].group(), "https://wiki.gnome.org/Apps/GTG/")

    def test_domain_with_short_suffix(selfs):
        match = urlregex.search("https://ticketsystem.company.x/issues/12345")
        selfs.assertEqual(list(match)[0].group(), "https://ticketsystem.company.x/issues/12345")
