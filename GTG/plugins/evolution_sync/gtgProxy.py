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

from GTG.core.task import Task
from GTG.plugins.evolution_sync.gtgTask import GtgTask
from GTG.plugins.evolution_sync.genericProxy import GenericProxy


class GtgProxy(GenericProxy):

    def __init__(self, plugin_api):
        super(GtgProxy, self).__init__()
        self.plugin_api = plugin_api
        self.requester = self.plugin_api.get_requester()

    def generateTaskList(self):
        self._tasks_list = []
        requester = self.plugin_api.get_requester()
        statuses = [Task.STA_ACTIVE, Task.STA_DISMISSED, Task.STA_DONE]
        tasks = map(self.plugin_api.get_task, \
                     requester.get_tasks_list(status = statuses))
        map(lambda task: self._tasks_list.append(GtgTask(task, \
                                        self.plugin_api, self)), tasks)

    def create_new_task(self, title, never_seen_before = True):
        new_gtg_local_task = self.requester.new_task(newtask=never_seen_before)
        new_task = GtgTask(new_gtg_local_task, self.plugin_api, self)
        new_task.title = title
        self._tasks_list.append(new_task)
        return new_task

    def delete_task(self, task):
        #NOTE: delete_task wants the internal gtg id, not the uuid
        id = task.get_gtg_task().get_id()
        self.requester.delete_task(id)

