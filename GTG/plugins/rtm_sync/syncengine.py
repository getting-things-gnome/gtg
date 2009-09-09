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
import time
import subprocess
import gobject
from xdg.BaseDirectory import xdg_config_home, xdg_cache_home
import pickle
import xml.utils.iso8601
from datetime import date

# IMPORTANT This add's the plugin's path to python sys path
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))+'/pyrtm')
from gtg_proxy import GtgProxy
from rtm_proxy import RtmProxy
from utility import *

class SyncEngine:

    def __init__(self, this_plugin):
        self.this_plugin = this_plugin
        self.rtm_proxy = RtmProxy ()
        self.gtg_proxy = GtgProxy(self.this_plugin.plugin_api)

    def rtmLogin (self):
        return self.rtm_proxy.login()

    def _firstSynchronization(self):
        gtg_to_rtm_id_mapping = []
        #generating sets to perform intersection of tasks
        #NOTE: assuming different titles!
        gtg_task_titles_set = set (map(lambda x: x.title, self.gtg_list))
        rtm_task_titles_set = set (map(lambda x: x.title, self.rtm_list))
        #tasks in common
        for title in rtm_task_titles_set.intersection (gtg_task_titles_set):
            gtg_to_rtm_id_mapping.append (
                    (filterAttr(self.gtg_list, 'title', title)[0].id,
                     filterAttr(self.rtm_list, 'title', title)[0].id))

        #tasks that must be added to GTG
        for title in rtm_task_titles_set.difference (gtg_task_titles_set):
            base_task = filterAttr(self.rtm_list,'title',title)[0]
            new_task = self.gtg_proxy.newTask(title, True)
            new_task.copy(base_task)
            gtg_to_rtm_id_mapping.append ((new_task.id, base_task.id))

        #tasks that must be added to RTM
        for title in gtg_task_titles_set.difference (rtm_task_titles_set):
            base_task = filterAttr(self.gtg_list,'title',title)[0]
            new_task = self.rtm_proxy.newTask(title)
            new_task.copy(base_task)
            gtg_to_rtm_id_mapping.append((base_task.id, new_task.id))
        return gtg_to_rtm_id_mapping

    def synchronize(self):
        self.update_progressbar(0.1)

        self.gtg_proxy.generateTaskList()
        self.rtm_proxy.generateTaskList()

        self.update_progressbar(0.3)
        self.gtg_list = self.gtg_proxy.task_list
        self.rtm_list = self.rtm_proxy.task_list

        ## loading the mapping of the last sync
        cache_dir = os.path.join(xdg_cache_home,'gtg/plugins/rtm-sync')
        gtg_to_rtm_id_mapping = smartLoadFromFile (\
                               cache_dir, 'gtg_to_rtm_id_mapping')
        if   gtg_to_rtm_id_mapping is None: 
            ###this is the first synchronization
            gtg_to_rtm_id_mapping = \
                    self._firstSynchronization()
        else:
            ###this is an update
            gtg_id_current_set = set(map(lambda x: x.id, self.gtg_list))
            rtm_id_current_set = set(map(lambda x: x.id, self.rtm_list))
            gtg_id_previous_list, rtm_id_previous_list = unziplist \
                    (gtg_to_rtm_id_mapping)
            gtg_id_previous_set = set (gtg_id_previous_list)
            rtm_id_previous_set = set (rtm_id_previous_list)
            gtg_to_rtm_id_dict = dict(gtg_to_rtm_id_mapping)
            rtm_to_gtg_id_dict = dict(zip(rtm_id_previous_list, \
                                          gtg_id_previous_list))

            #tasks removed from gtg since last synchronization
            gtg_removed = gtg_id_previous_set.difference(gtg_id_current_set)
            #tasks removed from rtm since last synchronization
            rtm_removed = rtm_id_previous_set.difference(rtm_id_current_set)
            #tasks added to gtg since last synchronization
            gtg_added = gtg_id_current_set.difference(gtg_id_previous_set)
            #tasks added to rtm since last synchronization
            rtm_added = rtm_id_current_set.difference(rtm_id_previous_set)
            #tasks still in common (which may need to be updated)
            common = rtm_id_current_set.intersection(gtg_id_current_set)
            

            #Delete from rtm the tasks that have been removed in gtg
            for gtg_id in gtg_removed:
                rtm_id = gtg_to_rtm_id_dict[gtg_id]
                map(lambda task: task.delete(), \
                    filterAttr(self.rtm_list,'id',rtm_id))

            #Delete from gtg the tasks that have been removed in rtm
            for rtm_id in rtm_removed:
                gtg_id = rtm_to_gtg_id_dict[rtm_id]
                map(lambda task: task.delete(), \
                    filterAttr(self.gtg_list,'id',gtg_id))



        smartSaveToFile(cache_dir,'gtg_to_rtm_id_mapping',\
                        gtg_to_rtm_id_mapping)

        self.update_status("Synchronization completed")
        self.update_progressbar(1.0)

#            if len (to_be_removed_from_gtg_extended) != 0:
#                to_be_removed_from_gtg, temp = self.unziplist(\
#                                to_be_removed_from_gtg_extended)
#                map (lambda x: plugin_api.get_requester().delete_task(x),\
#                                to_be_removed_from_gtg)
#
#            self.update_progressbar(0.8)
#            ##task that need to be updated
#            to_be_updated = filter (lambda x: x[0] != None and x[1] != None,\
#                                    gtg_to_rtm_task_id_mapping_new)
#            ##TODO:update
#            for item in to_be_updated:
#                if gtg_title_to_id_bijFun.rightFindElem(item[0])!=\
#                        rtm_title_to_id_bijFun.rightFindElem(item[1]):
#                    print "detected title change. still to implement"
#                    rtm_due=None
#                    gtg_due=None
#                    if rtm_task_id_to_task[item[1]].task.due != "":
#                        rtm_due = date.fromtimestamp(xml.utils.iso8601.parse(rtm_task_id_to_task[item[1]].task.due))
#                        print rtm_due
#                    if  plugin_api.get_task(item[0]).get_due_date() != "":
#                       gtg_due = date.fromtimestamp(xml.utils.iso8601.parse(plugin_api.get_task(item[0]).get_due_date()))
#                    if (gtg_due != None and rtm_due != None):
#                        if (gtg_due < rtm_due):
#                            print "gtg is before"
#                            print [gtg_due, rtm_due]
#                        else:
#                            print "gtg is not before"
#                            print [gtg_due, rtm_due]
#
#
#
#
#                    
#
#            ##new tasks
#            gtg_task_id_current_set = set (gtg_task_id_list)
#            rtm_task_id_current_set = set (rtm_task_id_list)
#            gtg_task_id_old_set, rtm_task_id_old_set = \
#                    self.unziplist (gtg_to_rtm_task_id_mapping_new)
#            gtg_new_tasks_set = \
#                    gtg_task_id_current_set.difference (gtg_task_id_old_set)
#            rtm_new_tasks_set = \
#                    rtm_task_id_current_set.difference (rtm_task_id_old_set)
#
#            for id in rtm_new_tasks_set:
#                new_task = plugin_api.get_requester().new_task(newtask=True)
#                new_task.set_title(rtm_title_to_id_bijFun.rightFindElem(id))
#                gtg_to_rtm_task_id_mapping_new.append ((new_task.get_id(), id))
#            #FIXME:gtg reuses id! need uuid
#            for id in gtg_new_tasks_set:
#                new_task= self.rtm.tasks.add(timeline=timeline,\
#                        name=gtg_title_to_id_bijFun.rightFindElem(id))\
#                        .list.taskseries.task
#                gtg_to_rtm_task_id_mapping.append ((id, new_task.id))
#
#        #TODO: ask if ok or undo (easy on rtm (see timeline),
#        #   but on gtg? need to keep a journal?  
#        self.smartSaveToFile(cache_dir,'gtg_to_rtm_task_id_mapping',\
#                        gtg_to_rtm_task_id_mapping)


    def update_progressbar(self,percent):
        self.this_plugin.progressbar_percent = percent
        gobject.idle_add(self.this_plugin.set_progressbar)
    def update_status(self,status):
        self.this_plugin.status = status
        gobject.idle_add(self.this_plugin.set_status)
