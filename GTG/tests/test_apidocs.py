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
import GTG
import os.path
import shutil
import uuid

from GTG.core import CoreConfig



class TestApiDocs(unittest.TestCase):
    """Test if the documentation still builds."""

    
    def test_pydoctor(self):
        if int(subprocess.call(['which', 'pydoctor'])):
            #if no pydoctor is present, abort the test w/out giving error
            return
        GTG_basedir = os.path.dirname(GTG.__file__)
        api_dir = os.path.join(GTG_basedir, 
                               'test_build_api-' + str(uuid.uuid4()))
        args = ['pydoctor', 
                '--add-package', GTG_basedir,
                '--make-html',
                '--html-output=' + api_dir , 
                '--project-name=GTG',
                '--project-url=http://gtg.fritalk.com/']
        assert(int(subprocess.call(args)) == 0)
        shutil.rmtree(api_dir)

def test_suite():
    CoreConfig().set_data_dir("./test_data")
    CoreConfig().set_conf_dir("./test_data")
    return unittest.TestLoader().loadTestsFromTestCase(TestApiDocs)
