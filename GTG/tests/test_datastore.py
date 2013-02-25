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

""" Tests for the datastore """

import unittest
import uuid
import time
from random import randint
import gobject

import GTG
from GTG.core.datastore import DataStore
from GTG.backends.genericbackend import GenericBackend
from GTG.core import CoreConfig
from liblarch import Tree


def sleep_within_loop(duration):
    main_loop = gobject.MainLoop()
    gobject.timeout_add(duration * 1000, main_loop.quit)
    # NOTE: I am not sure why, but I need add this
    # dumb thing to run _process method of LibLarch
    gobject.idle_add(lambda: True)
    main_loop.run()


class TestDatastore(unittest.TestCase):
    """ Tests for the DataStore object.  """

    def setUp(self):
        """
        Creates the environment for the tests
        @returns: None
        """
        self.datastore = DataStore()
        self.requester = self.datastore.get_requester()

    def test_task_factory(self):
        """ Test for the task_factory function """
        # generate a Task with a random id
        tid = str(uuid.uuid4())
        task = self.datastore.task_factory(tid, newtask=True)
        self.assertTrue(isinstance(task, GTG.core.task.Task))
        self.assertEqual(task.get_id(), tid)
        self.assertEqual(task.is_new(), True)
        tid = str(uuid.uuid4())
        task = self.datastore.task_factory(tid, newtask=False)
        self.assertEqual(task.is_new(), False)

    def test_new_task_and_has_task(self):
        """ Tests the new_task function """
        task = self.datastore.new_task()
        tid = task.get_id()
        self.assertTrue(isinstance(tid, str))
        self.assertTrue(tid != '')
        self.assertTrue(task.is_new())
        self.assertTrue(self.datastore.has_task(tid))
        self.assertTrue(len(self.datastore.get_all_tasks()) == 1)

    def test_get_all_tasks(self):
        """ Tests the get_all_tasks function """
        task_ids = []
        for i in xrange(1, 10):
            task = self.datastore.new_task()
            task_ids.append(task.get_id())
            return_list = self.datastore.get_all_tasks()
            self.assertEqual(len(return_list), i)
            task_ids.sort()
            return_list.sort()
            self.assertEqual(task_ids, return_list)

    def test_get_task(self):
        '''
        Tests the get_task function
        '''
        task = self.datastore.new_task()
        self.assertTrue(isinstance(self.datastore.get_task(task.get_id()),
                                   GTG.core.task.Task))
        self.assertEqual(self.datastore.get_task(task.get_id()), task)

    def test_get_requester(self):
        '''
        Tests the get_requester function
        '''
        requester = self.datastore.get_requester()
        self.assertTrue(isinstance(requester, GTG.core.requester.Requester))

    def test_get_tasks_tree(self):
        '''
        Tests the get_tasks_tree function
        '''
        tasks_tree = self.datastore.get_tasks_tree()
        self.assertTrue(isinstance(tasks_tree, Tree))

    def test_push_task(self):
        '''
        Tests the push_task function
        '''
        task_ids = []
        for i in xrange(1, 10):
            tid = str(uuid.uuid4())
            if tid not in task_ids:
                task_ids.append(tid)
            task = self.datastore.task_factory(tid)
            return_value1 = self.datastore.push_task(task)
            self.assertTrue(return_value1)
            # we do it twice, but it should be pushed only once if it's
            # working correctly (the second should be discarded)
            return_value2 = self.datastore.push_task(task)
            self.assertFalse(return_value2)
            stored_tasks = self.datastore.get_all_tasks()
            task_ids.sort()
            stored_tasks.sort()
            self.assertEqual(task_ids, stored_tasks)

    def test_register_backend(self):
        '''
        Tests the register_backend function. It also tests the
        get_all_backends and get_backend function as a side effect
        '''
        # create a simple backend dictionary
        backend = FakeBackend(enabled=True)
        tasks_in_backend_count = randint(1, 20)
        for temp in xrange(0, tasks_in_backend_count):
            backend.fake_add_random_task()
        backend_dic = {'backend': backend, 'pid': 'a'}
        self.datastore.register_backend(backend_dic)
        all_backends = self.datastore.get_all_backends(disabled=True)
        self.assertEqual(len(all_backends), 1)
        registered_backend = self.datastore.get_backend(backend.get_id())
        self.assertEqual(backend.get_id(), registered_backend.get_id())
        self.assertTrue(isinstance(registered_backend,
                                   GTG.core.datastore.TaskSource))
        self.assertTrue(registered_backend.is_enabled())
        self.assertEqual(registered_backend.fake_get_initialized_count(), 1)
        # we give some time for the backend to push all its tasks
        sleep_within_loop(1)
        self.assertEqual(len(self.datastore.get_all_tasks()),
                         tasks_in_backend_count)

        # same test, disabled backend
        backend = FakeBackend(enabled=False)
        for temp in xrange(1, randint(2, 20)):
            backend.fake_add_random_task()
        backend_dic = {'backend': backend, 'pid': 'b'}
        self.datastore.register_backend(backend_dic)
        all_backends = self.datastore.get_all_backends(disabled=True)
        self.assertEqual(len(all_backends), 2)
        all_backends = self.datastore.get_all_backends(disabled=False)
        self.assertEqual(len(all_backends), 1)
        registered_backend = self.datastore.get_backend(backend.get_id())
        self.assertEqual(backend.get_id(), registered_backend.get_id())
        self.assertTrue(isinstance(registered_backend,
                                   GTG.core.datastore.TaskSource))
        self.assertFalse(registered_backend.is_enabled())
        self.assertEqual(registered_backend.fake_get_initialized_count(), 0)
        # we give some time for the backend to push all its tasks (is
        # shouldn't, since it's disabled, but we give time anyway
        time.sleep(1)
        self.assertEqual(len(self.datastore.get_all_tasks()),
                         tasks_in_backend_count)

    def test_set_backend_enabled(self):
        '''
        Tests the set_backend_enabled function
        '''
        enabled_backend = FakeBackend(enabled=True)
        disabled_backend = FakeBackend(enabled=False)
        self.datastore.register_backend({'backend': enabled_backend,
                                         'pid': str(uuid.uuid4()),
                                         GenericBackend.KEY_DEFAULT_BACKEND:
                                         False})
        self.datastore.register_backend({'backend': disabled_backend,
                                         'pid': str(uuid.uuid4()),
                                         GenericBackend.KEY_DEFAULT_BACKEND:
                                         False})
        # enabling an enabled backend
        self.datastore.set_backend_enabled(enabled_backend.get_id(), True)
        self.assertEqual(enabled_backend.fake_get_initialized_count(), 1)
        self.assertTrue(enabled_backend.is_enabled())
        # disabling a disabled backend
        self.datastore.set_backend_enabled(disabled_backend.get_id(), False)
        self.assertEqual(disabled_backend.fake_get_initialized_count(), 0)
        self.assertFalse(disabled_backend.is_enabled())
        # disabling an enabled backend
        self.datastore.set_backend_enabled(enabled_backend.get_id(), False)
        self.assertEqual(enabled_backend.fake_get_initialized_count(), 1)
        countdown = 10
        while countdown >= 0 and enabled_backend.is_enabled():
            time.sleep(0.1)
        self.assertFalse(enabled_backend.is_enabled())
#        #enabling a disabled backend
#        self.datastore.set_backend_enabled(disabled_backend.get_id(), True)
#        self.assertEqual(disabled_backend.fake_get_initialized_count(), 1)
#        self.assertTrue(disabled_backend.is_enabled())

    def test_remove_backend(self):
        """ Tests the remove_backend function """
        enabled_backend = FakeBackend(enabled=True)
        disabled_backend = FakeBackend(enabled=False)
        self.datastore.register_backend({'backend': enabled_backend,
                                         'pid': str(uuid.uuid4()),
                                         GenericBackend.KEY_DEFAULT_BACKEND:
                                         False})
        self.datastore.register_backend({'backend': disabled_backend,
                                         'pid': str(uuid.uuid4()),
                                         GenericBackend.KEY_DEFAULT_BACKEND:
                                         False})
        # removing an enabled backend
        self.datastore.remove_backend(enabled_backend.get_id())
        # waiting
        countdown = 10
        while countdown >= 0 and enabled_backend.is_enabled():
            time.sleep(0.1)
        self.assertFalse(enabled_backend.is_enabled())
        self.assertEqual(
            len(self.datastore.get_all_backends(disabled=True)), 1)
        # removing a disabled backend
        self.datastore.remove_backend(disabled_backend.get_id())
        self.assertFalse(disabled_backend.is_enabled())
        self.assertEqual(
            len(self.datastore.get_all_backends(disabled=True)), 0)

    def test_flush_all_tasks(self):
        '''
        Tests the flush_all_tasks function
        '''
        # we add some tasks in the datastore
        tasks_in_datastore_count = 10  # randint(1, 20)
        for temp in xrange(0, tasks_in_datastore_count):
            self.datastore.new_task()
        datastore_stored_tids = self.datastore.get_all_tasks()
        self.assertEqual(tasks_in_datastore_count, len(datastore_stored_tids))

        # we enable a backend
        backend = FakeBackend(enabled=True)
        self.datastore.register_backend({'backend': backend, 'pid': 'a'})
        # we wait for the signal storm to wear off
        sleep_within_loop(2)
        # we sync
        self.datastore.get_backend(backend.get_id()).sync()
        # and we inject task in the backend
        tasks_in_backend_count = 5  # randint(1, 20)
        for temp in xrange(0, tasks_in_backend_count):
            backend.fake_add_random_task()
        backend_stored_tids = backend.fake_get_task_ids()
        self.assertEqual(tasks_in_backend_count, len(backend_stored_tids))
        self.datastore.flush_all_tasks(backend.get_id())
        # we wait for the signal storm to wear off
        sleep_within_loop(2)
        # we sync
        self.datastore.get_backend(backend.get_id()).sync()
        all_tasks_count = tasks_in_backend_count + tasks_in_datastore_count
        new_datastore_stored_tids = self.datastore.get_all_tasks()
        new_backend_stored_tids = backend.fake_get_task_ids()
        self.assertEqual(len(new_backend_stored_tids), all_tasks_count)
        self.assertEqual(len(new_datastore_stored_tids), all_tasks_count)
        new_datastore_stored_tids.sort()
        new_backend_stored_tids.sort()
        self.assertEqual(new_backend_stored_tids, new_datastore_stored_tids)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestDatastore)


class FakeBackend(unittest.TestCase):
    '''
    Mimics the behavior of a simple backend. Just used for testing
    '''

    def __init__(self, enabled=True):
        self.enabled = enabled
        self.initialized_count = 0
        self.tasks_ids = []
        self.backend_id = str(uuid.uuid4())
        self.purged = False

    def is_enabled(self):
        return self.enabled

    def initialize(self):
        self.initialized_count += 1
        self.enabled = True

    def queue_set_task(self, task):
        if task.get_id() not in self.tasks_ids:
            self.tasks_ids.append(task.get_id())

    def has_task(self, task_id):
        return task_id in self.tasks_ids

    def queue_remove_task(self, task_id):
        self.tasks_ids.remove(task_id)

    def get_id(self):
        return self.backend_id

    def start_get_tasks(self):
        for task_id in self.tasks_ids:
            self.datastore.push_task(self.datastore.task_factory(task_id))

    def quit(self, disabled=False):
        self.enabled = not disabled

    def is_default(self):
        return True

    def set_parameter(self, param_name, param_value):
        pass

    def get_attached_tags(self):
        return [CoreConfig.ALLTASKS_TAG]

    def register_datastore(self, datastore):
        self.datastore = datastore

    ##########################################################################
    # The following are used just for testing, they're not present inside a
    # normal backend
    ##########################################################################
    def fake_get_initialized_count(self):
        return self.initialized_count

    def fake_get_task_ids(self):
        return self.tasks_ids

    def fake_add_random_task(self):
        self.tasks_ids.append(str(uuid.uuid4()))
