# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 - Lionel Dricot & Bertrand Rousseau
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

import gtk


class CheckBoxUI(gtk.HBox):
    '''
    It's a widget displaying a simple checkbox, with some text to explain its
    meaning
    '''

    def __init__(self, req, backend, width, text, parameter):
        '''
        Creates the checkbox and the related label.

        @param req: a Requester
        @param backend: a backend object
        @param width: the width of the gtk.Label object
        @param parameter: the backend parameter this checkbox should display
                           and modify
        '''
        super(CheckBoxUI, self).__init__()
        self.backend = backend
        self.req = req
        self.text = text
        self.parameter = parameter
        self._populate_gtk(width)

    def _populate_gtk(self, width):
        '''Creates the checkbox and the related label

        @param width: the width of the gtk.Label object
        '''
        self.checkbutton = gtk.CheckButton(label=self.text)
        backend_parameters = self.backend.get_parameters()[self.parameter]
        self.checkbutton.set_active(backend_parameters)
        self.checkbutton.connect("toggled", self.on_modified)
        self.pack_start(self.checkbutton, False)

    def commit_changes(self):
        '''Saves the changes to the backend parameter'''
        self.backend.set_parameter(self.parameter,
                                   self.checkbutton.get_active())

    def on_modified(self, sender=None):
        ''' Signal callback, executed when the user clicks on the checkbox.
        Disables the backend. The user will re-enable it to confirm the changes
        (s)he made.

        @param sender: not used, only here for signal compatibility
        '''
        if self.backend.is_enabled() and not self.backend.is_default():
            self.req.set_backend_enabled(self.backend.get_id(), False)
