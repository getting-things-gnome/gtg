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

""" Tests for the SyncMeme class """

import unittest
import datetime

from GTG.backends.syncengine import SyncMeme


class TestSyncMeme(unittest.TestCase):
    """ Tests for the SyncEngine object. """

    def test_which_is_newest(self):
        """ test the which_is_newest function """
        meme = SyncMeme()
        # tasks have not changed
        local_modified = datetime.datetime.now()
        remote_modified = datetime.datetime.now()
        meme.set_local_last_modified(local_modified)
        meme.set_remote_last_modified(remote_modified)
        self.assertEqual(
            meme.which_is_newest(local_modified, remote_modified),
            None)
        # we update the local
        local_modified = datetime.datetime.now()
        self.assertEqual(
            meme.which_is_newest(local_modified, remote_modified),
            'local')
        # we update the remote
        remote_modified = datetime.datetime.now()
        self.assertEqual(
            meme.which_is_newest(local_modified, remote_modified),
            'remote')


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(TestSyncMeme)
