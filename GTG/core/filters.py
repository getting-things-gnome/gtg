# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) - The GTG Team
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
# -----------------------------------------------------------------------------

"""Filters for tags and tasks"""

from gi.repository import Gtk # type: ignore[import-untyped]
from GTG.core.tags import Tag
from GTG.core.tasks import Task, Status
from GTG.core import search


def unwrap(row, expected_type):
    """Find an item in TreeRow widget (sometimes nested)."""

    item = row.get_item()

    while type(item) is not expected_type:
        item = item.get_item()

    return item


class TagEmptyFilter(Gtk.Filter):
    __gtype_name__ = 'TagEmptyFilter'

    def __init__(self, ds, pane):
        super(TagEmptyFilter, self).__init__()
        self.ds = ds
        self.pane = pane
        self.show_zero = True


    def do_match(self, item) -> bool:
        tag = unwrap(item, Tag)

        if self.pane == 'open_view':
            return self.show_zero or tag.task_count_open > 0

        elif self.pane == 'closed_view':
            return self.show_zero or tag.task_count_closed > 0

        elif self.pane == 'actionable_view':
            return (self.show_zero or tag.task_count_actionable > 0) and tag.actionable

        else:
            return True



class TaskFilter(Gtk.Filter):
    __gtype_name__ = 'TaskFilter'

    def __init__(self, ds, pane) -> None:
        super(TaskFilter, self).__init__()
        self.ds = ds
        self.query = ''
        self.checks = None
        self.pane : str = pane
        self.tags: list[Tag] = []
        self.only_untagged = False


    def allow_untagged_only(self) -> None:
        self.tags = []
        self.only_untagged = True
        self.changed(Gtk.FilterChange.DIFFERENT)


    def set_required_tags(self,tags: list[Tag]) -> None:
        self.tags = tags
        self.only_untagged = False
        self.changed(Gtk.FilterChange.DIFFERENT)


    def set_pane(self,pane: str) -> None:
        self.pane = pane
        self.changed(Gtk.FilterChange.DIFFERENT)


    def set_query(self, query: str) -> None:
        self.query = query

        try:
            self.checks = search.parse_search_query(query)
        except search.InvalidQuery:
            self.checks = None

        self.changed(Gtk.FilterChange.DIFFERENT)


    def match_tags(self, task: Task) -> bool:
        """Match selected tags to task tags."""
        for tag in self.tags:
            matching_tags = set(tag.get_matching_tags())
            if set(task.tags).isdisjoint(matching_tags):
                return False
        return True


    def is_task_matched_by_pane(self,task: Task) -> bool:
        """Return true if and only if the current pane does not filter out the task."""
        if self.pane == 'active':
            return task.status is Status.ACTIVE
        elif self.pane == 'workview':
            return task.is_actionable
        elif self.pane == 'closed':
            return task.status is not Status.ACTIVE
        raise Exception("Unknown pane: " + self.pane)


    def is_task_matched_by_tags(self,task: Task) -> bool:
        """Return true if and only if the selected tag filtering option does not filter out the task."""
        if self.only_untagged:
            return len(task.tags) == 0
        return self.match_tags(task)


    def is_task_matched_by_query(self,task:Task) -> bool:
        """Return true if and only if the search query does not filter out the task."""
        return search.search_filter(task, self.checks)


    def do_match(self, item) -> bool:
        task = item if isinstance(item, Task) else unwrap(item, Task)
        return (self.is_task_matched_by_pane(task)
                and self.is_task_matched_by_tags(task)
                and self.is_task_matched_by_query(task))
