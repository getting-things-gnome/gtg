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

'''
Contains the Backend class for both Tomboy and Gnote
'''
# Note: To introspect tomboy, execute:
#    qdbus org.gnome.Tomboy /org/gnome/Tomboy/RemoteControl

import os
import threading
import uuid
import dbus
import datetime
import unicodedata

from GTG.tools.testingmode import TestingMode
from GTG.tools.borg import Borg
from GTG.backends.genericbackend import GenericBackend
from GTG.backends.backendsignals import BackendSignals
from GTG.backends.syncengine import SyncEngine, SyncMeme
from GTG.tools.logger import Log
from GTG.tools.watchdog import Watchdog
from GTG.tools.interruptible import interruptible
from GTG.tools.tags import extract_tags_from_text


class GenericTomboy(GenericBackend):
    '''Backend class for Tomboy/Gnote'''

###############################################################################
### Backend standard methods ##################################################
###############################################################################
    def __init__(self, parameters):
        """
        See GenericBackend for an explanation of this function.
        """
        super(GenericTomboy, self).__init__(parameters)
        # loading the saved state of the synchronization, if any
        self.data_path = os.path.join('backends/tomboy/',
                                      "sync_engine-" + self.get_id())
        self.sync_engine = self._load_pickled_file(self.data_path,
                                                   SyncEngine())
        # if the backend is being tested, we connect to a different DBus
        # interface to avoid clashing with a running instance of Tomboy
        if TestingMode().get_testing_mode():
            # just used for testing purposes
            self.BUS_ADDRESS = \
                self._parameters["use this fake connection instead"]
        else:
            self.BUS_ADDRESS = self._BUS_ADDRESS
        # we let some time pass before considering a tomboy task for importing,
        # as the user may still be editing it. Here, we store the Timer objects
        # that will execute after some time after each tomboy signal.
        # NOTE: I'm not sure if this is the case anymore (but it shouldn't hurt
        #      anyway). (invernizzi)
        self._tomboy_setting_timers = {}

    def initialize(self):
        '''
        See GenericBackend for an explanation of this function.
        Connects to the session bus and sets the callbacks for bus signals
        '''
        super(GenericTomboy, self).initialize()
        with self.DbusWatchdog(self):
            bus = dbus.SessionBus()
            bus.add_signal_receiver(self.on_note_saved,
                                    dbus_interface=self.BUS_ADDRESS[2],
                                    signal_name="NoteSaved")
            bus.add_signal_receiver(self.on_note_deleted,
                                    dbus_interface=self.BUS_ADDRESS[2],
                                    signal_name="NoteDeleted")

    @interruptible
    def start_get_tasks(self):
        '''
        See GenericBackend for an explanation of this function.
        Gets all the notes from Tomboy and sees if they must be added in GTG
        (and, if so, it adds them).
        '''
        tomboy_notes = []
        with self.TomboyConnection(self, *self.BUS_ADDRESS) as tomboy:
            with self.DbusWatchdog(self):
                tomboy_notes = [note_id for note_id in
                                tomboy.ListAllNotes()]
        # adding the new ones
        for note in tomboy_notes:
            self.cancellation_point()
            self._process_tomboy_note(note)
        # checking if some notes have been deleted while GTG was not running
        stored_notes_ids = self.sync_engine.get_all_remote()
        for note in set(stored_notes_ids).difference(set(tomboy_notes)):
            self.on_note_deleted(note, None)

    def save_state(self):
        '''Saves the state of the synchronization'''
        self._store_pickled_file(self.data_path, self.sync_engine)

    def quit(self, disable=False):
        '''
        See GenericBackend for an explanation of this function.
        '''

        def quit_thread():
            while True:
                try:
                    [key, timer] = \
                        self._tomboy_setting_timers.iteritems().next()
                except StopIteration:
                    break
                timer.cancel()
                del self._tomboy_setting_timers[key]
        threading.Thread(target=quit_thread).start()
        super(GenericTomboy, self).quit(disable)

###############################################################################
### Something got removed #####################################################
###############################################################################
    @interruptible
    def on_note_deleted(self, note, something):
        '''
        Callback, executed when a tomboy note is deleted.
        Deletes the related GTG task.

        @param note: the id of the Tomboy note
        @param something: not used, here for signal callback compatibility
        '''
        with self.datastore.get_backend_mutex():
            self.cancellation_point()
            try:
                tid = self.sync_engine.get_local_id(note)
            except KeyError:
                return
            if self.datastore.has_task(tid):
                self.datastore.request_task_deletion(tid)
                self.break_relationship(remote_id=note)

    @interruptible
    def remove_task(self, tid):
        '''
        See GenericBackend for an explanation of this function.
        '''
        with self.datastore.get_backend_mutex():
            self.cancellation_point()
            try:
                note = self.sync_engine.get_remote_id(tid)
            except KeyError:
                return
            with self.TomboyConnection(self, *self.BUS_ADDRESS) as tomboy:
                with self.DbusWatchdog(self):
                    if tomboy.NoteExists(note):
                        tomboy.DeleteNote(note)
                        self.break_relationship(local_id=tid)

    def _exec_lost_syncability(self, tid, note):
        '''
        Executed when a relationship between tasks loses its syncability
        property. See SyncEngine for an explanation of that.
        This function finds out which object (task/note) is the original one
        and which is the copy, and deletes the copy.

        @param tid: a GTG task tid
        @param note: a tomboy note id
        '''
        self.cancellation_point()
        meme = self.sync_engine.get_meme_from_remote_id(note)
        # First of all, the relationship is lost
        self.sync_engine.break_relationship(remote_id=note)
        if meme.get_origin() == "GTG":
            with self.TomboyConnection(self, *self.BUS_ADDRESS) as tomboy:
                with self.DbusWatchdog(self):
                    tomboy.DeleteNote(note)
        else:
            self.datastore.request_task_deletion(tid)

###############################################################################
### Process tasks #############################################################
###############################################################################
    def _process_tomboy_note(self, note):
        '''
        Given a tomboy note, finds out if it must be synced to a GTG note and,
        if so, it carries out the synchronization (by creating or updating a
        GTG task, or deleting itself if the related task has been deleted)

        @param note: a Tomboy note id
        '''
        with self.datastore.get_backend_mutex():
            self.cancellation_point()
            is_syncable = self._tomboy_note_is_syncable(note)
            has_task = self.datastore.has_task
            note_exists = self._tomboy_note_exists
            with self.DbusWatchdog(self):
                action, tid = self.sync_engine.analyze_remote_id(note,
                                                                 has_task,
                                                                 note_exists,
                                                                 is_syncable)
            Log.debug("processing tomboy (%s, %s)" % (action, is_syncable))

            if action == SyncEngine.ADD:
                tid = str(uuid.uuid4())
                task = self.datastore.task_factory(tid)
                self._populate_task(task, note)
                modified_for = self.get_modified_for_note(note)
                self.record_relationship(local_id=tid,
                                         remote_id=note,
                                         meme=SyncMeme(task.get_modified(),
                                                       modified_for,
                                                       self.get_id()))
                self.datastore.push_task(task)

            elif action == SyncEngine.UPDATE:
                task = self.datastore.get_task(tid)
                meme = self.sync_engine.get_meme_from_remote_id(note)
                newest = meme.which_is_newest(task.get_modified(),
                                              self.get_modified_for_note(note))
                if newest == "remote":
                    self._populate_task(task, note)
                    meme.set_local_last_modified(task.get_modified())
                    meme.set_remote_last_modified(
                        self.get_modified_for_note(note))
                    self.save_state()

            elif action == SyncEngine.REMOVE:
                with self.TomboyConnection(self, *self.BUS_ADDRESS) as tomboy:
                    with self.DbusWatchdog(self):
                        tomboy.DeleteNote(note)
                    try:
                        self.sync_engine.break_relationship(remote_id=note)
                    except KeyError:
                        pass

            elif action == SyncEngine.LOST_SYNCABILITY:
                self._exec_lost_syncability(tid, note)

    @interruptible
    def set_task(self, task):
        '''
        See GenericBackend for an explanation of this function.
        '''
        self.cancellation_point()
        is_syncable = self._gtg_task_is_syncable_per_attached_tags(task)
        tid = task.get_id()
        with self.datastore.get_backend_mutex():
            with self.TomboyConnection(self, *self.BUS_ADDRESS) as tomboy:
                has_task = self.datastore.has_task
                has_note = tomboy.NoteExists
                can_sync = is_syncable
                with self.DbusWatchdog(self):
                    action, note = self.sync_engine.analyze_local_id(tid,
                                                                     has_task,
                                                                     has_note,
                                                                     can_sync)
                Log.debug("processing gtg (%s, %d)" % (action, is_syncable))

                if action == SyncEngine.ADD:
                    # GTG allows multiple tasks with the same name,
                    # Tomboy doesn't. we need to handle the renaming
                    # manually
                    title = task.get_title()
                    duplicate_counter = 1
                    with self.DbusWatchdog(self):
                        note = tomboy.CreateNamedNote(title)
                        while note == "":
                            duplicate_counter += 1
                            note = tomboy.CreateNamedNote(title + "(%d)" %
                                                          duplicate_counter)
                    if duplicate_counter != 1:
                        # if we needed to rename, we have to rename also
                        # the gtg task
                        task.set_title(title + " (%d)" % duplicate_counter)

                    self._populate_note(note, task)
                    self.record_relationship(
                        local_id=tid, remote_id=note,
                        meme=SyncMeme(task.get_modified(),
                                      self.get_modified_for_note(note),
                                      "GTG"))

                elif action == SyncEngine.UPDATE:
                    meme = self.sync_engine.get_meme_from_local_id(
                        task.get_id())
                    modified_for = self.get_modified_for_note(note)
                    newest = meme.which_is_newest(task.get_modified(),
                                                  modified_for)
                    if newest == "local":
                        self._populate_note(note, task)
                        meme.set_local_last_modified(task.get_modified())
                        meme.set_remote_last_modified(
                            self.get_modified_for_note(note))
                        self.save_state()

                elif action == SyncEngine.REMOVE:
                    self.datastore.request_task_deletion(tid)
                    try:
                        self.sync_engine.break_relationship(local_id=tid)
                        self.save_state()
                    except KeyError:
                        pass

                elif action == SyncEngine.LOST_SYNCABILITY:
                    self._exec_lost_syncability(tid, note)

###############################################################################
### Helper methods ############################################################
###############################################################################
    @interruptible
    def on_note_saved(self, note):
        '''
        Callback, executed when a tomboy note is saved by Tomboy itself.
        Updates the related GTG task (or creates one, if necessary).

        @param note: the id of the Tomboy note
        '''
        self.cancellation_point()
        # NOTE: we let some seconds pass before executing the real callback, as
        #      the editing of the Tomboy note may still be in progress

        @interruptible
        def _execute_on_note_saved(self, note):
            self.cancellation_point()
            try:
                del self._tomboy_setting_timers[note]
            except:
                pass
            self._process_tomboy_note(note)
            self.save_state()

        try:
            self._tomboy_setting_timers[note].cancel()
        except KeyError:
            pass
        finally:
            timer = threading.Timer(5, _execute_on_note_saved,
                                    args=(self, note))
            self._tomboy_setting_timers[note] = timer
            timer.start()

    def _tomboy_note_is_syncable(self, note):
        '''
        Returns True if this tomboy note should be synced into GTG tasks.

        @param note: the note id
        @returns Boolean
        '''
        attached_tags = self.get_attached_tags()
        if GenericBackend.ALLTASKS_TAG in attached_tags:
            return True
        with self.TomboyConnection(self, *self.BUS_ADDRESS) as tomboy:
            with self.DbusWatchdog(self):
                content = tomboy.GetNoteContents(note)
            syncable = False
            for tag in attached_tags:
                try:
                    content.index(tag)
                    syncable = True
                    break
                except ValueError:
                    pass
            return syncable

    def _tomboy_note_exists(self, note):
        '''
        Returns True if  a tomboy note exists with the given id.

        @param note: the note id
        @returns Boolean
        '''
        with self.TomboyConnection(self, *self.BUS_ADDRESS) as tomboy:
            with self.DbusWatchdog(self):
                return tomboy.NoteExists(note)

    def get_modified_for_note(self, note):
        '''
        Returns the modification time for the given note id.

        @param note: the note id
        @returns datetime.datetime
        '''
        with self.TomboyConnection(self, *self.BUS_ADDRESS) as tomboy:
            with self.DbusWatchdog(self):
                return datetime.datetime.fromtimestamp(
                    tomboy.GetNoteChangeDate(note))

    def _tomboy_split_title_and_text(self, content):
        '''
        Tomboy does not have a "getTitle" and "getText" functions to get the
        title and the text of a note separately. Instead, it has a getContent
        function, that returns both of them.
        This function splits up the output of getContent into a title string
        and a text string.

        @param content: a string, the result of a getContent call
        @returns list: a list composed by [title, text]
        '''
        try:
            end_of_title = content.index('\n')
        except ValueError:
            return content, unicode("")
        title = content[: end_of_title]
        if len(content) > end_of_title:
            return title, content[end_of_title + 1:]
        else:
            return title, unicode("")

    def _populate_task(self, task, note):
        '''
        Copies the content of a Tomboy note into a task.

        @param task: a GTG Task
        @param note: a Tomboy note
        '''
        # add tags objects (it's not enough to have @tag in the text to add a
        # tag
        with self.TomboyConnection(self, *self.BUS_ADDRESS) as tomboy:
            with self.DbusWatchdog(self):
                content = tomboy.GetNoteContents(note)
        # update the tags list
        task.set_only_these_tags(extract_tags_from_text(content))
        # extract title and text
        [title, text] = self._tomboy_split_title_and_text(unicode(content))
        # Tomboy speaks unicode, we don't
        title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore')
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore')
        task.set_title(title)
        task.set_text(text)
        task.add_remote_id(self.get_id(), note)

    def _populate_note(self, note, task):
        '''
        Copies the content of a task into a Tomboy note.

        @param note: a Tomboy note
        @param task: a GTG Task
        '''
        title = task.get_title()
        with self.TomboyConnection(self, *self.BUS_ADDRESS) as tomboy:
            with self.DbusWatchdog(self):
                tomboy.SetNoteContents(note, title + '\n' +
                                       task.get_excerpt(strip_tags=False))

    def break_relationship(self, *args, **kwargs):
        '''
        Proxy method for SyncEngine.break_relationship, which also saves the
        state of the synchronization.
        '''
        # tomboy passes Dbus.String objects, which are not pickable. We convert
        # those to unicode
        if "remote_id" in kwargs:
            kwargs["remote_id"] = unicode(kwargs["remote_id"])
        try:
            self.sync_engine.break_relationship(*args, **kwargs)
            # we try to save the state at each change in the sync_engine:
            # it's slower, but it should avoid widespread task
            # duplication
            self.save_state()
        except KeyError:
            pass

    def record_relationship(self, *args, **kwargs):
        '''
        Proxy method for SyncEngine.break_relationship, which also saves the
        state of the synchronization.
        '''
        # tomboy passes Dbus.String objects, which are not pickable. We convert
        # those to unicode
        if "remote_id" in kwargs:
            kwargs["remote_id"] = unicode(kwargs["remote_id"])

        self.sync_engine.record_relationship(*args, **kwargs)
        # we try to save the state at each change in the sync_engine:
        # it's slower, but it should avoid widespread task
        # duplication
        self.save_state()

###############################################################################
### Connection handling #######################################################
###############################################################################
    class TomboyConnection(Borg):
        '''
        TomboyConnection creates a connection to TOMBOY via DBus and
        handles all the possible exceptions.
        It is a class that can be used with a with statement.
        Example::
            with self.TomboyConnection(self, *self.BUS_ADDRESS) as tomboy:
                #do something
        '''

        def __init__(self, backend, bus_name, bus_path, bus_interface):
            '''
            Sees if a TomboyConnection object already exists. If so, since we
            are inheriting from a Borg object, the initialization already took
            place.
            If not, it tries to connect to Tomboy via Dbus. If the connection
            is not possible, the user is notified about it.

            @param backend: a reference to a Backend
            @param bus_name: the DBus address of Tomboy
            @param bus_path: the DBus path of Tomboy RemoteControl
            @param bus_interface: the DBus address of Tomboy RemoteControl
            '''
            super(GenericTomboy.TomboyConnection, self).__init__()
            if hasattr(self, "tomboy_connection_is_ok") and \
                    self.tomboy_connection_is_ok:
                return
            self.backend = backend
            self.tomboy_connection_is_ok = True
            with GenericTomboy.DbusWatchdog(backend):
                bus = dbus.SessionBus()
                try:
                    obj = bus.get_object(bus_name, bus_path)
                    self.tomboy = dbus.Interface(obj, bus_interface)
                except dbus.DBusException:
                    self.tomboy_failed()
                    self.tomboy = None

        def __enter__(self):
            '''
            Returns the Tomboy connection

            @returns: dbus.Interface
            '''
            return self.tomboy

        def __exit__(self, exception_type, value, traceback):
            '''
            Checks the state of the connection.
            If something went wrong for the connection, notifies the user.

            @param exception_type: the type of exception that occurred, or
                                   None
            @param value: the instance of the exception occurred, or None
            @param traceback: the traceback of the error
            @returns: False if some exception must be re-raised.
            '''
            if isinstance(value, dbus.DBusException) or \
                    not self.tomboy_connection_is_ok:
                self.tomboy_failed()
                return True
            else:
                return False

        def tomboy_failed(self):
            """ Handle failed tomboy connection.

            Disable backend and show error in notification bar """
            self.tomboy_connection_is_ok = False
            BackendSignals().backend_failed(self.backend.get_id(),
                                            BackendSignals.ERRNO_DBUS)
            self.backend.quit(disable=True)

    class DbusWatchdog(Watchdog):
        '''
        A simple watchdog to detect stale dbus connections
        '''

        def __init__(self, backend):
            '''
            Simple constructor, which sets _when_taking_too_long as the
            function to run when the connection is taking too long.

            @param backend: a Backend object
            '''
            self.backend = backend
            super(GenericTomboy.DbusWatchdog, self).__init__(
                3, self._when_taking_too_long)

        def _when_taking_too_long(self):
            '''
            Function that is executed when the Dbus connection seems to be
            hanging. It disables the backend and signals the error to the user.
            '''
            Log.error("Dbus connection is taking too long for the Tomboy/Gnote"
                      "backend!")
            BackendSignals().backend_failed(self.backend.get_id(),
                                            BackendSignals.ERRNO_DBUS)
            self.backend.quit(disable=True)
