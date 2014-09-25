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


# Remove dependence of bugz due to that plugin just needs get action and
# it is done by Python xmlrpclib simply enough.
from xmlrpc.client import ServerProxy

from GTG.backends.bugzilla.bug import BugFactory
from GTG.backends.bugzilla.exceptions import BugzillaServiceDisabled
from GTG.backends.bugzilla.exceptions import BugzillaServiceNotExist


__all__ = ('BugzillaServiceFactory',)


class BugzillaService(object):
    name = 'Bugzilla Service'
    enabled = True
    tag_from = 'component'

    def __init__(self, scheme, net_location):
        self.scheme = scheme
        self.netloc = net_location

    def buildXmlRpcServerUrl(self):
        return '%(scheme)s://%(net_location)s/xmlrpc.cgi' % {
            'scheme': self.scheme, 'net_location': self.netloc,
        }

    def getProxy(self, server_url):
        return ServerProxy(server_url)

    def getBug(self, bug_id):
        server_url = self.buildXmlRpcServerUrl()
        proxy = self.getProxy(server_url)
        bugs = proxy.Bug.get({'ids': [bug_id]})
        comments = proxy.Bug.comments({'ids': [bug_id]})
        bug_data = bugs['bugs'][0]
        bug_data['gtg_cf_comments'] = comments['bugs'][str(bug_id)]['comments']
        return BugFactory.create(self.netloc, bug_data)


class GnomeBugzilla(BugzillaService):
    name = 'GNOME Bugzilla Service'
    tag_from = 'product'


class FreedesktopBugzilla(BugzillaService):
    ''' Bugzilla service of Freedesktop projects '''

    name = 'Freedesktop Bugzilla Service'


class GentooBugzilla(BugzillaService):
    ''' Bugzilla service of Gentoo project '''

    name = 'Gentoo Bugzilla Service'


class MozillaBugzilla(BugzillaService):
    ''' Bugzilla service of Mozilla products '''

    name = 'Mozilla Bugzilla Service'


class SambaBugzilla(BugzillaService):
    ''' Bugzilla service of Samba project '''

    enabled = False
    name = 'Samba Bugzilla Service'


class RedHatBugzilla(BugzillaService):
    ''' Bugzilla service provided by Red Hat '''

    name = 'Red Hat Bugzilla Service'

# Register bugzilla services manually, however store them in someplace and load
# them at once is better.
services = {
    'bugzilla.gnome.org': GnomeBugzilla,
    'bugs.freedesktop.org': FreedesktopBugzilla,
    'bugzilla.mozilla.org': MozillaBugzilla,
    'bugzilla.samba.org': SambaBugzilla,
    'bugs.gentoo.org': GentooBugzilla,
    'bugzilla.redhat.com': RedHatBugzilla,
}


class BugzillaServiceFactory(object):
    ''' Create a Bugzilla service using scheme and domain '''

    @staticmethod
    def create(scheme, net_location):
        '''
        Fatory method to create a new Bugzilla service

        @param scheme: the scheme part of bug URL
        @param net_location: consists of hostname and port, that is the key to
                             determine a concrete Bugzilla service
        @return: the instance of determined Bugzilla service
        @raises BugzillaServiceDisabled: when requested Bugzilla service is
                                         disabled now.
        @raises BugzillaServiceNotExist: when requested Bugzilla service does
                                         not exist.
        '''
        bz_service_cls = services.get(net_location, None)
        if bz_service_cls is None:
            raise BugzillaServiceNotExist(net_location)
        if not bz_service_cls.enabled:
            raise BugzillaServiceDisabled(net_location)
        return bz_service_cls(scheme, net_location)
