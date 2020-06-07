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
from gettext import gettext as _
from GTG.core.task import Task


# Regex to find GTG's tags
TAG_REGEX = re.compile(r'\@\w+')

# Regex to find internal links
# Starts with gtg:// followed by a UUID.
INTERNAL_REGEX = re.compile((r'gtg:\/\/'
                             r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}'),
                            re.IGNORECASE)


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
            view.open_subtask(self.tid)


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
            view.open_subtask(self.tid)


    def activate(self, view) -> None:
        """Open the link in this tag."""

        view.open_subtask(self.tid)

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
            view.browse_tag(self.tag_name)


    def activate(self, view) -> None:
        """Open the link in this tag."""

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

        # Tags applied to buffer
        self.tags = []

        # Subtask tags
        self.subtask_tags = []

        # Subtasks to be removed
        self.subs_to_remove = []


        # Task info
        self.data = {
            'title': '',
            'tags': set()
        }

        # Signals and callbacks
        self.id_modified = self.buffer.connect('changed', self.on_modified)
        self.connect('motion-notify-event', self.on_mouse_move)
        self.connect('key-press-event', self.on_key_pressed)
        self.connect('key-release-event', self.on_key_released)

        # Callback when tags are clicked
        self.browse_tag = NotImplemented
        self.new_subtask = NotImplemented
        self.delete_subtask = NotImplemented
        self.rename_subtask = NotImplemented
        self.open_subtask = NotImplemented
        self.save = NotImplemented
        self.add_tasktag = NotImplemented
        self.remove_tasktag = NotImplemented


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

        # Keep a copy and clear list of task tags
        prev_tasktags = self.data['tags'].copy()
        self.data['tags'].clear()

        start = self.detect_title()
        start.forward_line()

        self.subs_to_remove = self.subtask_tags.copy()

        # Parse the text line by line until the end of the buffer
        while not start.is_end():
            end = start.copy()
            end.forward_to_line_end()
            text = self.buffer.get_text(start, end, True)

            # Avoid empty new lines
            if text.startswith('\n'):
                start.forward_line()
                continue

            if self.detect_subtasks(text, start):
                start.forward_line()
                continue

            self.detect_url(text, start)
            self.detect_internal_link(text, start)
            self.detect_tag(text, start)

            start.forward_line()

        # Remove subtasks that were deleted
        for tid in self.subs_to_remove:
            self.delete_subtask(tid)
            self.subtask_tags.remove(tid)

        # Clear tags that were added but aren't used anymore
        for tasktag in prev_tasktags.difference(self.data['tags']):
            self.remove_tasktag(tasktag)

        log.debug(f'Processed in {time() - bench_start:.2} secs')

        self.buffer.set_modified(False)
        self.save()

        # Return False to only run the function once,
        # and clear the handle for next time.
        self.timeout = None
        return False

    # --------------------------------------------------------------------------
    # DETECTION
    # --------------------------------------------------------------------------

    def detect_subtasks(self, text: str, start: Gtk.TextIter) -> bool:
        """Detect a subtask line. Returns True if a subtask was found."""

        if not text.startswith('- '):
            return False

        subtask_title = text[2:]

        if not subtask_title:
            start.forward_line()
            return True

        # Tag initial line as invisible
        invisible_end = start.copy()
        invisible_end.forward_chars(2)

        invisible_tag = InvisibleTag()
        self.table.add(invisible_tag)
        self.buffer.apply_tag(invisible_tag, start, invisible_end)

        # Move beyond invisible tag
        start.forward_chars(2)

        end = start.copy()
        end.forward_to_line_end()

        # If it starts with a tag, store the tid and name
        if start.starts_tag():
            tag = start.get_tags()[0]
            tid = tag.tid

            if type(tag) is SubTaskTag:
                self.subs_to_remove.remove(tid)

            # Always rename if there's a tag
            self.rename_subtask(tid, subtask_title)

            # Remove subtask tag and recreate
            self.table.remove(tag)
        else:
            tid = self.new_subtask(subtask_title)
            self.subtask_tags.append(tid)

        task = self.req.get_task(tid)
        subtask_tag = SubTaskTag(task)
        self.table.add(subtask_tag)
        self.buffer.apply_tag(subtask_tag, start, end)

        return True


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
            tag_name = match.group(0)
            tag_tag = TaskTagTag(tag_name, self.req)
            self.tags.append(tag_tag)

            self.table.add(tag_tag)
            self.buffer.apply_tag(tag_tag, tag_start, tag_end)
            self.data['tags'].add(tag_name)

            self.add_tasktag(tag_name)


    def detect_internal_link(self, text: str, start: Gtk.TextIter) -> None:
        """Detect internal links (to other gtg tasks) and apply tags."""

        # Find all matches
        matches = re.finditer(INTERNAL_REGEX, text)

        # Go through each with its own iterator and tag 'em
        for match in matches:
            url_start = start.copy()
            url_end = start.copy()

            url_start.forward_chars(match.start())
            url_end.forward_chars(match.end())

            tid = match.group(0).replace('gtg://', '')
            task = self.req.get_task(tid)

            if task:
                link_tag = InternalLinkTag(task)
                self.tags.append(link_tag)

                self.table.add(link_tag)
                self.buffer.apply_tag(link_tag, url_start, url_end)


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

        end = start.copy()
        end.forward_to_line_end()
        buffer_end = self.buffer.get_end_iter()

        # Set the tag to the first line and remove it everywhere below
        self.buffer.apply_tag(self.title_tag, start, end)
        self.buffer.remove_tag(self.title_tag, end, buffer_end)

        self.data['title'] = self.buffer.get_text(start, end, False)

        return end

    # --------------------------------------------------------------------------
    # INTERACTIVITY
    # --------------------------------------------------------------------------

    def on_key_pressed(self, widget, event) -> None:
        """Callback when a key is pressed."""

        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        enter = event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter)

        if ctrl and enter:
            cursor_mark = self.buffer.get_insert()
            cursor_iter = self.buffer.get_iter_at_mark(cursor_mark)

            for tag in cursor_iter.get_tags():
                try:
                    tag.activate(self)

                except AttributeError:
                    # Not an interactive tag
                    pass

            return True


    def on_key_released(self, widget, event):
        """Callback when a key is released. Used for cursor hovering."""

        try:
            self.hovered_tag.reset()
            self.hovered_tag = None
        except AttributeError:
            pass

        cursor_mark = self.buffer.get_insert()
        cursor_iter = self.buffer.get_iter_at_mark(cursor_mark)

        for tag in cursor_iter.get_tags():
            try:
                tag.set_hover()
                self.hovered_tag = tag

            except AttributeError:
                pass


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
        try:
            tag = tags[0]
            tag.set_hover()
            window.set_cursor(self.cursor_hand)
            self.hovered_tag = tag

        except (AttributeError, IndexError):
            # Not an interactive tag, or no tag at all
            pass


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


    def select_title(self) -> None:
        """Select the first line (title)."""

        start = self.buffer.get_start_iter()
        end = start.copy()
        end.forward_to_line_end()
        self.buffer.select_range(start, end)


    def get_text(self) -> str:
        """Get the text in the taskview."""

        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()

        return self.buffer.get_text(start, end, False)
