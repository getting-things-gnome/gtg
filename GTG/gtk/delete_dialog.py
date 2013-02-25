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


import gtk

from GTG import _, ngettext
from GTG.gtk import ViewConfig


class DeletionUI():

    MAXIMUM_TIDS_TO_SHOW = 5

    def __init__(self, req):
        self.req = req
        self.tids_todelete = []
        # Tags which must be updated
        self.update_tags = []
        # Load window tree
        self.builder = gtk.Builder()
        self.builder.add_from_file(ViewConfig.DELETE_GLADE_FILE)
        signals = {"on_delete_confirm": self.on_delete_confirm,
                   "on_delete_cancel": lambda x: x.hide, }
        self.builder.connect_signals(signals)

    def on_delete_confirm(self, widget):
        """if we pass a tid as a parameter, we delete directly
        otherwise, we will look which tid is selected"""
        for tid in self.tids_todelete:
            if self.req.has_task(tid):
                self.req.delete_task(tid, recursive=True)
        self.tids_todelete = []

        # Update tags
        for tagname in self.update_tags:
            tag = self.req.get_tag(tagname)
            tag.modified()
        self.update_tags = []

    def delete_tasks(self, tids=None):
        if tids:
            self.tids_todelete = tids
        # We must at least have something to delete !
        if len(self.tids_todelete) > 0:
            tasklist = []
            self.update_tags = []
            for tid in self.tids_todelete:

                def recursive_list_tasks(task_list, root):
                    """Populate a list of all the subtasks and
                       their children, recursively.

                       Also collect the list of affected tags
                       which should be refreshed"""
                    if root not in task_list:
                        task_list.append(root)
                        for tagname in root.get_tags_name():
                            if tagname not in self.update_tags:
                                self.update_tags.append(tagname)
                        for i in root.get_subtasks():
                            if i not in task_list:
                                recursive_list_tasks(task_list, i)

                task = self.req.get_task(tid)
                recursive_list_tasks(tasklist, task)

            # We fill the text and the buttons' labels according to the number
            # of tasks to delete
            label = self.builder.get_object("label1")
            label_text = label.get_text()
            cdlabel2 = self.builder.get_object("cd-label2")
            cdlabel3 = self.builder.get_object("cd-label3")
            cdlabel4 = self.builder.get_object("cd-label4")
            singular = len(tasklist)
            label_text = ngettext("Deleting a task cannot be undone, "
                                  "and will delete the following task: ",
                                  "Deleting a task cannot be undone, "
                                  "and will delete the following tasks: ",
                                  singular)
            cdlabel2.set_label(ngettext("Are you sure you want to delete this"
                                        " task?",
                                        "Are you sure you want to delete "
                                        "these tasks?",
                                        singular))

            cdlabel3.set_label(ngettext("Keep selected task",
                                        "Keep selected tasks",
                                        singular))
            cdlabel4.set_label(ngettext("Permanently remove task",
                                        "Permanently remove tasks",
                                        singular))
            label_text = label_text[0:label_text.find(":") + 1]

            # we don't want to end with just one task that doesn't fit the
            # screen and a line saying "And one more task", so we go a
            # little over our limit
            missing_titles_count = len(tasklist) - self.MAXIMUM_TIDS_TO_SHOW
            if missing_titles_count >= 2:
                tasks = tasklist[: self.MAXIMUM_TIDS_TO_SHOW]
                titles_suffix = _("\nAnd %d more tasks" % missing_titles_count)
            else:
                tasks = tasklist
                titles_suffix = ""

            titles = "".join("\n - " + task.get_title() for task in tasks)
            label.set_text(label_text + titles + titles_suffix)
            delete_dialog = self.builder.get_object("confirm_delete")
            delete_dialog.resize(1, 1)
            cancel_button = self.builder.get_object("cancel")
            cancel_button.grab_focus()
            if delete_dialog.run() != 1:
                tasklist = []
            delete_dialog.hide()
            return tasklist
        else:
            return []
