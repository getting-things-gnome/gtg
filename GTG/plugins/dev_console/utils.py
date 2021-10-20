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

"""Utilities for the dev console."""

import functools
import sys
from contextlib import contextmanager
from gettext import gettext as _
from io import TextIOBase


@contextmanager
def swap_std(stdout=None, stderr=None):
    """Swaps temporarily stdout and stderr with the respective arguments."""
    try:
        if stdout:
            sys.stdout, stdout = stdout, sys.stdout
        if stderr:
            sys.stderr, stderr = stderr, sys.stderr
        yield
    finally:
        if stdout:
            sys.stdout = stdout
        if stderr:
            sys.stderr = stderr


def display_autocompletion(last_obj, matches, text_buffer,
                           old_command, new_command):
    """Print possible matches (to FakeOut)."""
    if len(matches) == 1:
        tokens = matches[0].split(last_obj)
        if len(tokens) >= 1:
            text_buffer.insert(text_buffer.get_end_iter(), tokens[1])
    elif len(matches) > 1:
        if new_command.startswith(old_command):
            # Complete the rest of the command if they have a common prefix.
            rest = new_command.replace(old_command, "")
            text_buffer.insert(text_buffer.get_end_iter(), rest)
        print()
        for match in matches:
            print(match)


class Namespace(dict):
    """Base for namespaces usable when executing a Python command."""

    def __init__(self):
        dict.__init__(self)
        for key in self.get_shortcuts():
            dict.__setitem__(self, key, None)

    @staticmethod
    def shortcut(func):
        """Decorator to add methods or properties to the namespace."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        setattr(wrapper, "__is_shortcut", True)
        return wrapper

    def __getitem__(self, key):
        if key in self.get_shortcuts():
            return getattr(self, key)
        return dict.__getitem__(self, key)

    def __setitem__(self, key, item):
        if key in self.get_shortcuts():
            print(_("Not possible to override {key}, because shortcuts "
                    "commands are read-only.").format(key=key), file=sys.stderr)
            return
        dict.__setitem__(self, key, item)

    def __repr__(self):
        return "<%s at %s>" % (self.__class__.__name__, hex(id(self)))

    @classmethod
    def get_shortcuts(cls):
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            is_shortcut = False
            if hasattr(attr, "__is_shortcut"):
                is_shortcut = getattr(attr, "__is_shortcut")
            elif isinstance(attr, property):
                if hasattr(attr.fget, "__is_shortcut"):
                    is_shortcut = getattr(attr.fget, "__is_shortcut")
            if is_shortcut:
                yield attr_name


class FakeOut(TextIOBase):
    """Replacement for sys.stdout/err which redirects writes."""

    def __init__(self, buf, tag):
        TextIOBase.__init__(self)
        self.buf = buf
        self.tag = tag

    def write(self, string):
        self.buf.write(string, self.tag)

    def writelines(self, lines):
        self.buf.write(lines, self.tag)
