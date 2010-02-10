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


# This is the UI manager. It will manage every GTG window and UI.

from GTG.taskbrowser.browser import TaskBrowser
from GTG.taskeditor.editor            import TaskEditor
from GTG.core.dbuswrapper import DBusTaskWrapper
from GTG.tools                        import clipboard

class Manager():

    def __init__(self,req,config,logger=None):
        self.config = config.conf_dict
        self.task_config = config.task_conf_dict
        self.req = req
        self.logger = logger
        # Editors
        self.opened_task  = {}   # This is the list of tasks that are already
                                 # opened in an editor of course it's empty
                                 # right now
                                 
        self.browser = None
                                 
        #Shared clipboard
        self.clipboard = clipboard.TaskClipboard(self.req)
        
        #FIXME : we should restore opened tasks here, not in the browser
        #also, browser should just be a window like another, to be restored or not

    def show_browser(self):
        self.browser = TaskBrowser(self.req, self.config, opentask=self.open_task,\
                        closetask=self.close_task, refreshtask=self.refresh_task,\
                        quit=self.quit, logger=self.logger)
        DBusTaskWrapper(self.req, self.browser)
        self.browser.main()
        
        
    def open_task(self, uid,thisisnew=False):
        """Open the task identified by 'uid'.

        If a Task editor is already opened for a given task, we present it.
        Else, we create a new one.
        """
        t = self.req.get_task(uid)
        tv = None
        if uid in self.opened_task:
            tv = self.opened_task[uid]
            tv.present()
        elif t:
            #FIXME : on_delete_task should not be in the browser but here
            tv = TaskEditor(
                self.req, t, self.browser.plugins, \
                self.browser.on_delete_task, self.close_task, self.open_task, \
                self.get_tasktitle,taskconfig=self.task_config, \
                plugin_apis=self.browser.p_apis,thisisnew=thisisnew,\
                clipboard = self.clipboard)
            #registering as opened
            self.opened_task[uid] = tv
        return tv

    def close_task(self, tid):
        # When an editor is closed, it should deregister itself.
        if tid in self.opened_task:
            del self.opened_task[tid]
            
    def refresh_task(self,tid):
        if self.opened_task.has_key(tid):
            self.opened_task[tid].refresh_editor(refreshtext=True)
            
    def get_tasktitle(self, tid):
        task = self.req.get_task(tid)
        return task.get_title()
        
        
    def quit(self):
        #save opened tasks and their positions.
        open_task = []
        for otid in self.opened_task.keys():     
            open_task.append(otid)
            self.opened_task[otid].close()
        self.config["browser"]["opened_tasks"] = open_task


