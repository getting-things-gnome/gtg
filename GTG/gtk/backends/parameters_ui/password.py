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

from gi.repository import Gtk

from gettext import gettext as _


class PasswordUI(Gtk.Box):
    """Widget displaying a gtk.Label and a textbox to input a password"""

    def __init__(self, req, backend, width):
        """Creates the gtk widgets and loads the current password in the text
        field

        @param req: a Requester
        @param backend: a backend object
        @param width: the width of the Gtk.Label object
        """
        super().__init__()
        self.backend = backend
        self.req = req
        self._populate_gtk(width)
        self._load_password()
        self._connect_signals()

    def _populate_gtk(self, width):
        """Creates the text box and the related label

        @param width: the width of the Gtk.Label object
        """
        self.set_spacing(10)
        password_label = Gtk.Label(label=_("Password:"))
        password_label.set_yalign(0)
        password_label.set_xalign(0)
        password_label.set_size_request(width=width, height=-1)
        self.append(password_label)
        self.password_textbox = Gtk.Entry()
        self.password_textbox.set_hexpand(True)
        self.append(self.password_textbox)

    def _load_password(self):
        """Loads the password from the backend"""
        password = self.backend.get_parameters()['password']
        self.password_textbox.set_invisible_char('*')
        self.password_textbox.set_visibility(False)
        self.password_textbox.set_text(password)

    def _connect_signals(self):
        """Connects the gtk signals"""
        self.password_textbox.connect('changed', self.on_password_modified)

    def commit_changes(self):
        """Saves the changes to the backend parameter ('password')"""
        password = self.password_textbox.get_text()
        self.backend.set_parameter('password', password)

    def on_password_modified(self, sender):
        """ Signal callback, executed when the user edits the password.
        Disables the backend. The user will re-enable it to confirm the changes
        (s)he made.

        @param sender: not used, only here for signal compatibility
        """
        if self.backend.is_enabled() and not self.backend.is_default():
            self.req.set_backend_enabled(self.backend.get_id(), False)
