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

"""Taskview widget used in the task editor."""


import re
from time import time
from uuid import uuid4
import logging

from gi.repository import Gtk, GLib, Gdk, GObject

from GTG.core.requester import Requester
import GTG.core.urlregex as url_regex
from webbrowser import open as openurl
from gettext import gettext as _
from typing import List

from GTG.gtk.editor.text_tags import (TitleTag, SubTaskTag, TaskTagTag,
                                      InternalLinkTag, LinkTag, CheckboxTag,
                                      InvisibleTag, SubheadingTag)

log = logging.getLogger(__name__)


# Regex to find GTG's tags.
# GTG Tags start with @ and can contain alphanumeric
# characters and/or dashes
TAG_REGEX = re.compile(r'\B\@\w+(\-\w+)*')

# Regex to find internal links
# Starts with gtg:// followed by a UUID.
INTERNAL_REGEX = re.compile((r'gtg:\/\/'
                             r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}'),
                            re.IGNORECASE)


class TaskView(Gtk.TextView):
    """Taskview widget

    This is a specialized Gtk textview with GTG features. It waits [n] seconds
    after the user has modified the buffer and analyzes the contents to find
    the title, tags, etc.

    Process() starts by removing all tags except subtasks. Then goes
    line-by-line detecting tags, subtasks, etc and applying Gtk.Textags
    to them. The tags themselves are in the text_tags module.

    Subtasks are not deleted since we need to keep a reference to the tasks.
    They are deleted and reapplied if the content needs to be refreshed.
    We also keep a reference to the subtask tids, we use this to know which
    subtasks were deleted in the text and have to be removed.

    This widget requires several callbacks to work. These have to be set
    after the widget has been initialized, otherwise many things won't work.
    """

    # Timeout in milliseconds
    PROCESSING_DELAY = 250

    # Mouse cursors
    CURSOR_HAND = Gdk.Cursor.new(Gdk.CursorType.HAND2)
    CURSOR_NORMAL = Gdk.Cursor.new(Gdk.CursorType.XTERM)


    def __init__(self, req: Requester, clipboard) -> None:
        super().__init__()

        self.req = req
        self.clipboard = clipboard

        # The timeout handler
        self.timeout = None

        # Title of the task
        self.title = None

        # Tags applied to this task
        self.task_tags = set()

        # Callbacks. These need to be set after init
        self.browse_tag_cb = NotImplemented
        self.add_tasktag_cb = NotImplemented
        self.remove_tasktag_cb = NotImplemented
        self.get_subtasks_cb = NotImplemented
        self.get_taglist_cb = NotImplemented
        self.new_subtask_cb = NotImplemented
        self.open_task_cb = NotImplemented
        self.delete_subtask_cb = NotImplemented
        self.rename_subtask_cb = NotImplemented
        self.refresh_cb = NotImplemented
        self.save_cb = NotImplemented

        # The tag currently hovered. This tag gets reset() when the mouse or
        # cursor moves away
        self.hovered_tag = None

        # URL currently right-clicked. This is used to populate the context
        # menu
        self.clicked_link = None

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

        # Add title tag
        self.title_tag = TitleTag()
        self.table.add(self.title_tag)

        self.checkbox_tag = CheckboxTag()
        self.table.add(self.checkbox_tag)

        # Tags applied to the buffer. Does not include Title or subtasks,
        # since this is used to remove the tags from the tag table, which
        # also removes them from the buffer
        self.tags_applied = []

        # Keep track of subtasks in this task. Tags keeps all the subtask tags
        # applied in the buffer, while 'to_delete' is a temporary list used in
        # process() to determine which subtasks we have to delete from the
        # task.
        self.subtasks = {
            'tags': [],
            'to_delete': []
        }

        # Signals and callbacks
        self.id_modified = self.buffer.connect('changed', self.on_modified)
        self.connect('motion-notify-event', self.on_mouse_move)
        self.connect('key-press-event', self.on_key_pressed)
        self.connect('key-release-event', self.on_key_released)


    def on_modified(self, buffer: Gtk.TextBuffer) -> None:
        """Called every time the text buffer changes."""

        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = None

        self.timeout = GLib.timeout_add(self.PROCESSING_DELAY, self.process)


    def process(self) -> None:
        """Process the contents of the text buffer."""

        if not self.buffer.props.text:
            # Why process if there's nothing to process
            return

        log.debug('Processing text buffer after %dms', self.PROCESSING_DELAY)
        bench_start = 0  # saving call on time() in non debug mode
        if log.isEnabledFor(logging.DEBUG):
            bench_start = time()

        # Clear all tags first
        [self.table.remove(t) for t in self.tags_applied]
        self.tags_applied = []

        # Keep a copy and clear list of task tags
        prev_tasktags = self.task_tags.copy()
        self.task_tags.clear()

        start = self.detect_title()
        start.forward_line()

        self.subtasks['to_delete'] = self.subtasks['tags'].copy()

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

            self.detect_subheading(text, start)
            self.detect_url(text, start)
            self.detect_internal_link(text, start)
            self.detect_tag(text, start)

            start.forward_line()

        # Remove subtasks that were deleted
        for tid in self.subtasks['to_delete']:
            self.delete_subtask_cb(tid)
            self.subtasks['tags'].remove(tid)

        # Clear tags that were added but aren't used anymore
        for tasktag in prev_tasktags.difference(self.task_tags):
            self.remove_tasktag_cb(tasktag)

        if log.isEnabledFor(logging.DEBUG):
            log.debug('Processed in %.2fms', (time() - bench_start) * 1000)

        self.buffer.set_modified(False)
        self.save_cb()

        # Return False to only run the function once,
        # and clear the handle for next time.
        self.timeout = None
        return False

    # --------------------------------------------------------------------------
    # DETECTION
    # --------------------------------------------------------------------------

    def detect_subtasks(self, text: str, start: Gtk.TextIter) -> bool:
        """Detect a subtask line. Returns True if a subtask was found."""

        # This function has three paths:
        # * "Initial" Path: We find the line starts with '- ' and has text.
        # * "Modified" Path: We find the line starts with a subtask tag
        # * "None" Path: The line doesn't have any subtasks

        # The structure of a subtask in terms of text tags is:
        # <subtask>
        #   <checkbox>[ ]</checkbox>
        #   <internal-link>Subtask name</internal-link>
        # </subtask>

        # Add a new subtask
        if text.startswith('- ') and len(text[2:]) > 0:
            # Remove the -
            delete_end = start.copy()
            delete_end.forward_chars(2)
            self.buffer.delete(start, delete_end)

            # Add new subtask
            tid = self.new_subtask_cb(text[2:])
            task = self.req.get_task(tid)
            status = task.get_status() if task else 'Active'

            # Add the checkbox
            self.add_checkbox(tid, start)
            after_checkbox = start.copy()
            after_checkbox.forward_char()

            # Add the internal link
            link_tag = InternalLinkTag(tid, status)
            self.table.add(link_tag)

            end = start.copy()
            end.forward_to_line_end()
            self.buffer.apply_tag(link_tag, after_checkbox, end)
            self.tags_applied.append(link_tag)

            # Add the subtask tag
            start.backward_char()
            subtask_tag = SubTaskTag(tid)
            self.table.add(subtask_tag)
            self.buffer.apply_tag(subtask_tag, start, end)

            self.subtasks['tags'].append(tid)
            return True

        # A subtask already exists
        elif start.starts_tag():
            # Detect if it's a subtask tag
            sub_tag = None

            for tag in start.get_tags():
                if type(tag) == SubTaskTag:
                    sub_tag = tag

            # Otherwise return early
            if not sub_tag:
                return False

            # Don't auto-remove it
            tid = sub_tag.tid
            task = self.req.get_task(tid)
            parents = task.get_parents()

            # Remove if its not a child of this task
            if not parents or parents[0] != self.tid:
                log.debug('Task %s is not a subtask of %s', tid, self.tid)
                log.debug('Removing subtask %s from content', tid)

                end = start.copy()
                end.forward_to_line_end()

                # Move the start iter to take care of the newline at
                # the previous line
                start.backward_chars(2)

                self.buffer.delete(start, end)

                return False

            # Check that we still have a checkbox
            after_checkbox = start.copy()
            after_checkbox.forward_char()

            has_checkbox = any(type(t) == CheckboxTag
                               for t in after_checkbox.get_tags())

            if not has_checkbox:
                check = self.buffer.get_slice(start, after_checkbox, True)

                # Check that there's still a checkbox. If the user has
                # deleted all text including the space after the checkbox,
                # the check for the tag will return False. In this case
                # we want to check if the checkbox is still around, if it
                # is the user might still type a new name for the task.
                # Otherwise, if the checkbox was deleted, we return and let
                # the text tags be deleted.
                if check != u'\uFFFC':
                    return False


            try:
                self.subtasks['to_delete'].remove(tid)
            except ValueError:
                pass

            self.rename_subtask_cb(tid, text)

            # Get the task and instantiate an internal link tag
            status = task.get_status() if task else 'Active'
            link_tag = InternalLinkTag(tid, status)
            self.table.add(link_tag)

            # Apply the new internal link tag (which was removed
            # by process())
            end = start.copy()
            end.forward_to_line_end()
            self.buffer.apply_tag(link_tag, after_checkbox, end)
            self.tags_applied.append(link_tag)

            # Re-apply the subtask tag too
            self.table.remove(sub_tag)
            subtask_tag = SubTaskTag(tid)
            self.table.add(subtask_tag)
            self.buffer.apply_tag(subtask_tag, start, end)

            return True

        # No subtask, no fun
        else:
            return False


    def on_checkbox_toggle(self, tid: uuid4) -> None:
        """Toggle a task status and refresh the subtask tag."""

        task = self.req.get_task(tid)

        if not task:
            log.warn('Failed to toggle status for %s', tid)
            return

        task.toggle_status()
        self.process()


    def add_checkbox(self, tid: int, start: Gtk.TextIter) -> None:
        """Add a checkbox for a subtask."""

        task = self.req.get_task(tid)
        checkbox = Gtk.CheckButton.new()

        if task and task.status != task.STA_ACTIVE:
            checkbox.set_active(True)

        checkbox.connect('toggled', lambda _: self.on_checkbox_toggle(tid))
        checkbox.set_can_focus(False)

        # Block the modified signal handler while we add the anchor
        # for the checkbox widget
        with GObject.signal_handler_block(self.buffer, self.id_modified):
            anchor = self.buffer.create_child_anchor(start)
            self.add_child_at_anchor(checkbox, anchor)
            end = start.copy()
            end.forward_char()
            self.buffer.apply_tag(self.checkbox_tag, start, end)

        self.buffer.set_modified(False)
        checkbox.show()


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
            tag_name = tag_name.replace('@', '')
            tag_tag = TaskTagTag(tag_name, self.req)
            self.tags_applied.append(tag_tag)

            self.table.add(tag_tag)
            self.buffer.apply_tag(tag_tag, tag_start, tag_end)
            self.task_tags.add(tag_name)

            self.add_tasktag_cb(tag_name)


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
                self.tags_applied.append(link_tag)

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
            self.tags_applied.append(url_tag)

            self.table.add(url_tag)
            self.buffer.apply_tag(url_tag, url_start, url_end)


    def detect_subheading(self, text: str, start: Gtk.TextIter) -> None:
        """Detect subheadings (akin to H2)."""

        if text.startswith('# ') and len(text) > 2:
            end = start.copy()
            end.forward_chars(2)

            invisible_tag = InvisibleTag()
            self.table.add(invisible_tag)
            self.buffer.apply_tag(invisible_tag, start, end)

            start.forward_chars(2)
            end.forward_to_line_end()

            subheading_tag = SubheadingTag()
            self.table.add(subheading_tag)
            self.buffer.apply_tag(subheading_tag, start, end)

            self.tags_applied.append(subheading_tag)
            self.tags_applied.append(invisible_tag)


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

        title = self.buffer.get_text(start, end, False)
        self.detect_tag(title, start)

        # If the title changed, save it and refresh the editor
        if self.title != title:
            self.title = title
            self.refresh_cb(title)

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

        try:
            self.hovered_tag.cursor_reset()
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

            try:
                tag.set_cursor_hover()
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
        window.set_cursor(self.CURSOR_NORMAL)

        if self.hovered_tag:
            try:
                self.hovered_tag.reset()
                self.hovered_tag = None

            except AttributeError:
                pass

        # Apply hover state if possible
        try:
            tag = tags[0]
            tag.set_hover()
            window.set_cursor(self.CURSOR_HAND)
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

        return self.title


    def select_title(self) -> None:
        """Select the first line (title)."""

        start = self.buffer.get_start_iter()
        end = start.copy()
        end.forward_to_line_end()
        self.buffer.select_range(start, end)


    def get_text(self) -> str:
        """Get the text in the taskview."""

        # Get all text (skip the first line, it's the title)
        start = self.buffer.get_start_iter()
        start.forward_line()

        end = self.buffer.get_end_iter()
        text = self.buffer.get_text(start, end, True)

        # Filter out subtasks. We only need to replace the names
        # of the subtasks with the appropiate markdown containing
        # the Task ID
        text = text.splitlines()

        while not start.is_end():
            try:
                tag = start.get_tags()[0]

                if type(tag) == SubTaskTag:
                    # Sneaky! The text list starts after the title,
                    # but the iterator is including that line. We need to
                    # remove that here to get the right index
                    line = start.get_line() - 1
                    tid = tag.tid
                    sub = f'{{! {tid} !}}'

                    text[line] = sub

            except IndexError:
                pass

            start.forward_to_tag_toggle()

        return '\n'.join(text)


    def insert(self, text: str) -> None:
        """Unserialize and insert text in the buffer."""

        subtasks = []
        text = text.splitlines()

        for index, line in enumerate(text):
            # Find the subtasks and store their lines
            if line.lstrip().startswith('{!'):
                # Get the Task ID
                tid = line.replace('{! ', '').replace(' !}', '').strip()

                # Remember there's a line for the title at the top
                real_index = index + 1

                subtasks.append((tid, real_index))

                # Clear lines where subtasks are
                text[index] = ''

        # Insert text (first line is taken by the title)
        start = self.buffer.get_start_iter()
        start.forward_line()
        self.buffer.insert(start, '\n'.join(text))

        # Insert subtasks. Remove existing subtasks from the list, we
        # will delete the rest at the end
        for sub in subtasks.copy():
            self.insert_existing_subtask(*sub)

            if self.req.has_task(sub[0]):
                subtasks.remove(sub)

        # Remove non-existing subtasks (subtasks that have been deleted)
        for sub in subtasks:
            start = self.buffer.get_iter_at_line(sub[1])
            end = start.copy()
            end.forward_line()

            self.buffer.delete(start, end)

        self.process()

    def insert_tags(self, tags: List) -> None:
        """Insert tags in buffer."""

        # Don't add tags that are already in the buffer
        for t in tags.copy():
            if t in self.task_tags:
                tags.remove(t)

        if not tags:
            # Bail early if there are no tags left in the list
            return

        # Check the first line (below the title). Do we have
        # tags there already? If there aren't add a new line
        # after the title, otherwise add a leading comma to
        # the text since we are appending to the tags in
        # that line
        first_line = self.buffer.get_iter_at_line(1)
        first_line_tags = first_line.get_tags()
        first_line.forward_to_line_end()

        if not first_line_tags:
            first_line = self.buffer.get_start_iter()
            first_line.forward_to_line_end()
            self.buffer.insert(first_line, '\n')
            text = ''
        else:
            text = ', '

        text += ', '.join(['@' + tag for tag in tags])
        self.buffer.insert(first_line, text)


    def insert_new_subtask(self) -> None:
        """Insert a new subtask in the buffer."""

        # Grab cursor position
        cursor_mark = self.buffer.get_insert()
        cursor_iter = self.buffer.get_iter_at_mark(cursor_mark)

        # Avoid title line
        if cursor_iter.get_line() == 0:
            cursor_iter.forward_line()

        # Check if the line is empty
        if cursor_iter.get_chars_in_line() > 1:
            cursor_iter.forward_to_line_end()
            self.buffer.insert(cursor_iter, '\n- ')
        else:
            self.buffer.insert(cursor_iter, '- ')

        self.buffer.place_cursor(cursor_iter)


    def insert_existing_subtask(self, tid: str, line: int = None) -> None:
        """Insert an existing subtask in the buffer."""

        # Check if the task exists first
        if not self.req.has_task(tid):
            log.debug('Task %s not found', tid)
            return

        if line is not None:
            start = self.buffer.get_iter_at_line(line)
        else:
            start = self.buffer.get_end_iter()
            self.buffer.insert(start, '\n')
            start.forward_line()
            line = start.get_line()

        # Add subtask name
        task = self.req.get_task(tid)
        self.buffer.insert(start, task.get_title())

        # Reset iterator
        start = self.buffer.get_iter_at_line(line)

        # Add checkbox
        self.add_checkbox(tid, start)

        # Apply link to subtask text
        end = start.copy()
        end.forward_to_line_end()

        link_tag = InternalLinkTag(tid, task.get_status())
        self.table.add(link_tag)
        self.buffer.apply_tag(link_tag, start, end)
        self.tags_applied.append(link_tag)

        # Apply subtask tag to everything
        start.backward_char()
        subtask_tag = SubTaskTag(tid)
        self.table.add(subtask_tag)
        self.buffer.apply_tag(subtask_tag, start, end)

        self.subtasks['tags'].append(tid)


    # --------------------------------------------------------------------------
    # VERSIONING
    # --------------------------------------------------------------------------
    @classmethod
    def format_update(cls, text: str) -> str:
        """Update the content's format to the new version."""

        # Unescape &quot;a and friends
        text = html.unescape(text)

        # Get rid of the content tag if it slip all the way there
        text = text.replace('</content>', '')
        text = text.replace('<content>', '')

        # Tag tags arent' needed anymore
        text = text.replace('</tag>', '')
        text = text.replace('<tag>', '')

        # New subtask style
        text = text.replace('</subtask>', ' !}')
        text = text.replace('<subtask>', '{! ')

        # Get rid of the arrow and indent
        text = text.replace('→', '')

        return text
