# -*- coding: utf-8 -*-
# Copyright (c) 2009 - Luca Invernizzi <invernizzi.l@gmail.com>
#               2012 - Izidor Matušov <izidor.matusov@gmail.com>
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

""" Text representation of GTG task for easier work in templates """


class TaskStr(object):
    """ Wrapper around GTG Task.
    It provides access to the task various attributes directly via python
    attributes instead of method calls and makes writing Cheetah
    templates easier. """
    # Ignore big number of properties and small number of public methods

    def __init__(self, task, subtasks):
        self.title = task.get_title()
        self.text = str(task.get_text())
        self.status = task.get_status()
        self.modified = str(task.get_modified_string())
        self.due_date = str(task.get_due_date())
        self.closed_date = str(task.get_closed_date())
        self.start_date = str(task.get_start_date())
        self.days_left = str(task.get_days_left())
        self.tags = [t.get_id() for t in task.get_tags()]

        self.subtasks = subtasks

    has_title = property(lambda s: s.title != "")
    has_text = property(lambda s: s.text != "")
    has_subtasks = property(lambda s: s.subtasks != [])
    has_status = property(lambda s: s.status != "")
    has_modified = property(lambda s: s.modified != "")
    has_due_date = property(lambda s: s.due_date != "")
    has_closed_date = property(lambda s: s.closed_date != "")
    has_start_date = property(lambda s: s.start_date != "")
    has_days_left = property(lambda s: s.days_left != "")
    has_tags = property(lambda s: s.tags != [])


def get_task_wrappers(tree, days=None, task_id=None):
    """ Recursively find all task on given tree and
    convert them into TaskStr

    tree - tree of tasks
    days - filter days in certain timespan
    task_id - return subtasks of this tasks. If not set, use root node """

    def _is_in_timespan(task):
        """ Return True if days is not set.
        If days < 0, returns True if the task has been done in the last
        #abs(days).
        If days >= 0, returns True if the task is due in the next #days """
        if days is None:
            return True
        elif days < 0:
            done = task.get_status() == task.STA_DONE
            closed_date = task.get_closed_date()
            return done and closed_date and closed_date.days_left() >= days
        else:
            return task.get_days_left() <= days

    subtasks = []
    for sub_id in tree.node_all_children(task_id):
        subtask = get_task_wrappers(tree, days, sub_id)
        if subtask is not None:
            subtasks.append(subtask)

    if task_id is None:
        return subtasks
    else:
        task = tree.get_node(task_id)
        if task is None or not _is_in_timespan(task):
            return None

        return TaskStr(task, subtasks)
