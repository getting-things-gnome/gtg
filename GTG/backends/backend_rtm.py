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
Remember the milk backend
'''

import os
import cgi
import uuid
import time
import threading
import datetime
import subprocess
import exceptions
from dateutil.tz import tzutc, tzlocal

from GTG.backends.genericbackend import GenericBackend
from GTG import _
from GTG.backends.backendsignals import BackendSignals
from GTG.backends.syncengine import SyncEngine, SyncMeme
from GTG.backends.rtm.rtm import createRTM, RTMError, RTMAPIError
from GTG.backends.periodicimportbackend import PeriodicImportBackend
from GTG.tools.dates import Date
from GTG.core.task import Task
from GTG.tools.interruptible import interruptible
from GTG.tools.logger import Log


class Backend(PeriodicImportBackend):

    _general_description = {
        GenericBackend.BACKEND_NAME: "backend_rtm",
        GenericBackend.BACKEND_HUMAN_NAME: _("Remember The Milk"),
        GenericBackend.BACKEND_AUTHORS: ["Luca Invernizzi"],
        GenericBackend.BACKEND_TYPE: GenericBackend.TYPE_READWRITE,
        GenericBackend.BACKEND_DESCRIPTION:
        _("This service synchronizes your tasks with the web service"
          " RememberTheMilk:\n\t\thttp://rememberthemilk.com\n\n"
          "Note: This product uses the Remember The Milk API but is not"
          " endorsed or certified by Remember The Milk"),
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
        self.sync_engine_path = os.path.join('backends/rtm/',
                                             "sync_engine-" + self.get_id())
        self.sync_engine = self._load_pickled_file(self.sync_engine_path,
                                                   SyncEngine())
        # reloading the oauth authentication token, if any
        self.token_path = os.path.join('backends/rtm/',
                                       "auth_token-" + self.get_id())
        self.token = self._load_pickled_file(self.token_path, None)
        self.enqueued_start_get_task = False
        self.login_event = threading.Event()
        self._this_is_the_first_loop = True

    def initialize(self):
        """
        See GenericBackend for an explanation of this function.
        """
        super(Backend, self).initialize()
        self.rtm_proxy = RTMProxy(self._ask_user_to_confirm_authentication,
                                  self.token)

    def save_state(self):
        """
        See GenericBackend for an explanation of this function.
        """
        self._store_pickled_file(self.sync_engine_path, self.sync_engine)

    def _ask_user_to_confirm_authentication(self):
        '''
        Calls for a user interaction during authentication
        '''
        self.login_event.clear()
        BackendSignals().interaction_requested(self.get_id(),
                                               "You need to authenticate to"
                                               " Remember The Milk. A browser"
                                               " is opening with a login page."
                                               "\n When you have  logged in "
                                               "and given GTG the requested "
                                               "permissions,\n"
                                               " press the 'Confirm' button",
                                               BackendSignals(
                                               ).INTERACTION_CONFIRM,
                                               "on_login")
        self.login_event.wait()

    def on_login(self):
        '''
        Called when the user confirms the login
        '''
        self.login_event.set()

###############################################################################
### TWO WAY SYNC ##############################################################
###############################################################################

    def do_periodic_import(self):
        """
        See PeriodicImportBackend for an explanation of this function.
        """

        # we get the old list of synced tasks, and compare with the new tasks
        # set
        stored_rtm_task_ids = self.sync_engine.get_all_remote()
        current_rtm_task_ids = [tid for tid in
                                self.rtm_proxy.get_rtm_tasks_dict().iterkeys()]

        if self._this_is_the_first_loop:
            self._on_successful_authentication()

        # If it's the very first time the backend is run, it's possible that
        # the user already synced his tasks in some way (but we don't know
        # that). Therefore, we attempt to induce those tasks relationships
        # matching the titles.
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
            for rtm_task_id in current_rtm_task_ids:
                rtm_task = self.rtm_proxy.get_rtm_tasks_dict()[rtm_task_id]
                try:
                    tids = gtg_titles_dic[rtm_task.get_title()]
                    # we remove the tid, so that it can't be linked to two
                    # different rtm tasks
                    tid = tids.pop()
                    gtg_task = self.datastore.get_task(tid)
                    meme = SyncMeme(gtg_task.get_modified(),
                                    rtm_task.get_modified(),
                                    "GTG")
                    self.sync_engine.record_relationship(
                        local_id=tid,
                        remote_id=rtm_task.get_id(),
                        meme=meme)
                except KeyError:
                    pass
            # a first run has been completed successfully
            self._parameters["is-first-run"] = False

        for rtm_task_id in current_rtm_task_ids:
            self.cancellation_point()
            # Adding and updating
            self._process_rtm_task(rtm_task_id)

        for rtm_task_id in set(stored_rtm_task_ids).difference(
                set(current_rtm_task_ids)):
            self.cancellation_point()
            # Removing the old ones
            if not self.please_quit:
                tid = self.sync_engine.get_local_id(rtm_task_id)
                self.datastore.request_task_deletion(tid)
                try:
                    self.sync_engine.break_relationship(remote_id=rtm_task_id)
                    self.save_state()
                except KeyError:
                    pass

    def _on_successful_authentication(self):
        '''
        Saves the token and requests a full flush on first autentication
        '''
        self._this_is_the_first_loop = False
        self._store_pickled_file(self.token_path,
                                 self.rtm_proxy.get_auth_token())
        # we ask the Datastore to flush all the tasks on us
        threading.Timer(10,
                        self.datastore.flush_all_tasks,
                        args=(self.get_id(),)).start()

    @interruptible
    def remove_task(self, tid):
        """
        See GenericBackend for an explanation of this function.
        """
        if not self.rtm_proxy.is_authenticated():
            return
        self.cancellation_point()
        try:
            rtm_task_id = self.sync_engine.get_remote_id(tid)
            if rtm_task_id not in self.rtm_proxy.get_rtm_tasks_dict():
                # we might need to refresh our task cache
                self.rtm_proxy.refresh_rtm_tasks_dict()
            rtm_task = self.rtm_proxy.get_rtm_tasks_dict()[rtm_task_id]
            rtm_task.delete()
            Log.debug("removing task %s from RTM" % rtm_task_id)
        except KeyError:
            pass
            try:
                self.sync_engine.break_relationship(local_id=tid)
                self.save_state()
            except:
                pass

###############################################################################
### Process tasks #############################################################
###############################################################################
    @interruptible
    def set_task(self, task):
        """
        See GenericBackend for an explanation of this function.
        """
        if not self.rtm_proxy.is_authenticated():
            return
        self.cancellation_point()
        tid = task.get_id()
        is_syncable = self._gtg_task_is_syncable_per_attached_tags(task)
        action, rtm_task_id = self.sync_engine.analyze_local_id(
            tid,
            self.datastore.has_task,
            self.rtm_proxy.has_rtm_task,
            is_syncable)
        Log.debug("GTG->RTM set task (%s, %s)" % (action, is_syncable))

        if action is None:
            return

        if action == SyncEngine.ADD:
            if task.get_status() != Task.STA_ACTIVE:
                # OPTIMIZATION:
                # we don't sync tasks that have already been closed before we
                # even synced them once
                return
            try:
                rtm_task = self.rtm_proxy.create_new_rtm_task(task.get_title())
                self._populate_rtm_task(task, rtm_task)
            except:
                rtm_task.delete()
                raise
            meme = SyncMeme(task.get_modified(),
                            rtm_task.get_modified(),
                            "GTG")
            self.sync_engine.record_relationship(
                local_id=tid, remote_id=rtm_task.get_id(), meme=meme)

        elif action == SyncEngine.UPDATE:
            try:
                rtm_task = self.rtm_proxy.get_rtm_tasks_dict()[rtm_task_id]
            except KeyError:
                # in this case, we don't have yet the task in our local cache
                # of what's on the rtm website
                self.rtm_proxy.refresh_rtm_tasks_dict()
                rtm_task = self.rtm_proxy.get_rtm_tasks_dict()[rtm_task_id]
            with self.datastore.get_backend_mutex():
                meme = self.sync_engine.get_meme_from_local_id(task.get_id())
                newest = meme.which_is_newest(task.get_modified(),
                                              rtm_task.get_modified())
                if newest == "local":
                    transaction_ids = []
                    try:
                        self._populate_rtm_task(
                            task, rtm_task, transaction_ids)
                    except:
                        self.rtm_proxy.unroll_changes(transaction_ids)
                        raise
                    meme.set_remote_last_modified(rtm_task.get_modified())
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
            try:
                rtm_task = self.rtm_proxy.get_rtm_tasks_dict()[rtm_task_id]
            except KeyError:
                # in this case, we don't have yet the task in our local cache
                # of what's on the rtm website
                self.rtm_proxy.refresh_rtm_tasks_dict()
                rtm_task = self.rtm_proxy.get_rtm_tasks_dict()[rtm_task_id]
            self._exec_lost_syncability(tid, rtm_task)

            self.save_state()

    def _exec_lost_syncability(self, tid, rtm_task):
        '''
        Executed when a relationship between tasks loses its syncability
        property. See SyncEngine for an explanation of that.

        @param tid: a GTG task tid
        @param note: a RTM task
        '''
        self.cancellation_point()
        meme = self.sync_engine.get_meme_from_local_id(tid)
        # First of all, the relationship is lost
        self.sync_engine.break_relationship(local_id=tid)
        if meme.get_origin() == "GTG":
            rtm_task.delete()
        else:
            self.datastore.request_task_deletion(tid)

    def _process_rtm_task(self, rtm_task_id):
        '''
        Takes a rtm task id and carries out the necessary operations to
        refresh the sync state
        '''
        self.cancellation_point()
        if not self.rtm_proxy.is_authenticated():
            return
        rtm_task = self.rtm_proxy.get_rtm_tasks_dict()[rtm_task_id]
        is_syncable = self._rtm_task_is_syncable_per_attached_tags(rtm_task)
        action, tid = self.sync_engine.analyze_remote_id(
            rtm_task_id,
            self.datastore.has_task,
            self.rtm_proxy.has_rtm_task,
            is_syncable)
        Log.debug("GTG<-RTM set task (%s, %s)" % (action, is_syncable))

        if action is None:
            return

        if action == SyncEngine.ADD:
            if rtm_task.get_status() != Task.STA_ACTIVE:
                # OPTIMIZATION:
                # we don't sync tasks that have already been closed before we
                # even saw them
                return
            tid = str(uuid.uuid4())
            task = self.datastore.task_factory(tid)
            self._populate_task(task, rtm_task)
            meme = SyncMeme(task.get_modified(),
                            rtm_task.get_modified(),
                            "RTM")
            self.sync_engine.record_relationship(
                local_id=tid,
                remote_id=rtm_task_id,
                meme=meme)
            self.datastore.push_task(task)

        elif action == SyncEngine.UPDATE:
            task = self.datastore.get_task(tid)
            with self.datastore.get_backend_mutex():
                meme = self.sync_engine.get_meme_from_remote_id(rtm_task_id)
                newest = meme.which_is_newest(task.get_modified(),
                                              rtm_task.get_modified())
                if newest == "remote":
                    self._populate_task(task, rtm_task)
                    meme.set_remote_last_modified(rtm_task.get_modified())
                    meme.set_local_last_modified(task.get_modified())
                else:
                    # we skip saving the state
                    return

        elif action == SyncEngine.REMOVE:
            try:
                rtm_task.delete()
                self.sync_engine.break_relationship(remote_id=rtm_task_id)
            except KeyError:
                pass

        elif action == SyncEngine.LOST_SYNCABILITY:
            self._exec_lost_syncability(tid, rtm_task)

        self.save_state()

###############################################################################
### Helper methods ############################################################
###############################################################################

    def _populate_task(self, task, rtm_task):
        '''
        Copies the content of a RTMTask in a Task
        '''
        task.set_title(rtm_task.get_title())
        task.set_text(rtm_task.get_text())
        task.set_due_date(rtm_task.get_due_date())
        status = rtm_task.get_status()
        if GTG_TO_RTM_STATUS[task.get_status()] != status:
            task.set_status(rtm_task.get_status())
        # tags
        tags = set(['@%s' % tag for tag in rtm_task.get_tags()])
        gtg_tags_lower = set([t.get_name().lower() for t in task.get_tags()])
        # tags to remove
        for tag in gtg_tags_lower.difference(tags):
            task.remove_tag(tag)
        # tags to add
        for tag in tags.difference(gtg_tags_lower):
            gtg_all_tags = self.datastore.get_all_tags()
            matching_tags = filter(lambda t: t.lower() == tag, gtg_all_tags)
            if len(matching_tags) != 0:
                tag = matching_tags[0]
            task.add_tag(tag)

    def _populate_rtm_task(self, task, rtm_task, transaction_ids=[]):
        '''
        Copies the content of a Task into a RTMTask

        @param task: a GTG Task
        @param rtm_task: an RTMTask
        @param transaction_ids: a list to fill with transaction ids
        '''
        # Get methods of an rtm_task are fast, set are slow: therefore,
        # we try to use set as rarely as possible

        # first thing: the status. This way, if we are syncing a completed
        # task it doesn't linger for ten seconds in the RTM Inbox
        status = task.get_status()
        if rtm_task.get_status() != status:
            self.__call_or_retry(rtm_task.set_status, status, transaction_ids)
        title = task.get_title()
        if rtm_task.get_title() != title:
            self.__call_or_retry(rtm_task.set_title, title, transaction_ids)
        text = task.get_excerpt(strip_tags=True, strip_subtasks=True)
        if rtm_task.get_text() != text:
            self.__call_or_retry(rtm_task.set_text, text, transaction_ids)
        tags = task.get_tags_name()
        rtm_task_tags = []
        for tag in rtm_task.get_tags():
            if tag[0] != '@':
                tag = '@' + tag
            rtm_task_tags.append(tag)
        # rtm tags are lowercase only
        if rtm_task_tags != [t.lower() for t in tags]:
            self.__call_or_retry(rtm_task.set_tags, tags, transaction_ids)
        due_date = task.get_due_date()
        if rtm_task.get_due_date() != due_date:
            self.__call_or_retry(rtm_task.set_due_date, due_date,
                                 transaction_ids)

    def __call_or_retry(self, fun, *args):
        '''
        This function cannot stand the call "fun" to fail, so it retries
        three times before giving up.
        '''
        MAX_ATTEMPTS = 3
        for i in xrange(MAX_ATTEMPTS):
            try:
                return fun(*args)
            except:
                if i >= MAX_ATTEMPTS:
                    raise

    def _rtm_task_is_syncable_per_attached_tags(self, rtm_task):
        '''
        Helper function which checks if the given task satisfies the filtering
        imposed by the tags attached to the backend.
        That means, if a user wants a backend to sync only tasks tagged @works,
        this function should be used to check if that is verified.

        @returns bool: True if the task should be synced
        '''
        attached_tags = self.get_attached_tags()
        if GenericBackend.ALLTASKS_TAG in attached_tags:
            return True
        for tag in rtm_task.get_tags():
            if "@" + tag in attached_tags:
                return True
        return False

###############################################################################
### RTM PROXY #################################################################
###############################################################################


class RTMProxy(object):
    '''
    The purpose of this class is producing an updated list of RTMTasks.
    To do that, it handles:
        - authentication to RTM
        - keeping the list fresh
        - downloading the list
    '''

    PUBLIC_KEY = "2a440fdfe9d890c343c25a91afd84c7e"
    PRIVATE_KEY = "ca078fee48d0bbfa"

    def __init__(self,
                 auth_confirm_fun,
                 token=None):
        self.auth_confirm = auth_confirm_fun
        self.token = token
        self.authenticated = threading.Event()
        self.login_event = threading.Event()
        self.is_not_refreshing = threading.Event()
        self.is_not_refreshing.set()

    ##########################################################################
    ### AUTHENTICATION #######################################################
    ##########################################################################

    def start_authentication(self):
        '''
        Launches the authentication process
        '''
        initialize_thread = threading.Thread(target=self._authenticate)
        initialize_thread.setDaemon(True)
        initialize_thread.start()

    def is_authenticated(self):
        '''
        Returns true if we've autheticated to RTM
        '''
        return self.authenticated.isSet()

    def wait_for_authentication(self):
        '''
        Inhibits the thread until authentication occours
        '''
        self.authenticated.wait()

    def get_auth_token(self):
        '''
        Returns the oauth token, or none
        '''
        try:
            return self.token
        except:
            return None

    def _authenticate(self):
        '''
        authentication main function
        '''
        self.authenticated.clear()
        while not self.authenticated.isSet():
            if not self.token:
                self.rtm = createRTM(
                    self.PUBLIC_KEY, self.PRIVATE_KEY, self.token)
                subprocess.Popen(['xdg-open', self.rtm.getAuthURL()])
                self.auth_confirm()
                try:
                    time.sleep(1)
                    self.token = self.rtm.getToken()
                except Exception:
                    # something went wrong.
                    self.token = None
                    continue
            try:
                if self._login():
                    self.authenticated.set()
            except exceptions.IOError:
                BackendSignals().backend_failed(self.get_id(),
                                                BackendSignals.ERRNO_NETWORK)

    def _login(self):
        '''
        Tries to establish a connection to rtm with a token got from the
        authentication process
        '''
        try:
            self.rtm = createRTM(self.PUBLIC_KEY, self.PRIVATE_KEY, self.token)
            self.timeline = self.rtm.timelines.create().timeline
            return True
        except (RTMError, RTMAPIError), e:
            Log.error("RTM ERROR" + str(e))
        return False

    ##########################################################################
    ### RTM TASKS HANDLING ###################################################
    ##########################################################################

    def unroll_changes(self, transaction_ids):
        '''
        Roll backs the changes tracked by the list of transaction_ids given
        '''
        for transaction_id in transaction_ids:
            self.rtm.transactions.undo(timeline=self.timeline,
                                       transaction_id=transaction_id)

    def get_rtm_tasks_dict(self):
        '''
        Returns a dict of RTMtasks. It will start authetication if necessary.
        The dict is kept updated automatically.
        '''
        if not hasattr(self, '_rtm_task_dict'):
            self.refresh_rtm_tasks_dict()
        else:
            time_difference = datetime.datetime.now() - \
                self.__rtm_task_dict_timestamp
            if time_difference.seconds > 60:
                self.refresh_rtm_tasks_dict()
        return self._rtm_task_dict.copy()

    def __getattr_the_rtm_way(self, an_object, attribute):
        '''
        RTM, to compress the XML file they send to you, cuts out all the
        unnecessary stuff.
        Because of that, getting an attribute from an object must check if one
        of those optimizations has been used.
        This function always returns a list wrapping the objects found
        (if any).
        '''
        try:
            list_or_object = getattr(an_object, attribute)
        except AttributeError:
            return []

        if isinstance(list_or_object, list):
            return list_or_object
        else:
            return [list_or_object]

    def __get_rtm_lists(self):
        '''
        Gets the list of the RTM Lists (the tabs on the top of rtm website)
        '''
        # Here's the attributes of RTM lists. For the list of them, see
        # http://www.rememberthemilk.com/services/api/methods/
        # rtm.lists.getList.rtm
        return self.__getattr_the_rtm_way(self.rtm.lists.getList().lists,
                                          'list')

    def __get_rtm_taskseries_in_list(self, list_id):
        '''
        Gets the list of "taskseries" objects in a rtm list.
        For an explenation of what are those, see
        http://www.rememberthemilk.com/services/api/tasks.rtm
        '''
        list_object_wrapper = self.rtm.tasks.getList(list_id=list_id,
                                                     filter='includeArchived\
                                                     :true').tasks
        list_object_list = self.__getattr_the_rtm_way(
            list_object_wrapper, 'list')
        if not list_object_list:
            return []
        # we asked for one, so we should get one
        assert(len(list_object_list) == 1)
        list_object = list_object_list[0]
        # check that the given list is the correct one
        assert(list_object.id == list_id)
        return self.__getattr_the_rtm_way(list_object, 'taskseries')

    def refresh_rtm_tasks_dict(self):
        '''
        Builds a list of RTMTasks fetched from RTM
        '''
        if not self.is_authenticated():
            self.start_authentication()
            self.wait_for_authentication()

        if not self.is_not_refreshing.isSet():
            # if we're already refreshing, we just wait for that to happen and
            # then we immediately return
            self.is_not_refreshing.wait()
            return
        self.is_not_refreshing.clear()
        Log.debug('refreshing rtm')

        # To understand what this function does, here's a sample output of the
        # plain getLists() from RTM api:
        #    http://www.rememberthemilk.com/services/api/tasks.rtm

        # our purpose is to fill this with "tasks_id: RTMTask" items
        rtm_tasks_dict = {}

        rtm_lists_list = self.__get_rtm_lists()
        # for each rtm list, we retrieve all the tasks in it
        for rtm_list in rtm_lists_list:
            if rtm_list.archived != '0' or rtm_list.smart != '0':
                # we skip archived and smart lists
                continue
            rtm_taskseries_list = self.__get_rtm_taskseries_in_list(
                rtm_list.id)
            for rtm_taskseries in rtm_taskseries_list:
                # we drill down to actual tasks
                rtm_tasks_list = self.__getattr_the_rtm_way(
                    rtm_taskseries, 'task')
                for rtm_task in rtm_tasks_list:
                    rtm_tasks_dict[rtm_task.id] = RTMTask(rtm_task,
                                                          rtm_taskseries,
                                                          rtm_list,
                                                          self.rtm,
                                                          self.timeline)

        # we're done: we store the dict in this class and we annotate the time
        #             we got it
        self._rtm_task_dict = rtm_tasks_dict
        self.__rtm_task_dict_timestamp = datetime.datetime.now()
        self.is_not_refreshing.set()

    def has_rtm_task(self, rtm_task_id):
        '''
        Returns True if we have seen that task id
        '''
        cache_result = rtm_task_id in self.get_rtm_tasks_dict()
        return cache_result
        # it may happen that the rtm_task is on the website but we haven't
        # downloaded it yet. We need to update the local cache.

        # it's a big speed loss. Let's see if we can avoid it.
        # self.refresh_rtm_tasks_dict()
        # return rtm_task_id in self.get_rtm_tasks_dict()

    def create_new_rtm_task(self, title, transaction_ids=[]):
        '''
        Creates a new rtm task
        '''
        result = self.rtm.tasks.add(timeline=self.timeline, name=title)
        rtm_task = RTMTask(result.list.taskseries.task,
                           result.list.taskseries,
                           result.list,
                           self.rtm,
                           self.timeline)
        # adding to the dict right away
        if hasattr(self, '_rtm_task_dict'):
            # if the list hasn't been downloaded yet, we do not create a list,
            # because the fact that the list is created is used to keep track
            # of list updates
            self._rtm_task_dict[rtm_task.get_id()] = rtm_task
        transaction_ids.append(result.transaction.id)
        return rtm_task


###############################################################################
### RTM TASK ##################################################################
###############################################################################
# dictionaries to translate a RTM status into a GTG one (and back)
GTG_TO_RTM_STATUS = {Task.STA_ACTIVE: True,
                     Task.STA_DONE: False,
                     Task.STA_DISMISSED: False}

RTM_TO_GTG_STATUS = {True: Task.STA_ACTIVE,
                     False: Task.STA_DONE}


class RTMTask(object):
    '''
    A proxy object that encapsulates a RTM task, giving an easier API to access
    and modify its attributes.
    This backend already uses a library to interact with RTM, but that is just
     a thin proxy for HTML gets and posts.
    The meaning of all "special words"

    http://www.rememberthemilk.com/services/api/tasks.rtm
    '''

    def __init__(self, rtm_task, rtm_taskseries, rtm_list, rtm, timeline):
        '''
        sets up the various parameters needed to interact with a task.

        @param task: the task object given by the underlying library
        @param rtm_list: the rtm list the task resides in.
        @param rtm_taskseries: all the tasks are encapsulated in a taskseries
            object. From RTM website::

            A task series is a grouping of tasks generated by a recurrence
            pattern (more specifically, a recurrence pattern of type every – an
            after type recurrence generates a new task series for every
            occurrence). Task series' share common properties such as:
                - Name.
                - Recurrence pattern.
                - Tags.
                - Notes.
                - Priority.
        @param rtm: a handle of the rtm object, to be able to speak with rtm.
                    Authentication should have already been done.
        @param timeline: a "timeline" is a series of operations rtm can undo in
                         bulk. We are free of requesting new timelines as we
                         please, with the obvious drawback of being slower.
        '''
        self.rtm_task = rtm_task
        self.rtm_list = rtm_list
        self.rtm_taskseries = rtm_taskseries
        self.rtm = rtm
        self.timeline = timeline

    def get_title(self):
        '''Returns the title of the task, if any'''
        return self.rtm_taskseries.name

    def set_title(self, title, transaction_ids=[]):
        '''Sets the task title'''
        title = cgi.escape(title)
        result = self.rtm.tasks.setName(timeline=self.timeline,
                                        list_id=self.rtm_list.id,
                                        taskseries_id=self.rtm_taskseries.id,
                                        task_id=self.rtm_task.id,
                                        name=title)
        transaction_ids.append(result.transaction.id)

    def get_id(self):
        '''Return the task id. The taskseries id is *different*'''
        return self.rtm_task.id

    def get_status(self):
        '''Returns the task status, in GTG terminology'''
        return RTM_TO_GTG_STATUS[self.rtm_task.completed == ""]

    def set_status(self, gtg_status, transaction_ids=[]):
        '''Sets the task status, in GTG terminology'''
        status = GTG_TO_RTM_STATUS[gtg_status]
        if status is True:
            api_call = self.rtm.tasks.uncomplete
        else:
            api_call = self.rtm.tasks.complete
        result = api_call(timeline=self.timeline,
                          list_id=self.rtm_list.id,
                          taskseries_id=self.rtm_taskseries.id,
                          task_id=self.rtm_task.id)
        transaction_ids.append(result.transaction.id)

    def get_tags(self):
        '''Returns the task tags'''
        tags = self.rtm_taskseries.tags
        if not tags:
            return []
        else:
            return self.__getattr_the_rtm_way(tags, 'tag')

    def __getattr_the_rtm_way(self, an_object, attribute):
        '''
        RTM, to compress the XML file they send to you, cuts out all the
        unnecessary stuff.
        Because of that, getting an attribute from an object must check if one
        of those optimizations has been used.
        This function always returns a list wrapping the objects found
        (if any).
        '''
        try:
            list_or_object = getattr(an_object, attribute)
        except AttributeError:
            return []
        if isinstance(list_or_object, list):
            return list_or_object
        else:
            return [list_or_object]

    def set_tags(self, tags, transaction_ids=[]):
        '''
        Sets a new set of tags to a task. Old tags are deleted.
        '''
        # RTM accept tags without "@" as prefix,  and lowercase
        tags = [tag[1:].lower() for tag in tags]
        # formatting them in a comma-separated string
        if len(tags) > 0:
            tagstxt = reduce(lambda x, y: x + ", " + y, tags)
        else:
            tagstxt = ""
        result = self.rtm.tasks.setTags(timeline=self.timeline,
                                        list_id=self.rtm_list.id,
                                        taskseries_id=self.rtm_taskseries.id,
                                        task_id=self.rtm_task.id,
                                        tags=tagstxt)
        transaction_ids.append(result.transaction.id)

    def get_text(self):
        '''
        Gets the content of RTM notes, aggregated in a single string
        '''
        notes = self.rtm_taskseries.notes
        if not notes:
            return ""
        else:
            note_list = self.__getattr_the_rtm_way(notes, 'note')
            return "".join(map(lambda note: "%s\n" % getattr(note, '$t'),
                               note_list))

    def set_text(self, text, transaction_ids=[]):
        '''
        deletes all the old notes in a task and sets a single note with the
        given text
        '''
        # delete old notes
        notes = self.rtm_taskseries.notes
        if notes:
            note_list = self.__getattr_the_rtm_way(notes, 'note')
            for note_id in [note.id for note in note_list]:
                result = self.rtm.tasksNotes.delete(timeline=self.timeline,
                                                    note_id=note_id)
                transaction_ids.append(result.transaction.id)

        if text == "":
            return
        text = cgi.escape(text)

        # RTM does not support well long notes (that is, it denies the request)
        # Thus, we split long text in chunks. To make them show in the correct
        # order on the website, we have to upload them from the last to the
        # first (they show the most recent on top)
        text_cursor_end = len(text)
        while True:
            text_cursor_start = text_cursor_end - 1000
            if text_cursor_start < 0:
                text_cursor_start = 0

            result = self.rtm.tasksNotes.add(timeline=self.timeline,
                                             list_id=self.rtm_list.id,
                                             taskseries_id=self.
                                             rtm_taskseries.id,
                                             task_id=self.rtm_task.id,
                                             note_title="",
                                             note_text=text[text_cursor_start:
                                                            text_cursor_end])
            transaction_ids.append(result.transaction.id)
            if text_cursor_start <= 0:
                break
            text_cursor_end = text_cursor_start - 1

    def get_due_date(self):
        '''
        Gets the task due date
        '''
        due = self.rtm_task.due
        if due == "":
            return Date.no_date()
        date = self.__time_rtm_to_datetime(due).date()
        return Date(date)

    def set_due_date(self, due, transaction_ids=[]):
        '''
        Sets the task due date
        '''
        kwargs = {'timeline': self.timeline,
                  'list_id': self.rtm_list.id,
                  'taskseries_id': self.rtm_taskseries.id,
                  'task_id': self.rtm_task.id}
        if due is not None:
            kwargs['parse'] = 1
            kwargs['due'] = self.__time_date_to_rtm(due)
        result = self.rtm.tasks.setDueDate(**kwargs)
        transaction_ids.append(result.transaction.id)

    def get_modified(self):
        '''
        Gets the task modified time, in local time
        '''
        # RTM does not set a "modified" attribute in a new note because it uses
        # a "added" attribute. We need to check for both.
        if hasattr(self.rtm_task, 'modified'):
            rtm_task_modified = self.__time_rtm_to_datetime(
                self.rtm_task.modified)
        else:
            rtm_task_modified = self.__time_rtm_to_datetime(
                self.rtm_task.added)
        if hasattr(self.rtm_taskseries, 'modified'):
            rtm_taskseries_modified = self.__time_rtm_to_datetime(
                self.rtm_taskseries.modified)
        else:
            rtm_taskseries_modified = self.__time_rtm_to_datetime(
                self.rtm_taskseries.added)
        return max(rtm_task_modified, rtm_taskseries_modified)

    def delete(self):
        self.rtm.tasks.delete(timeline=self.timeline,
                              list_id=self.rtm_list.id,
                              taskseries_id=self.rtm_taskseries.id,
                              task_id=self.rtm_task.id)

    # RTM speaks utc, and accepts utc if the "parse" option is set.
    def __tz_utc_to_local(self, dt):
        dt = dt.replace(tzinfo=tzutc())
        dt = dt.astimezone(tzlocal())
        return dt.replace(tzinfo=None)

    def __tz_local_to_utc(self, dt):
        dt = dt.replace(tzinfo=tzlocal())
        dt = dt.astimezone(tzutc())
        return dt.replace(tzinfo=None)

    def __time_rtm_to_datetime(self, string):
        string = string.split('.')[0].split('Z')[0]
        dt = datetime.datetime.strptime(string.split(".")[0],
                                        "%Y-%m-%dT%H:%M:%S")
        return self.__tz_utc_to_local(dt)

    def __time_rtm_to_date(self, string):
        string = string.split('.')[0].split('Z')[0]
        dt = datetime.datetime.strptime(string.split(".")[0], "%Y-%m-%d")
        return self.__tz_utc_to_local(dt)

    def __time_datetime_to_rtm(self, timeobject):
        if timeobject is None:
            return ""
        timeobject = self.__tz_local_to_utc(timeobject)
        return timeobject.strftime("%Y-%m-%dT%H:%M:%S")

    def __time_date_to_rtm(self, timeobject):
        if timeobject is None:
            return ""
        # WARNING: no timezone? seems to break the symmetry.
        return timeobject.strftime("%Y-%m-%d")

    def __str__(self):
        return "Task %s (%s)" % (self.get_title(), self.get_id())
