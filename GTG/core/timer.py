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

""" General class for representing time and periodic time intervals in GTG """

import datetime
import dbus

from gi.repository import GObject


class Timer(GObject.GObject):
    __signal_type__ = (GObject.SignalFlags.RUN_FIRST,
                       None,
                       [])

    __gsignals__ = {'refresh': __signal_type__}

    def __init__(self, config):
        self.config = config
        self.timeout_source = None
        GObject.GObject.__init__(self)
        bus = dbus.SystemBus()
        bus.add_signal_receiver(self.emit_refresh,
                                'Resuming',
                                'org.freedesktop.UPower',
                                'org.freedesktop.UPower')
        self.time_changed()

    def seconds_until(self, time):
        """Returns number of seconds remaining before next refresh"""
        now = datetime.datetime.now()
        secs_to_refresh = time-now
        if secs_to_refresh.total_seconds() < 0:
            secs_to_refresh += datetime.timedelta(days=1)
        return secs_to_refresh.total_seconds() + 1

    def emit_refresh(self):
        """Emit Signal for workview to refresh"""
        self.emit("refresh")
        self.time_changed()
        return False

    def time_changed(self):
        refresh_hour, refresh_mins = self.get_configuration()
        now = datetime.datetime.now()
        refresh_time = datetime.datetime(now.year, now.month, now.day,
                                         int(refresh_hour),
                                         int(refresh_mins), 0)
        secs_to_refresh = self.seconds_until(refresh_time)
        if self.timeout_source:
            GObject.source_remove(self.timeout_source)

        self.timeout_source = GObject.timeout_add_seconds(secs_to_refresh,
                                                          self.emit_refresh)

    def set_configuration(self, refresh_hour, refresh_min):
        try:
            datetime.time(int(refresh_hour), int(refresh_min))
        except (ValueError, TypeError):
            raise ValueError("{}:{} is not a valid time".format(refresh_hour,
                                                                refresh_min))

        self.config.set('hour', refresh_hour)
        self.config.set('min', refresh_min)

    def get_configuration(self):
        return self.config.get('hour'), self.config.get('min')
