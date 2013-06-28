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

import threading


class Watchdog(object):
    '''
    a simple thread-safe watchdog.
    usage::
        with Watchdod(timeout, error_function):
            #do something
    '''

    def __init__(self, timeout, error_function):
        '''
        Just sets the timeout and the function to execute when an error occours

        @param timeout: timeout in seconds
        @param error_function: what to execute in case the watchdog timer
                               triggers
        '''
        self.timeout = timeout
        self.error_function = error_function

    def __enter__(self):
        '''Starts the countdown'''
        self.timer = threading.Timer(self.timeout, self.error_function)
        self.timer.start()

    def __exit__(self, type, value, traceback):
        '''Aborts the countdown'''
        try:
            self.timer.cancel()
        except:
            pass
        if value is None:
            return True
        return False
