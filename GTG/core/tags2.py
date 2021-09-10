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

"""Everything related to tags."""


from gi.repository import GObject

from uuid import uuid4, UUID
import logging
import random

from lxml.etree import Element, SubElement
from typing import Any, Dict, Set

from GTG.core.base_store import BaseStore

log = logging.getLogger(__name__)


class Tag2(GObject.Object):
    """A tag that can be applied to a Task."""

    __gtype_name__ = 'gtg_Tag'
    __slots__ = ['id', 'name', 'icon', 'color', 'actionable', 'children']


    def __init__(self, id: UUID, name: str) -> None:
        self.id = id
        self.name = name

        self.icon = None
        self.color = None
        self.actionable = True
        self.children = []
        self.parent = None


    def __str__(self) -> str:
        """String representation."""

        return f'Tag: {self.name} ({self.id})'


    def __repr__(self) -> str:
        """String representation."""

        return (f'Tag "{self.name}" with id "{self.id}"')


    def __eq__(self, other) -> bool:
        """Equivalence."""

        return self.id == other.id


class TagStore(BaseStore):
    """A tree of tags."""

    __gtype_name__ = 'gtg_TagStore'


    #: Tag to look for in XML
    XML_TAG = 'tag'


    def __init__(self) -> None:
        self.used_colors: Set[Color] = set()
        self.lookup_names: Dict[str, Tag2] = {}

        super().__init__()


    def __str__(self) -> str:
        """String representation."""

        return f'Tag Store. Holds {len(self.lookup)} tag(s)'


    def find(self, name: str) -> Tag2:
        """Get a tag by name."""

        return self.lookup_names[name]


    def new(self, name: str, parent: UUID = None) -> Tag2:
        """Create a new tag and add it to the store."""

        name = name if not name.startswith('@') else name[1:]

        try:
            return self.lookup_names[name]
        except KeyError:
            tid = uuid4()
            tag = Tag2(id=tid, name=name)

            if parent:
                self.add(tag, parent)
            else:
                self.data.append(tag)
                self.lookup[tid] = tag
                self.lookup_names[name] = tag

            self.emit('added', tag)
            return tag


    def from_xml(self, xml: Element) -> None:
        """Load searches from an LXML element."""

        elements = list(xml.iter(self.XML_TAG))

        # Do parent searches first
        for element in elements.copy():

            tid = element.get('id')
            name = element.get('name')
            color = element.get('color')
            icon = element.get('icon')

            tag = Tag2(id=tid, name=name)
            tag.color = color
            tag.icon = icon

            self.add(tag)

            log.debug('Added %s', tag)


        for element in elements:
            parent_name = element.get('parent')

            if parent_name:
                tid = element.get('id')

                try:
                    parent = self.find(parent_name)
                    self.parent(tid, parent.id)
                    log.debug('Added %s as child of %s', tag, parent)
                except KeyError:
                    pass


    def to_xml(self) -> Element:
        """Save searches to an LXML element."""

        root = Element('taglist')

        parent_map = {}

        for tag in self.data:
            for child in tag.children:
                parent_map[child.id] = tag.id

        for tag in self.lookup.values():
            element = SubElement(root, self.XML_TAG)
            element.set('id', str(tag.id))
            element.set('name', tag.name)

            if tag.color:
                element.set('color', tag.color)

            if tag.icon:
                element.set('icon', tag.icon)

            try:
                element.set('parent', str(parent_map[tag.id]))
            except KeyError:
                pass

        return root


    def generate_color(self) -> str:
        """Generate a random color that isn't already used."""

        def rand_color() -> str:
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
             
            return f'#{r:02x}{g:02x}{b:02x}'

        color = rand_color()

        while color in self.used_colors:
            color = rand_color()

        self.used_colors.add(color)
        return color


    def add(self, item: Any, parent_id: UUID = None) -> None:
        """Add a tag to the tagstore."""

        super().add(item, parent_id)
        self.lookup_names[item.name] = item
        self.emit('added', item)
