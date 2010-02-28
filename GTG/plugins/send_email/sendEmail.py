# -*- coding: utf-8 -*-
# Copyright (c) 2009 - Luca Invernizzi <invernizzi.l@gmail.com>
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
import sys
import gio
try:
    import pygtk
    pygtk.require("2.0")
except: # pylint: disable-msg=W0702
    sys.exit(1)
try:
    import gtk
except: # pylint: disable-msg=W0702
    sys.exit(1)
import urllib


class pluginSendEmail:

    def __init__(self):
        #GUI initialization
        self.builder = gtk.Builder()

    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        self.logger = self.plugin_api.get_logger()

    def onTaskClosed(self, plugin_api):
        pass

    def onTaskOpened(self, plugin_api):
        # add a item (button) to the ToolBar
        tb_Taskicon = gtk.Image()
        tb_Taskicon.set_from_icon_name('mail-send', 32)
        tb_Taskicon.show()
        self.tb_Taskbutton = gtk.ToolButton(tb_Taskicon)
        self.tb_Taskbutton.set_label("Send via email")
        self.tb_Taskbutton.connect('clicked', self.onTbTaskButton, plugin_api)
        self.task_separator = gtk.SeparatorToolItem()
        plugin_api.add_task_toolbar_item(self.task_separator)
        plugin_api.add_task_toolbar_item(self.tb_Taskbutton)

    def deactivate(self, plugin_api):
        #everything should be removed, in case a task is currently opened
        #we may not be loaded in the taskeditor, so we have to check
        if hasattr(self, "task_separator"):
            plugin_api.remove_task_toolbar_item(self.task_separator)
        if hasattr(self, "tb_Taskbutton"):
            print self.tb_Taskbutton
            plugin_api.remove_task_toolbar_item(self.tb_Taskbutton)
            print "ciao"

## HELPER FUNCTIONS ############################################################

    def __log(self, message):
        if self.logger:
            self.logger.debug(message)

## CORE FUNCTIONS ##############################################################

    def onTbTaskButton(self, widget, plugin_api):
        task = plugin_api.get_task()
        parameters = urllib.urlencode({'subject': task.get_title(),
                                       'body':    task.get_excerpt()})
        parameters = parameters.replace('+','%20')
        gio.app_info_get_default_for_uri_scheme('mailto').launch_uris( \
                ['mailto:gtg@example.com?' + parameters])
