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
import evolution

from GTG.core.task import Task

#Add this file's directory to the path used to search for libraries
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evolutionTask import EvolutionTask
from genericProxy import GenericProxy


class EvolutionProxy(GenericProxy):
    
    __GTG_STATUSES = [Task.STA_ACTIVE,
                   Task.STA_DONE,
                   Task.STA_DISMISSED]

    __EVO_STATUSES = [evolution.ecal.ICAL_STATUS_CONFIRMED,
                   evolution.ecal.ICAL_STATUS_COMPLETED,
                   evolution.ecal.ICAL_STATUS_CANCELLED]

    def __init__(self):
        super(EvolutionProxy, self).__init__()

    def generateTaskList(self):
        task_personal = evolution.ecal.list_task_sources()[0][1]
        self._evolution_tasks = evolution.ecal.open_calendar_source(task_personal,
                                   evolution.ecal.CAL_SOURCE_TYPE_TODO)
        self._gtg_to_evo_status = dict(zip(self.__GTG_STATUSES,
                                            self.__EVO_STATUSES))
        self._evo_to_gtg_status = dict(zip(self.__EVO_STATUSES,
                                            self.__GTG_STATUSES))
        #Need to find a solution for the statuses GTG doesn't expect:
        for evo_status in [evolution.ecal.ICAL_STATUS_DRAFT,
                           evolution.ecal.ICAL_STATUS_FINAL,
                           evolution.ecal.ICAL_STATUS_INPROCESS,
                           evolution.ecal.ICAL_STATUS_NEEDSACTION,
                           evolution.ecal.ICAL_STATUS_NONE,
                           evolution.ecal.ICAL_STATUS_TENTATIVE,
                           evolution.ecal.ICAL_STATUS_X]:
            self._evo_to_gtg_status[evo_status] = Task.STA_ACTIVE
        self._tasks_list = []
        for task in self._evolution_tasks.get_all_objects():
            self._tasks_list.append(EvolutionTask(task, self))

    def create_new_task(self, title):
        task = evolution.ecal.ECalComponent(ical=evolution.ecal.CAL_COMPONENT_TODO)
        self._evolution_tasks.add_object(task)
        new_task = EvolutionTask(task, self)
        new_task.title = title
        self._tasks_list.append(new_task)
        return new_task

    def delete_task(self, task):
        evo_task = task.get_evolution_task()
        self._evolution_tasks.remove_object(evo_task)
        self._evolution_tasks.update_object(evo_task)

    def update_task(self, task):
        evo_task = task.get_evolution_task()
        self._evolution_tasks.update_object(evo_task)
