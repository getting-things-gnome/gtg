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

__all__ = ('ParameterUIWidget',)


class ParameterUIWidget(Gtk.Box):
    '''Base class for definition of possible paramter UI'''

    def __init__(self, req, backend, width,
                 parameter_name, gtk_kwargs={}):
        super(ParameterUIWidget, self).__init__(**gtk_kwargs)
        self.req = req
        self.backend = backend
        self.parameter_name = parameter_name
        self._populate_gtk(width)
        self._connect_signals()

    def _populate_gtk(self, width):
        '''Creates the gtk widgets'''
        raise NotImplementedError('Subclass should implement this method.')

    def _connect_signals(self):
        '''Implemented in subclass if necessary, otherwise do nothing'''

    def get_value(self):
        '''Get parameter's value'''
        raise NotImplementedError('Subclass should implement this method.')

    def commit_changes(self):
        '''Saves the changes to the backend parameter'''
        self.backend.set_parameter(self.parameter_name, self.get_value())

    def disable_backend(self):
        backend = self.backend
        if backend.is_enabled() and not backend.is_default():
            self.req.set_backend_enabled(backend.get_id(), False)

    def disable_backend_on_event(self, sender, data=None):
        self.disable_backend()