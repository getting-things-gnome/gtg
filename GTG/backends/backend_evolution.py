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
Backend for storing/loading tasks in Evolution Tasks
'''

import os
import time
import uuid
import datetime
import evolution
from dateutil.tz import tzutc, tzlocal

from GTG import _
from GTG.backends.genericbackend import GenericBackend
from GTG.backends.periodicimportbackend import PeriodicImportBackend
from GTG.backends.syncengine import SyncEngine, SyncMeme
from GTG.core.task import Task
from GTG.tools.interruptible import interruptible
from GTG.tools.dates import Date
from GTG.tools.logger import Log
from GTG.tools.tags import extract_tags_from_text

# Dictionaries to translate GTG tasks in Evolution ones
_GTG_TO_EVOLUTION_STATUS = \
    {Task.STA_ACTIVE: evolution.ecal.ICAL_STATUS_CONFIRMED,
     Task.STA_DONE: evolution.ecal.ICAL_STATUS_COMPLETED,
     Task.STA_DISMISSED: evolution.ecal.ICAL_STATUS_CANCELLED}

_EVOLUTION_TO_GTG_STATUS = \
    {evolution.ecal.ICAL_STATUS_CONFIRMED: Task.STA_ACTIVE,
     evolution.ecal.ICAL_STATUS_DRAFT: Task.STA_ACTIVE,
     evolution.ecal.ICAL_STATUS_FINAL: Task.STA_ACTIVE,
     evolution.ecal.ICAL_STATUS_INPROCESS: Task.STA_ACTIVE,
     evolution.ecal.ICAL_STATUS_NEEDSACTION: Task.STA_ACTIVE,
     evolution.ecal.ICAL_STATUS_NONE: Task.STA_ACTIVE,
     evolution.ecal.ICAL_STATUS_TENTATIVE: Task.STA_ACTIVE,
     evolution.ecal.ICAL_STATUS_X: Task.STA_ACTIVE,
     evolution.ecal.ICAL_STATUS_COMPLETED: Task.STA_DONE,
     evolution.ecal.ICAL_STATUS_CANCELLED: Task.STA_DISMISSED}


class Backend(PeriodicImportBackend):
    '''
    Evolution backend
    '''

    _general_description = {
        GenericBackend.BACKEND_NAME: "backend_evolution",
        GenericBackend.BACKEND_HUMAN_NAME: _("Evolution tasks"),
        GenericBackend.BACKEND_AUTHORS: ["Luca Invernizzi"],
        GenericBackend.BACKEND_TYPE: GenericBackend.TYPE_READWRITE,
        GenericBackend.BACKEND_DESCRIPTION:
        _("Lets you synchronize your GTG tasks with Evolution tasks"),
    }

    _static_parameters = {
        "period": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_INT,
            GenericBackend.PARAM_DEFAULT_VALUE: 10, },
        "is-first-run": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_BOOL,
            GenericBackend.PARAM_DEFAULT_VALUE: True, },
    }

###############################################################################
### Backend standard methods ##################################################
###############################################################################
    def __init__(self, parameters):
        '''
        See GenericBackend for an explanation of this function.
        Loads the saved state of the sync, if any
        '''
        super(Backend, self).__init__(parameters)
        # loading the saved state of the synchronization, if any
        self.sync_engine_path = os.path.join('backends/evolution/',
                                             "sync_engine-" + self.get_id())
        self.sync_engine = self._load_pickled_file(self.sync_engine_path,
                                                   SyncEngine())
        # sets up the connection to the evolution api
        task_personal = evolution.ecal.list_task_sources()[0][1]
        self._evolution_tasks = evolution.ecal.open_calendar_source(
            task_personal,
            evolution.ecal.CAL_SOURCE_TYPE_TODO)

    def do_periodic_import(self):
        """
        See PeriodicImportBackend for an explanation of this function.
        """
        stored_evolution_task_ids = set(self.sync_engine.get_all_remote())
        all_tasks = self._evolution_tasks.get_all_objects()
        current_evolution_task_ids = set([task.get_uid()
                                          for task in all_tasks])
        # If it's the very first time the backend is run, it's possible that
        # the user already synced his tasks in some way (but we don't know that
        # ). Therefore, we attempt to induce those tasks relationships matching
        # the titles.
        if self._parameters["is-first-run"]:
            gtg_titles_dic = {}
            for tid in self.datastore.get_all_tasks():
                gtg_task = self.datastore.get_task(tid)
                if not self._gtg_task_is_syncable_per_attached_tags(gtg_task):
                    continue
                gtg_title = gtg_task.get_title()
                if gtg_title in gtg_titles_dic:
                    gtg_titles_dic[gtg_task.get_title()].append(tid)
                else:
                    gtg_titles_dic[gtg_task.get_title()] = [tid]
            for evo_task_id in current_evolution_task_ids:
                evo_task = self._evo_get_task(evo_task_id)
                try:
                    tids = gtg_titles_dic[evo_task.get_summary()]
                    # we remove the tid, so that it can't be linked to two
                    # different evolution tasks
                    tid = tids.pop()
                    gtg_task = self.datastore.get_task(tid)
                    meme = SyncMeme(gtg_task.get_modified(),
                                    self._evo_get_modified(evo_task),
                                    "GTG")
                    self.sync_engine.record_relationship(
                        local_id=tid,
                        remote_id=evo_task.get_uid(),
                        meme=meme)
                except KeyError:
                    pass
            # a first run has been completed successfully
            self._parameters["is-first-run"] = False

        for evo_task_id in current_evolution_task_ids:
            # Adding and updating
            self.cancellation_point()
            self._process_evo_task(evo_task_id)

        for evo_task_id in stored_evolution_task_ids.difference(
                current_evolution_task_ids):
            # Removing the old ones
            self.cancellation_point()
            tid = self.sync_engine.get_local_id(evo_task_id)
            self.datastore.request_task_deletion(tid)
            try:
                self.sync_engine.break_relationship(remote_id=evo_task_id)
            except KeyError:
                pass

    def save_state(self):
        '''
        See GenericBackend for an explanation of this function.
        '''
        self._store_pickled_file(self.sync_engine_path, self.sync_engine)

###############################################################################
### Process tasks #############################################################
###############################################################################
    @interruptible
    def remove_task(self, tid):
        '''
        See GenericBackend for an explanation of this function.
        '''
        try:
            evo_task_id = self.sync_engine.get_remote_id(tid)
            self._delete_evolution_task(self._evo_get_task(evo_task_id))
        except KeyError:
            pass
        try:
            self.sync_engine.break_relationship(local_id=tid)
        except:
            pass

    @interruptible
    def set_task(self, task):
        '''
        See GenericBackend for an explanation of this function.
        '''
        tid = task.get_id()
        is_syncable = self._gtg_task_is_syncable_per_attached_tags(task)
        action, evo_task_id = self.sync_engine.analyze_local_id(
            tid,
            self.datastore.has_task,
            self._evo_has_task,
            is_syncable)
        Log.debug('GTG->Evo set task (%s, %s)' % (action, is_syncable))

        if action is None:
            return

        if action == SyncEngine.ADD:
            evo_task = evolution.ecal.ECalComponent(
                ical=evolution.ecal.CAL_COMPONENT_TODO)
            with self.datastore.get_backend_mutex():
                self._evolution_tasks.add_object(evo_task)
                self._populate_evo_task(task, evo_task)
                meme = SyncMeme(task.get_modified(),
                                self._evo_get_modified(evo_task),
                                "GTG")
                self.sync_engine.record_relationship(
                    local_id=tid, remote_id=evo_task.get_uid(),
                    meme=meme)

        elif action == SyncEngine.UPDATE:
            with self.datastore.get_backend_mutex():
                evo_task = self._evo_get_task(evo_task_id)
                meme = self.sync_engine.get_meme_from_local_id(task.get_id())
                newest = meme.which_is_newest(task.get_modified(),
                                              self._evo_get_modified(evo_task))
                if newest == "local":
                    self._populate_evo_task(task, evo_task)
                    meme.set_remote_last_modified(
                        self._evo_get_modified(evo_task))
                    meme.set_local_last_modified(task.get_modified())
                else:
                    # we skip saving the state
                    return

        elif action == SyncEngine.REMOVE:
            self.datastore.request_task_deletion(tid)
            try:
                self.sync_engine.break_relationship(local_id=tid)
            except KeyError:
                pass

        elif action == SyncEngine.LOST_SYNCABILITY:
            evo_task = self._evo_get_task(evo_task_id)
            self._exec_lost_syncability(tid, evo_task)
        self.save_state()

    def _process_evo_task(self, evo_task_id):
        '''
        Takes an evolution task id and carries out the necessary operations to
        refresh the sync state
        '''
        self.cancellation_point()
        evo_task = self._evo_get_task(evo_task_id)
        is_syncable = self._evo_task_is_syncable(evo_task)
        action, tid = self.sync_engine.analyze_remote_id(
            evo_task_id,
            self.datastore.has_task,
            self._evo_has_task,
            is_syncable)
        Log.debug('GTG<-Evo set task (%s, %s)' % (action, is_syncable))

        if action == SyncEngine.ADD:
            with self.datastore.get_backend_mutex():
                tid = str(uuid.uuid4())
                task = self.datastore.task_factory(tid)
                self._populate_task(task, evo_task)
                meme = SyncMeme(task.get_modified(),
                                self._evo_get_modified(evo_task),
                                "GTG")
                self.sync_engine.record_relationship(local_id=tid,
                                                     remote_id=evo_task_id,
                                                     meme=meme)
                self.datastore.push_task(task)

        elif action == SyncEngine.UPDATE:
            with self.datastore.get_backend_mutex():
                task = self.datastore.get_task(tid)
                meme = self.sync_engine.get_meme_from_remote_id(evo_task_id)
                newest = meme.which_is_newest(task.get_modified(),
                                              self._evo_get_modified(evo_task))
                if newest == "remote":
                    self._populate_task(task, evo_task)
                    meme.set_remote_last_modified(
                        self._evo_get_modified(evo_task))
                    meme.set_local_last_modified(task.get_modified())

        elif action == SyncEngine.REMOVE:
            return
            try:
                evo_task = self._evo_get_task(evo_task_id)
                self._delete_evolution_task(evo_task)
                self.sync_engine.break_relationship(remote_id=evo_task)
            except KeyError:
                pass

        elif action == SyncEngine.LOST_SYNCABILITY:
            self._exec_lost_syncability(tid, evo_task)
        self.save_state()

###############################################################################
### Helper methods ############################################################
###############################################################################
    def _evo_has_task(self, evo_task_id):
        '''Returns true if Evolution has that task'''
        return bool(self._evo_get_task(evo_task_id))

    def _evo_get_task(self, evo_task_id):
        '''Returns an Evolution task, given its uid'''
        return self._evolution_tasks.get_object(evo_task_id, "")

    def _evo_get_modified(self, evo_task):
        '''Returns the modified time of an Evolution task'''
        return datetime.datetime.fromtimestamp(evo_task.get_modified())

    def _delete_evolution_task(self, evo_task):
        '''Deletes an Evolution task, given the task object'''
        self._evolution_tasks.remove_object(evo_task)
        self._evolution_tasks.update_object(evo_task)

    def _populate_task(self, task, evo_task):
        '''
        Updates the attributes of a GTG task copying the ones of an Evolution
        task
        '''
        task.set_title(evo_task.get_summary())
        text = evo_task.get_description()
        if text is None:
            text = ""
        task.set_text(text)
        due_date_timestamp = evo_task.get_due()
        if isinstance(due_date_timestamp, (int, float)):
            due_date = self.__date_from_evo_to_gtg(due_date_timestamp)
        else:
            due_date = Date.no_date()
        task.set_due_date(due_date)
        status = evo_task.get_status()
        if task.get_status() != _EVOLUTION_TO_GTG_STATUS[status]:
            task.set_status(_EVOLUTION_TO_GTG_STATUS[status])
        task.set_only_these_tags(extract_tags_from_text(text))

    def _populate_evo_task(self, task, evo_task):
        evo_task.set_summary(task.get_title())
        text = task.get_excerpt(strip_tags=True, strip_subtasks=True)
        if evo_task.get_description() != text:
            evo_task.set_description(text)
        due_date = task.get_due_date()
        if due_date == Date.no_date():
            evo_task.set_due(None)
        else:
            evo_task.set_due(self.__date_from_gtg_to_evo(due_date))
        status = task.get_status()
        if _EVOLUTION_TO_GTG_STATUS[evo_task.get_status()] != status:
            evo_task.set_status(_GTG_TO_EVOLUTION_STATUS[status])
        # this calls are sometime ignored by evolution. Doing it twice
        # is a hackish way to solve the problem. (TODO: send bug report)
        self._evolution_tasks.update_object(evo_task)
        self._evolution_tasks.update_object(evo_task)

    def _exec_lost_syncability(self, tid, evo_task):
        '''
        Executed when a relationship between tasks loses its syncability
        property. See SyncEngine for an explanation of that.
        This function finds out which object is the original one
        and which is the copy, and deletes the copy.
        '''
        meme = self.sync_engine.get_meme_from_local_id(tid)
        self.sync_engine.break_relationship(local_id=tid)
        if meme.get_origin() == "GTG":
            evo_task = self._evo_get_task(evo_task.get_uid())
            self._delete_evolution_task(evo_task)
        else:
            self.datastore.request_task_deletion(tid)

    def _evo_task_is_syncable(self, evo_task):
        '''
        Returns True if this Evolution task should be synced into GTG tasks.

        @param evo_task: an Evolution task
        @returns Boolean
        '''
        attached_tags = set(self.get_attached_tags())
        if GenericBackend.ALLTASKS_TAG in attached_tags:
            return True
        return evo_task.is_disjoint(attached_tags)

    def __date_from_evo_to_gtg(self, evo_date_timestamp):
        """
        Converts an evolution date object into the format understood by GTG

        @param evo_date: an int, which represent time from epoch in UTC
                        convention
        """
        evo_datetime = datetime.datetime.fromtimestamp(evo_date_timestamp)
        # See self.__date_from_gtg_to_evo for an explanation
        evo_datetime = evo_datetime.replace(tzinfo=tzlocal())
        gtg_datetime = evo_datetime.astimezone(tzutc())
        # we strip timezone infos, as they're not used or expected in GTG
        gtg_datetime.replace(tzinfo=None)
        return Date(gtg_datetime.date())

    def __date_from_gtg_to_evo(self, gtg_date):
        """
        Converts a datetime.date object into the format understood by Evolution

        @param gtg_date: a GTG Date object
        """
        # GTG thinks in local time, evolution in utc
        # to convert date objects between different timezones, we must convert
        # them to datetime objects
        gtg_datetime = datetime.datetime.combine(gtg_date.to_py_date(),
                                                 datetime.time(0))
        # We don't want to express GTG date into a UTC equivalent. Instead, we
        # want the *same* date in GTG and evolution. Therefore, we must not do
        # the conversion Local-> UTC (which would point to the same moment in
        # time in different conventions), but do the opposite conversion UTC->
        # Local (which will refer to different points in time, but to the same
        # written date)
        gtg_datetime = gtg_datetime.replace(tzinfo=tzutc())
        evo_datetime = gtg_datetime.astimezone(tzlocal())
        return int(time.mktime(evo_datetime.timetuple()))
