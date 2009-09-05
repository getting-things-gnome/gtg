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

    def synchronize(self):
        gtg_proxy = GtgProxy(self.this_plugin.plugin_api)
        rtm_proxy = RtmProxy()
        rtm_proxy.login()

        gtg_proxy.generateTaskList()
        rtm_proxy.generateTaskList()

        gtg_list = gtg_proxy.task_list
        rtm_list = rtm_proxy.task_list

        ## loading the mapping of the last sync
        cache_dir = os.path.join(xdg_cache_home,'gtg/plugins/rtm-sync')
        gtg_to_rtm_id_mapping = smartLoadFromFile (\
                               cache_dir, 'gtg_to_rtm_id_mapping')
        if   gtg_to_rtm_id_mapping is None: 
            ###this is the first synchronization
            print "first sync"
            gtg_to_rtm_id_mapping = []
            #generating sets to perform intersection of tasks
            #NOTE: assuming different titles!
            gtg_task_titles_set = set (map(lambda x: x.title, gtg_list))
            rtm_task_titles_set = set (map(lambda x: x.title, rtm_list))
            #tasks in common
            for title in rtm_task_titles_set.intersection (gtg_task_titles_set):
                gtg_to_rtm_id_mapping.append (
                        (filterAttr(gtg_list, 'title', title)[0].id,
                         filterAttr(rtm_list, 'title', title)[0].id))

            #tasks that must be added to GTG
            for title in rtm_task_titles_set.difference (gtg_task_titles_set):
                new_task = gtg_proxy.newTask(title, True)
                gtg_to_rtm_id_mapping.append ((new_task.id,
                         filterAttr(rtm_list, 'title', title)[0].id))

            #tasks that must be added to RTM
            for title in gtg_task_titles_set.difference (rtm_task_titles_set):
                new_task = rtm_proxy.newTask(title)
                gtg_to_rtm_id_mapping.append (
                        (filterAttr(gtg_list, 'title', title)[0].id,
                         new_task.id))
            print gtg_to_rtm_id_mapping
#
#        else:
#            ###this is an update
#
#            ##updating the status of the task (present or removed)
#            #if the task is still present,return the task id, else return None
#            update_gtg_id = lambda x: x if \
#                    len(filter( lambda y: y == x,gtg_task_id_list)) != 0 else None
#            update_rtm_id = lambda x: x if \
#                    len(filter( lambda y: y == x,rtm_task_id_list)) != 0 else None
#            gtg_to_rtm_task_id_mapping_new = map ( lambda x: (update_gtg_id(x[0]),\
#                                update_rtm_id(x[1])), gtg_to_rtm_task_id_mapping)
#            #removing the tasks that have been removed in GTG or RTM
#            to_be_removed = filter (lambda x: (x[0] == None or x[1] == None) \
#                                    and not (x[0] == None and x[1] == None),\
#                                    gtg_to_rtm_task_id_mapping_new)
#            to_be_removed_from_rtm_extended = filter ( lambda x: x[0] == None , \
#                                                      to_be_removed)
#            to_be_removed_from_gtg_extended = filter ( lambda x: x[1] == None ,\
#                                                      to_be_removed)
#            to_be_removed_from_rtm = None
#            to_be_removed_from_gtg = None
#            self.update_progressbar(0.5)
#            print to_be_removed_from_rtm_extended
#            if len (to_be_removed_from_rtm_extended) != 0:
#                temp,to_be_removed_from_rtm = self.unziplist(\
#                                                to_be_removed_from_rtm_extended)
#                print to_be_removed_from_rtm
#                for elem in to_be_removed_from_rtm:
#                    map (lambda x: self.rtm.tasks.delete(timeline = timeline, \
#                            list_id = rtm_task_id_to_list_id[x], \
#                            taskseries_id = rtm_task_id_to_taskseries_id[x], \
#                            task_id = x), to_be_removed_from_rtm)
#
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
#        self.update_status("Synchronization completed")
#
#        self.update_progressbar(1.0)
#        
#    def update_progressbar(self,percent):
#        self.this_plugin.progressbar_percent = percent
#        gobject.idle_add(self.this_plugin.set_progressbar)
#    def update_status(self,status):
#        self.this_plugin.status = status
#        gobject.idle_add(self.this_plugin.set_status)
#
#
#
#
#
#
#
#        
#
#
#
#
#
#
