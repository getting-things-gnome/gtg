# -*- coding: utf-8 -*-
# Copyright (c) 2009 - Luca Invernizzi <invernizzi.l@gmail.com>
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

import os
import sys
import datetime
from xdg.BaseDirectory import xdg_data_home

#Add this file's directory to the path used to search for libraries
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gtgProxy import GtgProxy
from rtmProxy import RtmProxy


#GUI IMPORTS
from time import sleep
import gobject
from GTG import _



class TaskPair(object):

        def __init__(self, \
                     local_task,
                     remote_task):
            self.local_id = local_task.id
            self.remote_id = remote_task.id
            self.__remote_synced_until = remote_task.modified
            self.local_synced_until = local_task.modified
            self.__remote_first_seen = datetime.datetime.now()

        self = property(lambda self: self)

        remote_synced_until = property (\
                lambda self: self.__get_remote_synced_until(),\
                lambda self, t: self.__set_remote_synced_until(t))


        def __get_remote_synced_until(self):
            if self.__remote_synced_until == None or \
               self.__remote_synced_until <= self.__remote_first_seen:
                return self.__remote_first_seen
            else:
                return self.__remote_synced_until

        def __set_remote_synced_until(self, datetime_object):
            self.__remote_synced_until = datetime_object


class SyncEngine(object):

    def __init__(self, this_plugin):
        super(SyncEngine, self).__init__()
        self.this_plugin = this_plugin
        self.plugin_api = this_plugin.plugin_api
        self.logger = self.this_plugin.plugin_api.get_logger()
        self.local_proxy = GtgProxy(self.this_plugin.plugin_api)
        self.remote_proxy = RtmProxy(self.logger)
        self.rtm_has_logon = False

    def rtmLogin(self):
        self.rtm_has_logon = self.remote_proxy.login()

    def rtmHasLogon(self):
        return self.rtm_has_logon


    def synchronize(self):
        self.synchronizeWorker()

    def synchronizeWorker(self):
        #Generate the two list of tasks from the local and remote task source 
        self.update_status(_("Downloading task list..."))
        self.update_progressbar(0.1)
        self.remote_proxy.generateTaskList()
        self.local_proxy.generateTaskList()
        remote_tasks = self.remote_proxy.get_tasks_list()
        local_tasks = self.local_proxy.get_tasks_list()

        #Load the list of known links between tasks (tasks that are the same 
        # one saved in different task sources)
        self.taskpairs = self.plugin_api.load_configuration_object( \
                            "rtm-sync", \
                            "taskpairs", \
                            xdg_data_home)
        if self.taskpairs == None:
        #We have no previous knowledge of links, this must be the first
        #attempt to synchronize. So, we try to infer some by
        # linking tasks with the same title
            self._link_same_title(local_tasks, remote_tasks) 
        
        #We'll use some sets to see what is new and what was deleted
        old_local_ids = set(map(lambda tp: tp.local_id, self.taskpairs))
        old_remote_ids = set(map(lambda tp: tp.remote_id, self.taskpairs))
        current_local_ids = set(map(lambda t: t.id, local_tasks))
        current_remote_ids = set(map(lambda t: t.id, remote_tasks))
        #Tasks that have been added
        new_local_ids = current_local_ids.difference(old_local_ids)
        new_remote_ids = current_remote_ids.difference(old_remote_ids)
        #Tasks that have been deleted
        deleted_local_ids = old_local_ids.difference(current_local_ids)
        deleted_remote_ids = old_remote_ids.difference(current_remote_ids)
        #Local tasks with the remote task still existing (could need to be
        #updated)
        updatable_local_ids = current_local_ids.difference(new_local_ids)
        
        #Add tasks to the remote proxy
        self.update_status(_("Adding tasks to rtm.."))
        self.update_progressbar(0.3)
        [new_local_tasks, new_remote_tasks] = self._process_new_tasks(\
                                                        new_local_ids,\
                                                        local_tasks, \
                                                        self.remote_proxy)
        self._append_to_taskpairs(new_local_tasks, new_remote_tasks)

        #Add tasks to the local proxy
	self.update_status(_("Adding tasks to gtg.."))
        self.update_progressbar(0.4)
        [new_remote_tasks, new_local_tasks] = self._process_new_tasks(\
                                                        new_remote_ids,\
                                                        remote_tasks,\
                                                        self.local_proxy)
        self._append_to_taskpairs(new_local_tasks, new_remote_tasks)
        
        #Delete tasks from the remote proxy
	self.update_status(_("Deleting tasks from rtm.."))
        self.update_progressbar(0.5)
        taskpairs_deleted = filter(lambda tp: tp.local_id in deleted_local_ids,\
                                    self.taskpairs)
        remote_ids_to_delete = map( lambda tp: tp.remote_id, taskpairs_deleted)
        self._process_deleted_tasks(remote_ids_to_delete, remote_tasks,\
                                    self.remote_proxy)
        map(lambda tp: self.taskpairs.remove(tp), taskpairs_deleted)

        #Delete tasks from the local proxy
	self.update_status(_("Deleting tasks from gtg.."))
        self.update_progressbar(0.6)
        taskpairs_deleted = filter(lambda tp: tp.remote_id in deleted_remote_ids,\
                                    self.taskpairs)
        local_ids_to_delete = map( lambda tp: tp.local_id, taskpairs_deleted)
        self._process_deleted_tasks(local_ids_to_delete, local_tasks, self.local_proxy)
        map(lambda tp: self.taskpairs.remove(tp), taskpairs_deleted)

        #Update tasks
	self.update_status(_("Updating changed tasks.."))
        self.update_progressbar(0.8)
        local_to_taskpair = self._list_to_dict(self.taskpairs, \
                                                  "local_id", \
                                                  "self")
        local_id_to_task = self._list_to_dict(local_tasks, \
                                                  "id", \
                                                  "self")
        remote_id_to_task = self._list_to_dict(remote_tasks, \
                                                  "id", \
                                                  "self")
        for local_id in updatable_local_ids:
            taskpair = local_to_taskpair[local_id]
            local_task = local_id_to_task[local_id]
            remote_task = remote_id_to_task[taskpair.remote_id]
            local_was_updated = local_task.modified > \
                                    taskpair.local_synced_until
            remote_was_updated = remote_task.modified > \
                                    taskpair.remote_synced_until

            if local_was_updated and remote_was_updated:
                if local_task.modified > remote_task.modified:
                    self.update_substatus(_("Updating ") + local_task.title)
                    remote_task.copy(local_task)
                else: 
                #If the update time is the same one, we have to
                # arbitrary decide which gets copied
                    self.update_substatus(_("Updating ") + remote_task.title)
                    local_task.copy(remote_task)
            elif local_was_updated:
                self.update_substatus(_("Updating ") + local_task.title)
                remote_task.copy(local_task)
            elif remote_was_updated:
                self.update_substatus(_("Updating ") + remote_task.title)
                local_task.copy(remote_task)

            taskpair.remote_synced_until = remote_task.modified
            taskpair.local_synced_until = local_task.modified

        #Lastly, save the list of known links
        self.update_status(_("Saving current state.."))
        self.update_progressbar(0.9)
        self.plugin_api.save_configuration_object( \
                            "rtm-sync", \
                            "taskpairs", \
                            self.taskpairs,
                            xdg_data_home)
	self.close_gui(_("Synchronization completed."))


    def _append_to_taskpairs(self, local_tasks, remote_tasks):
        for local, remote in zip(local_tasks, remote_tasks):
            self.taskpairs.append(TaskPair( \
                                local_task = local,
                                remote_task = remote))

    def _task_ids_to_tasks(self, id_list, task_list):
        #TODO: this is not the quickest way to do this
        id_to_task = self._list_to_dict(task_list, "id", "self")
        return map(lambda id: id_to_task[id], id_list)
        


    def _process_new_tasks(self, new_ids, all_tasks, proxy):
        new_tasks = self._task_ids_to_tasks(new_ids, all_tasks)
        created_tasks = []
        for task in new_tasks:
            self.update_substatus(_("Adding ") + task.title)
            created_task = proxy.create_new_task(task.title)
            created_task.copy(task)
            created_tasks.append(created_task)
        return new_tasks, created_tasks

    def _process_deleted_tasks(self, ids_to_remove, all_tasks, proxy):
        tasks_to_remove = self._task_ids_to_tasks(ids_to_remove, all_tasks)
        for task in tasks_to_remove:
            self.update_substatus(_("Deleting ") + task.title)
            proxy.delete_task(task)

    def _list_to_dict(self, source_list, fun1, fun2):
        list1 = map(lambda elem: getattr(elem, fun1), source_list)
        list2 = map(lambda elem: getattr(elem, fun2), source_list)
        return dict(zip(list1, list2))

    def _link_same_title(self, local_list, remote_list):
        self.taskpairs = []
        local_title_to_task = self._list_to_dict(local_list, \
                                                "title", "self")
        remote_title_to_task = self._list_to_dict(remote_list, \
                                                 "title", "self")
        local_titles = map(lambda t: t.title, local_list)
        remote_titles = map(lambda t: t.title, remote_list)
        common_titles = set(local_titles).intersection(set(remote_titles))
        for title in common_titles:
            self.taskpairs.append(TaskPair( \
                                local_task = local_title_to_task[title],
                                remote_task = remote_title_to_task[title]))


## GUI 
    def close_gui(self, msg):
        self.update_status(msg)
        self.update_progressbar(1.0)
        sleep(2)
        self.update_status(_("Closing in one second"))
        sleep(1)
        gobject.idle_add(self.this_plugin.purgeDialog)

    def update_progressbar(self, percent):
        self.this_plugin.progressbar_percent = percent
        gobject.idle_add(self.this_plugin.set_progressbar)

    def update_status(self, status):
        self.this_plugin.status = status
        gobject.idle_add(self.this_plugin.set_status)

    def update_substatus(self, substatus):
        self.this_plugin.substatus = substatus
        gobject.idle_add(self.this_plugin.set_substatus)
