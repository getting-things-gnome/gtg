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

class TaskStr:
    '''
    This class is a wrapper around the classic GTG.core.task.Task. It provides
    access to the task various attributes directly via python attributes
    instead of method calls. This makes writing Cheetah templates easier
    '''

    def __init__(self,
                 title,
                 text,
                 subtasks,
                 status,
                 modified,
                 due_date,
                 closed_date,
                 start_date,
                 days_left,
                 tags,
                ):
        self.title         = title
        self.text          = text
        self.subtasks      = subtasks
        self.status        = status
        self.modified      = modified
        self.due_date      = due_date
        self.closed_date   = closed_date
        self.start_date    = start_date
        self.days_left     = days_left
        self.tags          = tags
    has_title         = property(lambda s: s.title       != "")
    has_text          = property(lambda s: s.text        != "")
    has_subtasks      = property(lambda s: s.subtasks    != [])
    has_status        = property(lambda s: s.status      != "")
    has_modified      = property(lambda s: s.modified    != "")
    has_due_date      = property(lambda s: s.due_date    != "")
    has_closed_date   = property(lambda s: s.closed_date != "")
    has_start_date    = property(lambda s: s.start_date  != "")
    has_days_left     = property(lambda s: s.days_left   != "")
    has_tags          = property(lambda s: s.tags        != [])

def TaskStr_factory(task):
    '''
    Creates a TaskStr object given a gtg task
    '''
    return TaskStr(title = task.get_title(),
                   text        = str(task.get_text()),
                   subtasks    = [],
                   status      = task.get_status(),
                   modified    = str(task.get_modified_string()),
                   due_date    = str(task.get_due_date()),
                   closed_date = str(task.get_closed_date()),
                   start_date  = str(task.get_start_date()),
                   days_left   = str(task.get_days_left()),
                   tags        = [t.get_name() for t in task.get_tags()])

def tree_to_TaskStr(tree, nodes, plugin_api, days = None):
    """This function performs a depth-first tree visits on a tree 
        using the given nodes as root. For each node of the tree it
        encounters, it generates a TaskStr object and returns that.
        The resulting TaskStr will be linked to its subtasks in the
        same way as the tree"""
    tasks_str = []
    for node_id in nodes:
        task = plugin_api.get_requester().get_task(node_id)
        #The task_str is added to the result only if it satisfies the time
        # limit imposed with the @days parameter of this function
        if days and not _is_task_in_timespan(task, days):
            continue
        task_str = TaskStr_factory(task)
        tasks_str.append(task_str)
        children = tree.node_all_children(node_id)
        task_str.subtasks = tree_to_TaskStr(tree,
                                            children,
                                            plugin_api,
                                            days)
    return tasks_str

def _is_task_in_timespan(task, days):
    '''If days < 0, returns True if the task has been closed in the last
    #abs(days). If days >= 0, returns True if the task is due in the next
    #days'''
    return (days < 0 and task.get_closed_date() and \
                (task.get_closed_date().days_left() >= days)) or \
           (days >= 0 and (task.get_days_left() <= days))

