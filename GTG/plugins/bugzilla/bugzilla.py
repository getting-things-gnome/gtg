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
import threading
from urlparse import urlparse

from GTG.plugins.bugzilla.server import ServersStore
from GTG.plugins.bugzilla.bug import Bug


class pluginBugzilla:

    def __init__(self):
        self.servers = ServersStore()

    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        self.connect_id = plugin_api.get_ui().connect(
                        "task-added-via-quick-add", self.task_added_cb)

    def task_added_cb(self, sender, task_id):
        #this is a gobject callback that will block the Browser.
        #decoupling with a thread. All interaction with task and tags objects
        #(anything in a Tree) must be done with gobject.idle_add (invernizzi)
        thread = threading.Thread(target = self.__analyze_task,
                                  args = (task_id, ))
        thread.setDaemon(True)
        thread.start()

    def __analyze_task(self, task_id):
        task = self.plugin_api.get_requester().get_task(task_id)
        url = task.get_title()
        r = urlparse(url)
        if r.hostname is None:
            return

        server = self.servers.get(r.hostname)
        if server is None:
            return

        base = '%s://%s' % (r.scheme, server.name)

        # get the number of the bug
        try:
            nb = r.query.split('id=')[1]
        except IndexError:
            return

        try:
            bug = Bug(base, nb)
        except:
            return

        title = bug.get_title()
        if title is None:
            # can't find the title of the bug
            return

        gobject.idle_add(task.set_title, '#%s: %s' % (nb, title))

        text = "%s\n\n%s" % (url, bug.get_description())
        gobject.idle_add(task.set_text, text)

        tag = server.get_tag(bug)
        if tag is not None:
            gobject.idle_add(task.add_tag, '@%s' % tag)

    def deactivate(self, plugin_api):
        plugin_api.get_ui().disconnect(self.connect_id)
