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

from GTG import _, ngettext


class PeriodUI(gtk.HBox):
    '''A widget to change the frequency of a backend synchronization
    '''

    def __init__(self, req, backend, width):
        '''
        Creates the gtk.Adjustment and the related label. Loads the current
        period.

        @param req: a Requester
        @param backend: a backend object
        @param width: the width of the gtk.Label object
        '''
        super(PeriodUI, self).__init__()
        self.backend = backend
        self.req = req
        self._populate_gtk(width)
        self._connect_signals()

    def _populate_gtk(self, width):
        '''Creates the gtk widgets

        @param width: the width of the gtk.Label object
        '''
        period_label = gtk.Label(_("Check for new tasks every"))
        period_label.set_alignment(xalign=0, yalign=0.5)
        period_label.set_line_wrap(True)
        period_label.set_size_request(width=width, height=-1)
        self.pack_start(period_label, False)
        align = gtk.Alignment(xalign=0, yalign=0.5, xscale=1)
        align.set_padding(0, 0, 10, 0)
        self.pack_start(align, False)
        period = self.backend.get_parameters()['period']
        self.adjustment = gtk.Adjustment(value=period,
                                         lower=1,
                                         upper=120,
                                         step_incr=1,
                                         page_incr=0,
                                         page_size=0)
        self.period_spin = gtk.SpinButton(adjustment=self.adjustment,
                                          climb_rate=0.3,
                                          digits=0)
        self.minutes_label = gtk.Label()
        self.update_minutes_label()
        self.minutes_label.set_alignment(xalign=0, yalign=0.5)
        self.pack_start(self.minutes_label, False)
        align.add(self.period_spin)
        self.show_all()

    def _connect_signals(self):
        '''Connects the gtk signals'''
        self.period_spin.connect('changed', self.on_spin_changed)

    def commit_changes(self):
        '''Saves the changes to the backend parameter'''
        self.backend.set_parameter('period', int(self.adjustment.get_value()))

    def on_spin_changed(self, sender):
        ''' Signal callback, executed when the user changes the period.
        Disables the backend. The user will re-enable it to confirm the changes
        (s)he made.

        @param sender: not used, only here for signal compatibility
        '''
        self.update_minutes_label()
        if self.backend.is_enabled() and not self.backend.is_default():
            self.req.set_backend_enabled(self.backend.get_id(), False)

    def update_minutes_label(self):
        adjustment = int(self.adjustment.get_value())
        self.minutes_label.set_markup(ngettext(" minute", " minutes",
                                               adjustment))
