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

from gi.repository import Gtk, Pango, GLib

from GTG.core.logger import log


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

    def __init__(self, req, clipboard) -> None:
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

        self.title_tag = self.buffer.create_tag('title',
                                                weight=Pango.Weight.BOLD,
                                                size_points=16,
                                                pixels_above_lines=15,
                                                pixels_below_lines=30)

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

        self.apply_title()

        # Return False to only run the function once,
        # and clear the handle for next time.
        self.timeout = None
        return False


    def apply_title(self) -> Gtk.TextIter:
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
        self.buffer.apply_tag_by_name('title', start, end)
        self.buffer.remove_tag_by_name('title', end, buffer_end)

        return end
