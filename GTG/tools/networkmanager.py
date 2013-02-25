#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 - Lionel Dricot & Bertrand Rousseau
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

""" Communicate with Network Manager over its D-Bus API

API spec: http://projects.gnome.org/NetworkManager/developers/api/09/spec.html
"""

import dbus

# A network device is connected, with global network connectivity.
NM_STATE_CONNECTED_GLOBAL = 70


def is_connection_up():
    """ Returns True if GTG can access the Internet """
    bus = dbus.SystemBus()
    proxy = bus.get_object('org.freedesktop.NetworkManager',
                           '/org/freedesktop/NetworkManager')
    network_manager = dbus.Interface(proxy, 'org.freedesktop.NetworkManager')

    return network_manager.state() == NM_STATE_CONNECTED_GLOBAL

if __name__ == "__main__":
    print "is_connection_up() == %s" % is_connection_up()
