# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
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
""" A dialog for batch adding/removal of tags """

from gi.repository import Gtk

from gettext import gettext as _
from GTG.gtk.browser import GnomeConfig
from GTG.core.tag import parse_tag_list

@Gtk.Template(filename=GnomeConfig.MODIFYTAGS_UI_FILE)

class ModifyTagsDialog(Gtk.Dialog):
    """
    Dialog for batch adding/removal of tags
    """

    __gtype_name__ = "ModifyTagsDialog"

    _tag_entry = Gtk.Template.Child()
    _apply_to_subtasks_check = Gtk.Template.Child()

    def __init__(self, tag_completion, app):
        super().__init__()

        self.app = app
        self.tasks = []

        self._tag_entry.set_completion(tag_completion)

        # Rember values from last time
        self.last_tag_entry = _("NewTag")
        self.last_apply_to_subtasks = False


    def parse_tag_list(self, text):
        """ Parse a line of a list of tasks. User can specify if the tag is
        positive or not by prepending '!'.

        @param  text:  string entry from user
        @return: list of tupples (tag, is_positive)
        """

        result = []
        for tag in text.split():
            if tag.startswith('!'):
                tag = tag[1:]
                is_positive = False
            else:
                is_positive = True

            result.append((tag, is_positive))
        return result


    def modify_tags(self, tasks):
        """ Show and run dialog for selected tasks """

        if not tasks:
            return

        self.tasks = tasks

        self._tag_entry.set_text(self.last_tag_entry)
        self._tag_entry.grab_focus()
        self._apply_to_subtasks_check.set_active(self.last_apply_to_subtasks)

        self.show()

    @Gtk.Template.Callback()
    def on_response(self, widget, response):
        if response == Gtk.ResponseType.APPLY:
            self.apply_changes()

        self.hide()

    def apply_changes(self):
        """ Apply changes """

        tags = self.parse_tag_list(self._tag_entry.get_text())

        # If the checkbox is checked, find all subtasks
        if self._apply_to_subtasks_check.get_active():
            for task in self.tasks:
                for subtask in task.children:
                    if subtask not in self.tasks:
                        self.tasks.append(subtask)

        for task in self.tasks:
            for tag, is_positive in tags:
                _tag = self.app.ds.tags.new(tag)

                if is_positive:
                    task.add_tag(_tag)
                else:
                    task.remove_tag(_tag)

        self.app.ds.save()
        self.app.ds.tasks.notify('task_count_no_tags')

        # Rember the last actions
        self.last_tag_entry = self._tag_entry.get_text()
        self.last_apply_to_subtasks = self._apply_to_subtasks_check.get_active()
