# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) - The Getting Things GNOME Team
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

"""Specialized Gtk.TextTags used in the Taskview widget."""

from uuid import uuid4
from gi.repository import Gtk, Pango, Gdk

from GTG.core.datastore2 import Datastore2
from GTG.core.tasks2 import Status
from GTG.gtk.colors import background_color
from webbrowser import open as openurl

# ------------------------------------------------------------------------------
# COLORS
# ------------------------------------------------------------------------------

colors = {
    'link_active': '#007bff',
    'link_inactive': 'gray',
    'background_hover': 'light gray',
    'invisible': '#888888',
}


def use_dark_mode() -> None:
    """Change colors array to dark mode colors."""

    colors['link_active'] = '#6eb4ff'
    colors['link_inactive'] = 'gray'
    colors['background_hover'] = '#454545'
    colors['invisible'] = '#555555'


def use_light_mode() -> None:
    """Change colors array to light mode colors."""

    colors['link_active'] = '#007bff'
    colors['link_inactive'] = 'gray'
    colors['background_hover'] = 'light gray'
    colors['invisible'] = '#888888'


# ------------------------------------------------------------------------------
# TEXT TAGS
# ------------------------------------------------------------------------------

class SubTaskTag(Gtk.TextTag):
    """Subtask Text tag."""

    def __init__(self, tid: uuid4) -> None:
        super().__init__()

        self.tid = tid


class CheckboxTag(Gtk.TextTag):
    """Checkbox tag. Only used to detect when a checkbox has been deleted."""

    def __init__(self) -> None:
        super().__init__()


class InvisibleTag(Gtk.TextTag):
    """Subtask Text tag."""


    def __init__(self) -> None:
        super().__init__()

        self.set_property('invisible', True)
        self.set_property('foreground', colors['invisible'])
        self.set_property('size_points', 16)


    def set_cursor_hover(self) -> None:
        """Change tag appareance when hovering."""

        self.set_property('invisible', False)


    def cursor_reset(self) -> None:
        """Reset tag appareance when not hovering."""

        self.set_property('invisible', True)


class InternalLinkTag(Gtk.TextTag):
    """Internal Link Text tag (for urls)."""


    def __init__(self, tid: uuid4, status: str) -> None:
        super().__init__()

        self.tid = tid

        self.set_property('underline', Pango.Underline.SINGLE)

        if status == Status.ACTIVE:
            self.set_property('strikethrough', False)
            self.set_property('foreground', colors['link_active'])
        else:
            self.set_property('strikethrough', True)
            self.set_property('foreground', colors['link_inactive'])


    def do_clicked(self, view, button) -> None:
        """Externally called callback for clicks that happen inside the tag."""

        # If there was a click...
        if button == Gdk.BUTTON_PRIMARY:
            view.open_subtask_cb(self.tid)


    def activate(self, view) -> None:
        """Open the link in this tag."""

        view.open_subtask_cb(self.tid)

    def set_hover(self) -> None:
        """Change tag appareance when hovering."""

        self.set_property('background', colors['background_hover'])


    def reset(self) -> None:
        """Reset tag appareance when not hovering."""

        self.set_property('background', None)


class LinkTag(Gtk.TextTag):
    """Link Text tag (for urls)."""


    def __init__(self, url: str) -> None:
        super().__init__()

        self.url = url

        self.set_property('foreground', colors['link_active'])
        self.set_property('underline', Pango.Underline.SINGLE)
        self.set_property('strikethrough', False)


    def do_clicked(self, view, button) -> None:
        """Externally called callback for clicks that happen inside the tag."""

        # Left click
        if button == Gdk.BUTTON_PRIMARY:
            openurl(self.url)

        # Right click
        elif button == Gdk.BUTTON_SECONDARY:
            view.clicked_link = self.url


    def activate(self, view) -> None:
        """Open the link in this tag."""

        openurl(self.url)


    def set_hover(self) -> None:
        """Change tag appareance when hovering."""

        self.set_property('background', colors['background_hover'])


    def reset(self) -> None:
        """Reset tag appareance when not hovering."""

        self.set_property('background', None)


class TitleTag(Gtk.TextTag):
    """Title Text tag (only one per buffer)."""


    def __init__(self) -> None:
        super().__init__()

        self.set_property('weight', Pango.Weight.BOLD)
        self.set_property('size_points', 16)
        self.set_property('pixels_above_lines', 15)
        self.set_property('pixels_below_lines', 30)


class SubheadingTag(Gtk.TextTag):
    """Subheading Text tag."""


    def __init__(self) -> None:
        super().__init__()

        self.set_property('size_points', 14)
        self.set_property('pixels_above_lines', 25)
        self.set_property('pixels_below_lines', 10)


class TaskTagTag(Gtk.TextTag):
    """Text tag for task tags."""


    def __init__(self, tag: str, ds: Datastore2) -> None:
        super().__init__()

        self.tag_name = tag
        self.tag = ds.tags.lookup_names[tag]

        try:
            # In darkmode, where the backdrop itself is dark we want
            # to increase the brightness.
            self.color = background_color([self.tag], use_alpha=False) or '#FFEA00'
        except AttributeError:
            self.color = '#FFEA00'

        self.set_property('background', self.color)
        self.set_property('foreground', 'black')


    def set_hover(self) -> None:
        """Change tag appareance when hovering."""

        try:
            color = self.tag.get_attribute('color') or '#EBDB34'
            self.set_property('background', color)
        except AttributeError:
            self.set_property('background', '#EBDB34')


    def reset(self) -> None:
        """Reset tag appareance when not hovering."""

        self.set_property('background', self.color)


    def do_clicked(self, view, button) -> None:
        """Externally called callback for clicks that happen inside the tag."""

        if button == Gdk.BUTTON_PRIMARY:
            view.browse_tag_cb(self.tag_name)


    def activate(self, view) -> None:
        """Open the link in this tag."""

        view.browse_tag_cb(self.tag_name)
