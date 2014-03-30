# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2014 - Lionel Dricot & Bertrand Rousseau
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

from threading import Thread, Event
from unittest import TestCase
import time

from GTG.tools.interruptible import interruptible, _cancellation_point


class TestInterruptibleDecorator(TestCase):

    def setUp(self):
        self.quit_condition = False
        self.thread_started = Event()

    @interruptible
    def never_ending(self, cancellation_point):
        self.thread_started.set()
        while True:
            time.sleep(0.01)
            cancellation_point()

    def test_interruptible_decorator(self):
        """ Tests for the @interruptible decorator. """
        cancellation_point = lambda: _cancellation_point(
            lambda: self.quit_condition)
        thread = Thread(target=self.never_ending, args=(cancellation_point,))
        thread.start()

        # Wait until thread comes to live
        self.thread_started.wait()

        # Ask to it to quit within 20ms
        self.quit_condition = True
        time.sleep(0.02)

        # Thread is finished
        self.assertFalse(thread.is_alive())
