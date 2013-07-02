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

import gobject
import re
import threading
import xmlrpclib
from urlparse import urlparse

from services import BugzillaServiceFactory
from services import BugzillaServiceNotExist
from notification import send_notification

__all__ = ('pluginBugzilla', )

bugIdPattern = re.compile('^\d+$')
bugURLPattern = re.compile('^(https?)://(.+)/show_bug\.cgi\?id=(\d+)$')


class GetBugInformationTask(threading.Thread):

    def __init__(self, task, **kwargs):
        ''' Initialize task data, where task is the GTG task object. '''
        self.task = task
        super(GetBugInformationTask, self).__init__(**kwargs)

    def parseBugUrl(self, url):
        r = urlparse(url)
        queries = dict([item.split('=') for item in r.query.split('&')])
        return r.scheme, r.hostname, queries

    def run(self):
        bug_url = self.task.get_title()

        # We only handle bug URL. When task's title is not a bug URL, stop
        # handling quietly.
        if bugURLPattern.match(bug_url) is None:
            return

        scheme, hostname, queries = self.parseBugUrl(bug_url)

        bug_id = queries.get('id', None)
        if bugIdPattern.match(bug_id) is None:
            # FIXME: make some sensable action instead of returning silently.
            return

        try:
            bugzillaService = BugzillaServiceFactory.create(scheme, hostname)
        except BugzillaServiceNotExist:
            # Stop quietly when bugzilla cannot be found. Currently, I don't
            # assume that user enters a wrong hostname or just an unkown
            # bugzilla service.
            return

        try:
            bug = bugzillaService.getBug(bug_id)
        except xmlrpclib.Fault, err:
            code = err.faultCode
            if code == 100:  # invalid bug ID
                title = 'Invalid bug ID #%s' % bug_id
            elif code == 101:  # bug ID not exist
                title = 'Bug #%s does not exist.' % bug_id
            elif code == 102:  # Access denied
                title = 'Access denied to bug %s' % bug_url
            else:  # unrecoganized error code currently
                title = err.faultString

            send_notification(bugzillaService.name, title)
        except Exception, err:
            send_notification(bugzillaService.name, err.message)
        else:
            title = '#%s: %s' % (bug_id, bug.summary)
            gobject.idle_add(self.task.set_title, title)
            text = "%s\n\n%s" % (bug_url, bug.description)
            gobject.idle_add(self.task.set_text, text)

            tags = bugzillaService.getTags(bug)
            if tags is not None and tags:
                for tag in tags:
                    gobject.idle_add(self.task.add_tag, '@%s' % tag)


class pluginBugzilla:

    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        self.connect_id = plugin_api.get_ui().connect(
            "task-added-via-quick-add", self.task_added_cb)

    def task_added_cb(self, sender, task_id):
        # this is a gobject callback that will block the Browser.
        # decoupling with a thread. All interaction with task and tags objects
        #(anything in a Tree) must be done with gobject.idle_add (invernizzi)

        task = self.plugin_api.get_requester().get_task(task_id)
        bugTask = GetBugInformationTask(task)
        bugTask.setDaemon(True)
        bugTask.start()

    def deactivate(self, plugin_api):
        plugin_api.get_ui().disconnect(self.connect_id)
