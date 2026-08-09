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

"""Structural tests for the recurring menu definition (#1339).

A menu item without an action attribute is inert in GTK4: it renders but
activates nothing. The weekly submenu lost the action on one weekday and
carried an orphan target on another item, so selecting them silently
failed to enable recurrence and the task closed without duplicating.
"""

from unittest import TestCase

from lxml import etree

UI_FILE = 'GTG/gtk/data/recurring_menu.ui'

KNOWN_ACTIONS = (
    'recurring_menu.is_recurring',
    'recurring_menu.recurr_every_day',
    'recurring_menu.recurr_every_otherday',
    'recurring_menu.recurr_every_week',
    'recurring_menu.recurr_week_day',
    'recurring_menu.recurr_month_today',
    'recurring_menu.recurr_year_today',
)


class TestRecurringMenuUi(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tree = etree.parse(UI_FILE)

    def _menu_items(self):
        return self.tree.findall('.//menu//item')

    def test_every_menu_item_has_an_action(self):
        for item in self._menu_items():
            if item.find('./attribute[@name="custom"]') is not None:
                continue
            label = item.find('./attribute[@name="label"]')
            action = item.find('./attribute[@name="action"]')
            self.assertIsNotNone(
                action,
                f'Menu item {label.text!r} has no action and is inert')

    def test_every_action_is_installed_by_the_menu_class(self):
        for item in self._menu_items():
            action = item.find('./attribute[@name="action"]')
            if action is None:
                continue
            self.assertIn(action.text, KNOWN_ACTIONS)

    def test_week_day_targets_are_parsable_terms(self):
        week_days = ('Monday', 'Tuesday', 'Wednesday', 'Thursday',
                     'Friday', 'Saturday', 'Sunday')
        for item in self._menu_items():
            action = item.find('./attribute[@name="action"]')
            if action is None or action.text != 'recurring_menu.recurr_week_day':
                continue
            target = item.find('./attribute[@name="target"]')
            self.assertIsNotNone(target)
            self.assertIn(target.text, week_days)
