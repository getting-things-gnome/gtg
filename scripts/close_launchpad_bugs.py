#!/usr/bin/python
# -*- coding: UTF-8 -*-
# Copyright © 2009 Luca Falavigna <dktrkranz@debian.org>
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

import sys, os, re
from launchpadlib.launchpad import Launchpad, EDGE_SERVICE_ROOT
from launchpadlib.credentials import Credentials
from re import findall
from urllib import urlopen

def lp_login():
        cachedir = os.path.expanduser('~/.cache/launchpadlib/')
        if not os.path.isdir(cachedir):
                os.makedirs(cachedir)
        creddir = os.path.expanduser("~/.cache/lp_credentials")
        if not os.path.isdir(creddir):
                os.makedirs(creddir)
                os.chmod(creddir, 0700)
        try:
                credfile = open(os.path.join(creddir, 'close_launchpad_bugs.txt'), 'r')
                credentials = Credentials()
                credentials.load(credfile)
                credfile.close()
                launchpad = Launchpad(credentials, EDGE_SERVICE_ROOT, cachedir)
        except IOError:
                launchpad = Launchpad.get_token_and_login('close_launchpad_bugs', EDGE_SERVICE_ROOT, cachedir)
                credfile = open(os.path.join(creddir, 'close_launchpad_bugs.txt'), 'w')
                launchpad.credentials.save(credfile)
                credfile.close()
        return launchpad

if len(sys.argv) != 2:
    print 'Usage: %s <release>' % sys.argv[0]
    sys.exit(1)

data = urlopen('https://launchpad.net/gtg/+milestone/%s' % sys.argv[1]).read()
bugs = findall('<a href="\S+/bugs/(\d+)">', data)
launchpad = lp_login()
if not 'gtg' in [e.name for e in launchpad.people[launchpad.me].super_teams]:
    print 'You are not a GTG developer, exiting.'
    sys.exit(0)
for bugno in bugs:
    try:
        bug = launchpad.bugs[bugno]
        for task in bug.bug_tasks:
            if task.bug_target_name == 'gtg' and task.status == 'Fix Committed':
                task.status = 'Fix Released'
                task.lp_save()
                print 'Bug %s marked as Fix Released' % bugno
    except:
        print 'UNABLE TO PROCESS BUG #%s' % bugno
        pass
