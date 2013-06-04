# -*- coding: utf-8 -*-

# Remove dependence of bugz due to that plugin just needs get action and
# it is done by Python xmlrpclib simply enough.
from xmlrpclib import ServerProxy

from bug import BugFactory

__all__ = ('BugzillaServiceFactory',)


class BugzillaService(object):
    name = 'Bugzilla Service'
    enabled = True
    tag_from = 'component'

    def __init__(self, scheme, domain):
        self.scheme = scheme
        self.domain = domain

    def buildXmlRpcServerUrl(self):
        return '%(scheme)s://%(domain)s/xmlrpc.cgi' % {
            'scheme': self.scheme, 'domain': self.domain,
        }

    def getProxy(self, server_url):
        return ServerProxy(server_url)

    def getBug(self, bug_id):
        server_url = self.buildXmlRpcServerUrl()
        proxy = self.getProxy(server_url)
        bugs = proxy.Bug.get({'ids': [bug_id, ]})
        return BugFactory.create(self.domain, bugs['bugs'][0])

    def getTags(self, bug):
        ''' Get a list of tags due to some bug attribute contains list rather
            than a string in some bugzilla service.
        '''
        tag_names = getattr(bug, self.tag_from, None)
        if tag_names is None:
            return []
        if not isinstance(tag_names, list):
            return [tag_names]
        return tag_names


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


class BugzillaServiceNotExist(Exception):
    pass


class BugzillaServiceDisabled(Exception):
    ''' Bugzilla service is disabled by user. '''

    def __init__(self, domain, *args, **kwargs):
        self.message = '%s is disabled.' % domain
        super(BugzillaServiceDisabled, self).__init__(*args, **kwargs)


class BugzillaServiceFactory(object):
    ''' Create a Bugzilla service using scheme and domain '''

    @staticmethod
    def create(scheme, domain):
        if domain in services:
            service = services[domain]
            if not service.enabled:
                raise BugzillaServiceDisabled(domain)
            return services[domain](scheme, domain)
        else:
            raise BugzillaServiceNotExist(domain)
