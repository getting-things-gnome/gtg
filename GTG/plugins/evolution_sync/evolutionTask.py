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
import time
import datetime

#Add this file's directory to the path used to search for libraries
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from genericTask import GenericTask


class EvolutionTask(GenericTask):

    def __init__(self, evo_task, evolution_proxy):
        super(EvolutionTask, self).__init__(evolution_proxy)
        self._evo_task = evo_task

    def _get_title(self):
        return self._evo_task.get_summary()

    def _set_title(self, title):
        self._evo_task.set_summary(title)
        self.get_proxy().update_task(self)

    def _get_id(self):
        return self._evo_task.get_uid()

    def _get_tags(self):
        #We could use Evolution's "Categories" as tags
        raise NotImplementedError()

    def _set_tags(self, tags):
        raise NotImplementedError()
        self.get_proxy().update_task(self)

    def _get_text(self):
        desc = self._evo_task.get_description()
        if desc == None:
            return ""
        return desc

    def _set_text(self, text):
        self._evo_task.set_description(text)
        self.get_proxy().update_task(self)

    def _set_status(self, status):
        #Since Evolution's statuses are fare more than GTG's,
        # we need to check that the current status is not one of the various
        # statuses translated in the same gtg status, passed by argument.
        # This way, we avoid to force a status change when it's not needed 
        # (and not wanted)
        current_status_in_gtg_terms = self.get_proxy()._evo_to_gtg_status[\
                                                   self._evo_task.get_status()]
        if current_status_in_gtg_terms != status:
            new_evo_status = self.get_proxy()._gtg_to_evo_status[status]
            self._evo_task.set_status(new_evo_status)
            self.get_proxy().update_task(self)

    def _get_status(self):
        status = self._evo_task.get_status()
        return self.get_proxy()._evo_to_gtg_status[status]

    def _get_due_date(self):
        due = self._evo_task.get_due()
        if isinstance(due, (int, float)):
            return self.__time_evo_to_date(due)

    def _set_due_date(self, due):
        if due == None:
            #TODO: I haven't find a way to reset the due date
            # We could copy the task, but that would lose all the attributes
            # currently not supported by the library used (and they're a lot)
            pass
        else:
            self._evo_task.set_due(self.__time_date_to_evo(due))
        self.get_proxy().update_task(self)

    def _get_modified(self):
        return self.__time_evo_to_datetime(self._evo_task.get_modified())

    def __time_evo_to_date(self, timestamp):
        return datetime.datetime.fromtimestamp(timestamp + time.timezone).date()

    def __time_evo_to_datetime(self, timestamp):
        return datetime.datetime.fromtimestamp(timestamp)

    def __time_datetime_to_evo(self, timeobject):
        return int(time.mktime(timeobject.timetuple()))

    def __time_date_to_evo(self, timeobject):
        #NOTE: need to substract the timezone to avoid the "one day before bug
        # (at the airport => no internet now, need to fill bug number in)
        #Explanation: gtg date format is converted to datetime in date/00:00 in 
        # local time, and time.mktime considers that when converting to UNIX
        # time. Evolution, however, doesn't convert back to local time.
        return self.__time_datetime_to_evo(timeobject) - time.timezone

    def get_evolution_task(self):
        return self._evo_task
