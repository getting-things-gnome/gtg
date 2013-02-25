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

""" Tests for interrupting cooperative threads """

from threading import Thread, Event
import time
import unittest

from GTG.tools.interruptible import interruptible, _cancellation_point


class TestInterruptible(unittest.TestCase):
    """ Tests for interrupting cooperative threads """

    def test_interruptible_decorator(self):
        """ Tests for the @interruptible decorator. """
        self.quit_condition = False
        cancellation_point = lambda: _cancellation_point(
            lambda: self.quit_condition)
        self.thread_started = Event()

        @interruptible
        def never_ending(cancellation_point):
            self.thread_started.set()
            while True:
                time.sleep(0.1)
                cancellation_point()
        thread = Thread(target=never_ending, args=(cancellation_point, ))
        thread.start()
        self.thread_started.wait()
        self.quit_condition = True
        countdown = 10
        while thread.is_alive() and countdown > 0:
            time.sleep(0.1)
            countdown -= 1
        self.assertFalse(thread.is_alive())


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestInterruptible)
