# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) The GTG Team
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

"""Base for all store classes."""


from gi.repository import GObject

from uuid import UUID
import logging

from lxml.etree import Element
from typing import List, Any, Dict


log = logging.getLogger(__name__)


class BaseStore(GObject.Object):
    """Base class for data stores."""


    def __init__(self) -> None:
        self.lookup: Dict[UUID, Any] = {}
        self.data: List[Any] = []

        super().__init__()

    # --------------------------------------------------------------------------
    # BASIC MANIPULATION
    # --------------------------------------------------------------------------

    def new(self) -> Any:
        raise NotImplemented


    def get(self, key: str) -> Any:
        """Get an item by id."""

        return self.lookup[key]


    def add(self, item: Any, parent_id: UUID = None) -> None:
        """Add an existing item to the store."""

        if item.id in self.lookup.keys():
            log.warn('Failed to add item with id %s, already added!',
                     item.id)

            raise KeyError

        if parent_id:
            try:
                self.lookup[parent_id].children.append(item)
                item.parent = self.lookup[parent_id]

            except KeyError:
                log.warn(('Failed to add item with id %s to parent %s, '
                         'parent not found!'), item.id, parent_id)
                raise

        else:
            self.data.append(item)

        self.lookup[item.id] = item
        log.debug('Added %s', item)


    @GObject.Signal(name='added', arg_types=(object,))
    def add_signal(self, *_):
        """Signal to emit when adding a new item."""


    @GObject.Signal(name='removed', arg_types=(str,))
    def remove_signal(self, *_):
        """Signal to emit when removing a new item."""


    @GObject.Signal(name='parent-change', arg_types=(object, object))
    def parent_change_signal(self, *_):
        """Signal to emit when an item parent changes."""


    @GObject.Signal(name='parent-removed', arg_types=(object, object))
    def parent_removed_signal(self, *_):
        """Signal to emit when an item's parent is removed."""


    def remove(self, item_id: UUID) -> None:
        """Remove an existing item from the store."""

        item = self.lookup[item_id]
        parent = item.parent

        for child in item.children:
            del self.lookup[child.id]

        if parent:
            parent.children.remove(item)
            del self.lookup[item_id]
        else:
            self.data.remove(item)
            del self.lookup[item_id]

        self.emit('removed', str(item_id))


    # --------------------------------------------------------------------------
    # PARENTING
    # --------------------------------------------------------------------------

    def parent(self, item_id: UUID, parent_id: UUID) -> None:
        """Add a child to an item."""

        try:
            item = self.lookup[item_id]
        except KeyError:
            raise

        try:
            self.data.remove(item)
            self.lookup[parent_id].children.append(item)
            item.parent = self.lookup[parent_id]

            self.emit('parent-change', item, self.lookup[parent_id])
        except KeyError:
            raise


    def unparent(self, item_id: UUID, parent_id: UUID) -> None:
        """Remove child item from a parent."""

        for child in self.lookup[parent_id].children:
            if child.id == item_id:
                self.data.append(child)
                self.lookup[parent_id].children.remove(child)
                child.parent = None

                self.emit('parent-removed',
                          self.lookup[item_id],
                          self.lookup[parent_id])
                return

        raise KeyError


    # --------------------------------------------------------------------------
    # SERIALIZING
    # --------------------------------------------------------------------------

    def from_xml(self, xml: Element) -> Any:
        raise NotImplemented


    def to_xml(self) -> Element:
        raise NotImplemented


    # --------------------------------------------------------------------------
    # UTILITIES
    # --------------------------------------------------------------------------

    def count(self, root_only: bool = False) -> int:
        """Count all the items in the store."""

        if root_only:
            return len(self.data)
        else:
            return len(self.lookup)


    def print_list(self) -> None:
        """Print the entre list of items."""

        print(self)

        for node in self.lookup.values():
            print(f'- {node}')


    def print_tree(self) -> None:
        """Print the all the items as a tree."""

        def recursive_print(tree: List, indent: int) -> None:
            """Inner print function. """

            tab =  '   ' * indent if indent > 0 else ''

            for node in tree:
                print(f'{tab} └ {node}')

                if node.children:
                    recursive_print(node.children, indent + 1)

        print(self)
        recursive_print(self.data, 0)
