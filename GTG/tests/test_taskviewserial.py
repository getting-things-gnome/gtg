# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2009 - Lionel Dricot & Bertrand Rousseau
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

"""Tests for GTG backends.

Some of these tests will generate files in
xdg.BaseDirectory.xdg_data_home/gtg directory.
"""

# Standard imports
import unittest

from GTG.gtk.editor import taskviewserial
from GTG.core import CoreConfig
    
class GtgBackendsUniTests(unittest.TestCase):
    """Tests for GTG backends."""

    def __init__(self, test):
        unittest.TestCase.__init__(self, test)
        self.taskfile = ''
        self.datafile = ''
        self.taskpath = ''
        self.datapath = ''

    def test_unserializer_parsexml(self):
        """Tests for parsexml in unserializing :
        - the task should be preserved
        """
        taskview = None
        unserial = taskviewserial.Unserializer(taskview)
        
        
def test_suite():
    CoreConfig().set_data_dir("./test_data")
    CoreConfig().set_conf_dir("./test_data")
    return unittest.TestLoader().loadTestsFromName(__name__)
