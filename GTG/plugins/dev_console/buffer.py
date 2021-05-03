# -----------------------------------------------------------------------------
# GTG Developer Console
# Based on Pitivi Developer Console
# Copyright (c) 2017-2018, Fabian Orccon <cfoch.fabian@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

"""Specialized buffer for the dev console."""

import builtins
import code
import traceback
import keyword
import os
import re
import sys

from gi.repository import GObject
from gi.repository import Gtk

from GTG.plugins.dev_console.utils import display_autocompletion
from GTG.plugins.dev_console.utils import FakeOut
from GTG.plugins.dev_console.utils import swap_std


class InteractiveConsole(code.InteractiveConsole):
    """
    Like Pythons InteractiveConsole, but doesn't call the global exception
    handler if overridden, so there won't be an error popup.
    """

    def showsyntaxerror(self, filename=None):
        etype, exc, tb = sys.exc_info()
        lines = traceback.format_exception_only(etype, exc)
        self.write(''.join(lines))

    def showtraceback(self):
        etype, exc, tb = sys.exc_info()
        lines = traceback.format_exception(etype, exc, tb.tb_next)
        self.write(''.join(lines))


class ConsoleHistory(GObject.Object):
    """Represents a console commands history."""

    __gsignals__ = {
        "pos-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        GObject.Object.__init__(self)
        self._pos = 0
        self._history = [""]

    def add(self, cmd):
        """Adds a command line to the history."""
        if not cmd.strip():
            return

        if len(self._history) > 1 and cmd == self._history[-2]:
            return

        self._history[-1] = cmd
        self._history.append("")
        self._pos = len(self._history) - 1

    def get(self):
        """Gets the command line at the current position."""
        return self._history[self._pos]

    # pylint: disable=invalid-name
    def up(self, cmd):
        """Sets the current command line with the previous used command line."""
        if self._pos > 0:
            self._history[self._pos] = cmd
            self._pos -= 1
            self.emit("pos-changed")

    def down(self, cmd):
        """Sets the current command line with the next available used command line."""
        if self._pos < len(self._history) - 1:
            self._history[self._pos] = cmd
            self._pos += 1
            self.emit("pos-changed")


class ConsoleBuffer(Gtk.TextBuffer):

    def __init__(self, namespace, welcome_message=""):
        Gtk.TextBuffer.__init__(self)

        self.prompt = sys.ps1
        self.output = self.create_tag("output")
        self.error = self.create_tag("error")
        self._stdout = FakeOut(self, self.output)
        self._stderr = FakeOut(self, self.error)
        self._console = InteractiveConsole(namespace)

        self.insert(self.get_end_iter(), welcome_message)
        self.before_prompt_mark = self.create_mark("before-prompt",
                                                   self.get_end_iter(),
                                                   left_gravity=True)
        self.insert_at_cursor(sys.ps1)
        self.prompt_mark = self.create_mark("after-prompt", self.get_end_iter(), left_gravity=True)

        self.history = ConsoleHistory()
        namespace["__history__"] = self.history
        self.history.connect("pos-changed", self.__history_pos_changed_cb)

        self.connect("insert-text", self.__insert_text_cb)

    def process_command_line(self):
        """Process the current input command line executing it if complete."""
        cmd = self.get_command_line()
        self.history.add(cmd)

        before_prompt_iter = self.get_iter_at_mark(self.before_prompt_mark)
        self.remove_all_tags(before_prompt_iter, self.get_end_iter())

        with swap_std(self._stdout, self._stderr):
            self.write("\n")
            is_command_incomplete = self._console.push(cmd)

        if is_command_incomplete:
            self.prompt = sys.ps2
        else:
            self.prompt = sys.ps1
        self.move_mark(self.before_prompt_mark, self.get_end_iter())
        self.write(self.prompt)

        self.move_mark(self.prompt_mark, self.get_end_iter())
        self.place_cursor(self.get_end_iter())

    def is_cursor(self, before=False, at=False, after=False):
        """Compares the position of the cursor compared to the prompt."""
        prompt_iter = self.get_iter_at_mark(self.prompt_mark)
        cursor_iter = self.get_iter_at_mark(self.get_insert())
        res = cursor_iter.compare(prompt_iter)
        return (before and res == -1) or (at and res == 0) or (after and res == 1)

    def write(self, text, tag=None):
        """Writes a text to the buffer."""
        if tag is None:
            self.insert(self.get_end_iter(), text)
        else:
            self.insert_with_tags(self.get_end_iter(), text, tag)

    def get_command_line(self):
        """Gets the last command line after the prompt.

        A command line can be a single line or multiple lines for example when
        a function or a class is defined.
        """
        after_prompt_iter = self.get_iter_at_mark(self.prompt_mark)
        end_iter = self.get_end_iter()
        return self.get_text(after_prompt_iter, end_iter, include_hidden_chars=False)

    def set_command_line(self, cmd):
        """Inserts a command line after the prompt."""
        after_prompt_iter = self.get_iter_at_mark(self.prompt_mark)
        end_iter = self.get_end_iter()
        self.delete(after_prompt_iter, end_iter)
        self.write(cmd)

    def show_autocompletion(self, command):
        """Prints the autocompletion to the view."""
        matches, last, new_command = self.get_autocompletion_matches(command)
        namespace = {
            "last": last,
            "matches": matches,
            "buf": self,
            "command": command,
            "new_command": new_command,
            "display_autocompletion": display_autocompletion
        }

        with swap_std(self._stdout, self._stderr):
            # pylint: disable=eval-used
            eval("display_autocompletion(last, matches, buf, command, new_command)",
                 namespace, self._console.locals)

        if len(matches) > 1:
            self.__refresh_prompt(new_command)

    def get_autocompletion_matches(self, input_text):
        """Returns possible matches for autocompletion."""
        # pylint: disable=bare-except, eval-used
        # Try to get the possible full object to scan.
        # For example, if input_text is "func(circle.ra", we obtain "circle.ra".
        identifiers = re.findall(r"[_A-Za-z][\w\.]*\w$", input_text)
        if identifiers:
            maybe_scannable_object = identifiers[0]
        else:
            maybe_scannable_object = input_text

        pos = maybe_scannable_object.rfind(".")
        if pos != -1:
            # In this case, we cannot scan "circle.ra", so we scan "circle".
            scannable_object = maybe_scannable_object[:pos]
        else:
            # This is the case when input was more simple, like "circ".
            scannable_object = maybe_scannable_object
        namespace = {"scannable_object": scannable_object}
        try:
            if pos != -1:
                str_eval = "dir(eval(scannable_object))"
            else:
                str_eval = "dir()"
            maybe_matches = eval(str_eval, namespace, self._console.locals)
        except Exception:
            return [], maybe_scannable_object, input_text
        if pos != -1:
            # Get substring after last dot (.)
            rest = maybe_scannable_object[(pos + 1):]
        else:
            rest = scannable_object
        # First, assume we are parsing an object.
        matches = [match for match in maybe_matches if match.startswith(rest)]

        # If not matches, maybe it is a keyword or builtin function.
        if not matches:
            tmp_matches = keyword.kwlist + dir(builtins)
            matches = [
                match for match in tmp_matches if match.startswith(rest)]

        if not matches:
            new_input_text = input_text
        else:
            maybe_scannable_pos = input_text.find(maybe_scannable_object)
            common = os.path.commonprefix(matches)
            if pos == -1:
                new_input_text = input_text[:maybe_scannable_pos] + common
            else:
                new_input_text = input_text[:maybe_scannable_pos] + \
                    maybe_scannable_object[:pos] + "." + common

        return matches, rest, new_input_text

    def __refresh_prompt(self, text=""):
        # Prepare the new line
        end_iter = self.get_end_iter()
        self.insert(end_iter, self.prompt)
        end_iter = self.get_end_iter()
        self.move_mark(self.prompt_mark, end_iter)
        self.place_cursor(end_iter)
        self.write(text)

    def __insert_text_cb(self, buf, unused_location, text, unused_len):
        command = self.get_command_line()
        if text == "\t" and command.strip() != "":
            # If input text is '\t' and command doesn't start with spaces or tab
            # prevent GtkTextView to insert the text "\t" for autocompletion.
            GObject.signal_stop_emission_by_name(buf, "insert-text")
            self.show_autocompletion(command)

    def __history_pos_changed_cb(self, history):
        cmd = history.get()
        self.set_command_line(cmd)
