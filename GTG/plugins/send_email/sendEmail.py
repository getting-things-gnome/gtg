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
        self.plugin_api = None
        self.tb_Managerbutton = None
        self.tb_Taskbutton= None

    def activate(self, plugin_api):
        """
        Calls the gtk function to show button on manager.
        """
        self.plugin_api = plugin_api
        self.req = self.plugin_api.get_requester()
        self._init_gtk(plugin_api)
        self.plugin_api.set_active_selection_changed_callback(
            self.selection_changed)

    def onTaskOpened(self, plugin_api):
        """
        Adds the button when a task is opened.
        """
        self.plugin_api = plugin_api
        # add a item (button) to the ToolBar
        tb_Taskicon = Gtk.Image()
        tb_Taskicon.set_from_icon_name('mail-send', 32)
        self.tb_Taskbutton= True
        self.tb_Taskbutton = Gtk.ToolButton.new(tb_Taskicon)
        self.tb_Taskbutton.set_label(_("Send via email"))
        self.tb_Taskbutton.set_tooltip_text("Send via email")
        self.tb_Taskbutton.connect('clicked', self.onTbTaskButton, plugin_api)
        self.tb_Taskbutton.show_all()

        plugin_api.add_toolbar_item(self.tb_Taskbutton)

    def deactivate(self, plugin_api):
        """
        Desactivates the plugin.
        """
        # everything should be removed, in case a task is currently opened

        if self.tb_Taskbutton:
            self.plugin_api.remove_toolbar_item(self.tb_Taskbutton)
            self.tb_Taskbutton = False
            self.plugin_api.remove_toolbar_item(self.tb_Managerbutton)
            self.tb_Managerbutton = False

        if self.tb_Managerbutton:
            self.plugin_api.remove_toolbar_item(self.tb_Managerbutton)
            self.tb_Managerbutton = False


## CORE FUNCTIONS #############################################################
    def selection_changed(self, selection):
        """
        To select multiple tasks in manager
        deactivates button if no task selection_changed
        """
        if selection.count_selected_rows() > 0:
            self.tb_Managerbutton.set_sensitive(True)
        else:
            self.tb_Managerbutton.set_sensitive(False)

    def _init_gtk(self, plugin_api):
        """ Initialize all the GTK widgets """
        self.tb_Managerbutton = True
        self.tb_Managerbutton = Gtk.ToolButton()
        self.tb_Managerbutton.set_sensitive(False)
        self.tb_Managerbutton.set_icon_name('mail-send')
        self.tb_Managerbutton.set_is_important(True)
        self.tb_Managerbutton.set_label(_("Send via email"))
        self.tb_Managerbutton.connect('clicked', self.onTbManagerButton, plugin_api)
        self.tb_Managerbutton.show()
        self.plugin_api.add_toolbar_item(self.tb_Managerbutton)

    def onTbTaskButton(self, widget, plugin_api):
        """
        When the user presses the button in task view.
        """
        task = plugin_api.get_ui().get_task()

        # Body contains Status Tags, Subtasks and Content.
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

    def onTbManagerButton(self, widget, plugin_api):
        """
        When the user presses the button in manager.
        """
        for tid in self.plugin_api.get_selected():
            task = self.req.get_task(tid)

        # Body contains Status Tags, Subtasks and Content.
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
