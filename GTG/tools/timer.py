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

from gi.repository import GObject


class Timer:

    def __init__(self):
        self.now = datetime.datetime.now()

    def seconds_before(self, time):
        """Returns number of seconds remaining before next refresh"""
        self.now = datetime.datetime.now()
        secs_to_refresh = (time-self.now).total_seconds()
        if secs_to_refresh < 0:
            secs_to_refresh = 86400 + int(secs_to_refresh)
        return secs_to_refresh

    def interval_to_time(self, interval):
        """Convert user given periodic interval to time"""
        self.now = datetime.datetime.now()
        refresh_hour = self.now.hour + int(interval)
        return datetime.datetime(self.now.year, self.now.month,
                                 self.now.day, refresh_hour,
                                 self.now.minute, self.now.second)

    def add_gobject_timeout(self, time, callback):
        return GObject.timeout_add_seconds(time, callback)
