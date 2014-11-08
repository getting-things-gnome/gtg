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

from GTG.gtk.backends_dialog.parameters_ui.ui_widget import ParameterUIWidget


class TextUI(ParameterUIWidget):
    '''A widget to display a simple textbox and a label to describe its content
    '''

    def __init__(self, req, backend, width, description, parameter_name):
        '''
        Creates the textbox and the related label. Loads the current
        content.

        @param req: a Requester
        @param backend: a backend object
        @param width: the width of the Gtk.Label object
        '''
        self.description = description
        super(TextUI, self).__init__(req, backend, width, parameter_name)

    def _populate_gtk(self, width):
        '''Creates the gtk widgets

        @param width: the width of the Gtk.Label object
        '''
        label = Gtk.Label(label="%s:" % self.description)
        label.set_line_wrap(True)
        label.set_alignment(xalign=0, yalign=0.5)
        label.set_size_request(width=width, height=-1)
        self.pack_start(label, False, True, 0)
        align = Gtk.Alignment.new(0, 0.5, 1, 0)
        align.set_padding(0, 0, 10, 0)
        self.pack_start(align, True, True, 0)
        self.textbox = Gtk.Entry()
        backend_parameters = self.backend.get_parameters()[self.parameter_name]
        self.textbox.set_text(backend_parameters)
        self.textbox.connect('changed', self.disable_backend_on_event)
        align.add(self.textbox)

    def get_value(self):
        return self.textbox.get_text()
