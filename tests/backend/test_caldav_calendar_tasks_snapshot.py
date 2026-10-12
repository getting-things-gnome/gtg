# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) - The Getting Things GNOME Team
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

"""Backend._get_calendar_tasks runs on the import worker thread (#1359)
while the main thread stays free to add or remove tasks, for instance
when the user creates one during a sync. Iterating the live lookup dict
then raises "dictionary changed size during iteration" and aborts the
import cycle. The worker must walk a snapshot instead."""

from unittest import TestCase
from unittest.mock import Mock, patch

from GTG.backends import backend_caldav
from GTG.backends.backend_caldav import Backend
from GTG.core.datastore import Datastore


class CalendarTasksSnapshotTest(TestCase):

    def setUp(self):
        parameters = {'pid': 'favorite', 'service-url': 'color',
                      'username': 'blue', 'password': 'no it is red',
                      'period': 1}
        self.backend = Backend(parameters)
        self.ds = Datastore()
        self.backend.register_datastore(self.ds)
        for title in ('one', 'two', 'three'):
            self.ds.tasks.new(title)

    def test_task_added_meanwhile_does_not_abort_the_walk(self):
        def add_task_from_main_thread(task, calendar):
            # Stands for the main thread adding a task while the worker
            # is between two items of the walk.
            if len(self.ds.tasks.lookup) < 6:
                self.ds.tasks.new('added during the walk')
            return True

        with patch.object(backend_caldav.CATEGORIES, 'has_calendar_tag',
                          side_effect=add_task_from_main_thread):
            found = dict(self.backend._get_calendar_tasks(Mock()))

        self.assertEqual(len(found), 3)

    def test_matching_tasks_are_still_returned(self):
        with patch.object(backend_caldav.CATEGORIES, 'has_calendar_tag',
                          return_value=True):
            found = dict(self.backend._get_calendar_tasks(Mock()))
        self.assertEqual(set(found),
                         {str(tid) for tid in self.ds.tasks.lookup})
