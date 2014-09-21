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

__all__ = ('CheckBoxUI',)


class CheckBoxUI(ParameterUIWidget):
    '''
    It's a widget displaying a simple checkbox, with some text to explain its
    meaning
    '''

    def __init__(self, req, backend, width, text, parameter_name):
        '''
        Creates the checkbox and the related label.

        @param req: a Requester
        @param backend: a backend object
        @param width: the width of the gtk.Label object
        @param parameter: the backend parameter this checkbox should display
                           and modify
        '''
        self.text = text
        super(CheckBoxUI, self).__init__(req, backend, width, parameter_name)

    def _populate_gtk(self, width):
        '''Creates the checkbox and the related label

        @param width: the width of the Gtk.Label object
        '''
        self.checkbutton = Gtk.CheckButton(label=self.text)
        backend_parameters = self.backend.get_parameters()[self.parameter_name]
        self.checkbutton.set_active(backend_parameters)
        self.checkbutton.connect("toggled", self.disable_backend_on_event)
        self.pack_start(self.checkbutton, False, True, 0)

    def get_value(self):
        return self.checkbutton.get_active()