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
import re

from gi.repository import GObject
from GTG.core.logger import log


class Timer(GObject.GObject):
    __signal_type__ = (GObject.SignalFlags.RUN_FIRST,
                       None,
                       [])

    __gsignals__ = {'refresh': __signal_type__}

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.timeout_source = None
        self.connect_to_dbus()
        self.time_changed()

    def connect_to_dbus(self):
        bus = dbus.SystemBus()
        bus.add_signal_receiver(self.on_prepare_for_sleep,
                                'PrepareForSleep',
                                'org.freedesktop.login1.Manager',
                                'org.freedesktop.login1')

    def seconds_until(self, time):
        """Returns number of seconds remaining before next refresh"""
        now = datetime.datetime.now()
        secs_to_refresh = time-now
        if secs_to_refresh.total_seconds() < 0:
            secs_to_refresh += datetime.timedelta(days=1)
        return int(secs_to_refresh.total_seconds()) + 1

    def on_prepare_for_sleep(self, sleeping):
        """Handle dbus prepare for sleep signal."""

        # Only emit the signal if we are resuming from suspend,
        # not preparing for it.
        if not sleeping:
            self.emit_refresh()

    def emit_refresh(self):
        """Emit Signal for workview to refresh"""

        self.emit("refresh")
        self.time_changed()
        return False

    def time_changed(self):
        refresh_time = datetime.datetime.combine(datetime.date.today(),
                                                 self.get_configuration())
        secs_to_refresh = self.seconds_until(refresh_time)
        if self.timeout_source:
            GObject.source_remove(self.timeout_source)

        self.timeout_source = GObject.timeout_add_seconds(secs_to_refresh,
                                                          self.emit_refresh)

    def set_configuration(self, time):
        self.config.set('hour', time.hour)
        self.config.set('min', time.minute)

    def get_configuration(self):
        try:
            return datetime.time(int(self.config.get('hour')),
                                 int(self.config.get('min')))
        except(ValueError):
            log.error("Invalid time values: %s:%s", self.config.get('hour'),
                      self.config.get('min'))
            return datetime.time(0, 0)

    def parse_time(self, time):
        """
        This function parses user input when setting
        start of the day in general preferences.
        input:  @time               user's input as string

        output: @hour               default format for hours
                @minute             default format for minutes
                @ValueError         raised if @time is not valid
        """
        time = time.strip()
        invalid_format = False
        # Format for HH:MM and optional am/pm
        match = re.match(r'^(?P<hour>[0-9]{1,2}):?(?P<minute>[0-9]{2})?'
                         r' ?(?P<am_pm>[ap]m)?$', time.lower())
        if match:
            hour = int(match.group('hour'))
            minute = int(match.group('minute') or 0)
            am_pm = match.group('am_pm')

            if am_pm == 'am' and int(hour) == 12:
                    hour = 0
            elif am_pm == 'pm':
                if 0 < int(hour) < 12:
                    hour = hour + 12
                elif hour == 12:
                    hour = 12
                elif hour > 12:
                    invalid_format = True

            if not invalid_format:
                return datetime.time(int(hour), int(minute))
            else:
                raise ValueError('This time value or format\
                                 is not allowed: {0}'.format(time))
        else:
            # The final attempt to parse the input
            return datetime.datetime.strptime(time, '%X')

    def get_formatted_time(self):
        """
        This function sets the correct, uncluttered format and is used
        in general preferences' time setting for the time widget.
        """
        formatted_time = self.get_configuration().strftime("%X")
        # We use comparison to a regular expression to attempt for
        # valid substring of the format HH:MM.
        return re.sub(r'([0-9]{1,2}:[0-9]{2}):[0-9]{2}', r'\1',
                      formatted_time)
