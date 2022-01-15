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

import os.path

from gi.repository import Gtk

from gettext import gettext as _


class PathUI(Gtk.Box):
    """Gtk widgets to show a path in a textbox, and a button to bring up a
    filesystem explorer to modify that path (also, a label to describe those)
    """

    def __init__(self, req, backend, width):
        """
        Creates the textbox, the button and loads the current path.

        @param req: a Requester
        @param backend: a backend object
        @param width: the width of the Gtk.Label object
        """
        super().__init__()
        self.backend = backend
        self.req = req
        self._populate_gtk(width)

    def _populate_gtk(self, width):
        """Creates the Gtk.Label, the textbox and the button

        @param width: the width of the Gtk.Label object
        """
        label = Gtk.Label(label=_("Filename:"))
        label.set_wrap(True)
        label.set_xalign(0)
        label.set_yalign(0.5)
        label.set_size_request(width=width, height=-1)
        self.append(label)
        self.textbox = Gtk.Entry()
        self.textbox.set_hexpand(True)
        self.textbox.set_text(self.backend.get_parameters()['path'])
        self.textbox.connect('changed', self.on_path_modified)
        self.append(self.textbox)
        self.button = Gtk.Button()
        self.button.set_label("Edit")
        self.button.connect('clicked', self.on_button_clicked)
        self.append(self.button)

    def commit_changes(self):
        """Saves the changes to the backend parameter"""
        self.backend.set_parameter('path', self.textbox.get_text())

    def on_path_modified(self, sender):
        """ Signal callback, executed when the user edits the path.
        Disables the backend. The user will re-enable it to confirm the changes
        (s)he made.

        @param sender: not used, only here for signal compatibility
        """
        if self.backend.is_enabled() and not self.backend.is_default():
            self.req.set_backend_enabled(self.backend.get_id(), False)

    def on_button_clicked(self, sender):
        """Shows the filesystem explorer to choose a new file

        @param sender: not used, only here for signal compatibility
        """
        self.chooser = Gtk.FileChooserDialog(
            title=None,
            action=Gtk.FileChooserAction.SAVE,
            buttons=(Gtk.STOCK_CANCEL,
                     Gtk.ResponseType.CANCEL,
                     Gtk.STOCK_OK,
                     Gtk.ResponseType.OK))
        self.chooser.set_default_response(Gtk.ResponseType.OK)
        # set default file as the current self.path
        dirname, basename = os.path.split(self.textbox.get_text())
        self.chooser.set_current_name(basename)
        self.chosser.set_current_folder(dirname)

        # filter files
        afilter = Gtk.FileFilter()
        afilter.set_name("All files")
        afilter.add_pattern("*")
        self.chooser.add_filter(afilter)
        afilter = Gtk.FileFilter()
        afilter.set_name("XML files")
        afilter.add_mime_type("text/plain")
        afilter.add_pattern("*.xml")
        self.chooser.add_filter(afilter)
        response = self.chooser.run()
        if response == Gtk.ResponseType.OK:
            self.textbox.set_text(self.chooser.get_filename())
        self.chooser.destroy()
