# j# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
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

'''Tests for bugzilla backend'''

__author__ = 'Chenxiong Qi'


import time
import unittest

from multiprocessing import Process
from xmlrpc.server import SimpleXMLRPCRequestHandler
from xmlrpc.server import SimpleXMLRPCServer
from xml.dom.minidom import parseString

import GTG.backends.bugzilla.bugzilla as bz_module

from GTG.backends import BackendFactory
from GTG.backends.bugzilla.bug import Bug
from GTG.backends.bugzilla.bug import bugs as bz_bugs
from GTG.backends.bugzilla.bugzilla import GetBugInformationTask
from GTG.backends.bugzilla.exceptions import BugzillaServiceDisabled
from GTG.backends.bugzilla.exceptions import BugzillaServiceNotExist
from GTG.backends.bugzilla.services import BugzillaService
from GTG.backends.bugzilla.services import create_bugzilla_service
from GTG.backends.bugzilla.services import services as bz_services
from GTG.core import CoreConfig
from GTG.core.datastore import DataStore
from GTG.core.requester import Requester

__all__ = ('TestBugzillaService',
           'TestBugzillaServiceFactory')


XMLRPC_HOST = 'localhost'
XMLRPC_PORT = 7777
BUG_URL_DOMAIN_PORT = '%s:%s' % (XMLRPC_HOST, XMLRPC_PORT)


class TestBugzillaServiceFactory(unittest.TestCase):
    '''Test Bugzilla service factory'''

    def setUp(self):
        self.gnome_bz_service = bz_services['bugzilla.gnome.org']
        self.freedesktop_bz_service = bz_services['bugs.freedesktop.org']
        self.mozilla_bz_service = bz_services['bugzilla.mozilla.org']

        self.org_gnome_enabled = self.gnome_bz_service.enabled
        self.org_freedesktop_enabled = self.freedesktop_bz_service.enabled
        self.org_mozilla_enabled = self.mozilla_bz_service.enabled

        # Change the predefined value for testing
        self.gnome_bz_service.enabled = True
        self.freedesktop_bz_service.enabled = True
        self.mozilla_bz_service.enabled = False

    def tearDown(self):
        # Restore the value of changed enabled to original value
        self.gnome_bz_service.enabled = self.org_gnome_enabled
        self.freedesktop_bz_service.enabled = self.org_freedesktop_enabled
        self.mozilla_bz_service.enabled = self.org_mozilla_enabled

    def test_create(self):
        self.assertRaises(BugzillaServiceNotExist,
                          create_bugzilla_service,
                          'https', 'bugs.mozilla.org')
        self.assertRaises(BugzillaServiceDisabled,
                          create_bugzilla_service,
                          'https', 'bugzilla.mozilla.org')
        self.assertRaises(BugzillaServiceNotExist,
                          create_bugzilla_service,
                          'http', 'xxxx')
        self.assertRaises(BugzillaServiceNotExist,
                          create_bugzilla_service,
                          'https', '')

        cls_bz_service = bz_services['bugs.freedesktop.org']
        sample_service = cls_bz_service('https', 'bugs.freedesktop.org')

        service = create_bugzilla_service('https',
                                                'bugs.freedesktop.org')
        self.assertEqual(service.scheme, sample_service.scheme)
        self.assertEqual(service.netloc, sample_service.netloc)


class XMLRPCClientMixin(object):

    def run_xmlrpc_server(self):
        self.xmlrpc_proc = run_fake_bugzilla_service()

    def terminate_xmlrpc_server(self):
        self.xmlrpc_proc.terminate()


class FakeBugzillaServiceMixin(object):

    def install_fake_bugzilla_service(self):
        '''Install fake bugzilla service and bug for testing'''
        self.bz_service_keyname = BUG_URL_DOMAIN_PORT

        bz_services.update({
            self.bz_service_keyname: FakeLocalhostBugzillaService,
        })
        bz_bugs.update({
            self.bz_service_keyname: FakeBug,
        })

    def uninstall_fake_bugzilla_service(self):
        '''Remove fake bugzilla service and bug'''
        del bz_services[self.bz_service_keyname]
        del bz_bugs[self.bz_service_keyname]


class TestBugzillaService(unittest.TestCase,
                          XMLRPCClientMixin,
                          FakeBugzillaServiceMixin):
    '''Test Bugzilla service'''

    def setUp(self):
        self.run_xmlrpc_server()

        # Sleeping in one minute to wait for XMLRPC service is ready to serve.
        # One minute is enough. However, if the service isn't ready in this
        # period of time, something wrong should happen.
        time.sleep(1)

        self.install_fake_bugzilla_service()

        self.local_bz_service = create_bugzilla_service(
            'http', self.bz_service_keyname)

    def tearDown(self):
        self.uninstall_fake_bugzilla_service()
        self.terminate_xmlrpc_server()

    def test_get_bug(self):
        bug = self.local_bz_service.getBug(2)
        self.assertEqual(str(bug.id), '2')

    # TODO:
    def test_get_wrong_bug(self):
        pass

    def test_get_tags(self):
        bug = self.local_bz_service.getBug(2)
        tags = self.local_bz_service.getTags(bug)
        self.assert_(isinstance(tags, list), 'tags should be a list object.')

        tags.sort()
        sample_tags = STOCK_FAKE_BUGS[2]['component'][:]
        sample_tags.sort()
        self.assertEqual(tags, sample_tags,
                         'tags does not equal to the sample.')


class TestBugzillaSyncTask(unittest.TestCase,
                           XMLRPCClientMixin,
                           FakeBugzillaServiceMixin):
    '''Test Bugzilla sync task for the synchronization service backend'''

    def setUp(self):
        '''
        Setup environment for synchronization task

        The environment must include following two aspects
        1. a XMLRPC server to response Bug.get invocation.
        2. a fake gobject module. Because, during the test, I don't want to
        wait the glib event loop to complete setting task's title. Immediate
        response is expected for test.
        3. a sample task, that is not stored in the backend storage.
        '''
        self.original_gobject = bz_module.gobject
        bz_module.gobject = FakeGObject()

        self.run_xmlrpc_server()
        self.install_fake_bugzilla_service()

        self.global_conf = CoreConfig()
        self.datastore = DataStore(global_conf=self.global_conf)
        self.requester = Requester(self.datastore, self.global_conf)
        self.task = self.requester.new_task()

        backend_factory = BackendFactory()
        self.backend_bugzilla = backend_factory.get_backend('backend_bugzilla')

        self.sample_bug = STOCK_FAKE_BUGS[1]

    def tearDown(self):
        # Have to remove stored tags from GTG stores, that is caused by the
        # Task.add_tag method.
        map(lambda tag_name: self.requester.remove_tag(tag_name),
            self.task.get_tags_name())

        self.requester.delete_task(self.task.get_id())
        self.uninstall_fake_bugzilla_service()
        self.terminate_xmlrpc_server()

        # IMPORTANT: to restore the original gobject module
        bz_module.gobject = self.original_gobject

    def test_sync_correct_bug_info(self):
        '''Sync a bug information without any error'''
        bug_url = 'http://%s/show_bug.cgi?id=%d' % (BUG_URL_DOMAIN_PORT,
                                                    self.sample_bug['id'])
        self.task.set_title(bug_url)

        sync_task = GetBugInformationTask(self.task, self.backend_bugzilla)
        sync_task.start()
        sync_task.join()

        sample_title = '#%s: %s' % (self.sample_bug['id'],
                                    self.sample_bug['summary'])
        test_title = self.task.get_title()
        self.assertEqual(test_title, sample_title)

        sample_text = '%s\n\n%s' % (bug_url, self.sample_bug['summary'])
        test_text = clean_task_content(self.task.get_text())
        self.assertEqual(test_text, sample_text)

        sample_tags = self.sample_bug['component'][:]
        sample_tags.sort()
        test_tags = [tag.get_name().strip('@') for tag in self.task.get_tags()]
        test_tags.sort()
        self.assertEqual(test_tags, sample_tags)


def clean_task_content(content):
    '''
    Get the raw content text without XML tags and task tags

    @param content: the content string returned by Task.get_text method.
    @return: the cleaned content
    '''
    xmldoc = parseString(content)
    root = xmldoc.documentElement
    # For this testing, the last element with type TextNode should be the one
    # I want.
    result = root.childNodes[-1].nodeValue
    return result.strip()


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


##############################################################################
# Fake objects and control methods for testing
#


class FakeGObject(object):
    '''Fake GObject to avoid to wait real gobject's event loop'''

    def idle_add(self, func, *args, **kwargs):
        return func(*args, **kwargs)


class FakeLocalhostBugzillaService(BugzillaService):
    '''Fake Bugzilla service running on localhost for testing'''

    name = 'Fake local Bugzilla Service'


class FakeBug(Bug):
    '''Fake Bug for testing'''


STOCK_FAKE_BUGS = {
    1: {
        'id': 1,
        'summary': '[RFE] add fake bugzilla service for testing',
        'component': ['Application', 'Database']
    },
    2: {
        'id': 2,
        'summary': '[FeatureRequest] bugzilla service should be '
                   'configurable',
        'component': ['Installer', 'GUI', 'DBus']
    }
}


class FakeBugzillaWSBug(object):
    '''Fake Bugzilla Webservice Bug'''

    def get(self, options):
        '''
        Get bugs

        @param options: a dictionary object, containing ids at least.
        @return: a list of bugs, each of those is a dictionary object.
        '''
        bugs = []
        ids = options.get('ids', ())
        for bug_id in ids:
            bugs.append(STOCK_FAKE_BUGS.get(int(bug_id)))
        return {
            'bugs': bugs,
            'faults': []
        }


class FakeBugzillaService(object):
    '''Fake Bugzilla servive'''

    def __init__(self):
        self.Bug = FakeBugzillaWSBug()


def run_fake_bugzilla_service():
    '''
    Run a fake Bugzilla service in a separate process

    @return: Popen object representing the process running fake Bugzilla
             service.
    '''
    proc = Process(target=run_xmlrpc_server)
    proc.start()
    return proc


class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/xmlrpc.cgi',)


def run_xmlrpc_server():
    '''
    Run the XMLRPC server hosting fake Bugzilla service

    This method will be invoked in the separate process launched for running
    the fake Bugzilla service.
    '''

    server = SimpleXMLRPCServer((XMLRPC_HOST, XMLRPC_PORT),
                                logRequests=False,
                                requestHandler=RequestHandler)
    server.register_instance(FakeBugzillaService(), allow_dotted_names=True)
    server.serve_forever()
