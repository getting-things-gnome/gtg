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

from GTG.core.task               import Task
from GTG.backends.genericbackend        import GenericBackend
from GTG.backends.periodicimportbackend import PeriodicImportBackend
from GTG.backends.backendsignals import BackendSignals
from GTG.backends.syncengine     import SyncEngine, SyncMeme
from GTG import _
from GTG.tools.logger import Log

def as_datetime(datestr):
    if not datestr:
        return datetime.datetime.min

    if len(datestr) > 20:
        return datetime.datetime.strptime(datestr, "%Y-%m-%d %H:%M:%S.%f")
    elif len(datestr) > 10:
        return datetime.datetime.strptime(datestr, "%Y-%m-%d %H:%M:%S")
    else:
        return datetime.datetime.strptime(datestr, "%Y-%m-%d")

class Backend(PeriodicImportBackend):

    _general_description = { \
        GenericBackend.BACKEND_NAME:       "backend_openerp", \
        GenericBackend.BACKEND_HUMAN_NAME: _("OpenERP"), \
        GenericBackend.BACKEND_AUTHORS:    ["Viktor Nagy"], \
        GenericBackend.BACKEND_TYPE:       GenericBackend.TYPE_READONLY, \
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
            GenericBackend.PARAM_DEFAULT_VALUE: "localhost",
        },
        "protocol": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE: "xmlrpc"
        },
        "server_port": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_INT,
            GenericBackend.PARAM_DEFAULT_VALUE: 8069,
        },
        "database": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE: "gtgdb",
        },
        "period": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_INT,
            GenericBackend.PARAM_DEFAULT_VALUE: 10,
        },
        "is-first-run": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_BOOL,
            GenericBackend.PARAM_DEFAULT_VALUE: True,
        },
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

    def _sync_tasks(self):
        '''
        Download tasks from the server and register them in GTG

        Existing tasks should not be registered.
        '''
        task_model = self.server.get_model("project.task")
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
        tasks = dict(map(lambda t: (str(t['id']), t), tasks))
        map(lambda l: tasks[str(l['id'])].update(l), logs)

        for task in tasks.values():
            self._process_openerp_task(task)

        #removing the old ones
        last_task_list = self.sync_engine.get_all_remote()
        for task_link in set(last_task_list).difference(set(tasks.keys())):
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
        action, tid = self.sync_engine.analyze_remote_id(str(task['id']),
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
                            remote_id = str(task['id']), \
                            meme = SyncMeme(\
                                        gtg.get_modified(), \
                                        as_datetime(task['write_date']), \
                                        self.get_id()))
                self.datastore.push_task(gtg)

            elif action == SyncEngine.UPDATE:
                gtg = self.datastore.get_task(tid)
                self._populate_task(gtg, task)
                meme = self.sync_engine.get_meme_from_remote_id( \
                                                    str(task['id']))
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
        tags.append('OpenERP')
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
        new_tags = set(['@' + str(tag) for tag in tags])

        current_tags = set(gtg.get_tags_name())
        #remove the lost tags
        for tag in current_tags.difference(new_tags):
            gtg.remove_tag(tag)
        #add the new ones
        for tag in new_tags.difference(current_tags):
            gtg.add_tag(tag)
        gtg.add_remote_id(self.get_id(), str(oerp['id']))

