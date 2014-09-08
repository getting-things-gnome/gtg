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

__all__ = ('BugFactory',)


class Bug(object):
    '''Represent a bug object'''

    def __init__(self, bug):
        '''
        Initialize Bug object using bug object retrieved via Bugzilla service
        XMLRPC
        '''
        self.bug = bug

    def __getattr__(self, name):
        value = self.bug.get(name, None)
        if value is None:
            raise AttributeError('Bug does not have attribute %s' % name)
        return value


class GnomeBug(Bug):
    pass


class FreedesktopBug(Bug):
    pass


class GentooBug(Bug):
    pass


class MozillaBug(Bug):
    pass


class SambaBug(Bug):
    pass


class RedHatBug(Bug):
    pass


bugs = {
    'bugzilla.gnome.org': GnomeBug,
    'bugs.freedesktop.org': FreedesktopBug,
    'bugzilla.mozilla.org': MozillaBug,
    'bugzilla.samba.org': SambaBug,
    'bugs.gentoo.org': GentooBug,
    'bugzilla.redhat.com': RedHatBug,
}


class BugFactory(object):
    '''Factory to create a concrete Bug object'''

    @staticmethod
    def create(bug_cls_key, bug):
        '''
        Create a concrete Bug object

        @param bug_cls_key: the key to determine the specific Bug class
        @param bug: a dictionary object parsed from the JSON representing a bug
                    returned from related Bugzilla service
        @return: the Bug object. None if no specific Bug class is found
        '''
        bug_cls = bugs.get(bug_cls_key, None)
        if bug_cls is None:
            return None
        else:
            return bug_cls(bug)
