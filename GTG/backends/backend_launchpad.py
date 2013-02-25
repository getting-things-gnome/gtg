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
Backend for importing launchpad bugs in GTG
'''
# Documentation on launchapadlib: https://help.launchpad.net/API/launchpadlib

import os
import uuid
import datetime
from xdg.BaseDirectory import xdg_cache_home
from launchpadlib.launchpad import Launchpad, \
    STAGING_SERVICE_ROOT, \
    EDGE_SERVICE_ROOT

from GTG.core.task import Task
from GTG.tools.testingmode import TestingMode
from GTG import _
from GTG.backends.genericbackend import GenericBackend
from GTG.backends.backendsignals import BackendSignals
from GTG.backends.syncengine import SyncEngine, SyncMeme
from GTG.tools.logger import Log
from GTG.info import NAME as GTG_NAME
from GTG.backends.periodicimportbackend import PeriodicImportBackend

# Uncomment this to see each http request
# import httplib2
# httplib2.debuglevel = 1


class Backend(PeriodicImportBackend):
    '''Launchpad backend, capable of importing launchpad bugs in GTG.'''

    _general_description = {
        GenericBackend.BACKEND_NAME: "backend_launchpad",
        GenericBackend.BACKEND_HUMAN_NAME: _("Launchpad"),
        GenericBackend.BACKEND_AUTHORS: ["Luca Invernizzi"],
        GenericBackend.BACKEND_TYPE: GenericBackend.TYPE_READONLY,
        GenericBackend.BACKEND_DESCRIPTION:
        _("This synchronization service lets you import the bugs assigned"
          " to you (or someone else) on Launchpad in GTG. As the"
          " bug state changes in Launchpad, the GTG task is "
          " updated.\n"
          "Please note that this is a read only synchronization service,"
          " which means that if you open one of the imported tasks and "
          " change one of the:\n"
          "  - title\n"
          "  - description\n"
          "  - tags\n"
          "Your changes <b>will</b> be reverted when the associated"
          " bug is modified. Apart from those, you are free to set "
          " any other field (start/due dates, subtasks...): your "
          " changes will be preserved. This is useful to add "
          " personal annotations to bug"),
    }

    _static_parameters = {
        "username": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE: "insert your username here"},
        "period": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_INT,
            GenericBackend.PARAM_DEFAULT_VALUE: 2, },
        "import-bug-tags": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_BOOL,
            GenericBackend.PARAM_DEFAULT_VALUE: False},
        "tag-with-project-name": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_BOOL,
            GenericBackend.PARAM_DEFAULT_VALUE: True},
    }

###############################################################################
### Backend standard methods ##################################################
###############################################################################
    def __init__(self, parameters):
        '''
        See GenericBackend for an explanation of this function.
        Re-loads the saved state of the synchronization
        '''
        super(Backend, self).__init__(parameters)
        # loading the saved state of the synchronization, if any
        self.data_path = os.path.join('backends/launchpad/',
                                      "sync_engine-" + self.get_id())
        self.sync_engine = self._load_pickled_file(self.data_path,
                                                   SyncEngine())

    def do_periodic_import(self):
        '''
        See GenericBackend for an explanation of this function.
        Connect to launchpad and updates the state of GTG tasks to reflect the
        bugs on launchpad.
        '''

        # IMPORTANT NOTE!
        # Bugs can be splitted in bug tasks (such as, you can assign a single
        # bug to multiple projects: you have one bug and several bug tasks).
        # At least, one bug contains a bug task (if it's referring to a single
        # project).
        # Here, we process bug tasks, since those are the ones that get
        # assigned to someone.
        # To avoid having multiple GTG Tasks for the same bug (because we use
        # bug tasks, this may happen if somebody is working at the same bug for
        # different projects), we use the bug self_link for indexing the tasks.

        # Connecting to Launchpad
        CACHE_DIR = os.path.join(xdg_cache_home, 'gtg/backends/',
                                 self.get_id())
        if TestingMode().get_testing_mode():
            SERVICE_ROOT = STAGING_SERVICE_ROOT
        else:
            SERVICE_ROOT = EDGE_SERVICE_ROOT
        try:
            self.cancellation_point()
            self.launchpad = Launchpad.login_anonymously(GTG_NAME,
                                                         SERVICE_ROOT,
                                                         CACHE_DIR)
        except:
            # The connection is not working (the exception type can be
            # anything)
            BackendSignals().backend_failed(self.get_id(),
                                            BackendSignals.ERRNO_NETWORK)
            return
        # Getting the user data
        try:
            self.cancellation_point()
            me = self.launchpad.people[self._parameters["username"]]
        except KeyError:
            self.quit(disable=True)
            BackendSignals().backend_failed(self.get_id(),
                                            BackendSignals.ERRNO_AUTHENTICATION
                                            )
            return
        # Fetching the bugs
        self.cancellation_point()
        my_bugs_tasks = me.searchTasks(assignee=me, status=["New",
                                                            "Incomplete",
                                                            "Confirmed",
                                                            "Triaged",
                                                            "In Progress",
                                                            "Fix Committed"])
        # Adding and updating
        for bug_task in my_bugs_tasks:
            self.cancellation_point()
            self._process_launchpad_bug(bug_task)

        # removing the old ones
        last_bug_list = self.sync_engine.get_all_remote()
        new_bug_list = [bug.self_link for bug in my_bugs_tasks]
        for bug_link in set(last_bug_list).difference(set(new_bug_list)):
            self.cancellation_point()
            # we make sure that the other backends are not modifying the task
            # set
            with self.datastore.get_backend_mutex():
                tid = self.sync_engine.get_local_id(bug_link)
                self.datastore.request_task_deletion(tid)
                try:
                    self.sync_engine.break_relationship(remote_id=bug_link)
                except KeyError:
                    pass

    def save_state(self):
        '''Saves the state of the synchronization'''
        self._store_pickled_file(self.data_path, self.sync_engine)

###############################################################################
### Process tasks #############################################################
###############################################################################
    def _process_launchpad_bug(self, bug):
        '''
        Given a bug object, finds out if it must be synced to a GTG note and,
        if so, it carries out the synchronization (by creating or
        updating a GTG task, or deleting itself if the related task has
        been deleted)

        @param note: a launchpad bug
        '''
        has_task = self.datastore.has_task
        action, tid = self.sync_engine.analyze_remote_id(bug.self_link,
                                                         has_task,
                                                         lambda b: True)
        Log.debug("processing launchpad (%s)" % (action))

        if action is None:
            return

        bug_dic = self._prefetch_bug_data(bug)
        # for the rest of the function, no access to bug must be made, so
        # that the time of blocking inside the with statements is short.
        # To be sure of that, set bug to None
        bug = None

        with self.datastore.get_backend_mutex():
            if action == SyncEngine.ADD:
                tid = str(uuid.uuid4())
                task = self.datastore.task_factory(tid)
                self._populate_task(task, bug_dic)
                self.sync_engine.record_relationship(local_id=tid,
                                                     remote_id=str(
                                                     bug_dic['self_link']),
                                                     meme=SyncMeme(
                                                     task.get_modified(),
                                                     bug_dic['modified'],
                                                     self.get_id()))
                self.datastore.push_task(task)

            elif action == SyncEngine.UPDATE:
                task = self.datastore.get_task(tid)
                self._populate_task(task, bug_dic)
                meme = self.sync_engine.get_meme_from_remote_id(
                    bug_dic['self_link'])
                meme.set_local_last_modified(task.get_modified())
                meme.set_remote_last_modified(bug_dic['modified'])
        self.save_state()

    def _populate_task(self, task, bug_dic):
        '''
        Fills a GTG task with the data from a launchpad bug.

        @param task: a Task
        @param bug: a launchpad bug dictionary, generated with
                    _prefetch_bug_data
        '''
        # set task status
        if bug_dic["completed"]:
            task.set_status(Task.STA_DONE)
        else:
            task.set_status(Task.STA_ACTIVE)
        if task.get_title() != bug_dic['title']:
            task.set_title(_("Bug") + " %s: " % bug_dic["number"]
                           + bug_dic['title'])
        text = self._build_bug_text(bug_dic)
        if task.get_excerpt() != text:
            task.set_text(text)
        new_tags_sources = []
        if self._parameters["import-bug-tags"]:
            new_tags_sources += bug_dic['tags']
        if self._parameters["tag-with-project-name"]:
            new_tags_sources += [dic['project_short']
                                 for dic in bug_dic['projects']]
        new_tags = set(['@' + str(tag) for tag in new_tags_sources])
        current_tags = set(task.get_tags_name())
        # remove the lost tags
        for tag in current_tags.difference(new_tags):
            task.remove_tag(tag)
        # add the new ones
        for tag in new_tags.difference(current_tags):
            task.add_tag(tag)
        task.add_remote_id(self.get_id(), bug_dic['self_link'])

    def _get_bug_modified_datetime(self, bug):
        '''
        Given a bug, returns its modification datetime

        @param bug: a launchpad bug
        '''
        # NOTE: giving directly bug.date_last_updated fails for a reason I
        #      couldn't find. (invernizzi)
        return datetime.datetime.strptime(
            bug.date_last_updated.strftime("YYYY-MM-DDTHH:MM:SS.mmmmmm"),
            "YYYY-MM-DDTHH:MM:SS.mmmmmm")

    def _prefetch_bug_data(self, bug_task):
        '''
        We fetch all the necessary info that we need from the bug to populate a
        task beforehand (these will be used in _populate_task).
        This function takes a long time to complete (all access to bug data are
        requests on then net), but it can crash without having the state of the
        related task half-changed.

        @param bug: a launchpad bug task
        @returns dict: a dictionary containing the relevant bug attributes
        '''
        bug = bug_task.bug
        # We need to use original link, not from bug object
        self_link = bug_task.self_link
        owner = bug.owner
        bug_dic = {'title': bug.title,
                   'text': bug.description,
                   'tags': bug.tags,
                   'self_link': self_link,
                   'modified': self._get_bug_modified_datetime(bug),
                   'owner': owner.display_name,
                   'completed': bug_task.status in ["Fix Committed",
                                                    "Fix Released"],
                   'owner_karma': owner.karma}
        bug_dic['number'] = bug_dic['self_link'][bug_dic['self_link'].rindex(
                                                 "/") + 1:]
        # find the projects target of the bug
        projects = []
        for task in bug.bug_tasks:
            # workaround: assignee.name doesn't work, although
            #            assignee.display_name does.
            try:
                a_sl = task.assignee.self_link
            except AttributeError:
                # bug task is not assigned to anyone
                continue
            a_sl[a_sl.index("~") + 1:]
            if a_sl[a_sl.index("~") + 1:] == self._parameters["username"]:
                t_sl = task.target.self_link
                projects.append(
                    {"project_short": t_sl[t_sl.rindex("/") + 1:],
                     "project_long": task.bug_target_display_name, })
        bug_dic["projects"] = projects
        return bug_dic

    def _build_bug_text(self, bug_dic):
        '''
        Creates the text that describes a bug
        '''
        text = _("Reported by: ") + '%s(karma: %s)' % \
            (bug_dic["owner"], bug_dic["owner_karma"]) + '\n'
        # one link is enough, since they're all alias
        bug_project = bug_dic['projects'][0]['project_short']
        text += _("Link to bug: ") + \
            "https://bugs.edge.launchpad.net/%s/+bug/%s" % \
            (bug_project, bug_dic["number"]) + '\n'
        text += '\n' + bug_dic["text"]
        return text
