# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) The GTG Team
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

from GTG.gtk.browser.quick_add import parse
from GTG.core.dates import Date


class TestQuickAddParse(TestCase):

    def test_empty(self):
        default_dict = {
            'title': '',
            'tags': set(),
            'start': None,
            'due': None,
            'recurring': None
        }

        self.assertEqual(default_dict, parse(''))


    def test_basic_title(self):
        expected = {
            'title': 'Do a thing',
            'tags': set(),
            'start': None,
            'due': None,
            'recurring': None
        }

        self.assertEqual(expected, parse('Do a thing'))

    def test_basic_tags(self):
        expected = {
            'title': 'Do a thing',
            'tags': set(('home', 'work')),
            'start': None,
            'due': None,
            'recurring': None
        }

        text1 = 'Do a thing tags:home,work'
        text2 = 'Do a thing tags: home,work'
        text3 = 'Do a thing tag: home,work'
        text4 = 'Do a thing tag:home,work'

        self.assertEqual(expected, parse(text1))
        self.assertEqual(expected, parse(text2))
        self.assertEqual(expected, parse(text3))
        self.assertEqual(expected, parse(text4))


    def test_strip_at(self):
        expected1 = {
            'title': 'Do a thing',
            'tags': set(('home', 'work')),
            'start': None,
            'due': None,
            'recurring': None
        }

        expected2 = {
            'title': 'Do a thing',
            'tags': set(('家', '仕事')),
            'start': None,
            'due': None,
            'recurring': None
        }

        text1 = 'Do a thing tags:@home,@work'
        text2 = 'Do a thing tags:@家,@仕事'

        self.assertEqual(expected1, parse(text1))
        self.assertEqual(expected2, parse(text2))


    def test_tags_in_title(self):
        expected1 = {
            'title': '@phone Maruk about @work',
            'tags': set(('phone', 'work')),
            'start': None,
            'due': None,
            'recurring': None
        }

        expected2 = {
            'title': '@phone Maruk about @work',
            'tags': set(('phone', 'work', 'fun')),
            'start': None,
            'due': None,
            'recurring': None
        }

        text1 = '@phone Maruk about @work'
        text2 = '@phone Maruk about @work tags: fun'

        self.assertEqual(expected1, parse(text1))
        self.assertEqual(expected2, parse(text2))


    def test_start(self):
        expected1 = {
            'title': 'Do a thing',
            'tags': set(),
            'start': Date.parse('monday'),
            'due': None,
            'recurring': None
        }

        expected2 = {
            'title': 'Do a thing',
            'tags': set(),
            'start': Date.parse('someday'),
            'due': None,
            'recurring': None
        }

        expected3 = {
            'title': 'Do a thing',
            'tags': set(),
            'start': Date.parse('2099/02/12'),
            'due': None,
            'recurring': None
        }

        text1 = 'Do a thing start:monday'
        text2 = 'Do a thing starts:monday'
        text3 = 'Do a thing start: monday'
        text4 = 'Do a thing defer: someday'
        text5 = 'Do a thing start: 2099/02/12'

        self.assertEqual(expected1, parse(text1))
        self.assertEqual(expected1, parse(text2))
        self.assertEqual(expected1, parse(text3))
        self.assertEqual(expected3, parse(text5))


    def test_due(self):
        expected1 = {
            'title': 'Do a thing',
            'tags': set(),
            'start': None,
            'due': Date.parse('monday'),
            'recurring': None
        }

        expected2 = {
            'title': 'Do a thing',
            'tags': set(),
            'start': None,
            'due': Date.parse('someday'),
            'recurring': None
        }

        expected3 = {
            'title': 'Do a thing',
            'tags': set(),
            'start': None,
            'due': Date.parse('2099/02/12'),
            'recurring': None
        }

        text1 = 'Do a thing due:monday'
        text2 = 'Do a thing due:monday'
        text3 = 'Do a thing due: monday'
        text4 = 'Do a thing due: someday'
        text5 = 'Do a thing due: 2099/02/12'

        self.assertEqual(expected1, parse(text1))
        self.assertEqual(expected1, parse(text2))
        self.assertEqual(expected1, parse(text3))
        self.assertEqual(expected3, parse(text5))


    def test_repeat(self):
        expected1 = {
            'title': 'Do a thing',
            'tags': set(),
            'start': None,
            'due': None,
            'recurring': 'other-day'
        }

        expected2 = {
            'title': 'Do a thing',
            'tags': set(),
            'start': None,
            'due': None,
            'recurring': 'month'
        }

        expected3 = {
            'title': 'Do a thing',
            'tags': set(),
            'start': None,
            'due': None,
            'recurring': 'monday'
        }

        expected4 = {
            'title': 'Do a thing',
            'tags': set(),
            'start': None,
            'due': None,
            'recurring': 'year'
        }

        text1 = 'Do a thing every: other-day'
        text2 = 'Do a thing every:other-day'
        text3 = 'Do a thing every:month'
        text4 = 'Do a thing every:monday'
        text5 = 'Do a thing every:year'

        self.assertEqual(expected1, parse(text1))
        self.assertEqual(expected1, parse(text2))
        self.assertEqual(expected2, parse(text3))
        self.assertEqual(expected4, parse(text5))

    def test_invalid_date(self):
        expected = {
            'title': 'Do a thing',
            'tags': set(),
            'start': None,
            'due': None,
            'recurring': None
        }

        self.assertEqual(expected, parse('Do a thing due:never'))
