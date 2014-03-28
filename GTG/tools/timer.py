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

""" General class for representing time and periodic time intervals in GTG"""

import datetime


class timer:

    def __init__(self):
        self.now = datetime.datetime.now()
        self.now = datetime.time(self.now.hour,
                                 self.now.minute, self.now.second)

    def seconds_before(self, time):
        """Returns number of seconds remaining before next refresh"""
        start = self.now.strftime("%H:%M:%S")
        end = time.strftime("%H:%M:%S")
        start_dt = datetime.datetime.strptime(start, '%H:%M:%S')
        end_dt = datetime.datetime.strptime(end, '%H:%M:%S')
        diff = (end_dt - start_dt)
        secs_to_refresh = diff.seconds
        return secs_to_refresh

    def interval_to_time(self, interval):
        """Convert user given periodic interval to time"""
        refresh_hour = self.now.hour + int(interval)
        refresh_time = datetime.time(refresh_hour,
                                     self.now.minute, self.now.second)
        return refresh_time
