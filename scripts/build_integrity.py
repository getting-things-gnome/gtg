#!/usr/bin/env python2
# -*- coding: UTF-8 -*-
# Copyright © 2012 Izidor Matušov <izidor.matusov@gmail.com
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
import re

exclude_list = ['data/.*', 'po/.*', 'doc/.*', 'AUTHORS', 'CHANGELOG',
                'LICENSE', 'README', 'gtcli_bash_completion', 'gtg.desktop',
                'org.gnome.GTG.service', 'setup.py',
                ]

# Build MANIFEST and also run build action
if os.system("python setup.py sdist > /dev/null") != 0:
    print "sdist operation failed"
    sys.exit(1)

if os.system("python setup.py build > /dev/null") != 0:
    print "build operation failed"
    sys.exit(1)

manifest_files = []

for f in open('MANIFEST', 'r'):
    f = f.strip()
    if f == "" or f.startswith('#'):
        continue
    f = os.path.normpath(f)

    exclude = False
    for ex in exclude_list:
        if re.match(ex, f):
            exclude = True
            break
    if exclude:
        continue

    manifest_files.append(f)

build_files = []
for root, dirs, files in os.walk('build/'):
    for f in files:
        filename = os.path.join(root, f)
        filename = filename.split('/', 1)[1]
        if filename.startswith('lib.') or filename.startswith('scripts-'):
            filename = filename.split('/', 1)[1]

        build_files.append(filename)

missing_files = list(set(manifest_files) - set(build_files))
if len(missing_files) > 0:
    missing_files.sort()
    print "Missing build files:"
    print "\n".join("\t%s" % f for f in missing_files)
    sys.exit(1)
