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

"""Write-path resilience of the sync queue (#1324).

A push that raises (e.g. a lost connection mid-write) used to escape
launch_setting_thread, killing the sync thread AND leaving to_set_timer
set so the queue never ran again -- the offline edit was lost silently.
The drain now catches the failure, re-queues the task, and only gives up
after MAX_SYNC_ATTEMPTS so one poison task can't loop or block the queue.
When connectivity returns, network-changed relaunches the pending drain.
"""

import weakref
from collections import deque
from unittest import TestCase
from unittest.mock import Mock, patch

import requests

import GTG.core.networkmanager as networkmanager
from GTG.backends.backend_caldav import Backend
from GTG.backends.backend_signals import BackendSignals
from GTG.backends.generic_backend import MAX_SYNC_ATTEMPTS
from GTG.core.datastore import Datastore

_MANGLED_LAUNCH = '_GenericBackend__try_launch_setting_thread'


def _make_backend():
    """A CalDAV backend (the only concrete user of the sync queue) wired
    to a fresh datastore, without touching the network."""
    datastore = Datastore()
    backend = Backend({'pid': 'favorite', 'service-url': 'x',
                       'username': 'u', 'password': 'p', 'period': 1,
                       'is-first-run': False})
    backend.register_datastore(datastore)
    return backend


class LaunchSettingThreadResilienceTest(TestCase):

    @patch('GTG.backends.generic_backend.is_connection_up', new=lambda: True)
    def test_failed_push_is_requeued_and_queue_not_wedged(self):
        backend = _make_backend()
        tid = 'task-1'
        backend.datastore.tasks.lookup[tid] = object()
        backend.set_task = Mock(
            side_effect=requests.exceptions.ConnectionError('down'))
        backend.to_set.appendleft(tid)

        backend.launch_setting_thread()  # must not raise

        self.assertIn(tid, backend.to_set)        # re-queued, not lost
        self.assertIsNone(backend.to_set_timer)   # queue not wedged (line 672)
        backend.set_task.assert_called_once()

    @patch('GTG.backends.generic_backend.is_connection_up', new=lambda: True)
    def test_poison_task_abandoned_after_three_attempts(self):
        backend = _make_backend()
        tid = 'task-1'
        backend.datastore.tasks.lookup[tid] = object()
        backend.set_task = Mock(
            side_effect=requests.exceptions.ConnectionError('down'))
        backend.to_set.appendleft(tid)

        signals = BackendSignals()
        with patch.object(signals, 'backend_failed') as failed:
            for _ in range(MAX_SYNC_ATTEMPTS):
                backend.launch_setting_thread()

        self.assertNotIn(tid, backend.to_set)     # abandoned, no HoL block
        self.assertIsNone(backend.to_set_timer)
        self.assertEqual(backend.set_task.call_count, MAX_SYNC_ATTEMPTS)
        failed.assert_called_once_with(backend.get_id(),
                                       BackendSignals.ERRNO_NETWORK)

    @patch('GTG.backends.generic_backend.is_connection_up', new=lambda: False)
    def test_offline_failures_do_not_count_toward_the_cap(self):
        # A failure while offline is transient: the task must stay queued
        # forever (until network-changed), never abandoned as a poison.
        backend = _make_backend()
        tid = 'task-1'
        backend.datastore.tasks.lookup[tid] = object()
        backend.set_task = Mock(
            side_effect=requests.exceptions.ConnectionError('down'))
        backend.to_set.appendleft(tid)

        signals = BackendSignals()
        with patch.object(signals, 'backend_failed') as failed:
            for _ in range(MAX_SYNC_ATTEMPTS + 2):
                backend.launch_setting_thread()

        self.assertIn(tid, backend.to_set)        # still queued
        failed.assert_not_called()

    @patch('GTG.backends.generic_backend.is_connection_up', new=lambda: True)
    def test_a_healthy_task_behind_a_poison_one_still_syncs(self):
        # The poison task is abandoned (not re-queued), so the drain keeps
        # going and the good task behind it is pushed.
        backend = _make_backend()
        poison, good = 'poison', 'good'
        backend.datastore.tasks.lookup[poison] = object()
        backend.datastore.tasks.lookup[good] = object()
        backend._sync_failures[poison] = MAX_SYNC_ATTEMPTS - 1  # one away

        pushed = []

        def push(task):
            # identity of the task object tells us which tid it was
            if task is backend.datastore.tasks.lookup[poison]:
                raise requests.exceptions.ConnectionError('down')
            pushed.append(task)

        backend.set_task = Mock(side_effect=push)
        backend.to_set.appendleft(good)     # popped last
        backend.to_set.appendleft(poison)   # popped first (head)

        signals = BackendSignals()
        with patch.object(signals, 'backend_failed'):
            backend.launch_setting_thread()

        self.assertNotIn(poison, backend.to_set)
        self.assertIn(backend.datastore.tasks.lookup[good], pushed)


class NetworkReturnTriggerTest(TestCase):

    def test_network_changed_retries_registered_backends(self):
        saved = networkmanager._retry_registry
        networkmanager._retry_registry = weakref.WeakSet()
        try:
            backend = Mock()
            networkmanager.register_for_retry(backend)
            networkmanager._notify_network_available()
            backend.retry_pending_sync.assert_called_once()
        finally:
            networkmanager._retry_registry = saved

    def test_retry_pending_sync_relaunches_only_when_writes_are_queued(self):
        backend = _make_backend()

        backend.to_set.appendleft('t')
        with patch.object(backend, _MANGLED_LAUNCH) as launch:
            backend.retry_pending_sync()
        launch.assert_called_once()

        backend.to_set = deque()
        backend.to_remove = deque()
        with patch.object(backend, _MANGLED_LAUNCH) as launch:
            backend.retry_pending_sync()
        launch.assert_not_called()
