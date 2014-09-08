# -*- coding: utf-8 -*-
# Copyright (c) 2009 - Guillaume Desmottes <gdesmott@gnome.org>
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


# For display error message in the CustomInfoBar. Defining these variables is
# following the way of using CustomInfoBar currently.
ERRNO_BUGZILLA_NO_PERM = "bugzilla no permission"
ERRNO_BUGZILLA_INVALID = "Bug Id is invalid"
ERRNO_BUGZILLA_NOT_EXIST = "Bug Id does not exist."
ERRNO_BUGZILLA_BUG_SYNC_FAIL = "Fail to sync bug"
ERRNO_BUGZILLA_UNKNOWN = "Unknown bugzilla xmlrpc error"


class BugzillaServiceNotExist(Exception):
    pass


class BugzillaServiceDisabled(Exception):
    ''' Bugzilla service is disabled by user. '''

    def __init__(self, domain, *args, **kwargs):
        self.message = '%s is disabled.' % domain
        super(BugzillaServiceDisabled, self).__init__(*args, **kwargs)
