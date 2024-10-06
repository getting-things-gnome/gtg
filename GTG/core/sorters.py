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

from gi.repository import Gtk # type: ignore[import-untyped]
from GTG.core.tasks import Task

def unwrap(row, expected_type):
    """Find an item in TreeRow widget (sometimes nested)."""

    item = row

    while type(item) is not expected_type:
        item = item.get_item()

    return item

class ReversibleSorter(Gtk.Sorter):

    def __init__(self) -> None:
        self._reverse: bool = False
        super().__init__()


    @property
    def reverse(self) -> bool:
        return self._reverse


    @reverse.setter
    def reverse(self, value: bool) -> None:
        self._reverse = value
        self.changed(Gtk.SorterChange.INVERTED)


    def reversible_compare(self, first, second) -> Gtk.Ordering:
        """Compare for reversible sorters."""

        if first == second:
            return Gtk.Ordering.EQUAL

        if first < second:
            if self._reverse:
                return Gtk.Ordering.LARGER
            else:
                return Gtk.Ordering.SMALLER

        if self._reverse:
            return Gtk.Ordering.SMALLER
        else:
            return Gtk.Ordering.LARGER


class TaskTitleSorter(ReversibleSorter):
    __gtype_name__ = 'TaskTitleSorter'

    def do_compare(self, a, b) -> Gtk.Ordering:

        a = unwrap(a, Task)
        b = unwrap(b, Task)

        first = a.title[0]
        second = b.title[0]

        return self.reversible_compare(first, second)


class TaskDueSorter(ReversibleSorter):
    __gtype_name__ = 'DueSorter'

    def do_compare(self, a, b) -> Gtk.Ordering:

        a = unwrap(a, Task)
        b = unwrap(b, Task)

        first = a.date_due
        second = b.date_due

        return self.reversible_compare(first, second)


class TaskStartSorter(ReversibleSorter):
    __gtype_name__ = 'StartSorter'

    def do_compare(self, a, b) -> Gtk.Ordering:

        a = unwrap(a, Task)
        b = unwrap(b, Task)

        first = a.date_start
        second = b.date_start

        return self.reversible_compare(first, second)


class TaskModifiedSorter(ReversibleSorter):
    __gtype_name__ = 'ModifiedSorter'

    def do_compare(self, a, b) -> Gtk.Ordering:

        a = unwrap(a, Task)
        b = unwrap(b, Task)

        first = a.date_modified
        second = b.date_modified

        return self.reversible_compare(first, second)


class TaskTagSorter(ReversibleSorter):
    __gtype_name__ = 'TagSorter'

    def get_first_letter(self, tags) -> str:
        """Get first letter of the first tag in a set of tags."""

        # Fastest way to get the first item
        # on a set in Python
        for t in tags:
            return t.name[0]

    def do_compare(self, a, b) -> Gtk.Ordering:

        a = unwrap(a, Task)
        b = unwrap(b, Task)

        if a.tags:
            first = self.get_first_letter(a.tags)
        else:
            first = 'zzzzzzz'

        if b.tags:
            second = self.get_first_letter(b.tags)
        else:
            second = 'zzzzzzz'

        return self.reversible_compare(first, second)


class TaskAddedSorter(ReversibleSorter):
    __gtype_name__ = 'AddedSorter'

    def do_compare(self, a, b) -> Gtk.Ordering:

        a = unwrap(a, Task)
        b = unwrap(b, Task)

        first = a.date_added
        second = b.date_added

        return self.reversible_compare(first, second)
