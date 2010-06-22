# -*- coding: utf-8 -*-
# pylint: disable-msg=W0201
# -----------------------------------------------------------------------------
# Getting Things Gnome! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2009 - Lionel Dricot & Bertrand Rousseau
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

from GTG     import _
from GTG.gtk import ViewConfig


class DeletionUI():
    def __init__(self,req):
        self.req = req
        self.tids_todelete = []
        # Load window tree
        self.builder = gtk.Builder() 
        self.builder.add_from_file(ViewConfig.DELETE_GLADE_FILE)
        signals = { "on_delete_confirm": self.on_delete_confirm,
                    "on_delete_cancel": lambda x: x.hide,}
        self.builder.connect_signals(signals)

    def on_delete_confirm(self, widget):
        """if we pass a tid as a parameter, we delete directly
        otherwise, we will look which tid is selected"""
        for tid in self.tids_todelete:
            task = self.req.get_task(tid)
            if task:
                task.delete()
            else:
                print "trying to delete task already deleted"
        self.tids_todelete = []

    def delete_tasks(self, tids=None):
        if tids:
            self.tids_todelete = tids
        #We must at least have something to delete !
        if len(self.tids_todelete) > 0:
            # We fill the text and the buttons' labels according to the number 
            # of tasks to delete
            label = self.builder.get_object("label1")
            label_text = label.get_text()
            cdlabel2 = self.builder.get_object("cd-label2")
            cdlabel3 = self.builder.get_object("cd-label3")
            cdlabel4 = self.builder.get_object("cd-label4")
            if len(self.tids_todelete) == 1:
                label_text = _("Deleting a task cannot be undone, and will delete the following task: ")
                cdlabel2.set_label(_("Are you sure you want to delete this task?"))
                cdlabel3.set_label(_("Keep selected task"))
                cdlabel4.set_label(_("Permanently remove task"))
            else:
                label_text = _("Deleting a task cannot be undone, and will delete the following tasks: ")
                cdlabel2.set_label(_("Are you sure you want to delete these tasks?"))
                cdlabel3.set_label(_("Keep selected tasks"))
                cdlabel4.set_label(_("Permanently remove tasks"))
            label_text = label_text[0:label_text.find(":") + 1]
            
            # I find the tasks that are going to be deleted
            tasks = []
            for tid in self.tids_todelete:
                def recursive_list_tasks(task_list, root):
                    """Populate a list of all the subtasks and 
                       their children, recursively"""
                    if root not in task_list:
                        task_list.append(root)
                        for i in root.get_subtasks():
                            recursive_list_tasks(task_list, i)
                task = self.req.get_task(tid)
                recursive_list_tasks(tasks, task)
            titles_list = [task.get_title() for task in tasks]
            titles = reduce (lambda x, y: x + "\n - " + y, titles_list)
            label.set_text("%s %s" % (label_text, "\n - " + titles))
            delete_dialog = self.builder.get_object("confirm_delete")
            delete_dialog.resize(1, 1)
            delete_dialog.run()
            delete_dialog.hide()
            #has the task been deleted ?
            return len(self.tids_todelete) == 0
        else:
            return False
