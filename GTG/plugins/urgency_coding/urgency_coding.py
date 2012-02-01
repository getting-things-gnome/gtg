# -*- coding: utf-8 -*-
# Copyright (c) 2012 - XYZ <xyz@mail.com>
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

class pluginUrgencyCoding:
    
    def __init__(self):
        self.plugin_api = None
        self.req = None

    def activate(self, plugin_api):
        """ Plugin is activated """
        self.plugin_api = plugin_api
        self.req = self.plugin_api.get_requester()
        # Set color function
        self.plugin_api.set_bgcolor_func(self.bgcolor)

    def bgcolor(self, node_id, standard_color):
        node = self.req.get_task(node_id)
        print '%s => from %s until %s' % (node.get_title(), node.get_start_date(), node.get_due_date())
        # Return color for this node
        return '#000'

    def deactivate(self, plugin_api):
        """ Plugin is deactivated """
        self.plugin_api.set_bgcolor_func()
