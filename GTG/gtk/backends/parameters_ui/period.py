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

from gettext import gettext as _, ngettext


class PeriodUI(Gtk.Box):
    """A widget to change the frequency of a backend synchronization
    """

    def __init__(self, req, backend, width):
        """
        Creates the Gtk.Adjustment and the related label. Loads the current
        period.

        @param req: a Requester
        @param backend: a backend object
        @param width: the width of the Gtk.Label object
        """
        super().__init__()
        self.backend = backend
        self.req = req
        self._populate_gtk(width)
        self._connect_signals()

    def _populate_gtk(self, width):
        """Creates the gtk widgets

        @param width: the width of the Gtk.Label object
        """
        self.set_spacing(10)
        period_label = Gtk.Label(label=_("Check for new tasks every"))
        period_label.set_xalign(0)
        period_label.set_yalign(0.5)
        period_label.set_wrap(True)
        period_label.set_size_request(width=width, height=-1)
        self.append(period_label)
        period = self.backend.get_parameters()['period']
        self.adjustment = Gtk.Adjustment(value=period,
                                         lower=1,
                                         upper=120,
                                         step_increment=1,
                                         page_increment=0,
                                         page_size=0)
        self.period_spin = Gtk.SpinButton(adjustment=self.adjustment,
                                          climb_rate=0.3,
                                          digits=0)
        self.append(self.period_spin)
        self.minutes_label = Gtk.Label()
        self.update_minutes_label()
        self.minutes_label.set_xalign(0)
        self.minutes_label.set_yalign(0.5)
        self.append(self.minutes_label)

    def _connect_signals(self):
        """Connects the gtk signals"""
        self.period_spin.connect('changed', self.on_spin_changed)

    def commit_changes(self):
        """Saves the changes to the backend parameter"""
        self.backend.set_parameter('period', int(self.adjustment.get_value()))

    def on_spin_changed(self, sender):
        """ Signal callback, executed when the user changes the period.
        Disables the backend. The user will re-enable it to confirm the changes
        (s)he made.

        @param sender: not used, only here for signal compatibility
        """
        self.update_minutes_label()
        if self.backend.is_enabled() and not self.backend.is_default():
            self.req.set_backend_enabled(self.backend.get_id(), False)

    def update_minutes_label(self):
        adjustment = int(self.adjustment.get_value())
        self.minutes_label.set_markup(ngettext(" minute", " minutes",
                                               adjustment))
