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
"""

from gi.repository import Gio
from gi.repository import Gtk
import urllib.request
import urllib.parse
import urllib.error

from GTG.core.translations import _


class SendEmailPlugin(object):

    def onTaskOpened(self, plugin_api):
        """
        Adds the button when a task is opened.
        """
        self.plugin_api = plugin_api
        # add a item (button) to the ToolBar
        tb_Taskicon = Gtk.Image()
        tb_Taskicon.set_from_icon_name('mail-send', 32)

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
        try:
            self.plugin_api.remove_toolbar_item(self.tb_Taskbutton)
        except:
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

        Gio.app_info_get_default_for_uri_scheme('mailto').launch_uris(
            ['mailto:' + 'gtg@example.com?' + parameters], None)
