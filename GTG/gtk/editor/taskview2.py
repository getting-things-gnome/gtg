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

import re

from gi.repository import Gtk, Pango, GLib

from GTG.core.logger import log
from GTG.core.requester import Requester
from GTG.gtk.colors import background_color
import GTG.core.urlregex as url_regex

from enum import Enum

# Regex to find GTG's tags
TAG_REGEX = re.compile(r'\@\w+')


class TagType(Enum):
    """Custom Text tags for GTG."""

    LINK = 'Link'
    TASKTAG = 'Task Tag'
    TITLE = 'Title'


class LinkTag(Gtk.TextTag):
    """Link Text tag (for urls)."""

    TYPE = TagType.LINK

    def __init__(self, url: str) -> None:
        super().__init__()

        self.url = url

        self.set_property('background', 'white')
        self.set_property('foreground', '#007bff')
        self.set_property('underline', Pango.Underline.SINGLE)
        self.set_property('strikethrough', False)


class TitleTag(Gtk.TextTag):
    """Title Text tag (only one per buffer)."""

    TYPE = TagType.TITLE

    def __init__(self) -> None:
        super().__init__()

        self.set_property('weight', Pango.Weight.BOLD)
        self.set_property('size_points', 16)
        self.set_property('pixels_above_lines', 15)
        self.set_property('pixels_below_lines', 30)


class TaskTagTag(Gtk.TextTag):
    """Text tag for task tags."""

    TYPE = TagType.TASKTAG

    def __init__(self, tag: str, req: Requester) -> None:
        super().__init__()

        self.tag_name = tag

        try:
            self.color = background_color([req.get_tag(tag)])
        except AttributeError:
            self.color = '#FFEA00'

        self.set_property('background', self.color)
        self.set_property('foreground', 'black')


class TaskView(Gtk.TextView):
    """Taskview widget

    This is a specialized Gtk textview with GTG features. It waits [n] seconds
    after the user has modified the buffer and analyzes the contents to find
    the title, tags, etc. When found, it applies Gtk.TextTags to them.
    """

    # Requester
    req = None

    # Clipboard
    clipboard = None

    # Timeout in milliseconds
    PROCESSING_DELAY = 250

    # The timeout handler
    timeout = None

    # Handle ID for the modified signal handler
    id_modified = None

    def __init__(self, req: Requester, clipboard) -> None:
        super().__init__()

        self.req = req
        self.clipboard = clipboard

        # Basic textview setup
        self.set_left_margin(20)
        self.set_right_margin(20)
        self.set_wrap_mode(Gtk.WrapMode.WORD)
        self.set_editable(True)
        self.set_cursor_visible(True)

        # Tags and buffer setup
        self.buffer = self.get_buffer()
        self.buffer.set_modified(False)
        self.table = self.buffer.get_tag_table()

        self.title_tag = TitleTag()
        self.table.add(self.title_tag)

        # Signals and callbacks
        self.id_modified = self.buffer.connect('changed', self.on_modified)


    def on_modified(self, buffer: Gtk.TextBuffer) -> None:
        """Called every time the text buffer changes."""

        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = None

        self.timeout = GLib.timeout_add(self.PROCESSING_DELAY, self.process)


    def process(self) -> None:
        """Process the contents of the text buffer."""

        log.debug(f'Processing text buffer after {self.PROCESSING_DELAY} ms')

        start = self.detect_title()
        start.forward_line()

        # Parse the text line by line until the end of the buffer
        while not start.is_end():
            end = start.copy()
            end.forward_to_line_end()
            text = self.buffer.get_text(start, end, True)

            # Avoid empty new lines
            if text.startswith('\n'):
                start.forward_line()
                continue


            self.detect_url(text, start)
            self.detect_tag(text, start)

            start.forward_line()


        # Return False to only run the function once,
        # and clear the handle for next time.
        self.timeout = None
        return False


    def detect_tag(self, text: str, start: Gtk.TextIter) -> None:
        """Detect GTGs tags and applies text tags to them."""

        # Find all matches
        matches = re.finditer(TAG_REGEX, text)

        # Go through each with its own iterator and tag 'em
        for match in matches:
            tag_start = start.copy()
            tag_end = start.copy()

            tag_start.forward_chars(match.start())
            tag_end.forward_chars(match.end())

            # I find this confusing too :)
            tag_tag = TaskTagTag(match.group(0), self.req)

            self.table.add(tag_tag)
            self.buffer.apply_tag(tag_tag, tag_start, tag_end)



    def detect_url(self, text: str, start: Gtk.TextIter) -> None:
        """Detect URLs and apply tags."""

        # Find all matches
        matches = url_regex.search(text)

        # Go through each with its own iterator and tag 'em
        for match in matches:
            url_start = start.copy()
            url_end = start.copy()

            url_start.forward_chars(match.start())
            url_end.forward_chars(match.end())

            url_tag = LinkTag(match.group(0))

            self.table.add(url_tag)
            self.buffer.apply_tag(url_tag, url_start, url_end)


    def detect_title(self) -> Gtk.TextIter:
        """Apply title tag to the first line."""

        start = self.buffer.get_start_iter()

        # Don't do anything if the task is empty
        if start.is_end():
            return

        # If the task starts with something that isn't a word (like
        # whitespace or returns), then move forward until we hit a word.
        while not start.starts_word():
            start.forward_char()

        end = start.copy()
        end.forward_to_line_end()
        buffer_end = self.buffer.get_end_iter()

        # Set the tag to the first line and remove it everywhere below
        self.buffer.apply_tag(self.title_tag, start, end)
        self.buffer.remove_tag(self.title_tag, end, buffer_end)

        return end
