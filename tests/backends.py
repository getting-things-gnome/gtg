#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personnal organizer for the GNOME desktop
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

"""Unittests for GTG
Some of these tests will generated files in 
xdg.BaseDirectory.xdg_data_home/gtg directory.
"""

# Standard imports
import unittest
import os
import xdg

# GTG imports
from GTG.backends import localfile
from GTG.core import datastore
from GTG.tools import cleanxml


class GtgBackendsUniTests(unittest.TestCase):
    """Unittests for GTG backends"""

    def __init__(self, test):
        unittest.TestCase.__init__(self, test)
        self.taskfile = ''
        self.datafile = ''
        self.taskpath = ''
        self.datapath = ''
        

    def test_localfile_get_name(self):
        """Tests for localfile/get_name function :
        - a string is expected.
        """
        res = localfile.get_name()
        expectedres = "Local File"
        self.assertEqual(res, expectedres)

    def test_localfile_get_description(self):
        """Tests for localfile/get_description function :
        - a string is expected.
        """
        res = localfile.get_description()
        expectedres = "Your tasks are saved in an XML file located in \
your HOME folder"
        self.assertEqual(res, expectedres)

    def test_localfile_get_parameters(self):
        """Tests for localfile/get_parameters function : 
        - a string is expected.
        """
        res = localfile.get_parameters()
        expectedres = "string"
        self.assertEqual(res['filename'], expectedres)

    def test_localfile_get_features(self):
        """Tests for localfile/get_features function : 
        - an empty dictionary is expected.
        """
        res = localfile.get_features()
        expectedres = {}
        self.assertEqual(res, expectedres)

    def test_localfile_get_type(self):
        """Tests for localfile/get_type function : 
        - a string is expected.
        """
        res = localfile.get_type()
        expectedres = "readwrite"
        self.assertEqual(res, expectedres)

    def test_localfile_backend(self):
        """Tests for localfile/Backend Class : 
        - an empty list is expected
        """
        res = localfile.Backend({})
        expectedres = []
        self.assertEqual(res.get_tasks_list(), expectedres)

    def test_localfile_backend_method1(self):
        """Tests for localfile/Backend/new_task_id method : 
        - None value is expected.
        """
        res = localfile.Backend({})
        expectedres = None
        self.assertEqual(res.new_task_id(), expectedres)

    def test_localfile_backend_method2(self):
        """Tests for localfile/Backend/get_tasks_list method : 
        - an integer value is expected.
        """
        self.create_test_environment()
        doc, configxml = cleanxml.openxmlfile(self.datapath, 'config')
        xmlproject = doc.getElementsByTagName('backend')
        for domobj in xmlproject:
            dic = {}
            if domobj.hasAttribute("module") :
                dic["module"] = str(domobj.getAttribute("module"))
                dic["pid"] = str(domobj.getAttribute("pid"))
                dic["xmlobject"] = domobj
                dic["filename"] = self.taskfile
        res = localfile.Backend(dic)
        expectedres = 1
        self.assertEqual(len(res.get_tasks_list()), expectedres)

    def test_localfile_backend_method3(self):
        """Tests for localfile/Backend/remove_task method : 
        - parse task file to check if task has been removed.
        """
        self.create_test_environment()
        doc, configxml = cleanxml.openxmlfile(self.datapath, 'config')
        xmlproject = doc.getElementsByTagName('backend')
        for domobj in xmlproject:
            dic = {}
            if domobj.hasAttribute("module") :
                dic["module"] = str(domobj.getAttribute("module"))
                dic["pid"] = str(domobj.getAttribute("pid"))
                dic["xmlobject"] = domobj
                dic["filename"] = self.taskfile
        beobj = localfile.Backend(dic)
        expectedres = True
        beobj.remove_task("0@1")
        dataline = open(self.taskpath, 'r').read()
        if "0@1" in dataline:
            res = False
        else:
            res = True
        expectedres = True
        self.assertEqual(res, expectedres)

    def test_localfile_backend_method4(self):
        """Tests for localfile/Backend/get_task method : 
        - Compares task titles to check if method works.
        """
        self.create_test_environment()
        doc, configxml = cleanxml.openxmlfile(self.datapath, 'config')
        xmlproject = doc.getElementsByTagName('backend')
        for domobj in xmlproject:
            dic = {}
            if domobj.hasAttribute("module") :
                dic["module"] = str(domobj.getAttribute("module"))
                dic["pid"] = str(domobj.getAttribute("pid"))
                dic["xmlobject"] = domobj
                dic["filename"] = self.taskfile
        beobj = localfile.Backend(dic)
        dstore = datastore.DataStore()
        newtask = dstore.new_task(tid="0@2", pid="1", newtask=True)
        beobj.get_task(newtask, "0@1")
        self.assertEqual(newtask.get_title(), u"Ceci est un test")

    def test_localfile_backend_method5(self):
        """Tests for localfile/Backend/set_task method : 
        - parses task file to check if new task has been stored.
        """
        self.create_test_environment()
        doc, configxml = cleanxml.openxmlfile(self.datapath, 'config')
        xmlproject = doc.getElementsByTagName('backend')
        for domobj in xmlproject:
            dic = {}
            if domobj.hasAttribute("module") :
                dic["module"] = str(domobj.getAttribute("module"))
                dic["pid"] = str(domobj.getAttribute("pid"))
                dic["xmlobject"] = domobj
                dic["filename"] = self.taskfile
        beobj = localfile.Backend(dic)
        dstore = datastore.DataStore()
        newtask = dstore.new_task(tid="0@2", pid="1", newtask=True)
        beobj.set_task(newtask)
        dataline = open(self.taskpath, 'r').read()
        if "0@2" in dataline:
            res = True
        else:
            res = False
        expectedres = True
        self.assertEqual(res, expectedres)

    def create_test_environment(self):
        """Create the test environment"""
        self.taskfile = 'test.xml'
        self.datafile = 'projectstest.xml'
        tasks = ['<?xml version="1.0" ?>\n', '<project>\n', 
            '\t<task id="0@1" status="Active" tags="">\n', '\t\t<title>\n', 
            '\t\t\tCeci est un test\n', '\t\t</title>\n', '\t</task>\n', 
            '</project>\n']
        data = ['<?xml version="1.0" ?>\n', '<config>\n', 
            '\t<backend filename="test.xml" module="localfile" pid="1"/>\n', 
            '</config>\n']
        testdir = os.path.join(xdg.BaseDirectory.xdg_data_home, 'gtg')
        if not os.path.exists(testdir):
            os.makedirs(testdir)
        self.taskpath = os.path.join(testdir, self.taskfile)
        self.datapath = os.path.join(testdir, self.datafile)
        open(self.taskpath, 'w').writelines(tasks)
        open(self.datapath, 'w').writelines(data)

if __name__ == '__main__': 
    unittest.main()

