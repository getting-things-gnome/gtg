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

class GenericTask(object):
    """GenericTask is the abstract interface that represents a generic task.
    GtgTask and RtmTask are the implementation of this"""

    title = property(lambda self: self._get_title(),
                     lambda self,arg: self._set_title(arg)) 

    id = property(lambda self: self._get_id())

    description = property(lambda self: self._get_description(),
                     lambda self,arg: self._set_description(arg)) 

    modified = property(lambda self: self._get_modified())

    due = property(lambda self: self._get_due(),
                     lambda self,arg: self._set_due(arg)) 

    tags = property(lambda self: self._get_tags(),
                     lambda self,arg: self._set_tags(arg)) 
    
    def __str__(self):
        return "Task " + self.title + "(" + self.id + ")"



class RtmTask (GenericTask):

    def __init__(self, task, list_id, taskseries_id):
        super(RtmTask, self).__init__()
        self.task = task
        self.list_id = list_id
        self.taskseries_id = taskseries_id

    def _get_title(self):
        return self.task.name

    def _set_title(self, title):
        #TODO
        pass

    def _get_id(self):
        return self.task.id


class GtgTask (GenericTask):

    def __init__(self, task):
        super(GtgTask, self).__init__()
        self.task = task

    def _get_title(self):
        return self.task.get_title()

    def _set_title(self, title):
        self.task.set_title(title)

    def _get_id(self):
        return self.task.get_id()
