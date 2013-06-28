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

""" Unit tests for GTG. """

import unittest
import os
import sys

TEST_MODULE_PREFIX = "GTG.tests."


def test_suite():
    '''
    Automatically loads all the tests in the GTG/tests directory and returns a
    unittest.TestSuite filled with them
    '''
    # find all the test files
    test_dir = os.path.dirname(__file__)
    test_files = filter(lambda f: f.endswith(".py") and f.startswith("test_"),
                        os.listdir(test_dir))

    # Loading of the test files and adding to the TestSuite
    test_suite = unittest.TestSuite()
    for module_name in [f[:-3] for f in test_files]:
            # module loading
            module_path = TEST_MODULE_PREFIX + module_name
            module = __import__(module_path)
            sys.modules[module_path] = module
            globals()[module_path] = module
            # fetching the testsuite

            # Crude hack to satisfy both GIT repository and GTG trunk
            if TEST_MODULE_PREFIX == "GTG.tests.":
                tests = getattr(module, "tests")
            else:
                tests = module

            a_test = getattr(tests, module_name)
            # adding it to the unittest.TestSuite
            test_suite.addTest(getattr(a_test, "test_suite")())

    return test_suite
