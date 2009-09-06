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
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))+'/pyrtm')
import rtm

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

    def copy (self, task):
        self.title = task.title
        self.tags = task.tags



class RtmTask (GenericTask):

    def __init__(self, task, list_id, taskseries_id, rtm, timeline):
        super(RtmTask, self).__init__()
        self.rtm = rtm
        self.timeline = timeline
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

    def _get_tags(self):
        if hasattr(self.task.tags,'tag'):
            if type (self.task.tags.tag) ==list:
                return self.task.tags.tag
            else:
                return [self.task.tags.tag]
        elif hasattr(self.task.tags,'list'):
            return map(lambda x: x.tag if hasattr(x,'tag') else None, \
                       self.task.tags.list)
            return ["ciao"]
        return []

    def _set_tags (self, tags):
#        print tags
#        self.rtm.tasks.setTags(timeline=self.timeline, list_id =self.list_id,\
#                   taskseries_id=self.taskseries_id,task_id=self.id,tags=tags)
        pass


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

    def _get_tags (self):
        return self.task.get_tags()

    def _set_tags (self, tags):
        #NOTE: isn't there a better mode than removing all tags?
        #      need to add function in GTG/core/task.py
        print tags
        old_tags = self.tags
        for tag in old_tags:
            self.task.remove_tag(tag)
        map (lambda tag: self.task.add_tag('@'+tag), tags)
