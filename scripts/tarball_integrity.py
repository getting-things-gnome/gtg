#!/usr/bin/env python2
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
import sys
import tarfile
from glob import glob

tarlist = list()
dirlist = list()
exclude_list = ('dist/', 'build/', '.bzr', 'test', 'pyc', 'scripts/', 'tmp/',
                'pot', 'HACKING', 'MANIFEST', 'Makefile', 'profile.py', '.swp')

for t in glob('dist/*.tar.gz'):
    tarball = tarfile.open(t, 'r')
    files = tarball.getnames()
    tarball.close()
    for f in [f for f in files if not f.endswith('/')]:
        # Skip the general directory
        if '/' not in f:
            continue
        tarlist.append(f.split('/', 1)[1])

for root, dirs, files in os.walk('.'):
    for f in files:
        if f.endswith('/'):
            continue

        filename = os.path.join(root, f).split('/', 1)[1]

        exclude = False
        for ex in exclude_list:
            if filename.count(ex):
                exclude = True
                break
        if exclude:
            continue

        dirlist.append(filename)

missing = list(set(dirlist) - set(tarlist))
if len(missing) > 0:
    missing.sort()
    print 'Missing files in tarball:'
    print '\n'.join("\t%s" % f for f in missing)
    sys.exit(1)
