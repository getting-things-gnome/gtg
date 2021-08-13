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


from gi.repository import GObject

from uuid import uuid4, UUID
from typing import Optional
import logging

from lxml.etree import Element, SubElement

from GTG.core.base_store import BaseStore

log = logging.getLogger(__name__)


class SavedSearch(GObject.Object):
    """A saved search."""

    __gtype_name__ = 'gtg_SavedSearch'
    __slots__ = ['id', 'name', 'query', 'icon', 'children']


    def __init__(self, id: UUID, name: str, query: str) -> None:
        self.id = id
        self.name = name
        self.query = query

        self.icon = None
        self.children = []
        self.parent = None


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


    def __str__(self) -> str:
        """String representation."""

        return f'Saved Search Store. Holds {len(self.lookup)} search(es)'


    def find(self, name: str) -> Optional[SavedSearch]:
        """Get a saved search by name."""

        for search in self.data:
            if search.name == name:
                return search


    def from_xml(self, xml: Element) -> None:
        """Load searches from an LXML element."""

        elements = list(xml.iter(self.XML_TAG))

        # Do parent searches first
        for element in elements:

            search_id = element.get('id')
            name = element.get('name')
            query = element.get('query')

            search = SavedSearch(id=search_id, name=name, query=query)

            self.add(search)
            log.debug('Added %s', search)


        for element in elements:
            parent_name = element.get('parent')

            if parent_name and parent_name != 'search':
                tid = element.get('id')

                parent = self.find(parent_name)

                if parent:
                    self.parent(tid, parent.id)
                    log.debug('Added %s as child of %s', element, parent)


    def to_xml(self) -> Element:
        """Save searches to an LXML element."""

        root = Element('searchlist')

        parent_map = {}

        for search in self.data:
            for child in search.children:
                parent_map[child.id] = search.name

        for search in self.lookup.values():
            element = SubElement(root, self.XML_TAG)
            element.set('id', str(search.id))
            element.set('name', search.name)
            element.set('query', search.query)

            try:
                element.set('parent', str(parent_map[search.id]))
            except KeyError:
                # Toplevel search
                pass

        return root


    def new(self, name: str, query: str, parent: UUID = None) -> SavedSearch:
        """Create a new saved search and add it to the store."""

        search_id = uuid4()
        search = SavedSearch(id=search_id, name=name, query=query)

        if parent:
            self.add(search, parent)
        else:
            self.data.append(search)
            self.lookup[search_id] = search

        return search
