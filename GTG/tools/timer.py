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


class timer:

    def __init__(self):
        self.now = datetime.datetime.now()

    def seconds_before(self, time):
        """Returns number of seconds remaining before next refresh"""
        secs_to_refresh = (time-self.now).seconds
        return (secs_to_refresh+1)

    def interval_to_time(self, interval):
        """Convert user given periodic interval to time"""
        refresh_hour = self.now.hour + int(interval)
        refresh_time = datetime.datetime(self.now.year, self.now.month,
                                         self.now.day, refresh_hour,
                                         self.now.minute, self.now.second)
        return refresh_time
