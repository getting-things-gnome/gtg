
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

    def onTaskOpened(self, plugin_api):
        """
        Adds the button when a task is opened.
        """
        self.plugin_api = plugin_api

        self.menu_item = Gtk.ModelButton.new()
        self.menu_item.props.text = _("Send via email")
        self.menu_item.connect("clicked", self.onTbTaskButton, plugin_api)
        self.plugin_api.add_menu_item(self.menu_item)

    def deactivate(self, plugin_api):
        """
        Desactivates the plugin.
        """
        pass

    def onTbTaskButton(self, widget, plugin_api):
        """
        When the user presses the button.
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

        Gio.AppInfo.launch_default_for_uri(f'mailto:gtg@example.com?{parameters}')
