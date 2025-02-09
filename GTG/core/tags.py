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


from gi.repository import GObject, Gtk, Gio, Gdk # type: ignore[import-untyped]

from uuid import uuid4, UUID
import logging
import random
import re

from lxml.etree import Element, SubElement, _Element
from typing import Dict, List, Set, Optional

from GTG.core.base_store import BaseStore, StoreItem

log = logging.getLogger(__name__)


def extract_tags_from_text(text):
    """ Given a string, returns a list of the @tags contained in that """

    return re.findall(r'(?:^|[\s])(@[\w\/\.\-\:\&]*\w)', text)


class Tag(StoreItem):
    """A tag that can be applied to a Task."""

    __gtype_name__ = 'gtg_Tag'

    def __init__(self, id: UUID, name: str) -> None:
        self._name = name

        self._icon: Optional[str] = None
        self._color: Optional[str] = None
        self.actionable = True

        self._task_count_open = 0
        self._task_count_actionable = 0
        self._task_count_closed = 0

        super().__init__(id)


    def __str__(self) -> str:
        """String representation."""

        return f'Tag: {self.name} ({self.id})'


    def __repr__(self) -> str:
        """String representation."""

        return (f'Tag "{self.name}" with id "{self.id}"')


    def __eq__(self, other) -> bool:
        """Equivalence."""

        return self.id == other.id




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
        self.notify('has-icon')


    @GObject.Property(type=str)
    def color(self) -> Optional[str]:
        """Read only property."""

        return self._color


    @color.setter
    def set_color(self, value: str) -> None:
        self._color = value
        self.notify('has-color')


    @GObject.Property(type=bool, default=False)
    def has_color(self) -> bool:

        return (self._color is not None) and (self._icon is None)


    @GObject.Property(type=bool, default=False)
    def has_icon(self) -> bool:

        return self._icon is not None


    @GObject.Property(type=int, default=0)
    def task_count_open(self) -> int:

        return self._task_count_open


    @task_count_open.setter
    def set_task_count_open(self, value: int) -> None:
        self._task_count_open = value


    @GObject.Property(type=int, default=0)
    def task_count_actionable(self) -> int:

        return self._task_count_actionable


    @task_count_actionable.setter
    def set_task_count_actionable(self, value: int) -> None:
        self._task_count_actionable = value


    @GObject.Property(type=int, default=0)
    def task_count_closed(self) -> int:

        return self._task_count_closed


    @task_count_closed.setter
    def set_task_count_closed(self, value: int) -> None:
        self._task_count_closed = value


    def get_matching_tags(self) -> List['Tag']:
        """Return the tag with its descendants."""
        matching = [self]
        for c in self.children:
            matching += c.get_matching_tags()
        return matching


    def __hash__(self):
        return id(self)


class TagStore(BaseStore[Tag]):
    """A tree of tags."""

    __gtype_name__ = 'gtg_TagStore'


    #: Tag to look for in XML
    XML_TAG = 'tag'


    def __init__(self) -> None:
        self.used_colors: Set[str] = set()
        self.lookup_names: Dict[str, Tag] = {}
        self.tid_to_children_model: Dict[UUID,Gio.ListStore] = dict()

        super().__init__()


        self.model = Gio.ListStore.new(Tag)
        self.tree_model = Gtk.TreeListModel.new(self.model, False, False, self.model_expand)


    def model_expand(self, item):
        model = Gio.ListStore.new(Tag)

        if type(item) == Gtk.TreeListRow:
            item = item.get_item()

        # open the first one
        if item.children:
            for child in item.children:
                model.append(child)

        self.tid_to_children_model[item.id] = model
        return Gtk.TreeListModel.new(model, False, False, self.model_expand)


    def __str__(self) -> str:
        """String representation."""

        return f'Tag Store. Holds {len(self.lookup)} tag(s)'

    def get_all_tag_names(self) -> List[str]:
        """Return all tag names."""
        return list(self.lookup_names.keys())


    def find(self, name: str) -> Tag:
        """Get a tag by name."""

        return self.lookup_names[name]


    def new(self, name: str, parent: Optional[UUID] = None) -> Tag: # type: ignore[override]
        """Create a new tag and add it to the store."""

        name = name if not name.startswith('@') else name[1:]

        try:
            return self.lookup_names[name]
        except KeyError:
            tid = uuid4()
            tag = Tag(id=tid, name=name)

            if parent:
                self.add(tag, parent)
            else:
                self.add(tag)

            self.emit('added', tag)
            return tag


    def from_xml(self, xml: _Element) -> None:
        """Load searches from an LXML element."""

        elements = list(xml.iter(self.XML_TAG))

        # Do parent searches first
        for element in elements.copy():

            tid = element.get('id')
            name = element.get('name')
            color = element.get('color')
            icon = element.get('icon')
            nonactionable = element.get('nonactionable') or 'False'

            if color:
                if not color.startswith('#'):
                    color = '#' + color

                rgb = Gdk.RGBA()
                rgb.parse(color)
                red = int(rgb.red * 255)
                blue = int(rgb.blue * 255)
                green = int(rgb.green * 255)
                color = '#{:02x}{:02x}{:02x}'.format(red, green, blue)

            tag = Tag(id=UUID(tid), name=str(name))
            tag.color = color
            tag.icon = icon
            tag.actionable = (nonactionable == 'False')

            self.add(tag)

            log.debug('Added %s', tag)


        for element in elements:
            child_id: UUID = UUID(element.get('id'))
            hex_parent_id: Optional[str] = element.get('parent')
            if hex_parent_id is None:
                continue

            try:
                parent_id: UUID = UUID(hex_parent_id)
            except ValueError:
                log.debug('Malformed parent UUID: %s', tag, hex_parent_id)
                continue

            try:
                self.parent(child_id, parent_id)
                log.debug('Added %s as child of %s', tag, hex_parent_id)
            except KeyError:
                log.debug('Failed to add %s as child of %s', tag, hex_parent_id)


    def to_xml(self) -> _Element:
        """Save searches to an LXML element."""

        root = Element('taglist')

        parent_map = {}

        for tag in self.lookup.values():
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


            element.set('nonactionable', str(not tag.actionable))

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


    def _remove_from_parent_model(self,tag_id: UUID) -> None:
        """
        Remove the tag indicated by tag_id from the model of its parent's children.
        This is required to trigger a GUI update.
        """
        item = self.lookup[tag_id]
        if item.parent is None:
            return
        if item.parent.id not in self.tid_to_children_model:
            return
        model = self.tid_to_children_model[item.parent.id]
        pos = model.find(item)
        if pos[0]:
            model.remove(pos[1])


    def _append_to_parent_model(self,tag_id: UUID) -> None:
        """
        Appends the tag indicated by tag_id to the model of its parent's children.
        This is required to trigger a GUI update.
        """
        item = self.lookup[tag_id]
        if item.parent is None:
            return
        if item.parent.id not in self.tid_to_children_model:
            return
        model = self.tid_to_children_model[item.parent.id]
        pos = model.find(item)
        if not pos[0]:
            model.append(item)


    def add(self, item: Tag, parent_id: Optional[UUID] = None) -> None:
        """Add a tag to the tagstore."""

        super().add(item, parent_id)
        self.lookup_names[item.name] = item

        # Update UI
        if not parent_id:
            self.model.append(item)
        else:
            self._append_to_parent_model(item.id)

        self.emit('added', item)
        if parent_id:
            self.lookup[parent_id].notify('children_count')


    def remove(self, item_id: UUID) -> None:
        """Remove an existing tag."""

        item = self.lookup[item_id]
        parent = item.parent

        # Remove from UI
        if item.parent is not None:
            self._remove_from_parent_model(item.id)
        else:
            pos = self.model.find(item)
            self.model.remove(pos[1])

        super().remove(item_id)
        if parent:
            self.lookup[parent.id].notify('children_count')


    def parent(self, item_id: UUID, parent_id: UUID) -> None:

        item = self.lookup[item_id]

        # Remove from UI
        if item.parent is not None:
            old_parent = item.parent
            self._remove_from_parent_model(item_id)
            self.lookup[old_parent.id].notify('children_count')
        else:
            pos = self.model.find(item)
            self.model.remove(pos[1])

        super().parent(item_id, parent_id)

        # Add back to UI
        self._append_to_parent_model(item_id)
        self.lookup[parent_id].notify('children_count')


    def unparent(self, item_id: UUID) -> None:

        item = self.lookup[item_id]
        parent = item.parent
        if parent is None:
            return

        # Remove from UI
        self._remove_from_parent_model(item_id)

        super().unparent(item_id)

        # Add back to UI
        self.model.append(item)

        parent.notify('children_count')
