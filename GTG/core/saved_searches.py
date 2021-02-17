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

from gi.repository import GObject

from uuid import uuid4
from dataclasses import dataclass, field
import logging

from lxml.etree import Element, SubElement
from typing import List


log = logging.getLogger(__name__)


class SavedSearch(GObject.Object):
    """A saved search."""

    def __init__(self, id: uuid4, name: str, query: str) -> None:
        self.id = id
        self.name = name
        self.query = query

        self.icon = None
        self.children = []


    def __str__(self) -> str:
        """String representation."""

        return f'Saved Search: {self.name} ({self.id})'


    def __repr__(self) -> str:
        """String representation."""

        return (f'Saved Search "{self.name}" '
                f'with query "{self.query}" and id "{self.id}"')


class SavedSearchStore:
    """A list of saved searches."""

    #: Tag to look for in XML
    XML_TAG = 'savedSearch'


    def __init__(self) -> None:
        self.lookup = {}
        self.data = []


    def __str__(self) -> str:
        """String representation."""

        return f'Saved Search Store. Holds {len(self.lookup)} search(es)'


    def from_xml(self, xml: Element) -> 'SavedSearchStore':
        """Load searches from an LXML element."""

        elements = list(xml.iter(self.XML_TAG))

        # Do parent searches first
        for element in elements.copy():
            parent = element.get('parent')

            # Note: Previous versions of GTG stored saved searches as
            # tags with a "search" parent, and this stuck for a while
            # after the file format changed.
            if parent and parent != 'search':
                continue

            search_id = element.get('id')
            name = element.get('name')
            query = element.get('query')

            search = SavedSearch(id=search_id, name=name, query=query)

            self.add(search)
            log.debug('Added %s', search)
            elements.remove(element)


        # Now the remaining searches are children
        for element in elements:
            parent = element.get('parent')
            sid = element.get('id')
            name = element.get('name')
            query = element.get('query')

            search = SavedSearch(sid=sid, name=name, query=query)
            self.add_child(parent, search)
            log.debug('Added %s as child of %s', search, parent)


    def to_xml(self) -> Element:
        """Save searches to an LXML element."""

        root = Element('SavedSearches')

        parent_map = {}

        for search in self.data:
            for child in search.children:
                parent_map[child.id] = search.id

        for search in self.lookup.values():
            element = SubElement(root, self.XML_TAG)
            element.set('id', str(search.id))
            element.set('name', search.name)
            element.set('query', search.query)

            try:
                element.set('parent', parent_map[search.id])
            except KeyError:
                pass

        return root


    def get(sid: str) -> SavedSearch:
        """Get a saved search by id."""

        return self.lookup[sid]


    def new(self, name: str, query: str, parent: uuid4 = None) -> SavedSearch:
        """Create a new saved search and add it to the store."""

        search_id = uuid4()
        search = SavedSearch(id=search_id, name=name, query=query)

        if parent:
            self.add_child(parent, search)
        else:
            self.data.append(search)
            self.lookup[search_id] = search

        return search


    def add(self, search: SavedSearch, parent: uuid4 = None) -> None:
        """Add an existing search to the store."""

        if search.sid in self.lookup.keys():
            log.warn('Failed to add saved search with id %s, already added!',
                     search.sid)
            raise KeyError

        if parent:
            try:
                parent_search = self.lookup[parent]
            except TypeError:
                log.warn(('Passed the wrong type as parent: ', type(parent)))

                if hasattr(parent, 'sid'):
                    parent_search = self.lookup[parent.sid]
                else:
                    log.warn('Could not add saved search')
                raise

            try:
                parent_search.children.append(search)
            except AttributeError:
                log.warn(('Failed to add search with id %s to parent %s, '
                         'parent not found!'), search.sid, parent)
                raise

        else:
            self.data.append(search)

        self.lookup[search.sid] = search
        log.debug('Added %s', search)


    def remove(self, sid: uuid4) -> None:
        """Remove an existing search from the store."""

        try:
            for search in self.data:
                if search.sid == sid:
                    for child in search.children:
                        search.children.remove(child)
                        del self.lookup[child.sid]

                    self.data.remove(search)

            del self.lookup[sid]

            log.debug('Removed saved search with id %s', sid)

        except KeyError:
            log.warn('Failed to remove saved search %s, id not found!', sid)
            raise


    def add_child(self, parent: uuid4, search: SavedSearch) -> None:
        """Add a child to a search."""

        try:
            self.lookup[parent].children.append(search)
            self.lookup[search.sid] = search

        except KeyError:
            raise


    def remove_child(self, parent: uuid4, sid: uuid4) -> None:
        """Remove child search from a parent."""

        for s in self.lookup[parent].children:
            if s.sid == sid:
                self.lookup[parent].children.remove(s)
                del self.lookup[s.sid]
                return

        raise KeyError


    def count(self, root_only: bool = False) -> int:
        """Count all the searches in the store."""

        if root_only:
            return len(self.data)
        else:
            return len(self.lookup)


    def print_list(self) -> None:
        """Print the entre list of searches."""

        print(self)

        for search in self.lookup.values():
            print((f'- "{search.name}" with query "{search.query}" '
                   f'and id "{search.sid}"'))


    def print_tree(self) -> None:
        """Print the all the searches as a tree."""

        def recursive_print(tree: List, indent: int) -> None:
            """Inner print function. """

            tab =  '   ' * indent if indent > 0 else ''

            for node in tree:
                print(f'{tab} └ {node}')

                if node.children:
                    recursive_print(node.children, indent + 1)

        print(self)
        recursive_print(self.data, 0)

