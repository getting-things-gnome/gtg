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

"""
- Sends the task by e-mail. (Luca Invernizzi)
- Added support for tags and subtasks. (Thibault Févry)
- Added support to send email from manager. (Kunaal Jain)
"""

from gi.repository import Gio
from gi.repository import Gtk
import urllib.request
import urllib.parse
import urllib.error

from GTG import _


class pluginSendEmail:
    """
    The plugin.
    """
    def __init__(self):
        """
        Initialize variables.
        """
        self.browser_plugin_api = None
        self.taskview_plugin_api = None
        self.tb_Managerbutton = None
        self.tb_Taskbutton = None

    def activate(self, plugin_api):
        """
        Adds the task button on manager.
        """
        self.browser_plugin_api = plugin_api
        self.req = plugin_api.get_requester()
        self.tb_Managerbutton = self.get_new_button()
        self.tb_Managerbutton.connect('clicked', self.onTbManagerButton, plugin_api)
        self.tb_Managerbutton.show()
        plugin_api.add_toolbar_item(self.tb_Managerbutton)
        plugin_api.set_active_selection_changed_callback(
            self.selection_changed)

    def onTaskOpened(self, plugin_api):
        """
        Adds the button when a task is opened.
        """
        # add a item (button) to the ToolBar
        self.taskview_plugin_api = plugin_api
        self.tb_Taskbutton = self.get_new_button()
        self.tb_Taskbutton.set_sensitive(True)
        self.tb_Taskbutton.connect('clicked', self.onTbTaskButton, plugin_api)
        self.tb_Taskbutton.show()
        plugin_api.add_toolbar_item(self.tb_Taskbutton)

    def deactivate(self, plugin_api):
        """
        Desactivates the plugin.
        """
        # everything should be removed, in case a task is currently opened

        if self.tb_Taskbutton:
            self.taskview_plugin_api.remove_toolbar_item(self.tb_Taskbutton)
            self.tb_Taskbutton = None
            self.browser_plugin_api.remove_toolbar_item(self.tb_Managerbutton)
            self.tb_Managerbutton = None

        if self.tb_Managerbutton:
            self.browser_plugin_api.remove_toolbar_item(self.tb_Managerbutton)
            self.tb_Managerbutton = None



    def selection_changed(self, selection):
        """
        To select multiple tasks in manager
        deactivates button if no task selection_changed
        """
        if selection.count_selected_rows() > 0:
            self.tb_Managerbutton.set_sensitive(True)
        else:
            self.tb_Managerbutton.set_sensitive(False)

    def get_new_button(self):
        """ Initialize a new button """
        button = Gtk.ToolButton()
        button.set_sensitive(False)
        button.set_icon_name('mail-send')
        button.set_is_important(True)
        button.set_label(_("Send via email"))
        return button

    def onTbTaskButton(self, widget, plugin_api):
        """
        When the user presses the button in task view.
        """
        task = plugin_api.get_ui().get_task()
        self.sendEmail(task)

    def onTbManagerButton(self, widget, plugin_api):
        """
        When the user presses the button in manager.
        """
        for tid in plugin_api.get_selected():
            task = self.req.get_task(tid)
            self.sendEmail(task)


    def sendEmail(self, task):
        """
        Body contains Status Tags, Subtasks and Content.
        """
        body = _("Status: %s") % (task.get_status()) + \
            _("\nTags: %s") % (", ".join(task.get_tags_name())) + \
            _("\nSubtasks:\n%s") % (
                "\n - ".join([i.get_title() for i in task.get_subtasks()])) + \
            _("\nTask content:\n%s") % (task.get_excerpt())

        # Title contains the title and the start and due dates.
        title = _("Task: %(task_title)s") % {'task_title': task.get_title()}

        parameters = urllib.parse.urlencode({'subject': title, 'body': body})
        parameters = parameters.replace('+', '%20')

        Gio.app_info_get_default_for_uri_scheme('mailto').launch_uris(
            ['mailto:' + 'gtg@example.com?' + parameters], None)
