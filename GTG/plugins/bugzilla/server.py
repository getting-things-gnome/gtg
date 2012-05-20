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

SERVER_TAG_PRODUCT = 1
SERVER_TAG_COMPONENT = 2

class ServersStore:
    def __init__(self):
        self.servers = {}

        # GNOME
        server = Server('bugzilla.gnome.org')
        server.tag = SERVER_TAG_PRODUCT
        self.add(server)

        # freedesktop.org
        server = Server('bugs.freedesktop.org')
        server.tag = SERVER_TAG_COMPONENT
        self.add(server)

        # Mozilla
        server = Server('bugzilla.mozilla.org')
        server.tag = SERVER_TAG_COMPONENT
        self.add(server)

        # Samba
        server = Server('bugzilla.samba.org')
        server.tag = SERVER_TAG_COMPONENT
        self.add(server)
        
        # GENTOO
        server = Server('bugs.gentoo.org')
        server.tag = SERVER_TAG_COMPONENT
        self.add(server)

    def add(self, server):
        self.servers[server.name] = server

    def get(self, name):
        return self.servers.get(name)

class Server:
    def __init__(self, name):
        self.name = name
        self.tag = None

    def get_tag(self, bug):
        if self.tag is None:
            return None
        elif self.tag == SERVER_TAG_PRODUCT:
            return bug.get_product()
        elif self.tag == SERVER_TAG_COMPONENT:
            return bug.get_component()
