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

"""Sorters for tags and tasks."""

from gi.repository import Gtk, GObject, Gdk
from GTG.core.tasks2 import Task2

def unwrap(row, expected_type):
    """Find an item in TreeRow widget (sometimes nested)."""
    
    item = row
    
    while type(item) is not expected_type:
        item = item.get_item()

    return item


class TaskTitleSorter(Gtk.Sorter):
    __gtype_name__ = 'TaskTitleSorter'

    def __init__(self):
        super(TaskTitleSorter, self).__init__()


    def do_compare(self, a, b) -> Gtk.Ordering:
        
        a = unwrap(a, Task2)
        b = unwrap(b, Task2)

        first = a.title[-1]
        second = b.title[-1]

        if first > second:
            return Gtk.Ordering.LARGER
        elif first < second:
            return Gtk.Ordering.SMALLER
        else:
            return Gtk.Ordering.EQUAL


class TaskDueSorter(Gtk.Sorter):
    __gtype_name__ = 'DueSorter'

    def __init__(self):
        super(TaskDueSorter, self).__init__()


    def do_compare(self, a, b) -> Gtk.Ordering:
        
        a = unwrap(a, Task2)
        b = unwrap(b, Task2)

        first = a.date_due
        second = b.date_due

        if first > second:
            return Gtk.Ordering.LARGER
        elif first < second:
            return Gtk.Ordering.SMALLER
        else:
            return Gtk.Ordering.EQUAL


class TaskStartSorter(Gtk.Sorter):
    __gtype_name__ = 'StartSorter'

    def __init__(self):
        super(TaskStartSorter, self).__init__()


    def do_compare(self, a, b) -> Gtk.Ordering:
        
        a = unwrap(a, Task2)
        b = unwrap(b, Task2)

        first = a.date_start
        second = b.date_start

        if first > second:
            return Gtk.Ordering.LARGER
        elif first < second:
            return Gtk.Ordering.SMALLER
        else:
            return Gtk.Ordering.EQUAL


class TaskModifiedSorter(Gtk.Sorter):
    __gtype_name__ = 'ModifiedSorter'

    def __init__(self):
        super(TaskModifiedSorter, self).__init__()


    def do_compare(self, a, b) -> Gtk.Ordering:
        
        a = unwrap(a, Task2)
        b = unwrap(b, Task2)

        first = a.date_modified
        second = b.date_modified

        if first > second:
            return Gtk.Ordering.LARGER
        elif first < second:
            return Gtk.Ordering.SMALLER
        else:
            return Gtk.Ordering.EQUAL


class TaskTagSorter(Gtk.Sorter):
    __gtype_name__ = 'TagSorter'

    def __init__(self):
        super(TaskTagSorter, self).__init__()


    def get_first_letter(self, tags) -> str:
        """Get first letter of the first tag in a set of tags."""
        
        # Fastest way to get the first item
        # on a set in Python
        for t in tags:
            return t.name[0]

    def do_compare(self, a, b) -> Gtk.Ordering:
        
        a = unwrap(a, Task2)
        b = unwrap(b, Task2)

        if a.tags:
            first = self.get_first_letter(a.tags)
        else:
            first = 'zzzzzzz'

        if b.tags:
            second = self.get_first_letter(b.tags)
        else:
            second = 'zzzzzzz'

        if first > second:
            return Gtk.Ordering.LARGER
        elif first < second:
            return Gtk.Ordering.SMALLER
        else:
            return Gtk.Ordering.EQUAL


class TaskAddedSorter(Gtk.Sorter):
    __gtype_name__ = 'AddedSorter'

    def __init__(self):
        super(TaskAddedSorter, self).__init__()


    def do_compare(self, a, b) -> Gtk.Ordering:
        
        a = unwrap(a, Task2)
        b = unwrap(b, Task2)

        first = a.date_added
        second = b.date_added

        if first > second:
            return Gtk.Ordering.LARGER
        elif first < second:
            return Gtk.Ordering.SMALLER
        else:
            return Gtk.Ordering.EQUAL

