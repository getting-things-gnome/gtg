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


from gi.repository import GObject # type: ignore[import-untyped]

from uuid import UUID
import logging

from lxml.etree import _Element
from typing import Dict, Optional, TypeVar, Generic
from typing_extensions import Self


log = logging.getLogger(__name__)

S = TypeVar('S',bound='StoreItem')

class StoreItem(GObject.Object):
    """Base class for items in BaseStore."""

    __gtype_name__ = 'gtg_StoreItem'


    def __init__(self,id: UUID):
        self.id: UUID = id
        self.parent: Optional[Self] = None
        self.children: list[Self] = []
        super().__init__()


    @GObject.Property(type=int)
    def children_count(self) -> int:
        """Read only property."""
        return len(self.children)


    @GObject.Property(type=bool, default=False)
    def has_children(self) -> bool:
        return len(self.children) > 0


    def add_child(self,child:Self):
        """Add an item as child if not yet present."""
        if child in self.children:
            return
        self.children.append(child)
        self.notify('children_count')
        if len(self.children) == 1:
            self.notify('has_children')


    def remove_child(self,child:Self):
        """Remove a child item if present."""
        if child not in self.children:
            return
        self.children.remove(child)
        self.notify('children_count')
        if len(self.children) == 0:
            self.notify('has_children')


    def get_ancestors(self) -> list[Self]:
        """Return all ancestors of this tag"""
        ancestors: list[Self] = []
        here = self
        while here.parent:
            here = here.parent
            ancestors.append(here)
        return ancestors


    def is_parentable_to(self, target) -> bool:
        """Check for parenting an item to its own descendant or to itself."""
        return self != target and self not in target.get_ancestors()



class BaseStore(GObject.Object,Generic[S]):
    """Base class for data stores."""


    def __init__(self) -> None:
        self.lookup: Dict[UUID, S] = {}
        self.data: list[S] = []

        super().__init__()

    # --------------------------------------------------------------------------
    # BASIC MANIPULATION
    # --------------------------------------------------------------------------

    def new(self) -> S:
        """Creates a new item in the store.
        NOTE: Subclasses may override the signature of this method.
        """
        raise NotImplementedError


    def get(self, key: UUID) -> S:
        """Get an item by id."""

        return self.lookup[key]


    def add(self, item: S, parent_id: Optional[UUID] = None) -> None:
        """Add an existing item to the store."""

        if item.id in self.lookup.keys():
            log.warning('Failed to add item with id %s, already added!',
                        item.id)
            raise KeyError

        if parent_id and parent_id not in self.lookup:
            log.warning(('Failed to add item with id %s to parent %s, '
                         'parent not found!'), item.id, parent_id)
            raise KeyError

        if parent_id:
            self.lookup[parent_id].add_child(item)
            item.parent = self.lookup[parent_id]
        else:
            self.data.append(item)

        self.lookup[item.id] = item
        self.emit('added', item)
        log.debug('Added %s', item)


    @GObject.Signal(name='added', arg_types=(object,))
    def add_signal(self, *_):
        """Signal to emit when adding a new item."""


    @GObject.Signal(name='removed', arg_types=(object,))
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
        children_ids = [ c.id for c in item.children ]

        for cid in children_ids:
            self.remove(cid)

        if parent:
            parent.remove_child(item)
        else:
            self.data.remove(item)
        del self.lookup[item_id]

        self.emit('removed', item)


    def batch_remove(self,item_ids: list[UUID]) -> None:
        """Remove multiple items, ensuring nothing gets deleted twice"""
        for key in item_ids:
            if key in self.lookup:
                self.remove(key)


    # --------------------------------------------------------------------------
    # PARENTING
    # --------------------------------------------------------------------------

    def parent(self, item_id: UUID, parent_id: UUID) -> None:
        """Add a child to an item."""

        if item_id not in self.lookup:
            raise KeyError("item_id is not in store: "+str(item_id))
        if parent_id not in self.lookup:
            raise KeyError("parent_id is not in store: "+str(parent_id))

        item = self.lookup[item_id]
        item.parent = self.lookup[parent_id]

        self.data.remove(item)
        self.lookup[parent_id].add_child(item)
        self.emit('parent-change', item, self.lookup[parent_id])


    def unparent(self, item_id: UUID) -> None:
        """Remove child item from its parent (if exists)."""
        if item_id not in self.lookup:
            raise KeyError("item_id is not in store: "+str(item_id))
        if self.lookup[item_id].parent is None:
            return

        child = self.lookup[item_id]
        parent = child.parent
        assert parent is not None

        parent.remove_child(child)
        self.data.append(child)
        child.parent = None

        self.emit('parent-removed',child,parent)


    # --------------------------------------------------------------------------
    # SERIALIZING
    # --------------------------------------------------------------------------

    def from_xml(self, xml: _Element) -> None:
        """Load data from XML.
        NOTE: Subclasses may override the signature of this method.
        """
        raise NotImplementedError


    def to_xml(self) -> _Element:
        raise NotImplementedError


    # --------------------------------------------------------------------------
    # UTILITIES
    # --------------------------------------------------------------------------

    def count(self, root_only: bool = False) -> int:
        """Count all the items in the store."""

        if root_only:
            return len(self.data)
        else:
            return len(self.lookup)


    def refresh_lookup_cache(self) -> None:
        """Refresh lookup cache."""

        def add_children(nodes) -> None:
            """Recursively add children to lookup."""

            for n in nodes:
                self.lookup[n.id] = n

                if n.children:
                    add_children(n.children)


        self.lookup.clear()
        add_children(self.data)


    def print_list(self) -> None:
        """Print the entre list of items."""

        print(self)

        for node in self.lookup.values():
            print(f'- {node}')


    def print_tree(self) -> None:
        """Print the all the items as a tree."""

        def recursive_print(tree: list, indent: int) -> None:
            """Inner print function. """

            tab =  '   ' * indent if indent > 0 else ''

            for node in tree:
                print(f'{tab} └ {node}')

                if node.children:
                    recursive_print(node.children, indent + 1)

        print(self)
        recursive_print(self.data, 0)
