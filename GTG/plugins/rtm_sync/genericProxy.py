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

class GenericProxy(object):

    def __init__(self):
        super(GenericProxy, self).__init__()
        self._tasks_list = []

    def get_tasks_list(self):
        return self._tasks_list

    def generateTaskList(self):
        raise NotImplementedError()

    def create_new_task(self, title):
        raise NotImplementedError()

    def delete_task(self, task):
        raise NotImplementedError()

