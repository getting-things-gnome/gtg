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

    def __init__(self, tag_completion, req):
        super().__init__()
        self.req = req
        self.tasks = []

        self._tag_entry.set_completion(tag_completion)

        # Rember values from last time
        self.last_tag_entry = _("NewTag")
        self.last_apply_to_subtasks = False

    def modify_tags(self, tasks):
        """ Show and run dialog for selected tasks """
        if len(tasks) == 0:
            return

        self.tasks = tasks

        self._tag_entry.set_text(self.last_tag_entry)
        self._tag_entry.grab_focus()
        self._apply_to_subtasks_check.set_active(self.last_apply_to_subtasks)

        self.show()

        self.tasks = []

    @Gtk.Template.Callback()
    def on_response(self, widget, response):
        if response == Gtk.ResponseType.APPLY:
            self.apply_changes()
        self.hide()

    def apply_changes(self):
        """ Apply changes """
        tags = parse_tag_list(self._tag_entry.get_text())

        # If the checkbox is checked, find all subtasks
        if self._apply_to_subtasks_check.get_active():
            for task_id in self.tasks:
                task = self.req.get_task(task_id)
                # FIXME: Python not reinitialize the default value of its
                # parameter therefore it must be done manually. This function
                # should be refractored # as far it is marked as depricated
                for subtask in task.get_subtasks():
                    subtask_id = subtask.get_id()
                    if subtask_id not in self.tasks:
                        self.tasks.append(subtask_id)

        for task_id in self.tasks:
            task = self.req.get_task(task_id)
            for tag, is_positive in tags:
                if is_positive:
                    task.add_tag(tag)
                else:
                    task.remove_tag(tag)
            task.sync()

        # Rember the last actions
        self.last_tag_entry = self._tag_entry.get_text()
        self.last_apply_to_subtasks = self._apply_to_subtasks_check.get_active()
# -----------------------------------------------------------------------------
