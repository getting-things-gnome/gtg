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

from urlparse import urlparse
from server import ServersStore
from bug import Bug

class pluginBugzilla:

    def __init__(self):
        self.servers = ServersStore()

    def activate(self, plugin_api):
        plugin_api.register_quick_add_cb(self.task_added_cb)

    def task_added_cb(self, task):
        url = task.get_title()
        r = urlparse(url)

        server = self.servers.get(r.hostname)
        if server is None:
            return

        base = '%s://%s' % (r.scheme, server.name)
        nb = r.query.split('=')[1]
        bug = Bug(base, nb)

        task.set_title('#%s: %s' % (nb, bug.get_title()))
        task.set_text(url)

        tag = server.get_tag(bug)
        if tag is not None:
            task.add_tag('@%s' % tag)

    def deactivate(self, plugin_api):
        plugin_api.unregister_quick_add_cb(self.task_added_cb)

    def onTaskOpened(self, plugin_api):
        pass
