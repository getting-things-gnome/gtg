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

from gi.repository import GObject
import unittest
import uuid

from GTG.tests.signals_testing import SignalCatcher, GobjectSignalsManager


class TestSignalTesting(unittest.TestCase):

    def setUp(self):
        self.gobject_signal_manager = GobjectSignalsManager()
        self.gobject_signal_manager.init_signals()

    def tearDown(self):
        self.gobject_signal_manager.terminate_signals()

    def test_signal_catching(self):
        generator = FakeGobject()
        arg = str(uuid.uuid4())
        with SignalCatcher(self, generator, 'one') \
                as [signal_catched_event, signal_arguments]:
            generator.emit_signal('one', arg)
            signal_catched_event.wait()
        self.assertEqual(len(signal_arguments), 1)
        self.assertEqual(len(signal_arguments[0]), 1)
        one_signal_arguments = signal_arguments[0]
        self.assertEqual(arg, one_signal_arguments[0])


class FakeGobject(GObject.GObject):
    __gsignals__ = {'one': (GObject.SignalFlags.RUN_FIRST,
                               None, (str, )),
                    'two': (GObject.SignalFlags.RUN_FIRST,
                               None, (str, ))}

    def emit_signal(self, signal_name, argument):
        GObject.idle_add(self.emit, signal_name, argument)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestSignalTesting)
