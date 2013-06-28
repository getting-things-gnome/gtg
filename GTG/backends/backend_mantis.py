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

import os
import uuid

from GTG import _
from GTG.backends.genericbackend import GenericBackend
from GTG.backends.backendsignals import BackendSignals
from GTG.backends.periodicimportbackend import PeriodicImportBackend
from GTG.backends.syncengine import SyncEngine, SyncMeme
from GTG.tools.logger import Log

from GTG.core.task import Task
from suds.client import Client

'''
Backend for importing mantis issues in GTG

Dependencies:
  * python-suds
'''


class Backend(PeriodicImportBackend):
    _general_description = {
        GenericBackend.BACKEND_NAME: "backend_mantis",
        GenericBackend.BACKEND_HUMAN_NAME: _("MantisBT"),
        GenericBackend.BACKEND_AUTHORS: ["Luca Invernizzi", "Alayn Gortazar"],
        GenericBackend.BACKEND_TYPE: GenericBackend.TYPE_READONLY,
        GenericBackend.BACKEND_DESCRIPTION:
        _("This synchronization service lets you import the issues found"
          " on Mantis using a prestablished filter called 'gtg'."
          " As the issue state changes in Mantis, the GTG task is "
          " updated.\n"
          "Please note that this is a read only synchronization service,"
          " which means that if you open one of the imported tasks and "
          " change one of the:\n"
          "  - title\n"
          "  - description\n"
          "  - tags\n"
          "Your changes <b>will</b> be reverted when the associated"
          " issue is modified. Apart from those, you are free to set "
          " any other field (start/due dates, subtasks...): your "
          " changes will be preserved. This is useful to add "
          " personal annotations to issue"),
    }

    _static_parameters = {
        "period": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_INT,
            GenericBackend.PARAM_DEFAULT_VALUE: 5, },
        "username": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE: 'insert your username', },
        "password": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_PASSWORD,
            GenericBackend.PARAM_DEFAULT_VALUE: '', },
        "service-url": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE: 'http://example.com/mantis',
        },
        "tag-with-project-name": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_BOOL,
            GenericBackend.PARAM_DEFAULT_VALUE: True},
    }

    def __init__(self, parameters):
        '''
        See GenericBackend for an explanation of this function.
        Re-loads the saved state of the synchronization
        '''
        super(Backend, self).__init__(parameters)
        # loading the saved state of the synchronization, if any
        self.data_path = os.path.join('backends/mantis/',
                                      "sync_engine-" + self.get_id())
        self.sync_engine = self._load_pickled_file(self.data_path,
                                                   SyncEngine())

    def save_state(self):
        '''Saves the state of the synchronization'''
        self._store_pickled_file(self.data_path, self.sync_engine)

    def do_periodic_import(self):
        # Establishing connection
        try:
            self.cancellation_point()
            client = Client('%s/api/soap/mantisconnect.php?wsdl' %
                           (self._parameters['service-url']))
        except KeyError:
            self.quit(disable=True)
            BackendSignals().backend_failed(self.get_id(),
                                            BackendSignals.ERRNO_AUTHENTICATION
                                            )
            return

        projects = client.service.mc_projects_get_user_accessible(
            self._parameters['username'],
            self._parameters['password'])
        filters = client.service.mc_filter_get(self._parameters['username'],
                                               self._parameters['password'], 0)

        # Fetching the issues
        self.cancellation_point()
        my_issues = []
        for filt in filters:
            if filt['name'] == 'gtg':
                for project in projects:
                    my_issues = client.service.mc_filter_get_issues(
                        self._parameters['username'],
                        self._parameters['password'],
                        project['id'],
                        filt['id'], 0, 100)
                    for issue in my_issues:
                        self.cancellation_point()
                        self._process_mantis_issue(issue)
        last_issue_list = self.sync_engine.get_all_remote()
        new_issue_list = [str(issue['id']) for issue in my_issues]
        for issue_link in set(last_issue_list).difference(set(new_issue_list)):
            self.cancellation_point()
            # we make sure that the other backends are not modifying the task
            # set
            with self.datastore.get_backend_mutex():
                tid = self.sync_engine.get_local_id(issue_link)
                self.datastore.request_task_deletion(tid)
                try:
                    self.sync_engine.break_relationship(remote_id=issue_link)
                except KeyError:
                    pass
        return

###############################################################################
### Process tasks #############################################################
###############################################################################
    def _process_mantis_issue(self, issue):
        '''
        Given a issue object, finds out if it must be synced to a GTG note and,
        if so, it carries out the synchronization (by creating or
        updating a GTG task, or deleting itself if the related task has
        been deleted)

        @param note: a mantis issue
        '''
        has_task = self.datastore.has_task
        action, tid = self.sync_engine.analyze_remote_id(str(issue['id']),
                                                         has_task,
                                                         lambda b: True)
        Log.debug("processing mantis (%s)" % (action))

        if action is None:
            return

        issue_dic = self._prefetch_issue_data(issue)
        # for the rest of the function, no access to issue must be made, so
        # that the time of blocking inside the with statements is short.
        # To be sure of that, set issue to None
        issue = None

        with self.datastore.get_backend_mutex():
            if action == SyncEngine.ADD:
                tid = str(uuid.uuid4())
                task = self.datastore.task_factory(tid)
                self._populate_task(task, issue_dic)
                self.sync_engine.record_relationship(local_id=tid,
                                                     remote_id=str(
                                                     issue_dic['number']),
                                                     meme=SyncMeme(
                                                     task.get_modified(),
                                                     issue_dic['modified'],
                                                     self.get_id()))
                self.datastore.push_task(task)

            elif action == SyncEngine.UPDATE:
                task = self.datastore.get_task(tid)
                self._populate_task(task, issue_dic)
                meme = self.sync_engine.get_meme_from_remote_id(
                    issue_dic['number'])
                meme.set_local_last_modified(task.get_modified())
                meme.set_remote_last_modified(issue_dic['modified'])
        self.save_state()

    def _prefetch_issue_data(self, mantis_issue):
        '''
        We fetch all the necessary info that we need from the mantis_issue to
        populate a task beforehand (these will be used in _populate_task).

        @param mantis_issue: a mantis issue
        @returns dict: a dictionary containing the relevant issue attributes
        '''
        issue_dic = {'title': mantis_issue['summary'],
                     'text': mantis_issue['description'],
                     'reporter': mantis_issue['reporter'].name,
                     'modified': mantis_issue['last_updated'],
                     'project': mantis_issue['project'].name,
                     'status': mantis_issue['status'].name,
                     'completed': (mantis_issue['status'].id >= 80),
                     'number': str(mantis_issue['id'])}

        try:
            issue_dic['assigned'] = mantis_issue['handler'].name == \
                self._parameters['username']
        except AttributeError:
            issue_dic['assigned'] = False

        return issue_dic

    def _populate_task(self, task, issue_dic):
        '''
        Fills a GTG task with the data from a mantis issue.

        @param task: a Task
        @param issue_dic: a mantis issue

        '''
        # set task status
        if issue_dic["completed"]:
            task.set_status(Task.STA_DONE)
        else:
            task.set_status(Task.STA_ACTIVE)
        if task.get_title() != issue_dic['title']:
            task.set_title(_("Iss.") + " %s: " % issue_dic["number"]
                           + issue_dic['title'])
        text = self._build_issue_text(issue_dic)
        if task.get_excerpt() != text:
            task.set_text(text)

        new_tags = set([])
        if self._parameters["tag-with-project-name"]:
            new_tags = set(['@' + issue_dic['project']])
        current_tags = set(task.get_tags_name())
        # add the new ones
        for tag in new_tags.difference(current_tags):
            task.add_tag(tag)

        task.add_remote_id(self.get_id(), issue_dic['number'])

    def _build_issue_text(self, issue_dic):
        '''
        Creates the text that describes a issue
        '''
        text = _("Reported by: ") + issue_dic["reporter"] + '\n'
        text += _("Link to issue: ") + \
            self._parameters['service-url'] + '/view.php?id=%s' % \
            (issue_dic["number"]) + '\n'
        text += '\n' + issue_dic["text"]
        return text
