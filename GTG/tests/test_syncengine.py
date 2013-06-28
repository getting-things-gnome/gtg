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

""" Tests for the SyncEngine class """

import unittest
import uuid

from GTG.backends.syncengine import SyncEngine


class TestSyncEngine(unittest.TestCase):
    """ Tests for the SyncEngine object. """

    def setUp(self):
        self.ftp_local = FakeTaskProvider()
        self.ftp_remote = FakeTaskProvider()
        self.sync_engine = SyncEngine()

    def test_analyze_element_and_record_and_break_relationship(self):
        """ Test for the _analyze_element, analyze_remote_id, analyze_local_id,
        record_relationship, break_relationship """
        # adding a new local task
        has_local_task = self.ftp_local.has_task
        has_remote_task = self.ftp_remote.has_task
        local_id = uuid.uuid4()
        self.ftp_local.fake_add_task(local_id)
        self.assertEqual(self.sync_engine.analyze_local_id(local_id,
                                                           has_local_task,
                                                           has_remote_task),
                         (SyncEngine.ADD, None))
        # creating the related remote task
        remote_id = uuid.uuid4()
        self.ftp_remote.fake_add_task(remote_id)
        # informing the sync_engine about that
        self.sync_engine.record_relationship(local_id, remote_id, object())
        # verifying that it understood that
        self.assertEqual(self.sync_engine.analyze_local_id(local_id,
                                                           has_local_task,
                                                           has_remote_task),
                         (SyncEngine.UPDATE, remote_id))
        self.assertEqual(self.sync_engine.analyze_remote_id(remote_id,
                                                            has_local_task,
                                                            has_remote_task),
                         (SyncEngine.UPDATE, local_id))
        # and not the reverse
        self.assertEqual(self.sync_engine.analyze_remote_id(local_id,
                                                            has_local_task,
                                                            has_remote_task),
                         (SyncEngine.ADD, None))
        self.assertEqual(self.sync_engine.analyze_local_id(remote_id,
                                                           has_local_task,
                                                           has_remote_task),
                         (SyncEngine.ADD, None))
        # now we remove the remote task
        self.ftp_remote.fake_remove_task(remote_id)
        self.assertEqual(self.sync_engine.analyze_local_id(local_id,
                                                           has_local_task,
                                                           has_remote_task),
                         (SyncEngine.REMOVE, None))
        self.sync_engine.break_relationship(local_id=local_id)
        self.assertEqual(self.sync_engine.analyze_local_id(local_id,
                                                           has_local_task,
                                                           has_remote_task),
                         (SyncEngine.ADD, None))
        self.assertEqual(self.sync_engine.analyze_remote_id(remote_id,
                                                            has_local_task,
                                                            has_remote_task),
                         (SyncEngine.ADD, None))
        # we add them back and remove giving the remote id as key to find
        # what to delete
        self.ftp_local.fake_add_task(local_id)
        self.ftp_remote.fake_add_task(remote_id)
        self.ftp_remote.fake_remove_task(remote_id)
        self.sync_engine.record_relationship(local_id, remote_id, object)
        self.sync_engine.break_relationship(remote_id=remote_id)
        self.assertEqual(self.sync_engine.analyze_local_id(local_id,
                                                           has_local_task,
                                                           has_remote_task),
                         (SyncEngine.ADD, None))
        self.assertEqual(self.sync_engine.analyze_remote_id(remote_id,
                                                            has_local_task,
                                                            has_remote_task),
                         (SyncEngine.ADD, None))

    def test_syncability(self):
        """ Test for the _analyze_element, analyze_remote_id, analyze_local_id.
        Checks that the is_syncable parameter is used correctly """
        # adding a new local task unsyncable
        has_local_task = self.ftp_local.has_task
        has_remote_task = self.ftp_remote.has_task
        local_id = uuid.uuid4()
        self.ftp_local.fake_add_task(local_id)
        self.assertEqual(self.sync_engine.analyze_local_id(local_id,
                                                           has_local_task,
                                                           has_remote_task,
                                                           False),
                         (None, None))
        # adding a new local task, syncable
        local_id = uuid.uuid4()
        self.ftp_local.fake_add_task(local_id)
        self.assertEqual(self.sync_engine.analyze_local_id(local_id,
                                                           has_local_task,
                                                           has_remote_task),
                         (SyncEngine.ADD, None))
        # creating the related remote task
        remote_id = uuid.uuid4()
        self.ftp_remote.fake_add_task(remote_id)
        # informing the sync_engine about that
        self.sync_engine.record_relationship(local_id, remote_id, object())
        # checking that it behaves correctly with established relationships
        self.assertEqual(self.sync_engine.analyze_local_id(local_id,
                                                           has_local_task,
                                                           has_remote_task,
                                                           True),
                         (SyncEngine.UPDATE, remote_id))
        self.assertEqual(self.sync_engine.analyze_local_id(local_id,
                                                           has_local_task,
                                                           has_remote_task,
                                                           False),
                         (SyncEngine.LOST_SYNCABILITY, remote_id))
        self.assertEqual(self.sync_engine.analyze_remote_id(remote_id,
                                                            has_local_task,
                                                            has_remote_task,
                                                            True),
                         (SyncEngine.UPDATE, local_id))
        self.assertEqual(self.sync_engine.analyze_remote_id(remote_id,
                                                            has_local_task,
                                                            has_remote_task,
                                                            False),
                         (SyncEngine.LOST_SYNCABILITY, local_id))
        # now we remove the remote task
        self.ftp_remote.fake_remove_task(remote_id)
        self.assertEqual(self.sync_engine.analyze_local_id(local_id,
                                                           has_local_task,
                                                           has_remote_task,
                                                           True),
                         (SyncEngine.REMOVE, None))
        self.assertEqual(self.sync_engine.analyze_local_id(local_id,
                                                           has_local_task,
                                                           has_remote_task,
                                                           False),
                         (SyncEngine.REMOVE, None))
        self.sync_engine.break_relationship(local_id=local_id)
        self.assertEqual(self.sync_engine.analyze_local_id(local_id,
                                                           has_local_task,
                                                           has_remote_task,
                                                           True),
                         (SyncEngine.ADD, None))
        self.assertEqual(self.sync_engine.analyze_local_id(local_id,
                                                           has_local_task,
                                                           has_remote_task,
                                                           False),
                         (None, None))
        self.assertEqual(self.sync_engine.analyze_remote_id(remote_id,
                                                            has_local_task,
                                                            has_remote_task,
                                                            True),
                         (SyncEngine.ADD, None))
        self.assertEqual(self.sync_engine.analyze_remote_id(remote_id,
                                                            has_local_task,
                                                            has_remote_task,
                                                            False),
                         (None, None))


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestSyncEngine)


class FakeTaskProvider(object):

    def __init__(self):
        self.dic = {}

    def has_task(self, tid):
        return tid in self.dic

##############################################################################
### Function with the fake_ prefix are here to assist in testing, they do not
### need to be present in the real class
##############################################################################
    def fake_add_task(self, tid):
        self.dic[tid] = "something"

    def fake_get_task(self, tid):
        return self.dic[tid]

    def fake_remove_task(self, tid):
        del self.dic[tid]
