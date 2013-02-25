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


class TextUI(gtk.HBox):
    '''A widget to display a simple textbox and a label to describe its content
    '''

    def __init__(self, req, backend, width, description, parameter_name):
        '''
        Creates the textbox and the related label. Loads the current
        content.

        @param req: a Requester
        @param backend: a backend object
        @param width: the width of the gtk.Label object
        '''
        super(TextUI, self).__init__()
        self.backend = backend
        self.req = req
        self.parameter_name = parameter_name
        self.description = description
        self._populate_gtk(width)

    def _populate_gtk(self, width):
        '''Creates the gtk widgets

        @param width: the width of the gtk.Label object
        '''
        label = gtk.Label("%s:" % self.description)
        label.set_line_wrap(True)
        label.set_alignment(xalign=0, yalign=0.5)
        label.set_size_request(width=width, height=-1)
        self.pack_start(label, False)
        align = gtk.Alignment(xalign=0, yalign=0.5, xscale=1)
        align.set_padding(0, 0, 10, 0)
        self.pack_start(align, True)
        self.textbox = gtk.Entry()
        backend_parameters = self.backend.get_parameters()[self.parameter_name]
        self.textbox.set_text(backend_parameters)
        self.textbox.connect('changed', self.on_text_modified)
        align.add(self.textbox)

    def commit_changes(self):
        '''Saves the changes to the backend parameter'''
        self.backend.set_parameter(self.parameter_name,
                                   self.textbox.get_text())

    def on_text_modified(self, sender):
        ''' Signal callback, executed when the user changes the text.
        Disables the backend. The user will re-enable it to confirm the changes
        (s)he made.

        @param sender: not used, only here for signal compatibility
        '''
        if self.backend.is_enabled() and not self.backend.is_default():
            self.req.set_backend_enabled(self.backend.get_id(), False)
