# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2013-2014 - Parin Porecha
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
GTGOnline! backend
'''

import os
import cgi
import uuid
import time
import threading
import datetime
import subprocess
import exceptions
import requests
import json
import cookielib

import pynotify

#from dateutil.tz import tzutc, tzlocal
from lxml import html
from re import sub
from hashlib import md5

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
from GTG.tools.dates import Date

class Backend(PeriodicImportBackend):
    """
    GTGOnline! Backend
    """

    _general_description = {
        GenericBackend.BACKEND_NAME: "backend_gtgonline",
        GenericBackend.BACKEND_HUMAN_NAME: _("GTGOnline!"),
        GenericBackend.BACKEND_AUTHORS: ["Parin Porecha"],
        GenericBackend.BACKEND_TYPE: GenericBackend.TYPE_READWRITE,
        GenericBackend.BACKEND_DESCRIPTION:
        _("This service synchronizes your tasks with Getting Things Gnome's"
          " Web Application - GTGOnline!\n\n"
          "Note: This product uses the GTGOnline! API and is even"
          " certified by GTGOnline!\n"
          "How cool is that !"),
    }

    _static_parameters = {
        "username": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE:
                'user@example.com', },
        "password": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_PASSWORD,
            GenericBackend.PARAM_DEFAULT_VALUE: '', },
        "period": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_INT,
            GenericBackend.PARAM_DEFAULT_VALUE: 5, },
    }
    
    # USE BELOW ONLY IF ACCESSING LOCALHOST INSIDE CAMPUS
    #NO_PROXY = {'no': 'pass'}
    
    IS_REQUESTS_LATEST = True
    
    BASE_URL = "http://gtgonline-parinporecha.rhcloud.com/"
    URLS = {
        'auth': BASE_URL + 'user/auth_gtg/',
        'tasks': {
            'get': BASE_URL + 'tasks/serial/',
            'new': BASE_URL + 'tasks/new/',
            'update': BASE_URL + 'tasks/bulk_update/',
            'delete': BASE_URL + 'tasks/delete/',
        },
        'tags': BASE_URL + 'tags/all/',
    }
    
    CONVERT_24_HR = '%d/%m/%y'
    CONVERT_24_HR_WITH_TIME = '%d/%m/%y %H:%M:%S'
    GTG_NO_DATE = datetime.date.max - datetime.timedelta(1)
    GTG_SOMEDAY_DATE = datetime.date.max
    GTGONLINE_SOMEDAY_DATE = datetime.datetime.now() + datetime.timedelta(30)
    
    LOCAL = 0
    REMOTE = 1
    
    WEB_STATUS_TO_GTG = {
        0: 'Active',
        1: 'Done',
        2: 'Dismiss',
    }
    
    def __init__(self, params):
        """ Constructor of the object """
        super(Backend, self).__init__(params)
        self._sync_tasks = set()
        self._changed_locally = set()
        self._changed_remotely = set()
        # loading the saved state of the synchronization, if any
        self.data_path = os.path.join('backends/gtgonline/',
                                      "sync_engine-" + self.get_id())
        self.sync_engine = self._load_pickled_file(self.data_path,
                                                   SyncEngine())
    
    def initialize(self):
        """ This is called when a backend is enabled """
        super(Backend, self).initialize()
        
        self.hash_dict_path = os.path.join('backends/gtgonline/',
                                      "hash_dict-" + self.get_id() + \
                                      self._parameters["username"])
        #print "Data path = \n****\n****\n" + str(self.hash_dict_path) + "\n****\n****\n"
        self.hash_dict = self._load_pickled_file(self.hash_dict_path, \
                                                 default_value = {})
        if requests.__version__ < '1.0':
            #print "Using requests 0.x"
            self.IS_REQUESTS_LATEST = False
            if requests.__version__[:4] != '0.14':
                print "Backend GTGOnline! has been disabled \
                because the requests module you're using is very old. \
                Please update it (pip install requests)"
                self.error_caught_abort(BackendSignals.ERRNO_NETWORK)
        
        pynotify.init("started")
        self.try_auth()
        #print "returned here"
            
    def try_auth(self):
        """
        Checks whether the credentials entered match a user on the server.
        """
        params = {"email": self._parameters["username"],
                  "password": self._parameters["password"],}
        auth_response = requests.post(self.URLS['auth'], params)
        if auth_response.status_code != 200:
            self.error_caught_abort(BackendSignals.ERRNO_NETWORK)
        if auth_response.text != '1':
            self.error_caught_abort(BackendSignals.ERRNO_AUTHENTICATION)
    
    def error_caught_abort(self, error):
        """
        Provided credentials are not valid.
        Disable this instance and show error to user
        """
        #Log.error('Failed to authenticate')
        BackendSignals().backend_failed(self.get_id(),
                        error)
        self.quit(disable=True)
        
    def do_periodic_import(self, ):
        #print "Importing ..."
        tasks = self.fetch_tasks_from_server()
        self.process_tasks(tasks)
        #tags = self.fetch_tags_from_server()
        #self.process_tags(tags)
        self.save_state()
        pynotify.Notification("Sync Done", "Added: 5 tasks\nUpdated: 9 tasks\nDeleted: 2 tasks\n(^^This isn't real, just a representation)", "dialog-info").show()
        
    def save_state(self):
        '''Saves the state of the synchronization'''
        #print "Saving Data path = \n****\n****\n" + str(self.hash_dict_path) + "\n****\n****\n"
        #print "Hash Dict = \n****\n****\n" + str(self.hash_dict) + "\n****\n****\n"
        #for task_id in self.hash_dict.keys():
            #task = self.datastore.get_task(task_id)
            #if task != None:
                #print "Id = " + task_id + " Title = " + task.get_title()
            #else:
                #print "!!! BAD ID !!! = " + task_id
        
        #print "save_state called"
        #print "hash_dict = " + str(self.hash_dict)
        self._store_pickled_file(self.data_path, self.sync_engine)
        self._store_pickled_file(self.hash_dict_path, self.hash_dict)
        
    def fetch_tasks_from_server(self, ):
        """
        Queries the server for the tasks of a user.
        The server gives a JSON response which is then sent for parsing
        """
        #print "Fetching tasks started ..."
        params = {"email": self._parameters["username"],
                  "password": self._parameters["password"],}
        tasks = requests.post(self.URLS['tasks']['get'], params)
        #print "response received = " + str(tasks.json)
        if tasks.status_code == 200:
            #print "json = " + str(tasks.json())
            if not self.IS_REQUESTS_LATEST:
                return tasks.json
            return tasks.json()
        return ''
    
    def process_tasks(self, fetched_remote_tasks):
        """
        The main method.
        Based on hash dictionary stored locally and the JSON response received
        from server, local tasks and remote tasks are divided into 6 scenarios
        of sync - "local new", "local update", "local delete", "remote new",
        "remote update" and "remote delete". They are then sent to the various
        functions to implement these scenarios
        """
        #print "Tasks = " + str(remote_tasks)
        #print "Backend id = " + self.get_id()
        
        local_tasks = self.datastore.get_all_tasks()
        gtg_titles_dic = {}
        remote_add = []
        update = []
        remote_delete = []
        local_delete = []
        remote_ids_list = []
        #server_ids = [task['id'] for task in remote_tasks]
        server_id_dict = {}
        local_id_dict = {}
        old_local_tasks = []
        #print "Remote tasks = " + str(fetched_remote_tasks)
        for task in fetched_remote_tasks:
            server_id_dict[str(task['id'])] = task
        
        #print "server id dict = " + str(server_id_dict)
        
        for tid in local_tasks:
            gtg_task = self.datastore.get_task(tid)
            if not self._gtg_task_is_syncable_per_attached_tags(gtg_task):
                #print "NOT SYNCABLE = " + gtg_task.get_title()
                continue
            
            sync_details = self.hash_dict.get(tid, [None, None])
            if sync_details[1] == None:
                remote_add.append(gtg_task)
                self.get_or_save_hash(tid)
                gtg_task.sync()
            else:
                old_local_tasks.append(gtg_task)
        
        remote_add = self.modify_tasks_for_gtgonline(remote_add)
        id_dict = self.remote_add_tasks(remote_add)
        self.add_remote_id_to_sync_details(id_dict)
        #print "Id dict = " + str(id_dict)
        
        remote_ids_in_hash_dict = [i[1] for i in self.hash_dict.values()]
        
        new_remote_tasks = list(set(server_id_dict.keys()) - \
                                set(remote_ids_in_hash_dict))
        deleted_local_tasks = list(set(self.hash_dict.keys()) - set(local_tasks))
        self.process_local_new_scenario(new_remote_tasks, server_id_dict)
        self.process_remote_delete_scenario(deleted_local_tasks)
        
        for gtg_task in old_local_tasks:
            sync_details = self.hash_dict.get(gtg_task.get_id(), [None, None])
            remote_id = sync_details[1]
            remote_ids_list.append(remote_id)
            if remote_id in server_id_dict.keys():
                #print "Sending task to update scenario"
                self.process_update_scenario(gtg_task, \
                                             server_id_dict[remote_id], \
                                             sync_details[0])
            else:
                local_delete.append(gtg_task)
                self.send_task_for_deletion(gtg_task)
            gtg_task.sync()
        
        #print "*\n*\nRemote Tasks list = " + str(new_remote_tasks) + "\n*\n*\n"
        #print "*\n*\nOld Local tasks list = " + str(old_local_tasks) + "\n*\n*\n"
        #print "*\n*\nLocal Id dict = " + str(local_id_dict) + "\n*\n*\n"
        #print "*\n*\nServer Id dict = " + str(server_id_dict) + "\n*\n*\n"
        
        #print "Remote add = " + str(remote_add)
        #print "Update = " + str(update)
        #print "Local delete = " + str(local_delete)
        
        self.save_state()
    
    def modify_tasks_for_gtgonline(self, task_list):
        """
        Newly created local tasks have to be created on the server also.
        This method takes a list of local tasks, and returns a dictionary
        with the task ids as keys and as value a dictionary containing the
        task details like name, dates, status, subtask ids
        """
        details = {}
        for task in task_list:
            start_date = self.convert_date_to_str(task.get_start_date().date())
            due_date = self.convert_date_to_str(task.get_due_date().date())
            details[task.get_id()] = {
                'name': task.get_title(),
                'description': self.strip_xml_tags(task.get_text()),
                'start_date': start_date,
                'due_date': due_date,
                'status': task.get_status(),
                'subtasks': [subt.get_id() for subt in task.get_subtasks()]
            }
            #details.append()
        #print "Tasks Details = " + str(details)
        return details
    
    def remote_add_tasks(self, task_list):
        """
        "Remote New" Implementation.
        A task list is sent to the server for creation and the server returns
        a dictionary containing Remote task ids of the created tasks as keys
        and Local ids of those tasks as values. This dict is then used to
        update the hash dictionary ( register the task as synced )
        """
        #print "Adding tasks started ..."
        #print "Task list to send = " + json.dumps(task_list)
        params = {
            "email": self._parameters["username"],
            "password": self._parameters["password"],
            "task_list": json.dumps(task_list),
        }
        ids = requests.post(self.URLS['tasks']['new'], \
                            data = { key: str(value) for key, value in params.items() })
        #print "ids received = " + str(ids.json)
        if not self.IS_REQUESTS_LATEST:
            return ids.json
        return ids.json()
    
    def add_remote_id_to_sync_details(self, id_dict):
        """
        For a newly created task on server, this method adds it's remote id
        to the task element in hash dictionary
        """
        for key, value in id_dict.iteritems():
            
            self.hash_dict[key][1] = value
            
            #with self.datastore.get_backend_mutex():
                #gtg_task = self.datastore.get_task(key)
                #gtg_task.add_remote_id(self.get_id(), value)
                #self.datastore.push_task(gtg_task)
    
    def process_update_scenario(self, local_task, remote_task, task_hash):
        """
        This method takes input a local task, remote task and the latest hash
        from hash dictionary. Both the tasks are hashed and compared with the
        latest hash and this way it is decided which one to update
        """
        task = self.get_latest_task(local_task, remote_task, task_hash)
        if task == local_task:
            #print "Sent remote task to update"
            self.remote_update_task(local_task, remote_task['id'])
        elif task == remote_task:
            #print "Send local task to update"
            self.local_update_task(remote_task, local_task)
    
    def get_latest_task(self, local_task, remote_task, task_hash):
        """
        Compares task hashes with latest hash, updates the hash dictionary
        and returns the latest task
        """
        local_id = local_task.get_id()
        #print "In getting latest task, local id = " + str(local_id)
        local_hash = self.compute_task_hash(local_task)
        remote_hash = self.compute_task_hash(remote_task, mode = self.REMOTE)
        
        if local_hash == task_hash == remote_hash:
            #print "ALL HASHES ARE EQUAL"
            return None
        elif local_hash != task_hash and remote_hash == task_hash:
            #print "Local is Latest. Update Remote"
            self.hash_dict[local_id][0] = local_hash
            return local_task
        elif local_hash == task_hash and remote_hash != task_hash:
            #print "Remote is Latest. Update Local"
            self.hash_dict[local_id][0] = remote_hash
            return remote_task
        else:
            #print "BOTH HASHES ARE DIFFERENT, Update local"
            self.hash_dict[local_id][0] = remote_hash
            return remote_task
        
        '''
        local_mod = local_task.get_modified()
        remote_mod = self.str_to_datetime(remote_task['last_modified_date'])
        print "local_mod = " + str(local_mod) + " remote_due = " + str(remote_mod)
        
        if local_mod < remote_mod:
            print "Remote is Latest. Update Local"
            return remote_task
        else:
            print "Local is Latest. Update Remote"
            return local_task
        '''
    
    def remote_update_task(self, task, task_id):
        """
        "Remote Update" implementation.
        A dictionary with remote task ids as keys and the new details as values
        is sent to the server. Server returns '1' on success and '0' on failure
        """
        #print "Updating remote task started ..."
        start_date = self.convert_date_to_str(task.get_start_date().date())
        due_date = self.convert_date_to_str(task.get_due_date().date())
        #print "Due Date = " + str(due_date)
        #print "Is due date fuzzy ? = " + str(task.get_due_date().is_fuzzy())
        task_list = [
            {
                "task_id": task_id,
                "name": task.get_title(),
                "description": self.strip_xml_tags(task.get_text()),
                "start_date": start_date,
                "due_date": due_date,
                "status": task.get_status(),
                "subtask_ids": self.get_subtask_remote_ids(task),
            }
        ]
        params = {
            "email": self._parameters["username"],
            "password": self._parameters["password"],
            "task_list": json.dumps(task_list),
            "origin": "gtg",
        }
        response = requests.post(self.URLS['tasks']['update'], params)
        
        #print "Update response = " + str(response.json)
        return
    
    def get_subtask_remote_ids(self, local_task):
        """
        Takes input a local task, and returns the remote ids of it's subtasks
        """
        local_subtask_ids = local_task.get_subtasks()
        #print "Subtasks of local task = " + str(local_subtask_ids)
        remote_subtask_ids = []
        for task in local_subtask_ids:
            remote_subtask_ids.append(self.hash_dict.get(task.get_id(), \
                                                         None)[1])
        #print "Remote Subtask Ids = " + str(remote_subtask_ids)
        return remote_subtask_ids
    
    def local_update_task(self, remote_task, local_task):
        """
        "Local Update" implementation.
        """
        #print "Updating local task started ..."
        local_task.set_title(_(remote_task["name"]))
        local_task.set_text(_(remote_task["description"]))
        
        #print "Task Status = " + str(remote_task["status"])
        status = self.WEB_STATUS_TO_GTG.get(remote_task["status"], 'Active')
        local_task.set_status(status)
        
        start_date = self.str_to_datetime(remote_task["start_date"], \
                                        return_date = True, without_time = True)
        due_date = self.str_to_datetime(remote_task["due_date"], \
                                        return_date = True, without_time = True)
        
        local_task.set_start_date(Date(start_date))
        
        current_due_date = local_task.get_due_date()
        if current_due_date.is_fuzzy():
            #print "Local task,= " + local_task.get_title() + " due date is FUZZY"
            due_date = self.get_fuzzy_date(current_due_date, due_date)
        
        local_task.set_due_date(Date(due_date))
        new_tags = set(['@' + tag["name"] for tag in remote_task["tags"]])
        #print "new_tags = " + str(new_tags)
        current_tags = set(local_task.get_tags_name())
        # remove the lost tags
        for tag in current_tags.difference(new_tags):
            local_task.remove_tag(tag)
        # add the new ones
        for tag in new_tags.difference(current_tags):
            local_task.add_tag(tag)
        
        #if local_task.get_remote_ids().get(self.get_id(), None) == None:
            #local_task.add_remote_id(self.get_id(), remote_task["id"])
        
        if len(local_task.get_subtasks()) != len(remote_task["subtasks"]):
            local_task = self.add_subtasks_from_remote(local_task, \
                                                        remote_task)
        
        #print "Before returning, local_task = " + str(local_task)
        return local_task
    
    def add_subtasks_from_remote(self, local_task, remote_task):
        local_subtasks = set(local_task.get_subtasks())
        remote_subtasks = remote_task["subtasks"]
        #print "Remote_subtasks = " + str(remote_subtasks)
        remote_subtask_local_id = []
        
        for key, value in self.hash_dict.iteritems():
            if value[1] in remote_subtasks:
                remote_subtask_local_id.append(key)
        
        #print "Local Subtasks = " + str(list(local_subtasks))
        #print "Remote subtask local id = " + str(remote_subtask_local_id)
        for subtask in set(remote_subtask_local_id).difference(local_subtasks):
            #print "Adding subtask = " + str(subtask)
            local_task.add_child(subtask)
        
        return local_task
    
    def send_task_for_deletion(self, task):
        self.datastore.request_task_deletion(task.get_id())
    
    def process_local_new_scenario(self, remote_ids, remote_task_dict):
        #print "Local New Task started ..."
        #print "Remote ids = " + str(remote_ids)
        local_tasks_dict = {}
        for web_id in remote_ids:
            remote_task = remote_task_dict[web_id]
            #print "LOCAL NEW TASK = " + str(remote_task)
            tid = str(uuid.uuid4())
            local_task = self.datastore.task_factory(tid)
            local_task = self.local_update_task(remote_task, local_task)
            #print "All Tasks = " + str(self.datastore.get_all_tasks())
            self.get_or_save_hash(tid, task_object = local_task, \
                                  web_id = web_id)
            local_tasks_dict[web_id] = local_task
        
        #print "Local Tasks Dict = " + str(local_tasks_dict)
        for key, value in local_tasks_dict.iteritems():
            remote_subtask_ids = remote_task_dict[key]["subtasks"]
            #print "Remote subtask Ids = " + str(remote_subtask_ids)
            local_subtask_ids = [local_tasks_dict[str(task_id)].get_id() \
                                 for task_id in remote_subtask_ids]
            #print "Local subtask ids = " + str(local_subtask_ids)
            for local_id in local_subtask_ids:
                value.add_child(local_id)
            self.datastore.push_task(value)
            
    
    def process_remote_delete_scenario(self, local_ids):
        ids_to_be_deleted = []
        for task_id in local_ids:
            web_id = self.hash_dict.get(task_id, [None, None])[1]
            #print "web_id = " + str(web_id)
            if web_id != None:
                ids_to_be_deleted.append(web_id)
                self.hash_dict.pop(task_id, None)
        self.remote_delete_task(ids_to_be_deleted)
    
    def remote_delete_task(self, web_id_list):
        #print "Deleting remote tasks started ..." + str(web_id_list)
        params = {"email": self._parameters["username"],
                  "password": self._parameters["password"],
                  "task_id_list": json.dumps(web_id_list), "origin": "gtg",}
        tags = requests.post(self.URLS['tasks']['delete'], params)
    
    def fetch_tags_from_server(self, ):
        #print "Fetching tags started ..."
        params = {"email": self._parameters["username"],
                  "password": self._parameters["password"],}
        tags = requests.post(self.URLS['tags'], params)
        #print "response received = " + str(tags.json)
        return tags.json()
    
    def process_tags(self, tags):
        print "Tags = " + str(tags)
        
    def strip_xml_tags(self, text):
        """
        GTG stores links to subtasks, tags and some tags in task description.
        GTGOnline! does not store it that way. Hence, these tags have to be
        stripped out of the description. This is what this method does
        """
        text = sub(r"<.?content>", "", text)
        text = sub(r"<.?tag>", "", text)
        text = sub(r"<subtask>.*</subtask>\n*", "", text)
        return text
    
    def convert_date_to_str(self, date_obj):
        """
        Converts a datetime object to a string in the format used by GTGOnline!
        """
        if date_obj == self.GTG_NO_DATE or date_obj == self.GTG_SOMEDAY_DATE:
            return ''
        #elif date_obj == self.GTG_SOMEDAY_DATE:
            #date_obj = self.GTGONLINE_SOMEDAY_DATE
        date = date_obj.strftime(self.CONVERT_24_HR)
        return date
    
    def str_to_datetime(self, date_str, return_date = False, \
                        without_time = False):
        """
        Takes input a string and if it matches with the format, returns
        a datetime object, else returns None
        """
        try:
            if without_time:
                datetime_obj = datetime.datetime.strptime(date_str, \
                                                      self.CONVERT_24_HR)
            else:
                datetime_obj = datetime.datetime.strptime(date_str, \
                                                  self.CONVERT_24_HR_WITH_TIME)
        except Exception:
            return None
        if return_date:
            return datetime_obj.date()
        return datetime_obj
    
    def get_fuzzy_date(self, current_due_date, due_date):
        #print "Current due_date = " + str(current_due_date)
        #print "New due date = " + str(Date(due_date).date())
        #print "FUzzy date in datetime = " + str(Date(current_due_date).date())
        if Date(current_due_date).date() == Date(due_date).date():
            #print "Both are same"
            return current_due_date
        return due_date
    
    def set_task(self, task):
        #print "BACKEND_GTGONLINE : Set task was called"
        #task.sync()
        self.save_state()
    
    def get_or_save_hash(self, task_id, task_object = None, \
                         web_id = None):
        """
        Searches hash dictionary if a task is present or not.
        If not, it creates it.
        If you know the remote id of the task, give it in keyword arg 'web_id'
        """
        task_hash_list = self.hash_dict.get(task_id, None)
        #print "Task hash list = " + str(task_hash_list)
        if task_hash_list == None:
            if task_object != None:
                task = task_object
            else:
                task = self.datastore.get_task(task_id)
            #print "For task_id = " + str(task_id) + " task = " + str(task)
            task_hash = self.compute_task_hash(task, mode = self.LOCAL)
            #remote_ids = task.get_remote_ids()
            #web_id = remote_ids.get(self.get_id(), None)
            task_hash_list = [task_hash, web_id]
            self.hash_dict[task_id] = task_hash_list
        return task_hash_list
    
    def compute_task_hash(self, task, mode = None):
        """
        Computes the hash of a task.
        Requires task name, description, start date, due date, status and
        no. of subtasks
        """
        if mode == self.REMOTE:
            in_str = task['name']
            in_str += task['description']
            in_str += task['start_date']
            in_str += task['due_date']
            in_str += self.WEB_STATUS_TO_GTG.get(task['status'], 'Active')
            in_str += str(len(task['subtasks']))
        else:
            in_str = task.get_title()
            in_str += self.strip_xml_tags(task.get_text())
            in_str += self.convert_date_to_str(task.get_start_date().date())
            in_str += self.convert_date_to_str(task.get_due_date().date())
            in_str += task.get_status()
            in_str += str(len(task.get_subtasks()))
        return md5(in_str).hexdigest()
