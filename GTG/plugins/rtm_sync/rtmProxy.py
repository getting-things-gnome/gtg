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
#import time
import subprocess
#import gobject
from xdg.BaseDirectory import xdg_config_home
from GTG.core.task import Task
from GTG import _
import pickle
#import xml.utils.iso8601
#from datetime import date

#This add's the plugin's path to python sys path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+'/pyrtm')
import rtm
from rtmTask import RtmTask
from genericProxy import GenericProxy


class RtmProxy(GenericProxy):

    __GTG_STATUSES = [Task.STA_ACTIVE,
                   Task.STA_DONE]

    __RTM_STATUSES = [True,
                      False]

    def __init__(self, logger):
        super(RtmProxy, self).__init__()
        self.token = None
        self.logger = logger
        self._gtg_to_rtm_status = dict(zip(self.__GTG_STATUSES,
                                            self.__RTM_STATUSES))
        self._gtg_to_rtm_status[Task.STA_DISMISSED] = "1"
        self._rtm_to_gtg_status = dict(zip(self.__RTM_STATUSES,
                                            self.__GTG_STATUSES))

    def getToken(self):
        """gets a token from file (if a previous sync has been
            performed), or opens a browser to request a new one
            (in which case the function returns true). NOTE: token
            is valid forever """
        if self.token == None:
            self.config_dir = \
                os.path.join(xdg_config_home, 'gtg/plugins/rtm-sync')
            self.token = self._smartLoadFromFile(self.config_dir, 'token')
        if self.token == None:
            self.rtm=rtm.createRTM("2a440fdfe9d890c343c25a91afd84c7e", \
                                   "ca078fee48d0bbfa")
            subprocess.Popen(['xdg-open', self.rtm.getAuthURL()])
            return False
        return True

    def login(self):
        if hasattr(self, 'rtm'):
            try:
                self.token = self.rtm.getToken()
            except:
                self.token = None
        if(self.getToken() == False):
            return False
        try:
            self.rtm = rtm.createRTM("2a440fdfe9d890c343c25a91afd84c7e",\
                               "ca078fee48d0bbfa", self.token)
        except:
            self.token = None
        self._smartSaveToFile(self.config_dir, 'token', self.token)
        #NOTE: a timeline is an undo list for RTM. It can be used for
        # journaling(timeline rollback is atomical)
        self.timeline = self.rtm.timelines.create().timeline
        return True

    def downloadFromWeb(self):
        #NOTE: syncing only incomplete tasks for now
        #(it's easier to debug the things you see)
        lists_id_list = map(lambda x: x.id, \
                             self.rtm.lists.getList().lists.list)

        # Download all non-archived tasks in the list with id x
        def get_list_of_taskseries(x):
            currentlist = self.rtm.tasks.getList(list_id = x, \
                                filter = 'includeArchived:false').tasks
            if hasattr(currentlist, 'list'):
                return currentlist.list
            else:
                return []
        task_list_global= map(get_list_of_taskseries, lists_id_list)
        taskseries_list = filter(lambda x: hasattr(x[0], 'taskseries'), \
                                  zip(task_list_global, lists_id_list))
        tasks_list_wrapped = map(lambda x: (x[0].taskseries, x[1]), \
                                 taskseries_list)
        tasks_list_normalized = map(lambda x: zip(x[0], [x[1]] * len(x[0]), \
                map(lambda x: x.id, x[0])) if type(x[0]) == list \
                else [(x[0], x[1], x[0].id)], tasks_list_wrapped)
        tasks_list_unwrapped = []
        task_objects_list = []
        list_ids_list = []
        taskseries_ids_list = []
        if len(tasks_list_normalized)>0:
            tasks_list_unwrapped = reduce(lambda x, y: x+y, \
                                          tasks_list_normalized)
            task_objects_list, list_ids_list, taskseries_ids_list = \
                    self._unziplist(tasks_list_unwrapped)

        return zip(task_objects_list, list_ids_list, taskseries_ids_list)

    def generateTaskList(self):
        self._task_list = []
        data = self.downloadFromWeb()
        for task, list_id, taskseries_id in data:
            self._task_list.append(RtmTask(task, list_id, taskseries_id, \
                                          self.rtm, self.timeline, \
                                          self.logger, self))
        if self.logger:
            map(lambda task: self.logger.debug("RTM task: |" + task.title),
                                               self._task_list)

    def create_new_task(self, title):
        result = self.rtm.tasks.add(timeline=self.timeline, name=title)
        new_task= RtmTask(result.list.taskseries.task, result.list.id,\
                          result.list.taskseries.id, self.rtm, self.timeline,\
                         self.logger, self)
        self._task_list.append(new_task)
        return new_task

    def get_tasks_list(self):
        return self._task_list

    def delete_task(self, task):
        self._task_list.remove(task)
        task.delete()

    def _smartLoadFromFile(self, dirname, filename):
        path=dirname+'/'+filename
        if os.path.isdir(dirname):
            if os.path.isfile(path):
                try:
                    with open(path, 'r') as file:
                        item = pickle.load(file)
                except:
                    return None
                return item
        else:
            os.makedirs(dirname)

    def _smartSaveToFile(self, dirname, filename, item, **kwargs):
        path=dirname+'/'+filename
        try:
            with open(path, 'wb') as file:
                pickle.dump(item, file)
        except:
            if kwargs.get('critical', False):
                raise Exception(_("saving critical object failed"))

    def _unziplist(self, a):
        if len(a) == 0:
            return [], []
        return tuple(map(list, zip(*a)))
