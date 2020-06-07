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


from gi.repository import Gtk, Pango

from GTG.core.task import Task
from GTG.gtk.colors import background_color
from GTG.core.requester import Requester
from webbrowser import open as openurl


class SubTaskTag(Gtk.TextTag):
    """Subtask Text tag."""


    def __init__(self, task: Task) -> None:
        super().__init__()

        self.tid = task.tid

        self.set_property('background', 'white')
        self.set_property('underline', Pango.Underline.SINGLE)
        self.set_property('left-margin', 40)

        if task.status == Task.STA_ACTIVE:
            self.set_property('strikethrough', False)
            self.set_property('foreground', '#007bff')
        else:
            self.set_property('strikethrough', True)
            self.set_property('foreground', 'gray')

        self.connect('event', self.on_tag)


    def on_tag(self, tag, view, event, _iter) -> None:
        """Callback for events that happen inside the tag."""

        button = event.get_button()

        # If there was a click...
        if button[0] and button[1] == 1:
            view.open_subtask_cb(self.tid)


    def activate(self, view) -> None:
        """Open the link in this tag."""

        view.open_subtask(self.tid)


    def set_hover(self) -> None:
        """Change tag appareance when hovering."""

        self.set_property('background', 'light gray')


    def reset(self) -> None:
        """Reset tag appareance when not hovering."""

        self.set_property('background', 'white')


class InvisibleTag(Gtk.TextTag):
    """Subtask Text tag."""


    def __init__(self) -> None:
        super().__init__()

        self.set_property('invisible', True)
        self.set_property('left-margin', 40)
        self.set_property('foreground', '#111111')
        self.set_property('background', '#DDDDDD')


    def set_hover(self) -> None:
        """Change tag appareance when hovering."""

        self.set_property('invisible', False)


    def reset(self) -> None:
        """Reset tag appareance when not hovering."""

        self.set_property('invisible', True)


class InternalLinkTag(Gtk.TextTag):
    """Internal Link Text tag (for urls)."""


    def __init__(self, task: Task) -> None:
        super().__init__()

        self.tid = task.tid

        self.set_property('background', 'white')
        self.set_property('underline', Pango.Underline.SINGLE)

        if task.status == Task.STA_ACTIVE:
            self.set_property('strikethrough', False)
            self.set_property('foreground', '#007bff')
        else:
            self.set_property('strikethrough', True)
            self.set_property('foreground', 'gray')

        self.connect('event', self.on_tag)


    def on_tag(self, tag, view, event, _iter) -> None:
        """Callback for events that happen inside the tag."""

        button = event.get_button()

        # If there was a click...
        if button[0] and button[1] == 1:
            view.open_subtask_cb(self.tid)


    def activate(self, view) -> None:
        """Open the link in this tag."""

        view.open_subtask_cb(self.tid)

    def set_hover(self) -> None:
        """Change tag appareance when hovering."""

        self.set_property('background', 'light gray')


    def reset(self) -> None:
        """Reset tag appareance when not hovering."""

        self.set_property('background', 'white')


class LinkTag(Gtk.TextTag):
    """Link Text tag (for urls)."""


    def __init__(self, url: str) -> None:
        super().__init__()

        self.url = url

        self.set_property('background', 'white')
        self.set_property('foreground', '#007bff')
        self.set_property('underline', Pango.Underline.SINGLE)
        self.set_property('strikethrough', False)

        self.connect('event', self.on_tag)


    def on_tag(self, tag, view, event, _iter) -> None:
        """Callback for events that happen inside the tag."""

        button = event.get_button()

        # If there was a click...
        if button[0]:

            # Left click
            if button[1] == 1:
                openurl(self.url)

            # Right click
            elif button[1] == 3:
                view.clicked_link = self.url


    def activate(self, view) -> None:
        """Open the link in this tag."""

        openurl(self.url)


    def set_hover(self) -> None:
        """Change tag appareance when hovering."""

        self.set_property('background', 'light gray')


    def reset(self) -> None:
        """Reset tag appareance when not hovering."""

        self.set_property('background', 'white')


class TitleTag(Gtk.TextTag):
    """Title Text tag (only one per buffer)."""


    def __init__(self) -> None:
        super().__init__()

        self.set_property('weight', Pango.Weight.BOLD)
        self.set_property('size_points', 16)
        self.set_property('pixels_above_lines', 15)
        self.set_property('pixels_below_lines', 30)


class TaskTagTag(Gtk.TextTag):
    """Text tag for task tags."""


    def __init__(self, tag: str, req: Requester) -> None:
        super().__init__()

        self.tag_name = tag
        self.tag = req.get_tag(tag)

        try:
            self.color = background_color([self.tag]) or'#FFEA00'
        except AttributeError:
            self.color = '#FFEA00'

        self.set_property('background', self.color)
        self.set_property('foreground', 'black')

        self.connect('event', self.on_tag)


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


    def on_tag(self, tag, view, event, _iter) -> None:
        """Callback for events that happen inside the tag."""

        button = event.get_button()

        if button[0] and button[1] == 1:
            view.browse_tag_cb(self.tag_name)


    def activate(self, view) -> None:
        """Open the link in this tag."""

        view.browse_tag_cb(self.tag_name)
