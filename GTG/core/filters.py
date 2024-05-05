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

from gi.repository import Gtk, GObject, Gdk
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


    def do_match(self, item) -> bool:
        tag = unwrap(item, Tag)

        if self.pane == 'open':
            return tag.task_count_open > 0

        elif self.pane == 'closed':
            return tag.task_count_closed > 0

        elif self.pane == 'workview':
            return tag.task_count_actionable > 0 and tag.actionable

        else:
            return True


class TaskPaneFilter(Gtk.Filter):
    __gtype_name__ = 'TaskPaneFilter'

    def __init__(self, ds, pane, tags = [], no_tags=False):
        super(TaskPaneFilter, self).__init__()
        self.ds = ds
        self.pane = pane
        self.tags = set()
        self.no_tags = no_tags
        self.expand = False


    def expand_tags(self) -> set:
        """Expand tags to include their children."""

        def get_children(children: set) -> None:
            for child in children:
                result.add(child)

                if child.children:
                    get_children(child.children)


        result = set()

        for tag in self.tags:
            result.add(tag)

            if tag.children:
                get_children(tag.children)

        return result


    def match_tags(self, task: Task) -> bool:
        """Match selected tags to task tags."""

        all_tags = self.expand_tags()
        return len(all_tags.intersection(set(task.tags))) >= len(self.tags)


    def do_match(self, item) -> bool:
        task = unwrap(item, Task)

        if self.pane == 'active':
            show = task.status is Status.ACTIVE
        elif self.pane == 'workview':
            show = task.is_actionable

            if self.expand:
                item.set_expanded(True)
                self.expand = False

        elif self.pane == 'closed':
            show = task.status is not Status.ACTIVE

        if show:
            if self.no_tags:
                current = not task.tags
                return current or any(bool(c.tags) for c in task.children)
            elif self.tags:
                current = self.match_tags(task)
                return current or any(self.match_tags(c) for c in task.children)
            else:
                return True
        else:
            return False


class SearchTaskFilter(Gtk.Filter):
    __gtype_name__ = 'SearchTaskFilter'

    def __init__(self, ds, pane):
        super(SearchTaskFilter, self).__init__()
        self.ds = ds
        self.query = ''
        self.checks = None
        self.pane = pane
        self.expand = False
        self.tags = set()


    def set_query(self, query: str) -> None:
        self.query = query

        try:
            self.checks = search.parse_search_query(query)
        except search.InvalidQuery:
            self.checks = None


    def match_tags(self, task: Task) -> bool:
        """Match selected tags to task tags."""

        return len(self.tags.intersection(set(task.tags))) >= len(self.tags)


    def do_match(self, item) -> bool:
        task = unwrap(item, Task)

        if self.pane == 'active':
            show = task.status is Status.ACTIVE
        elif self.pane == 'workview':
            show = task.is_actionable
            if self.expand:
                item.set_expanded(True)
                self.expand = False
        elif self.pane == 'closed':
            show = task.status is not Status.ACTIVE

        if show:
            if self.tags:
                current = self.match_tags(task)
                tag_show = current or any(self.match_tags(c) for c in task.children)

                return tag_show and search.search_filter(task, self.checks)

            return search.search_filter(task, self.checks)
        else:
            return False
