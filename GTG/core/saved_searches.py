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

"""Everything related to saved searches."""


from gi.repository import GObject, Gio # type: ignore[import-untyped]

from uuid import uuid4, UUID
from typing import Optional
import logging

from lxml.etree import Element, _Element, SubElement

from GTG.core.base_store import BaseStore, StoreItem

log = logging.getLogger(__name__)


class SavedSearch(StoreItem):
    """A saved search."""

    __gtype_name__ = 'gtg_SavedSearch'


    def __init__(self, id: UUID, name: str, query: str) -> None:
        self._name = name
        self._query = query
        self._icon : Optional[str] = None

        super().__init__(id)

    @GObject.Property(type=str)
    def name(self) -> str:
        """Read only property."""

        return self._name

    @name.setter
    def set_name(self, value: str) -> None:
        self._name = value


    @GObject.Property(type=str)
    def icon(self) -> Optional[str]:
        """Read only property."""

        return self._icon


    @icon.setter
    def set_icon(self, value: str) -> None:
        self._icon = value


    @GObject.Property(type=str)
    def query(self) -> str:
        """Read only property."""

        return self._query


    @query.setter
    def set_query(self, value: str) -> None:
        self._query = value


    def __str__(self) -> str:
        """String representation."""

        return f'Saved Search: {self.name} ({self.id})'


    def __repr__(self) -> str:
        """String representation."""

        return (f'Saved Search "{self.name}" '
                f'with query "{self.query}" and id "{self.id}"')


    def __eq__(self, other) -> bool:
        """Equivalence."""

        return self.id == other.id


class SavedSearchStore(BaseStore):
    """A list of saved searches."""

    __gtype_name__ = 'gtg_SavedSearchStore'

    #: Tag to look for in XML
    XML_TAG = 'savedSearch'

    def __init__(self) -> None:
        super().__init__()

        self.model = Gio.ListStore.new(SavedSearch)


    def __str__(self) -> str:
        """String representation."""

        return f'Saved Search Store. Holds {len(self.lookup)} search(es)'


    def find(self, name: str) -> Optional[SavedSearch]:
        """Get a saved search by name."""

        for search in self.data:
            if search.name == name:
                return search
        return None


    def from_xml(self, xml: _Element) -> None:
        """Load searches from an LXML element."""

        elements = list(xml.iter(self.XML_TAG))

        for element in elements:

            search_id = UUID(element.get('id'))
            name = element.get('name')
            assert name is not None, "Missing 'name' property for saved search "+str(search_id)
            query = element.get('query')
            assert query is not None, "Missing 'query' property for saved search "+str(search_id)

            search = SavedSearch(id=search_id, name=name, query=query)

            self.add(search)
            log.debug('Added %s', search)


    def to_xml(self) -> _Element:
        """Save searches to an LXML element."""

        root = Element('searchlist')

        for search in self.lookup.values():
            element = SubElement(root, self.XML_TAG)
            element.set('id', str(search.id))
            element.set('name', search.name)
            element.set('query', search.query)

        return root


    def new(self, name: str, query: str, parent: Optional[UUID] = None) -> SavedSearch: # type: ignore[override]
        """Create a new saved search and add it to the store."""

        search_id = uuid4()
        search = SavedSearch(id=search_id, name=name, query=query)

        if not self.find(name):
            self.data.append(search)
            self.lookup[search_id] = search
            self.model.append(search)

        return search


    def add(self, item, parent_id: Optional[UUID] = None) -> None:
        """Add a saved search to the store."""

        super().add(item, parent_id)
        self.model.append(item)

        self.emit('added', item)


    def remove(self, item_id: UUID) -> None:
        """Remove an existing saved search."""

        # Remove from UI
        item = self.lookup[item_id]
        pos = self.model.find(item)
        self.model.remove(pos[1])

        super().remove(item_id)
