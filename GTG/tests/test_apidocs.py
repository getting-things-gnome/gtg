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

""" Tests for the documentation. """

import unittest

import subprocess
import GTG
import os.path
import shutil
import uuid


class TestApiDocs(unittest.TestCase):
    """ Test if the documentation still builds. """

    def test_pydoctor(self):
        if int(subprocess.call(['which', 'pydoctor'], stdout=subprocess.PIPE)):
            # if no pydoctor is present, abort the test w/out giving error
            return
        GTG_basedir = os.path.dirname(GTG.__file__)
        api_dir = os.path.join(GTG_basedir, '..', 'tmp',
                               'test_build_api-' + str(uuid.uuid4()))
        if not os.path.isdir(api_dir):
            os.makedirs(api_dir)
        args = ['pydoctor',
                '--add-package', GTG_basedir,
                '--make-html',
                '--html-output=' + api_dir,
                '--project-name=GTG',
                '--project-url=http://gtg.fritalk.com/']
        # we suppress printing of errors to keep a clean output
        assert(int(subprocess.call(args,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)) == 0)
        shutil.rmtree(api_dir)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestApiDocs)
