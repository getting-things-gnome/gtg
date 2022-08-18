
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
"""

from gi.repository import Gio
from gi.repository import Gtk
import urllib.request
import urllib.parse
import urllib.error

from gettext import gettext as _


class SendEmailPlugin():

    ACTION_GROUP_PREF = "editor_plugin_email"

    def onTaskOpened(self, plugin_api):
        """
        Adds the button when a task is opened.
        """
        group = Gio.SimpleActionGroup()
        send_action = Gio.SimpleAction.new("send_as_email", None)
        send_action.connect("activate", self._on_send_activate, plugin_api)
        group.add_action(send_action)
        plugin_api.get_ui().insert_action_group(self.ACTION_GROUP_PREF, group)

        self.menu_item = Gio.MenuItem.new(
            _("Send via email"), ".".join([self.ACTION_GROUP_PREF, "send_as_email"])
        )
        plugin_api.add_menu_item(self.menu_item)

    def onTaskClosed(self, plugin_api):
        """
        Removes the button when a task is closed.
        """
        plugin_api.get_ui().insert_action_group(self.ACTION_GROUP_PREF, None)
        plugin_api.remove_menu_item(self.menu_item)

    def deactivate(self, plugin_api):
        """
        Desactivates the plugin.
        """
        pass

    def _on_send_activate(self, action, param, plugin_api):
        """
        When the user presses the button.
        """
        task = plugin_api.get_ui().get_task()

        # Body contains Status Tags, Subtasks and Content.
        body = _("Status: %s") % (task.status) + \
            _("\nTags: %s") % (", ".join(t.name for t in task.tags)) + \
            _("\nSubtasks: %s") % (
                "".join(["\n- "+subtask.title for subtask in task.children])) + \
            _("\nTask content:\n%s") % (task.content)

        # Title contains the title and the start and due dates.
        title = _("Task: %(task_title)s") % {'task_title': task.title}

        parameters = urllib.parse.urlencode({'subject': title, 'body': body})
        parameters = parameters.replace('+', '%20')

        Gio.AppInfo.launch_default_for_uri(f'mailto:gtg@example.com?{parameters}')
