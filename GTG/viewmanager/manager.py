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
import gtk
import gobject

import GTG
from GTG.viewmanager.delete_dialog import DeletionUI
from GTG.taskbrowser.browser import TaskBrowser
from GTG.taskeditor.editor            import TaskEditor
from GTG.viewmanager.dbuswrapper import DBusTaskWrapper
from GTG.tools                        import clipboard
from GTG.core.plugins.engine          import PluginEngine
from GTG.core.plugins.api             import PluginAPI

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
        self.pengine = None
        self.plugins = None
        self.plugin_api = None
        self.p_apis = []
                                 
        #Shared clipboard
        self.clipboard = clipboard.TaskClipboard(self.req)
        
        #Signals
        self.req.connect("task-modified", self.on_task_modified)
        
        #Browser
        #FIXME : the browser should not be built by default and should be a 
        # window like another and not necessary (like the editor)
        self.open_browser()
        
        #Deletion UI
        self.delete_dialog = DeletionUI(self.req)
        
        #Preferences windows
        #FIXME : put the preferences out of the browser and put them here
        
        #DBus
        #FIXME: DBus should not require the browser !
        DBusTaskWrapper(self.req, self.browser)
        
        #Plugins
        self._init_plugin_engine()

    def open_browser(self):
        if not self.browser:
            self.browser = TaskBrowser(self.req, self.config, \
                            opentask=self.open_task,\
                            closetask=self.close_task,\
                            deletetasks=self.delete_tasks,\
                            quit=self.close_browser, logger=self.logger)

    #FIXME : the browser should not be the center of the universe.
    # In fact, we should build a system where view can register themselves
    # as "stay_alive" views. As long as at least one "stay_alive" view
    # is registered, gtg keeps running. It quit only when the last 
    # "stay_alive view" is closed (and then unregistered).
    # Currently, the browser is our only "stay_alive" view.
    def close_browser(self,sender=None):
        self.quit()
    
    def _init_plugin_engine(self):
        #FIXME : the plugin engine should not require the browser.
        # It should be the browser that need the plugin engine
        # plugins - Init
        self.pengine = PluginEngine(GTG.PLUGIN_DIR)
        # loads the plugins in the plugin dir
        self.plugins = self.pengine.load_plugins()
        # initializes the plugin api class
        self.plugin_api = PluginAPI(window         = self.browser.window,
                                    config         = self.config,
                                    data_dir       = GTG.DATA_DIR,
                                    builder        = self.browser.builder,
                                    requester      = self.req,
                                    tagpopup       = self.browser.tagpopup,
                                    tagview        = self.browser.tags_tv,
                                    task           = None,
                                    texteditor     = None,
                                    quick_add_cbs  = self.browser.priv['quick_add_cbs'],
                                    browser        = self.browser,
                                    logger         = self.logger)
        self.p_apis.append(self.plugin_api)
        # enable some plugins
        if len(self.pengine.plugins) > 0:
            # checks the conf for user settings
            if "plugins" in self.config:
                if "enabled" in self.config["plugins"]:
                    plugins_enabled = self.config["plugins"]["enabled"]
                if "disabled" in self.config["plugins"]:
                    plugins_disabled = self.config["plugins"]["disabled"]
                for name, plugin in self.pengine.plugins.iteritems():
                    if name in plugins_enabled and name not in plugins_disabled:
                        plugin.enabled = True
                    else:
                        # plugins not explicitly enabled are disabled
                        plugin.enabled = False
        # initializes and activates each plugin (that is enabled)
        self.pengine.activate_plugins(self.p_apis)


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
                self.req, t, self.plugins, \
                self.delete_tasks, self.close_task, self.open_task, \
                self.get_tasktitle,taskconfig=self.task_config, \
                plugin_apis=self.p_apis,thisisnew=thisisnew,\
                clipboard = self.clipboard)
            #registering as opened
            self.opened_task[uid] = tv
        return tv

    def close_task(self, tid):
        # When an editor is closed, it should deregister itself.
        if tid in self.opened_task:
            del self.opened_task[tid]
        else:
            print "the %s editor was already unregistered" %tid
            
    def refresh_task(self,tid):
        if self.opened_task.has_key(tid):
            self.opened_task[tid].refresh_editor(refreshtext=True)
            
    def delete_tasks(self,tids):
        if self.delete_dialog.delete_tasks(tids):
            #FIXME: the editor should catch the close signal to close himself
            for t in tids:
                self.close_task(t)
            
    def get_tasktitle(self, tid):
        task = self.req.get_task(tid)
        if task:
            return task.get_title()
        else:
            return None
            
    def on_task_modified(self, sender, tid):
        if self.logger:
            self.logger.debug("Modify task with ID: %s" % tid)
        #We refresh the opened windows for that tasks,
        #his children and his parents
        #It might be faster to refresh every opened editor
        tlist = [tid]
        task = self.req.get_task(tid)
        if task:
            tlist += task.get_parents()
            tlist += task.get_children()
            for uid in tlist:
                self.refresh_task(uid)
            #if the modified task is active, we have to refresh everything
            #to avoid some odd stuffs when loading
            
### MAIN ###################################################################
    def main(self):
        gobject.threads_init()
        gtk.main()
        return 0
        
        
    def quit(self,sender=None):
        gtk.main_quit()
        #save opened tasks and their positions.
        open_task = []
        for otid in self.opened_task.keys():     
            open_task.append(otid)
            self.opened_task[otid].close()
        self.config["browser"]["opened_tasks"] = open_task
        
        # adds the plugin settings to the conf
        if len(self.pengine.plugins) > 0:
            self.config["plugins"] = {}
            self.config["plugins"]["disabled"] = \
              self.pengine.disabled_plugins().keys()
            self.config["plugins"]["enabled"] = \
              self.pengine.enabled_plugins().keys()
        # plugins are deactivated
        self.pengine.deactivate_plugins(self.p_apis)


