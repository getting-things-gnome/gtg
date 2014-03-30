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

    def __init__(self, bug):
        ''' Initialize Bug object using bug object retrieved via Bugzilla
            service XMLRPC
        '''
        self.bug = bug

    @property
    def summary(self):
        return self.bug['summary']

    @property
    def product(self):
        return self.bug['product']

    @property
    def description(self):
        return self.bug['summary']

    @property
    def component(self):
        return self.bug['component']


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
    @staticmethod
    def create(serviceDomain, bug):
        return bugs[serviceDomain](bug)
