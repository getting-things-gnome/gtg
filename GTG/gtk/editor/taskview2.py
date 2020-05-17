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
from time import time

from gi.repository import Gtk, Pango, GLib, Gdk

from GTG.core.logger import log
from GTG.core.requester import Requester
from GTG.gtk.colors import background_color
import GTG.core.urlregex as url_regex
from webbrowser import open as openurl
from GTG.core.translations import _

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


    def set_hover(self) -> None:
        """Change tag appareance when hovering."""

        self.set_property('background', 'light gray')


    def reset(self) -> None:
        """Reset tag appareance when not hovering."""

        self.set_property('background', 'white')


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
        self.tag = req.get_tag(tag)

        try:
            self.color = background_color([self.tag])
        except AttributeError:
            self.color = '#FFEA00'

        self.set_property('background', self.color)
        self.set_property('foreground', 'black')

        self.connect('event', self.on_tag)

    def set_hover(self) -> None:
        """Change tag appareance when hovering."""

        try:
            self.set_property('background', self.tag.get_attribute('color'))
        except AttributeError:
            self.set_property('background', '#EBDB34')


    def reset(self) -> None:
        """Reset tag appareance when not hovering."""

        self.set_property('background', self.color)


    def on_tag(self, tag, view, event, _iter) -> None:
        """Callback for events that happen inside the tag."""

        button = event.get_button()

        if button[0] and button[1] == 1:
            view.browse_tag(self.tag_name)


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

        # Mouse cursors
        self.cursor_hand = Gdk.Cursor.new(Gdk.CursorType.HAND2)
        self.cursor_normal = Gdk.Cursor.new(Gdk.CursorType.XTERM)

        # URL when right-clicking (used to populate RMB menu)
        self.clicked_link = None

        # Tag currently under the cursor
        self.hovered_tag = None

        # Tags and buffer setup
        self.buffer = self.get_buffer()
        self.buffer.set_modified(False)
        self.table = self.buffer.get_tag_table()

        self.title_tag = TitleTag()
        self.table.add(self.title_tag)
        self.tags = []


        # Task info
        self.data = {
            'title': '',
            'tags': ''
        }

        # Signals and callbacks
        self.id_modified = self.buffer.connect('changed', self.on_modified)
        self.connect('motion-notify-event', self.on_mouse_move)

        # Callback when tags are clicked
        self.browse_tag = NotImplemented


    def on_modified(self, buffer: Gtk.TextBuffer) -> None:
        """Called every time the text buffer changes."""

        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = None

        self.timeout = GLib.timeout_add(self.PROCESSING_DELAY, self.process)


    def process(self) -> None:
        """Process the contents of the text buffer."""

        log.debug(f'Processing text buffer after {self.PROCESSING_DELAY} ms')
        bench_start = time()

        # Clear all tags first
        [self.table.remove(t) for t in self.tags]
        self.tags = []

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

        log.debug(f'Processed in {time() - bench_start:.2} secs')

        # Return False to only run the function once,
        # and clear the handle for next time.
        self.timeout = None
        return False

    # --------------------------------------------------------------------------
    # DETECTION
    # --------------------------------------------------------------------------

    def detect_tag(self, text: str, start: Gtk.TextIter) -> None:
        """Detect GTGs tags and applies text tags to them."""

        # Find all matches
        matches = re.finditer(TAG_REGEX, text)
        self.data['tags'] = []

        # Go through each with its own iterator and tag 'em
        for match in matches:
            tag_start = start.copy()
            tag_end = start.copy()

            tag_start.forward_chars(match.start())
            tag_end.forward_chars(match.end())

            # I find this confusing too :)
            tag_tag = TaskTagTag(match.group(0), self.req)
            self.tags.append(tag_tag)

            self.table.add(tag_tag)
            self.buffer.apply_tag(tag_tag, tag_start, tag_end)
            self.data['tags'].append(match.group(0))



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
            self.tags.append(url_tag)

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

        self.data['title'] = self.buffer.get_text(start, end, True)

        return end

    # --------------------------------------------------------------------------
    # INTERACTIVITY
    # --------------------------------------------------------------------------

    def on_mouse_move(self, view, event) -> None:
        """Callback when the mouse moves."""

        # Get the tag at the X, Y coords of the mosue cursor
        window = event.window
        _unused, x, y, _unused = window.get_pointer()
        x, y = view.window_to_buffer_coords(Gtk.TextWindowType.TEXT, x, y)
        tags = view.get_iter_at_location(x, y)[1].get_tags()

        # Reset cursor and hover states
        window.set_cursor(self.cursor_normal)

        if self.hovered_tag:
            self.hovered_tag.reset()
            self.hovered_tag = None

        # Apply hover state if possible
        if tags:
            tag = tags[0]
            if tag.TYPE in {TagType.LINK, TagType.TASKTAG}:
                window.set_cursor(self.cursor_hand)
                tag.set_hover()
                self.hovered_tag = tag


    def do_populate_popup(self, popup) -> None:
        """Adds link-related options to the context menu."""

        if self.clicked_link:
            item_open_link = Gtk.MenuItem()
            item_open_link.set_label(_('Open Link'))
            item_open_link.connect('activate',
                                   lambda _m, url: openurl(url),
                                   self.clicked_link)

            popup.prepend(item_open_link)

            item_copy_link = Gtk.MenuItem()
            item_copy_link.set_label(_('Copy Link to Clipboard'))
            item_copy_link.connect('activate',
                                   self.copy_url,
                                   self.clicked_link)

            popup.prepend(item_copy_link)

            popup.show_all()

            self.clicked_link = ""


    def copy_url(self, menu_item, url: str) -> None:
        """Copy url to clipboard."""

        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(url, -1)
        clipboard.store()

    # --------------------------------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------------------------------

    def get_title(self) -> str:
        """Get the task's title."""

        return self.data['title']
