# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
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
from functools import reduce

from gi.repository import Gtk

from GTG.core.tag import ALLTASKS_TAG


class ImportTagsUI(Gtk.Box):
    """
    It's a widget displaying a couple of radio buttons, a label and a textbox
    to let the user change the attached tags (or imported)
    """

    def __init__(self, req, backend, width, title, anybox_text, somebox_text,
                 parameter_name):
        """Populates the widgets and refresh the tags to display

        @param req: a requester
        @param backend: the backend to configure
        @param width: the length of the radio buttons
        @param title: the text for the label describing what this collection
                      of gtk widgets is used for
        @param anybox_text: the text for the "Any tag matches" radio button
        @param somebox_text: the text for the "only this set of tags matches"
                             radio button
        @param parameter_name: the backend parameter this widget should modify
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.backend = backend
        self.req = req
        self.title = title
        self.anybox_text = anybox_text
        self.somebox_text = somebox_text
        self.parameter_name = parameter_name
        self._populate_gtk(width)
        self._refresh_tags()
        self._connect_signals()

    def _populate_gtk(self, width):
        """
        Populates the widgets

        @param width: the length of the radio buttons
        """
        title_label = Gtk.Label()
        title_label.set_xalign(0)
        title_label.set_yalign(0)
        title_label.set_markup(f"<big><b>{self.title}</b></big>")
        self.append(title_label)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.append(vbox)
        self.all_tags_radio = Gtk.CheckButton(group=None,
                                              label=self.anybox_text)
        vbox.append(self.all_tags_radio)
        self.some_tags_radio = Gtk.CheckButton(group=self.all_tags_radio,
                                               label=self.somebox_text)
        self.some_tags_radio.set_size_request(width=width, height=-1)
        box = Gtk.Box()
        box.set_spacing(10)
        vbox.append(box)
        box.append(self.some_tags_radio)
        self.tags_entry = Gtk.Entry()
        self.tags_entry.set_hexpand(True)
        box.append(self.tags_entry)

    def on_changed(self, radio, data=None):
        """ Signal callback, executed when the user modifies something.
        Disables the backend. The user will re-enable it to confirm the changes
        (s)he made.

        @param sender: not used, only here for signal compatibility
        @param data: not used, only here for signal compatibility
        """
        # every change in the config disables the backend
        self.req.set_backend_enabled(self.backend.get_id(), False)
        self._refresh_textbox_state()

    def commit_changes(self):
        """Saves the changes to the backend parameter"""
        if self.all_tags_radio.get_active():
            tags = [ALLTASKS_TAG]
        else:
            tags = self.tags_entry.get_text().split(",")
            # stripping spaces
            tags = [t.strip() for t in tags]
            # removing empty tags
            tags = [t for t in tags if t]

        self.backend.set_parameter(self.parameter_name, tags)

    def _refresh_textbox_state(self):
        """Refreshes the content of the textbox"""
        self.tags_entry.set_sensitive(self.some_tags_radio.get_active())

    def _refresh_tags(self):
        """
        Refreshes the list of tags to display in the textbox, and selects
        the correct radio button
        """
        tags_list = self.backend.get_parameters()[self.parameter_name]
        has_all_tasks = ALLTASKS_TAG in tags_list
        self.all_tags_radio.set_active(has_all_tasks)
        self.some_tags_radio.set_active(not has_all_tasks)
        self._refresh_textbox_state()
        if not has_all_tasks:
            tags_text = ""
            if tags_list:
                tags_text = reduce(lambda a, b: a + ", " + b, tags_list)
            self.tags_entry.set_text(tags_text)

    def _connect_signals(self):
        """Connects the gtk signals"""
        self.some_tags_radio.connect("toggled", self.on_changed)
        self.all_tags_radio.connect("toggled", self.on_changed)
        self.tags_entry.connect("changed", self.on_changed)
