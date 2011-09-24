# -*- encoding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things Gnome! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2009 - Lionel Dricot & Bertrand Rousseau
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
OpenERP backend
'''

import os
import uuid
import datetime
import openerplib

from xdg.BaseDirectory import xdg_cache_home

from GTG import _
from GTG.backends.genericbackend        import GenericBackend
from GTG.backends.periodicimportbackend import PeriodicImportBackend
from GTG.backends.backendsignals import BackendSignals
from GTG.backends.syncengine     import SyncEngine, SyncMeme
from GTG.core.task               import Task
from GTG.tools.dates import RealDate, no_date
from GTG.tools.interruptible            import interruptible
from GTG.tools.logger import Log

def as_datetime(datestr):
    if not datestr:
        return no_date

    return RealDate(datetime.datetime.strptime(datestr[:10], "%Y-%m-%d").date())

class Backend(PeriodicImportBackend):

    _general_description = { \
        GenericBackend.BACKEND_NAME:       "backend_openerp", \
        GenericBackend.BACKEND_HUMAN_NAME: _("OpenERP"), \
        GenericBackend.BACKEND_AUTHORS:    ["Viktor Nagy"], \
        GenericBackend.BACKEND_TYPE:       GenericBackend.TYPE_READWRITE, \
        GenericBackend.BACKEND_DESCRIPTION: \
            _("This backend synchronizes your tasks with an OpenERP server"),
        }

    _static_parameters = {
        "username": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE: "insert your username here"
        },
        "password": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_PASSWORD,
            GenericBackend.PARAM_DEFAULT_VALUE: "",
        },
        "server_host": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE: "erp.toolpart.hu",
        },
        "protocol": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE: "xmlrpcs"
        },
        "server_port": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_INT,
            GenericBackend.PARAM_DEFAULT_VALUE: 8071,
        },
        "database": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE: "ToolPartTeam",
        },
        "period": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_INT,
            GenericBackend.PARAM_DEFAULT_VALUE: 10,
        },
        "is-first-run": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_BOOL,
            GenericBackend.PARAM_DEFAULT_VALUE: True,
        },
        GenericBackend.KEY_ATTACHED_TAGS: {
             GenericBackend.PARAM_TYPE: GenericBackend.TYPE_LIST_OF_STRINGS,
             GenericBackend.PARAM_DEFAULT_VALUE: ['@OpenERP'],
        }
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
        #loading the saved state of the synchronization, if any
        self.sync_engine_path = os.path.join('backends/openerp/', \
                                      "sync_engine-" + self.get_id())
        self.sync_engine = self._load_pickled_file(self.sync_engine_path, \
                                                   SyncEngine())

    def do_periodic_import(self):
        if not self._check_server():
            return

        self.cancellation_point()
        self._sync_tasks()

    def save_state(self):
        """
        See GenericBackend for an explanation of this function.
        """
        self._store_pickled_file(self.sync_engine_path, self.sync_engine)

    @interruptible
    def remove_task(self, tid):
        """
        See GenericBackend for an explanation of this function.
        """
        self.cancellation_point()
        try:
            oerp_id = self.sync_engine.get_remote_id(tid)
            Log.debug("removing task %s from OpenERP" % oerp_id)
            self._unlink_task(oerp_id)
        except KeyError:
            pass
        try:
            self.sync_engine.break_relationship(local_id = tid)
        except:
            pass

    @interruptible
    def set_task(self, task):
        """
        TODO: write set_task method
        """
        self.cancellation_point()
        tid = task.get_id()
        is_syncable = self._gtg_task_is_syncable_per_attached_tags(task)
        action, oerp_id = self.sync_engine.analyze_local_id( \
                                tid, \
                                self.datastore.has_task, \
                                self._erp_has_task, \
                                is_syncable)
        Log.debug("GTG->OERP set task (%s, %s)" % (action, is_syncable))

        if action == None:
            return

        if action == SyncEngine.ADD:
            Log.debug('Adding task')
            return # raise NotImplementedError

        elif action == SyncEngine.UPDATE:
            # we deal only with updating openerp state
            by_status = {
                Task.STA_ACTIVE: lambda oerp_id: \
                    self._set_open(oerp_id),
                Task.STA_DISMISSED: lambda oerp_id: \
                    self._set_state(oerp_id,'cancel'),
                Task.STA_DONE: lambda oerp_id: \
                    self._set_state(oerp_id,'close'),
            }
            try:
                by_status[task.get_status()](oerp_id)
            except:
                # the given state transition might not be available
                raise

        elif action == SyncEngine.REMOVE:
            self.datastore.request_task_deletion(tid)
            try:
                self.sync_engine.break_relationship(local_id = tid)
            except KeyError:
                pass

        elif action == SyncEngine.LOST_SYNCABILITY:
            pass

###################################
### OpenERP related
###################################

    def _check_server(self):
        """connect to server"""
        Log.debug( 'checking server connection' )
        try:
            self.server = openerplib.get_connection(
                hostname=self._parameters["server_host"],
                port=self._parameters["server_port"],
                protocol=self._parameters["protocol"],
                database=self._parameters["database"],
                login=self._parameters["username"],
                password=self._parameters["password"])
        except:
            self.server = None
            BackendSignals().backend_failed(self.get_id(), \
                            BackendSignals.ERRNO_NETWORK)
            return False

        try:
            self.server.check_login()
        except:
            self.server = None
            BackendSignals().backend_failed(self.get_id(), \
                            BackendSignals.ERRNO_AUTHENTICATION)
            return False

        return True

    def _get_model(self):
        if not self.server:
            self._check_server()
        return self.server.get_model('project.task')

    def _sync_tasks(self):
        '''
        Download tasks from the server and register them in GTG

        Existing tasks should not be registered.
        '''
        task_model = self._get_model()
        task_ids = task_model.search([("user_id","=", self.server.user_id)])
        tasks = task_model.read(task_ids,
                    ['name', 'description', 'context_id',
                     'date_deadline', 'notes', 'priority',
                    'timebox_id', 'project_id', 'state',
                    'date_start', 'date_end'])
        self.cancellation_point()
        # merge last modified date with generic task data
        logs = task_model.perm_read(task_ids, {}, False)
        self.cancellation_point()
        def get_task_id(id):
            return '%s$%d' % (self._parameters['server_host'], id)

        def adjust_task(task):
            id = task['id']
            task['rid'] = get_task_id(id)
            return (id, task)

        tasks = dict(map(adjust_task, tasks))
        map(lambda l: tasks[l['id']].update(l), logs)
        Log.debug(str(tasks))

        for task in tasks.values():
            self._process_openerp_task(task)

        #removing the old ones
        last_task_list = self.sync_engine.get_all_remote()
        new_task_keys = map(get_task_id, tasks.keys())
        for task_link in set(last_task_list).difference(set(new_task_keys)):
            self.cancellation_point()
            #we make sure that the other backends are not modifying the task
            # set
            with self.datastore.get_backend_mutex():
                tid = self.sync_engine.get_local_id(task_link)
                self.datastore.request_task_deletion(tid)
                try:
                    self.sync_engine.break_relationship(remote_id = task_link)
                except KeyError:
                    pass

    def _process_openerp_task(self, task):
        '''
        From the task data find out if this task already exists or should be
        updated.
        '''
        Log.debug("Processing task %s (%d)" % (task['name'], task['id']))
        action, tid = self.sync_engine.analyze_remote_id(task['rid'],
                self.datastore.has_task, lambda b: True)

        if action == None:
            return

        self.cancellation_point()
        with self.datastore.get_backend_mutex():
            if action == SyncEngine.ADD:
                tid = str(uuid.uuid4())
                gtg = self.datastore.task_factory(tid)
                self._populate_task(gtg, task)
                self.sync_engine.record_relationship(local_id = tid,\
                            remote_id = task['rid'], \
                            meme = SyncMeme(\
                                        gtg.get_modified(), \
                                        as_datetime(task['write_date']), \
                                        self.get_id()))
                self.datastore.push_task(gtg)

            elif action == SyncEngine.UPDATE:
                gtg = self.datastore.get_task(tid)
                self._populate_task(gtg, task)
                meme = self.sync_engine.get_meme_from_remote_id( \
                                                    task['rid'])
                meme.set_local_last_modified(gtg.get_modified())
                meme.set_remote_last_modified(as_datetime(task['write_date']))
        self.save_state()

    def _populate_task(self, gtg, oerp):
        '''
        Fills a GTG task with the data from a launchpad bug.

        @param gtg: a Task in GTG
        @param oerp: a Task in OpenERP
        '''
        # draft, open, pending, cancelled, done
        if oerp["state"] in ['draft', 'open', 'pending']:
            gtg.set_status(Task.STA_ACTIVE)
        elif oerp['state'] == 'done':
            gtg.set_status(Task.STA_DONE)
        else:
            gtg.set_status(Task.STA_DISMISSED)
        if gtg.get_title() != oerp['name']:
            gtg.set_title(oerp['name'])

        text = ''
        if oerp['description']:
            text += oerp['description']
        if oerp['notes']:
            text += '\n\n' + oerp['notes']
        if gtg.get_excerpt() != text:
            gtg.set_text(text)

        if oerp['date_deadline'] and \
           gtg.get_due_date() != as_datetime(oerp['date_deadline']):
            gtg.set_due_date(as_datetime(oerp['date_deadline']))
        if oerp['date_start'] and \
           gtg.get_start_date() != as_datetime(oerp['date_start']):
            gtg.set_start_date(as_datetime(oerp['date_start']))
        if oerp['date_end'] and \
           gtg.get_closed_date() != as_datetime(oerp['date_end']):
            gtg.set_closed_date(as_datetime(oerp['date_end']))

        tags = [oerp['project_id'][1].replace(' ', '_')]
        if self._parameters[GenericBackend.KEY_ATTACHED_TAGS]:
            tags.extend(self._parameters[GenericBackend.KEY_ATTACHED_TAGS])
        # priority
        priorities = {
            '4': _('VeryLow'),
            '3': _('Low'),
            '2': _('Medium'),
            '1': _('Urgent'),
            '0': _('VeryUrgent'),
        }
        tags.append(priorities[oerp['priority']])
        if oerp.has_key('context_id'):
            tags.append(oerp['context_id'] \
                    and oerp['context_id'][1].replace(' ', '_') or "NoContext")
        if oerp.has_key('timebox_id'):
            tags.append(oerp['timebox_id'] \
                    and oerp['timebox_id'][1].replace(' ', '_') or 'NoTimebox')
        new_tags = set(['@' + str(tag) for tag in filter(None, tags)])

        current_tags = set(gtg.get_tags_name())
        #remove the lost tags
        for tag in current_tags.difference(new_tags):
            gtg.remove_tag(tag)
        #add the new ones
        for tag in new_tags.difference(current_tags):
            gtg.add_tag(tag)
        gtg.add_remote_id(self.get_id(), oerp['rid'])

    def _unlink_task(self, task_id):
        """Delete a task on the server"""
        task_model = self._get_model()
        task_id = int(task_id.split('$')[1])
        task_model.unlink(task_id)

    def _erp_has_task(self, task_id):
        Log.debug('Checking task %d' % int(task_id.split('$')[1]))
        task_model = self._get_model()
        if task_model.read(int(task_id.split('$')[1]), ['id']):
            return True
        return False

    def _set_state(self, oerp_id, state):
        Log.debug('Setting task %s to %s' % (oerp_id, state))
        task_model = self._get_model()
        oerp_id = int(oerp_id.split('$')[1])
        getattr(task_model, 'do_%s' % state)([oerp_id])

    def _set_open(self, oerp_id):
        ''' this might mean reopen or open '''
        task_model = self._get_model()
        tid = int(oerp_id.split('$')[1])
        if task_model.read(tid, ['state'])['state'] == 'draft':
            self._set_state(oerp_id, 'open')
        else:
            self._set_state(oerp_id, 'reopen')

