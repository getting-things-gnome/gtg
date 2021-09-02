# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) - The GTG Team
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

import re
from unittest import TestCase
from GTG.gtk.editor.taskview import TAG_REGEX


class TestTaskView(TestCase):
    def test_detect_tags(self):
        """Check that tags are being detected correctly."""

        content = 'mmmm @aaaa @aaa-bbbb @ @ccc @これはタグ @1234'
        matches = re.finditer(TAG_REGEX, content)

        target_tags = ['@aaaa', '@aaa-bbbb', '@ccc', '@これはタグ', '@1234']

        for index, match in enumerate(matches):
            self.assertEqual(match.group(0), target_tags[index])


    def test_no_detect_tags(self):
        """Check that things that aren't tags aren't being detected."""

        content = 'mmmm an@email.com xxxx@ @--- no@tag'
        matches = re.findall(TAG_REGEX, content)

        self.assertEqual([], matches)
