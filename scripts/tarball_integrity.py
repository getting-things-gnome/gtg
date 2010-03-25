#!/usr/bin/python
# -*- coding: UTF-8 -*-
# Copyright © 2010 Luca Falavigna <dktrkranz@debian.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import tarfile
from glob import glob

tarlist = list()
dirlist = list()
exclude_list = ('dist/', 'build/','.bzr', 'test', 'pyc', 'scripts/', 'pot', \
                'HACKING', 'MANIFEST', 'Makefile', 'profile.py')

for t in glob('dist/*.tar.gz'):
    tarball = tarfile.open(t, 'r')
    files = tarball.getnames()
    tarball.close()
    for f in [f for f in files if not f.endswith('/')]:
        tarlist.append(f.split('/', 1)[1])

for root, dirs, files in os.walk('.'):
    for f in [f for f in files if not f.endswith('/')]:
        dirlist.append(os.path.join(root, f).split('/', 1)[1])

if len(tarlist):
    print 'Missing files in tarball:'
    for f in dirlist:
        if f and f not in tarlist:
            for ex in exclude_list:
                if f and f.count(ex):
                    f = None
                    continue
            if f:
                print f
