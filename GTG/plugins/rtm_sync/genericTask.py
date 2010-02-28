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
    """GenericTask is the abstract interface that represents a generic task."""

    def __init__(self, proxy):
        self.__proxy = proxy

    def __str__(self):
        return "Task " + self.title + "(" + self.id + ")"

    def toString(self):
        return "Task:\n" + \
                "\t - Title:    " + self.title         + "\n" + \
                "\t - ID:       " + self.id            + "\n" + \
                "\t - Modified: " + str(self.modified) + "\n" + \
                "\t - Due:      " + str(self.due_date) + "\n" 

    def copy(self, task):
        #Minimizing the number of actions will allow a faster RTM plugin
        # (where GET is fast, but SET is slow)
        if self.title != task.title:
            self.title = task.title
        if self.text != task.text:
            self.text = task.text
        if self.status != task.status:
            self.status = task.status
        if self.due_date != task.due_date:
            self.due_date = task.due_date
        #we'll let the tasks object decide what to do with tags
        self.tags = task.tags

    def get_proxy(self):
        return self.__proxy

    title = property(lambda self: self._get_title(),
                     lambda self, arg: self._set_title(arg))

    id = property(lambda self: self._get_id())

    text = property(lambda self: self._get_text(),
                     lambda self, arg: self._set_text(arg))

    status = property(lambda self: self._get_status(),
                     lambda self, arg: self._set_status(arg))

    modified = property(lambda self: self._get_modified())

    due_date = property(lambda self: self._get_due_date(),
                     lambda self, arg: self._set_due_date(arg))

    tags = property(lambda self: self._get_tags(),
                     lambda self, arg: self._set_tags(arg))

    self = property(lambda self: self)
