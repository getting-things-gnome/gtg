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

from GTG import _, ngettext
from GTG.gtk.backends_dialog.parameters_ui.ui_widget import ParameterUIWidget

__all__ = ('PeriodUI',)


class PeriodUI(ParameterUIWidget):
    '''A widget to change the frequency of a backend synchronization'''

    def _populate_gtk(self, width):
        '''Creates the gtk widgets

        @param width: the width of the Gtk.Label object
        '''
        period_label = Gtk.Label(label=_("Check for new tasks every"))
        period_label.set_alignment(xalign=0, yalign=0.5)
        period_label.set_line_wrap(True)
        period_label.set_size_request(width=width, height=-1)
        self.pack_start(period_label, False, True, 0)
        align = Gtk.Alignment.new(0, 0.5, 1, 0)
        align.set_padding(0, 0, 10, 0)
        self.pack_start(align, False, True, 0)
        period = self.backend.get_parameters()['period']
        self.adjustment = Gtk.Adjustment(value=period,
                                         lower=1,
                                         upper=120,
                                         step_incr=1,
                                         page_incr=0,
                                         page_size=0)
        self.period_spin = Gtk.SpinButton(adjustment=self.adjustment,
                                          climb_rate=0.3,
                                          digits=0)
        self.minutes_label = Gtk.Label()
        self.update_minutes_label()
        self.minutes_label.set_alignment(xalign=0, yalign=0.5)
        self.pack_start(self.minutes_label, False, True, 0)
        align.add(self.period_spin)
        self.show_all()

    def _connect_signals(self):
        '''Connects the gtk signals'''
        self.period_spin.connect('changed', self.on_spin_changed)

    def get_value(self):
        return int(self.adjustment.get_value())

    def on_spin_changed(self, sender):
        ''' Signal callback, executed when the user changes the period.
        Disables the backend. The user will re-enable it to confirm the changes
        (s)he made.

        @param sender: not used, only here for signal compatibility
        '''
        self.update_minutes_label()
        self.disable_backend()

    def update_minutes_label(self):
        adjustment = int(self.adjustment.get_value())
        self.minutes_label.set_markup(ngettext(" minute", " minutes",
                                               adjustment))
