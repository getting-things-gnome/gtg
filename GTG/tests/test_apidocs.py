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

"""Tests for the documentation."""

import unittest

import subprocess
#import GTG



class TestApiDocs(unittest.TestCase):
    """Test if the documentation still builds."""

    
    def test_pydoctor(self):
        args = ['pydoctor', '--add-package', 'GTG' ,'--make-html',
             '--html-output=doc/api',  '--project-name=GTG',
             '--project-url=http://gtg.fritalk.com/']
        assert(int(subprocess.call(args)) == 0)

def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestApiDocs)
