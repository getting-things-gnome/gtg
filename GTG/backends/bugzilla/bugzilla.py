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
import urllib

from collections import namedtuple
from xmlrpc.client import Fault as XmlrpcFault

from gi.repository import GObject

from GTG.backends.bugzilla import exceptions
from GTG.backends.bugzilla.notification import send_notification
from GTG.backends.bugzilla.services import create_bugzilla_service
from GTG.core.translations import _
from GTG.tools.logger import Log

__all__ = ('BugInformationSyncTask',)

BugSyncTaskInfo = namedtuple('BugSyncTaskInfo',
                             ['scheme', 'net_location', 'bug_id'])
BUG_URL_PATTERN = re.compile(r'^(https?)://(.+)/show_bug\.cgi\?id=(\d+)$')

BUGZILLA_NO_PERM_MESSAGE = _("You have no permission to read bug <b>%s</b>.")
BUGZILLA_INVALID_MESSAGE = _("Bug ID <b>%s</b> is invalid")
BUGZILLA_NOT_EXIST_MESSAGE = _("Bug ID <b>%s</b> does not exist.")
BUGZILLA_BUG_SYNC_FAIL_MESSAGE = _("Failed to synchronize information for "
                                   "bug <b>%s</b> due to some unknown reason.")


def parse_bug_url(url):
    '''
    Extract URL data

    @param url: a string representing a URL
    @return: a tuple containing scheme, hostname, and a list of key-value
             queries
    '''
    r = urllib.parse.urlparse(url)
    return r.scheme, r.netloc, urllib.parse.parse_qs(r.query)


def convert_to_list(value):
    if isinstance(value, (list, tuple)):
        return list(value)
    else:
        return [value]


class BugInformationSyncTask(threading.Thread):

    def __init__(self, task, backend, **kwargs):
        ''' Initialize task data, where task is the GTG task object. '''
        self.task = task
        self.backend = backend
        super().__init__(**kwargs)

    def _collect_tags(self, bug):
        tags = []
        parameters = self.backend.get_parameters()

        if parameters['bugzilla-tag-use-priority']:
            tags += convert_to_list(bug.priority)

        if parameters['bugzilla-tag-use-severity']:
            tags += convert_to_list(bug.severity)

        if parameters['bugzilla-tag-use-component']:
            tags += convert_to_list(bug.component)

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

    @classmethod
    def get_bug_sync_task_info(cls, bug_url):
        '''
        Get synchronization information from task's title

        @param bug_url: the URL from task's title
        @return: an object representing task information. None if the URL is
        not valid.
        '''
        if BUG_URL_PATTERN.match(bug_url) is None:
            return None
        scheme, netloc, queries = parse_bug_url(bug_url)
        bug_id = queries.get('id', None)
        if bug_id is not None:
            bug_id = bug_id[0]
        return BugSyncTaskInfo(scheme=scheme,
                               net_location=netloc,
                               bug_id=bug_id)

    def run(self):
        bug_url = self.task.get_title()
        task_info = self.get_bug_sync_task_info(bug_url)
        if task_info is None:
            return

        try:
            bugzillaService = create_bugzilla_service(task_info.scheme,
                                                      task_info.net_location)
        except exceptions.BugzillaServiceNotExist:
            Log.warning('GTG does not support this bugzilla service yet.'
                        ' {0}'.format(task_info.net_location))
            return
        except exceptions.BugzillaServiceDisabled:
            Log.warning('Bugzilla service {0} is disabled now.'.format(
                task_info.net_location))
            return

        try:
            bug = bugzillaService.getBug(task_info.bug_id)
        except XmlrpcFault as err:
            err_no = err.faultCode
            if err_no == 100:
                error_no = exceptions.ERRNO_BUGZILLA_INVALID
                error_message = BUGZILLA_INVALID_MESSAGE % task_info.bug_id
            elif err_no == 101:
                error_no = exceptions.ERRNO_BUGZILLA_NOT_EXIST
                error_message = BUGZILLA_NOT_EXIST_MESSAGE % task_info.bug_id
            elif err_no == 102:
                error_no = exceptions.ERRNO_BUGZILLA_NO_PERM
                error_message = BUGZILLA_NO_PERM_MESSAGE % task_info.bug_id
            else:
                error_no = exceptions.ERRNO_BUGZILLA_UNKNOWN
                error_message = err.faultString

            send_notification(self.backend, error_no, error_message)
        except socket.gaierror as err:
            # NOTE: TBD, is it necessary to let user know this problem?
            Log.error('Failed to synchronize bug {0} due to a network problem '
                      '"{1}"'.format(task_info.bug_id, str(err)))
        except Exception as err:
            error_message = BUGZILLA_BUG_SYNC_FAIL_MESSAGE % task_info.bug_id
            send_notification(self.backend,
                              exceptions.ERRNO_BUGZILLA_BUG_SYNC_FAIL,
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


def sync_bug_info(task, backend):
    '''Synchronize bug information according to URL in task title

    This is the entry point to Bugzilla backend. Anyone who wants to
    synchronize a bug information according to a task's title, calls this
    method instead of initiating BugInformationSyncTask directly.

    Implementation of synchronization would be changed. Call this method is
    safe without any affection by the changes.
    '''
    task = BugInformationSyncTask(task, backend)
    task.daemon = True
    task.start()
