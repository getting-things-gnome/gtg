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
import sys
import os
# IMPORTANT This add's the plugin's path to python sys path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generic_task import GtgTask
from generic_proxy import GenericProxy


class GtgProxy(GenericProxy):

    def __init__(self, plugin_api):
        super(GtgProxy, self).__init__()
        self.plugin_api = plugin_api

    def generateTaskList(self):
        tasks = map(self.plugin_api.get_task, \
                     self.plugin_api.get_requester().get_active_tasks_list())
        map(lambda task: self.task_list.append(GtgTask(task, \
                                        self.plugin_api)), tasks)

    def newTask(self, title, never_seen_before):
        new_task = GtgTask(self.plugin_api.get_requester().new_task(
                             newtask=never_seen_before), self.plugin_api)
        new_task.title = title
        self.task_list.append(new_task)
        return new_task
