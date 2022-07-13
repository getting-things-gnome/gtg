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
from GTG.core.tags2 import Tag2


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
        tag = unwrap(item, Tag2)
        
        return self.ds.task_count[self.pane].get(tag.name, False)
