# -*- coding: utf-8 -*-
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

from GTG import _
from GTG.gtk.backends_dialog.parameters_ui.ui_widget import ParameterUIWidget

__all__ = ('PasswordUI',)


class PasswordUI(ParameterUIWidget):
    '''Widget displaying a gtk.Label and a textbox to input a password'''

    def __init__(self, req, backend, width, parameter_name):
        '''Creates the gtk widgets and loads the current password in the text
        field

        @param req: a Requester
        @param backend: a backend object
        @param width: the width of the Gtk.Label object
        '''
        super(PasswordUI, self).__init__(req, backend, width, parameter_name)
        self._load_password()

    def _populate_gtk(self, width):
        '''Creates the text box and the related label

        @param width: the width of the Gtk.Label object
        '''
        password_label = Gtk.Label(label=_("Password:"))
        password_label.set_alignment(xalign=0, yalign=0.5)
        password_label.set_size_request(width=width, height=-1)
        self.pack_start(password_label, False, True, 0)
        align = Gtk.Alignment.new(0, 0.5, 1, 0)
        align.set_padding(0, 0, 10, 0)
        self.pack_start(align, True, True, 0)
        self.password_textbox = Gtk.Entry()
        align.add(self.password_textbox)

    def _load_password(self):
        '''Loads the password from the backend'''
        password = self.backend.get_parameters()['password']
        self.password_textbox.set_invisible_char('*')
        self.password_textbox.set_visibility(False)
        self.password_textbox.set_text(password)

    def _connect_signals(self):
        '''Connects the gtk signals'''
        self.password_textbox.connect('changed', self.disable_backend_on_event)

    def get_value(self):
        return self.password_textbox.get_text()
