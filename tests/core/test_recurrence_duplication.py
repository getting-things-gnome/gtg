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

"""Regression tests for #1339.

Completing a recurring task duplicates it as its next occurrence. The
duplicate must itself be recurring, otherwise the chain dies at its next
completion and the task disappears from the Open and Actionable views.
"""

from unittest import TestCase

from GTG.core.tasks import Status, TaskStore


class TestRecurrenceDuplication(TestCase):

    def _active_tasks(self, store):
        return [t for t in store.lookup.values() if t.status == Status.ACTIVE]

    def test_duplicate_inherits_recurrence(self):
        store = TaskStore()
        task = store.new('Water the plants')
        task.set_recurring(True, 'day', newtask=True)

        task.toggle_active()

        actives = self._active_tasks(store)
        self.assertEqual(len(actives), 1)
        duplicate = actives[0]
        self.assertTrue(duplicate.is_recurring)
        self.assertEqual(duplicate.recurring_term, 'day')

    def test_duplicate_due_date_is_next_occurrence(self):
        store = TaskStore()
        task = store.new('Water the plants')
        task.set_recurring(True, 'day', newtask=True)

        task.toggle_active()

        duplicate = self._active_tasks(store)[0]
        self.assertGreater(duplicate.date_due, task.date_due)

    def test_recurring_chain_survives_repeated_completions(self):
        store = TaskStore()
        task = store.new('Water the plants')
        task.set_recurring(True, 'day', newtask=True)

        for _ in range(5):
            actives = self._active_tasks(store)
            self.assertEqual(len(actives), 1)
            actives[0].toggle_active()

        self.assertEqual(len(self._active_tasks(store)), 1)

    def test_duplicated_children_inherit_recurrence(self):
        store = TaskStore()
        parent = store.new('Morning routine')
        store.new('Stretch', parent=parent.id)
        parent.set_recurring(True, 'day', newtask=True)

        parent.toggle_active()

        actives = self._active_tasks(store)
        self.assertEqual(len(actives), 2)
        for task in actives:
            self.assertTrue(task.is_recurring)
            self.assertEqual(task.recurring_term, 'day')
