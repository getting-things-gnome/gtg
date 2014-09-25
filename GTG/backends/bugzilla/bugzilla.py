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

import re
import threading
import socket

from xmlrpc.client import Fault as XmlrpcFault

from collections import namedtuple
from urllib.parse import urlparse

from gi.repository import GObject

from GTG import _
from GTG.tools.logger import Log

from GTG.backends.bugzilla.exceptions import BugzillaServiceDisabled
from GTG.backends.bugzilla.exceptions import BugzillaServiceNotExist
from GTG.backends.bugzilla.exceptions import ERRNO_BUGZILLA_BUG_SYNC_FAIL
from GTG.backends.bugzilla.exceptions import ERRNO_BUGZILLA_INVALID
from GTG.backends.bugzilla.exceptions import ERRNO_BUGZILLA_NO_PERM
from GTG.backends.bugzilla.exceptions import ERRNO_BUGZILLA_NOT_EXIST
from GTG.backends.bugzilla.exceptions import ERRNO_BUGZILLA_UNKNOWN
from GTG.backends.bugzilla.notification import send_notification
from GTG.backends.bugzilla.services import BugzillaServiceFactory

__all__ = ('GetBugInformationTask',)

BugSyncTaskInfo = namedtuple('BugSyncTaskInfo',
                             ['scheme', 'net_location', 'bug_id'])
bugURLPattern = re.compile('^(https?)://(.+)/show_bug\.cgi\?id=(\d+)$')

BUGZILLA_NO_PERM_MESSAGE = _("You have no permission to read bug <b>%s</b>.")
BUGZILLA_INVALID_MESSAGE = _("Bug ID <b>%s</b> is invalid")
BUGZILLA_NOT_EXIST_MESSAGE = _("Bug ID <b>%s</b> does not exist.")
BUGZILLA_BUG_SYNC_FAIL_MESSAGE = _("Failed to synchronize information for "
                                   "bug <b>%s</b> due to some unknown reason.")


def parseBugUrl(url):
    '''
    Extract URL data

    @param url: a string representing a URL
    @return: a tuple containing scheme, hostname, and a list of key-value
             queries
    '''
    r = urlparse(url)
    queries = dict([item.split('=') for item in r.query.split('&')])
    return r.scheme, r.netloc, queries


def get_bug_sync_task_info(bug_url):
    '''
    Get synchronization information from task's title

    @param bug_url: the URL from task's title
    @return: an object representing task information. None if the URL is not
             valid.
    '''
    if bugURLPattern.match(bug_url) is None:
        return None
    scheme, netloc, queries = parseBugUrl(bug_url)
    bug_id = queries.get('id', None)
    return BugSyncTaskInfo(scheme=scheme,
                           net_location=netloc,
                           bug_id=bug_id)


def tag_conv(value):
    if isinstance(value, (list, tuple)):
        return list(value)
    else:
        return [value]


class BugInformationSyncTask(threading.Thread):

    def __init__(self, task, backend, **kwargs):
        ''' Initialize task data, where task is the GTG task object. '''
        self.task = task
        self.backend = backend
        super(BugInformationSyncTask, self).__init__(**kwargs)

    def _collect_tags(self, bug):
        tags = []
        parameters = self.backend.get_parameters()

        if parameters['bugzilla-tag-use-priority']:
            tags += tag_conv(bug.priority)

        if parameters['bugzilla-tag-use-severity']:
            tags += tag_conv(bug.severity)

        if parameters['bugzilla-tag-use-component']:
            tags += tag_conv(bug.component)

        custom_tags = parameters['bugzilla-tag-customized']
        tags += custom_tags.split(',')

        return [tag.replace(' ', '_') for tag in tags]

    def add_tags(self, bug, bugzilla_service):
        '''Add tags to task

        Tags are determined from the configuration configured by user

        @param task: the task being synchronized
        @type: L{Task}
        @param bugzilla_service: instance of Bugzilla service
        @type: L{bugzillaService}
        '''
        tags = self._collect_tags(bug)
        if tags is not None and tags:
            for tag in tags:
                GObject.idle_add(self.task.add_tag, '@' + tag)

    def append_comment(self, bug, bug_url, bugzilla_service):
        '''Append comment to task content if user configured'''
        if self.backend.get_parameters()['bugzilla-add-comment']:
            text = bug.gtg_cf_comments[0]['text']
        else:
            text = "{0}\n\n{1}".format(bug_url, bug.summary)
        GObject.idle_add(self.task.set_text, text)

    def run(self):
        bug_url = self.task.get_title()
        task_info = get_bug_sync_task_info(bug_url)
        if task_info is None:
            return

        try:
            bugzillaService = BugzillaServiceFactory.create(
                task_info.scheme, task_info.net_location)
        except (BugzillaServiceNotExist, BugzillaServiceDisabled):
            # Stop quietly when bugzilla cannot be found. Currently, I don't
            # assume that user enters a wrong hostname or just an unkown
            # bugzilla service.
            return

        try:
            bug = bugzillaService.getBug(task_info.bug_id)
        except XmlrpcFault as err:
            err_no = err.faultCode
            if err_no == 100:
                error_no = ERRNO_BUGZILLA_INVALID
                error_message = BUGZILLA_INVALID_MESSAGE % task_info.bug_id
            elif err_no == 101:
                error_no = ERRNO_BUGZILLA_NOT_EXIST
                error_message = BUGZILLA_NOT_EXIST_MESSAGE % task_info.bug_id
            elif err_no == 102:
                error_no = ERRNO_BUGZILLA_NO_PERM
                error_message = BUGZILLA_NO_PERM_MESSAGE % task_info.bug_id
            else:
                error_no = ERRNO_BUGZILLA_UNKNOWN
                error_message = err.faultString

            send_notification(self.backend, error_no, error_message)
        except socket.gaierror as err:
            # NOTE: TBD, is it necessary to let user know this problem?
            Log.error('Failed to synchronize bug {0} due to a network problem '
                      '"{1}"'.format(task_info.bug_id, str(err)))
        except Exception as err:
            error_message = BUGZILLA_BUG_SYNC_FAIL_MESSAGE % task_info.bug_id
            send_notification(self.backend,
                              ERRNO_BUGZILLA_BUG_SYNC_FAIL,
                              error_message)
            Log.error('Failed to synchronize information of bug {0} from {1}. '
                      'Server error message "{2}"'.format(task_info.bug_id,
                                                          bugzillaService.name,
                                                          str(err)))
        else:
            title = '#%s: %s' % (task_info.bug_id, bug.summary)
            GObject.idle_add(self.task.set_title, title)

            self.append_comment(bug, bug_url, bugzillaService)
            self.add_tags(bug, bugzillaService)
