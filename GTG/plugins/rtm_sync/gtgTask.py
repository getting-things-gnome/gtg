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
import datetime

from GTG.tools.dates import NoDate, RealDate

#Add this file's directory to the path used to search for libraries
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from genericTask import GenericTask

class GtgTask(GenericTask):

    def __init__(self, gtg_task, plugin_api, gtg_proxy):
        super(GtgTask, self).__init__(gtg_proxy)
        self._gtg_task = gtg_task
        self.plugin_api = plugin_api

    def _get_title(self):
        return self._gtg_task.get_title()

    def _set_title(self, title):
        self._gtg_task.set_title(title)

    def _get_id(self):
        return self._gtg_task.get_uuid()

    def _get_tags(self):
        return [t.get_name() for t in self._gtg_task.get_tags()]

    def _set_tags(self, tags):
        other_tags = []
        for tag in tags:
            if tag[0] != '@':
                tag = '@' + tag
            other_tags.append(tag)
        gtg_tags = self._gtg_task.get_tags()
        gtg_tags_lower = [t.get_name().lower() for t in gtg_tags]
        gtg_tags_set = set(gtg_tags_lower)
        other_tags_set = set([t.lower() for t in other_tags])
        #tags to remove
        for tag in gtg_tags_set.difference(other_tags_set):
            self._gtg_task.remove_tag(tag)
        #tags to add
        for tag in other_tags_set.difference(gtg_tags_set):
            gtg_all_tags = [t.get_name() for t in \
                            self.plugin_api.get_requester().get_all_tags()]
            matching_tags = filter(lambda t: t.lower() == tag, gtg_all_tags)
            if len(matching_tags) !=  0:
                tag = matching_tags[0]
            self._gtg_task.add_tag(tag)

    def _get_text(self):
        return self._gtg_task.get_excerpt(strip_tags = True, \
                                          strip_subtasks = True)
    def _set_text(self, text):
        #fill in subtasks
        self._gtg_task.set_text(text)

    def _set_status(self, status):
        self._gtg_task.set_status(status)

    def _get_status(self):
        return self._gtg_task.get_status()

    def _get_due_date(self):
        due_date = self._gtg_task.get_due_date()
        if due_date == NoDate():
                return None
        return due_date.to_py_date()

    def _set_due_date(self, due):
        if due == None:
            gtg_due = NoDate()
        else:
            gtg_due = RealDate(due)
        self._gtg_task.set_due_date(gtg_due)

    def _get_modified(self):
        modified = self._gtg_task.get_modified()
        if modified == None or modified == "":
            return None
        return self.__time_gtg_to_datetime(modified)

    def get_gtg_task(self):
        return self._gtg_task

    def __time_gtg_to_datetime(self, string):
        #FIXME: need to handle time with TIMEZONES!
        string = string.split('.')[0].split('Z')[0]
        if string.find('T') == -1:
            return datetime.datetime.strptime(string.split(".")[0], "%Y-%m-%d")
        return datetime.datetime.strptime(string.split(".")[0], \
                                          "%Y-%m-%dT%H:%M:%S")
