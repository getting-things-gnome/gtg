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

""" Tests for the tomboy backend """

from datetime import datetime
from dbus.mainloop.glib import DBusGMainLoop
import dbus
import dbus.glib
import dbus.service
import errno
import gobject
import math
import os
import random
import signal
import sys
import tempfile
import threading
import time
import unittest
import uuid

from GTG.backends import BackendFactory
from GTG.backends.genericbackend import GenericBackend
from GTG.core.datastore import DataStore

PID_TOMBOY = False


class TestBackendTomboy(unittest.TestCase):
    """ Tests for the tomboy backend """

    def setUp(self):
        thread_tomboy = threading.Thread(target=self.spawn_fake_tomboy_server)
        thread_tomboy.start()
        thread_tomboy.join()
        # only the test process should go further, the dbus server one should
        # stop here
        if not PID_TOMBOY:
            return
        # we create a custom dictionary listening to the server, and register
        # it in GTG.
        additional_dic = {}
        additional_dic["use this fake connection instead"] = (
            FakeTomboy.BUS_NAME, FakeTomboy.BUS_PATH, FakeTomboy.BUS_INTERFACE)
        additional_dic[GenericBackend.KEY_ATTACHED_TAGS] = \
            [GenericBackend.ALLTASKS_TAG]
        additional_dic[GenericBackend.KEY_DEFAULT_BACKEND] = True
        dic = BackendFactory().get_new_backend_dict('backend_tomboy',
                                                    additional_dic)
        self.datastore = DataStore()
        self.backend = self.datastore.register_backend(dic)
        # waiting for the "start_get_tasks" to settle
        time.sleep(1)
        # we create a dbus session to speak with the server
        self.bus = dbus.SessionBus()
        obj = self.bus.get_object(FakeTomboy.BUS_NAME, FakeTomboy.BUS_PATH)
        self.tomboy = dbus.Interface(obj, FakeTomboy.BUS_INTERFACE)

    def spawn_fake_tomboy_server(self):
        # the fake tomboy server has to be in a different process,
        # otherwise it will lock on the GIL.
        # For details, see
        # http://lists.freedesktop.org/archives/dbus/2007-January/006921.html

        # we use a lockfile to make sure the server is running before we start
        # the test
        global PID_TOMBOY
        lockfile_fd, lockfile_path = tempfile.mkstemp()
        PID_TOMBOY = os.fork()
        if PID_TOMBOY:
            # we wait in polling that the server has been started
            while True:
                try:
                    fd = os.open(lockfile_path,
                                 os.O_CREAT | os.O_EXCL | os.O_RDWR)
                except OSError, e:
                    if e.errno != errno.EEXIST:
                        raise
                    time.sleep(0.3)
                    continue
                os.close(fd)
                break
        else:
            FakeTomboy()
            os.close(lockfile_fd)
            os.unlink(lockfile_path)

    def tearDown(self):
        if not PID_TOMBOY:
            return
        self.datastore.save(quit=True)
        time.sleep(0.5)
        self.tomboy.FakeQuit()
        # FIXME: self.bus.close()
        os.kill(PID_TOMBOY, signal.SIGKILL)
        os.waitpid(PID_TOMBOY, 0)

    def test_everything(self):
        # we cannot use separate test functions because we only want a single
        # FakeTomboy dbus server running
        if not PID_TOMBOY:
            return
        for function in dir(self):
            if function.startswith("TEST_"):
                getattr(self, function)()
                self.tomboy.Reset()
                for tid in self.datastore.get_all_tasks():
                    self.datastore.request_task_deletion(tid)
                time.sleep(0.1)

    def TEST_processing_tomboy_notes(self):
        self.backend.set_attached_tags([GenericBackend.ALLTASKS_TAG])
        # adding a note
        note = self.tomboy.CreateNamedNote(str(uuid.uuid4()))
        self.backend._process_tomboy_note(note)
        self.assertEqual(len(self.datastore.get_all_tasks()), 1)
        tid = self.backend.sync_engine.sync_memes.get_local_id(note)
        task = self.datastore.get_task(tid)
        # re-adding that (should not change anything)
        self.backend._process_tomboy_note(note)
        self.assertEqual(len(self.datastore.get_all_tasks()), 1)
        self.assertEqual(
            self.backend.sync_engine.sync_memes.get_local_id(note), tid)
        # removing the note and updating gtg
        self.tomboy.DeleteNote(note)
        self.backend.set_task(task)
        self.assertEqual(len(self.datastore.get_all_tasks()), 0)

    def TEST_set_task(self):
        self.backend.set_attached_tags([GenericBackend.ALLTASKS_TAG])
        # adding a task
        task = self.datastore.requester.new_task()
        task.set_title("title")
        self.backend.set_task(task)
        self.assertEqual(len(self.tomboy.ListAllNotes()), 1)
        note = self.tomboy.ListAllNotes()[0]
        self.assertEqual(str(self.tomboy.GetNoteTitle(note)), task.get_title())
        # re-adding that (should not change anything)
        self.backend.set_task(task)
        self.assertEqual(len(self.tomboy.ListAllNotes()), 1)
        self.assertEqual(note, self.tomboy.ListAllNotes()[0])
        # removing the task and updating tomboy
        self.datastore.request_task_deletion(task.get_id())
        self.backend._process_tomboy_note(note)
        self.assertEqual(len(self.tomboy.ListAllNotes()), 0)

    def TEST_update_newest(self):
        self.backend.set_attached_tags([GenericBackend.ALLTASKS_TAG])
        task = self.datastore.requester.new_task()
        task.set_title("title")
        self.backend.set_task(task)
        note = self.tomboy.ListAllNotes()[0]
        gtg_modified = task.get_modified()
        tomboy_modified = self._modified_string_to_datetime(
            self.tomboy.GetNoteChangeDate(note))
        # no-one updated, nothing should happen
        self.backend.set_task(task)
        self.assertEqual(gtg_modified, task.get_modified())
        self.assertEqual(tomboy_modified,
                         self._modified_string_to_datetime(
                         self.tomboy.GetNoteChangeDate(note)))
        # we update the GTG task
        UPDATED_GTG_TITLE = "UPDATED_GTG_TITLE"
        task.set_title(UPDATED_GTG_TITLE)
        self.backend.set_task(task)
        self.assertTrue(gtg_modified < task.get_modified())
        self.assertTrue(tomboy_modified <=
                        self._modified_string_to_datetime(
                        self.tomboy.GetNoteChangeDate(note)))
        self.assertEqual(task.get_title(), UPDATED_GTG_TITLE)
        self.assertEqual(self.tomboy.GetNoteTitle(note), UPDATED_GTG_TITLE)
        gtg_modified = task.get_modified()
        tomboy_modified = self._modified_string_to_datetime(
            self.tomboy.GetNoteChangeDate(note))
        # we update the TOMBOY task
        UPDATED_TOMBOY_TITLE = "UPDATED_TOMBOY_TITLE"
        # the resolution of tomboy notes changed time is 1 second, so we need
        # to wait. This *shouldn't* be needed in the actual code because
        # tomboy signals are always a few seconds late.
        time.sleep(1)
        self.tomboy.SetNoteContents(note, UPDATED_TOMBOY_TITLE)
        self.backend._process_tomboy_note(note)
        self.assertTrue(gtg_modified <= task.get_modified())
        self.assertTrue(tomboy_modified <=
                        self._modified_string_to_datetime(
                        self.tomboy.GetNoteChangeDate(note)))
        self.assertEqual(task.get_title(), UPDATED_TOMBOY_TITLE)
        self.assertEqual(self.tomboy.GetNoteTitle(note), UPDATED_TOMBOY_TITLE)

    def TEST_processing_tomboy_notes_with_tags(self):
        self.backend.set_attached_tags(['@a'])
        # adding a not syncable note
        note = self.tomboy.CreateNamedNote("title" + str(uuid.uuid4()))
        self.backend._process_tomboy_note(note)
        self.assertEqual(len(self.datastore.get_all_tasks()), 0)
        # re-adding that (should not change anything)
        self.backend._process_tomboy_note(note)
        self.assertEqual(len(self.datastore.get_all_tasks()), 0)
        # adding a tag to that note
        self.tomboy.SetNoteContents(note, "something with @a")
        self.backend._process_tomboy_note(note)
        self.assertEqual(len(self.datastore.get_all_tasks()), 1)
        # removing the tag and resyncing
        self.tomboy.SetNoteContents(note, "something with no tags")
        self.backend._process_tomboy_note(note)
        self.assertEqual(len(self.datastore.get_all_tasks()), 0)
        # adding a syncable note
        note = self.tomboy.CreateNamedNote("title @a" + str(uuid.uuid4()))
        self.backend._process_tomboy_note(note)
        self.assertEqual(len(self.datastore.get_all_tasks()), 1)
        tid = self.backend.sync_engine.sync_memes.get_local_id(note)
        task = self.datastore.get_task(tid)
        # re-adding that (should not change anything)
        self.backend._process_tomboy_note(note)
        self.assertEqual(len(self.datastore.get_all_tasks()), 1)
        self.assertEqual(
            self.backend.sync_engine.sync_memes.get_local_id(note), tid)
        # removing the note and updating gtg
        self.tomboy.DeleteNote(note)
        self.backend.set_task(task)
        self.assertEqual(len(self.datastore.get_all_tasks()), 0)

    def TEST_set_task_with_tags(self):
        self.backend.set_attached_tags(['@a'])
        # adding a not syncable task
        task = self.datastore.requester.new_task()
        task.set_title("title")
        self.backend.set_task(task)
        self.assertEqual(len(self.tomboy.ListAllNotes()), 0)
        # making that task  syncable
        task.set_title("something else")
        task.add_tag("@a")
        self.backend.set_task(task)
        self.assertEqual(len(self.tomboy.ListAllNotes()), 1)
        note = self.tomboy.ListAllNotes()[0]
        self.assertEqual(str(self.tomboy.GetNoteTitle(note)), task.get_title())
        # re-adding that (should not change anything)
        self.backend.set_task(task)
        self.assertEqual(len(self.tomboy.ListAllNotes()), 1)
        self.assertEqual(note, self.tomboy.ListAllNotes()[0])
        # removing the syncable property and updating tomboy
        task.remove_tag("@a")
        self.backend.set_task(task)
        self.assertEqual(len(self.tomboy.ListAllNotes()), 0)

    def TEST_multiple_task_same_title(self):
        self.backend.set_attached_tags(['@a'])
        how_many_tasks = int(math.ceil(20 * random.random()))
        for iteration in xrange(0, how_many_tasks):
            task = self.datastore.requester.new_task()
            task.set_title("title")
            task.add_tag('@a')
            self.backend.set_task(task)
        self.assertEqual(len(self.tomboy.ListAllNotes()), how_many_tasks)

    def _modified_string_to_datetime(self, modified_string):
        return datetime.fromtimestamp(modified_string)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestBackendTomboy)


class FakeTomboy(dbus.service.Object):
    """
    D-Bus service object that mimics TOMBOY
    """

    # We don't directly use the tomboy dbus path to avoid conflicts
    # if tomboy is running during the test
    BUS_NAME = "Fake.Tomboy"
    BUS_PATH = "/Fake/Tomboy"
    BUS_INTERFACE = "Fake.Tomboy.RemoteControl"

    def __init__(self):
        # Attach the object to D-Bus
        DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(self.BUS_NAME, bus=self.bus)
        dbus.service.Object.__init__(self, bus_name, self.BUS_PATH)
        self.notes = {}
        threading.Thread(target=self.fake_main_loop).start()

    @dbus.service.method(BUS_INTERFACE, in_signature="s", out_signature="s")
    def GetNoteContents(self, note):
        return self.notes[note]['content']

    @dbus.service.method(BUS_INTERFACE, in_signature="s", out_signature="b")
    def NoteExists(self, note):
        return note in self.notes

    @dbus.service.method(BUS_INTERFACE, in_signature="s", out_signature="d")
    def GetNoteChangeDate(self, note):
        return self.notes[note]['changed']

    @dbus.service.method(BUS_INTERFACE, in_signature="ss")
    def SetNoteContents(self, note, text):
        self.fake_update_note(note)
        self.notes[note]['content'] = text

    @dbus.service.method(BUS_INTERFACE, in_signature="s", out_signature="s")
    def GetNoteTitle(self, note):
        return self._GetNoteTitle(note)

    def _GetNoteTitle(self, note):
        content = self.notes[note]['content']
        try:
            end_of_title = content.index('\n')
        except ValueError:
            return content
        return content[:end_of_title]

    @dbus.service.method(BUS_INTERFACE, in_signature="s")
    def DeleteNote(self, note):
        del self.notes[note]

    @dbus.service.method(BUS_INTERFACE, in_signature="s", out_signature="s")
    def CreateNamedNote(self, title):
        # this is to mimic the way tomboy handles title clashes
        if self._FindNote(title) != '':
            return ''
        note = str(uuid.uuid4())
        self.notes[note] = {'content': title}
        self.fake_update_note(note)
        return note

    @dbus.service.method(BUS_INTERFACE, in_signature="s", out_signature="s")
    def FindNote(self, title):
        return self._FindNote(title)

    def _FindNote(self, title):
        for note in self.notes:
            if self._GetNoteTitle(note) == title:
                return note
        return ''

    @dbus.service.method(BUS_INTERFACE, out_signature="as")
    def ListAllNotes(self):
        return list(self.notes)

    @dbus.service.signal(BUS_INTERFACE, signature='s')
    def NoteSaved(self, note):
        pass

    @dbus.service.signal(BUS_INTERFACE, signature='s')
    def NoteDeleted(self, note):
        pass

###############################################################################
### Function with the fake_ prefix are here to assist in testing, they do not
### need to be present in the real class
###############################################################################
    def fake_update_note(self, note):
        self.notes[note]['changed'] = time.mktime(datetime.now().timetuple())

    def fake_main_loop(self):
        gobject.threads_init()
        dbus.glib.init_threads()
        self.main_loop = gobject.MainLoop()
        self.main_loop.run()

    @dbus.service.method(BUS_INTERFACE)
    def Reset(self):
        self.notes = {}

    @dbus.service.method(BUS_INTERFACE)
    def FakeQuit(self):
        threading.Timer(0.2, self._fake_quit).start()

    def _fake_quit(self):
        self.main_loop.quit()
        sys.exit(0)
