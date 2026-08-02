# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2026 - the GTG contributors
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

import os
import time
import shutil
import tempfile
from unittest import TestCase

from GTG.core.datastore import Datastore


OLD = time.time() - 40 * 86_400
RECENT = time.time() - 2 * 86_400


class BackupDirTestCase(TestCase):
    """Common scaffolding: a fake data directory with its backup/ dir."""


    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.root, 'gtg')
        self.backup_dir = os.path.join(self.data_dir, 'backup')
        os.makedirs(self.backup_dir)
        self.main = os.path.join(self.data_dir, 'gtg_data.xml')
        self._write(self.main)


    def tearDown(self):
        shutil.rmtree(self.root)


    def _write(self, filepath, mtime=None, content='<data/>'):
        with open(filepath, 'w') as filedesc:
            filedesc.write(content)
        if mtime:
            os.utime(filepath, (mtime, mtime))
        return filepath


    def _daily(self, date, mtime=OLD):
        name = f'gtg_data.xml.{date}.bak'
        return self._write(os.path.join(self.backup_dir, name), mtime)


class TestPurgeBackups(BackupDirTestCase):
    """Regression tests for the purge targeting the wrong directory.

    purge_backups() used to walk the data directory instead of the
    backup directory: dated daily backups were never removed, while
    any file older than the cutoff in the data directory was silently
    deleted, including the pre-migration 0.6 files of users coming
    from 0.6."""


    def test_purge_does_not_touch_data_directory(self):
        for name in ('gtg_tasks.xml', 'tags.xml', 'projects.xml'):
            self._write(os.path.join(self.data_dir, name), OLD)

        Datastore.purge_backups(self.main)

        for name in ('gtg_tasks.xml', 'tags.xml', 'projects.xml'):
            self.assertTrue(
                os.path.exists(os.path.join(self.data_dir, name)),
                f'{name} must survive: the data directory is not a backup')


    def test_purge_removes_old_dated_dailies(self):
        old_daily = self._daily('2025-01-01', OLD)

        Datastore.purge_backups(self.main)

        self.assertFalse(os.path.exists(old_daily))


    def test_purge_keeps_recent_dailies(self):
        recent_daily = self._daily('2026-08-01', RECENT)

        Datastore.purge_backups(self.main)

        self.assertTrue(os.path.exists(recent_daily))


    def test_purge_keeps_rotating_baks_regardless_of_age(self):
        rotating = self._write(
            os.path.join(self.backup_dir, 'gtg_data.xml.bak.3'), OLD)

        Datastore.purge_backups(self.main)

        self.assertTrue(os.path.exists(rotating),
                        'rotating copies are managed by count, not age')


    def test_purge_ignores_foreign_files_in_backup_dir(self):
        foreign = self._write(
            os.path.join(self.backup_dir, 'notes.txt'), OLD)

        Datastore.purge_backups(self.main)

        self.assertTrue(os.path.exists(foreign))


    def test_purge_survives_missing_backup_dir(self):
        shutil.rmtree(self.backup_dir)

        Datastore.purge_backups(self.main)  # must not raise
