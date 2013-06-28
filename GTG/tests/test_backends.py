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

""" Tests for GTG backends.

Some of these tests will generate files in
xdg.BaseDirectory.xdg_data_home/gtg directory.
"""

# Standard imports
import unittest
import os
import xdg

# GTG imports
from GTG.backends import backend_localfile as localfile
from GTG.tools import cleanxml
from GTG.core import CoreConfig


class GtgBackendsUniTests(unittest.TestCase):
    """Tests for GTG backends."""

    def __init__(self, test):
        unittest.TestCase.__init__(self, test)
        self.taskfile = ''
        self.datafile = ''
        self.taskpath = ''
        self.datapath = ''

    def SetUp(self):
        CoreConfig().set_data_dir("./test_data")
        CoreConfig().set_conf_dir("./test_data")

    def test_localfile_get_name(self):
        """Tests for localfile/get_name function :
        - a string is expected.
        """
        res = localfile.Backend.get_name()
        expectedres = "backend_localfile"
        self.assertEqual(res, expectedres)

    def test_localfile_get_description(self):
        """Tests for localfile/get_description function :
        - a string is expected.
        """
        res = localfile.Backend.get_description()
        expectedres = "Your tasks are saved"
        self.assertEqual(res[:len(expectedres)], expectedres)

    def test_localfile_get_static_parameters(self):
        """Tests for localfile/get_static_parameters function:
        - a string is expected.
        """
        res = localfile.Backend.get_static_parameters()
        self.assertEqual(res['path']['type'], "string")

    def test_localfile_get_type(self):
        """Tests for localfile/get_type function:
        - a string is expected.
        """
        res = localfile.Backend.get_type()
        expectedres = "readwrite"
        self.assertEqual(res, expectedres)

    def test_localfile_backend_method3(self):
        """Tests for localfile/Backend/remove_task method:
        - parse task file to check if task has been removed.
        """
        self.create_test_environment()
        doc, configxml = cleanxml.openxmlfile(self.datapath, 'config')
        xmlproject = doc.getElementsByTagName('backend')
        for domobj in xmlproject:
            dic = {}
            if domobj.hasAttribute("module"):
                dic["module"] = str(domobj.getAttribute("module"))
                dic["pid"] = str(domobj.getAttribute("pid"))
                dic["xmlobject"] = domobj
                dic["Enabled"] = True
                dic["path"] = self.taskpath
        beobj = localfile.Backend(dic)
        expectedres = True
        beobj.remove_task("0@1")
        beobj.quit()
        dataline = open(self.taskpath, 'r').read()
        if "0@1" in dataline:
            res = False
        else:
            res = True
        expectedres = True
        self.assertEqual(res, expectedres)

    def create_test_environment(self):
        """Create the test environment"""
        self.taskfile = 'test.xml'
        self.datafile = 'projectstest.xml'
        tasks = [
            '<?xml version="1.0" ?>\n',
            '<project>\n',
            '\t<task id="0@1" status="Active" tags="">\n',
            '\t\t<title>\n',
            '\t\t\tCeci est un test\n',
            '\t\t</title>\n',
            '\t</task>\n',
            '</project>\n',
        ]
        data = [
            '<?xml version="1.0" ?>\n',
            '<config>\n',
            '\t<backend filename="test.xml" module="localfile" pid="1"/>\n',
            '</config>\n',
        ]
        self.testdir = os.path.join(xdg.BaseDirectory.xdg_data_home, 'gtg')
        if not os.path.exists(self.testdir):
            os.makedirs(self.testdir)
        self.taskpath = os.path.join(self.testdir, self.taskfile)
        self.datapath = os.path.join(self.testdir, self.datafile)
        open(self.taskpath, 'w').writelines(tasks)
        open(self.datapath, 'w').writelines(data)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
