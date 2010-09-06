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
"""
Manager loads the prefs and launches the gtk main loop
"""
try:
    import pygtk
    pygtk.require('2.0')
except: # pylint: disable-msg=W0702
    raise SystemExit(1)

import gtk
import gobject

import GTG
from GTG.gtk.delete_dialog   import DeletionUI
from GTG.gtk.browser.browser import TaskBrowser
from GTG.gtk.editor.editor   import TaskEditor
from GTG.gtk.preferences     import PreferencesDialog
from GTG.gtk.dbuswrapper     import DBusTaskWrapper
from GTG.tools               import clipboard
from GTG.core.plugins.engine import PluginEngine
from GTG.core.plugins.api    import PluginAPI
from GTG.tools.logger        import Log



class Manager:
    

    ############## init #####################################################
    def __init__(self, req, config):
        self.config_obj = config
        self.config = config.conf_dict
        self.task_config = config.task_conf_dict
        self.req = req
        # Editors
        self.opened_task  = {}   # This is the list of tasks that are already
                                 # opened in an editor of course it's empty
                                 # right now
                                 
        self.browser = None
        self.__start_browser_hidden = False
                                 
        #Shared clipboard
        self.clipboard = clipboard.TaskClipboard(self.req)
        
        #Browser
        #FIXME : the browser should not be built by default and should be a 
        # window like another and not necessary (like the editor)
        self.open_browser()
        
        self.__init_plugin_engine()
        
        if not self.__start_browser_hidden:
            self.show_browser()
        
        #Deletion UI
        self.delete_dialog = None
        
        #Preferences and Backends windows
        # Initialize  dialogs
        self.preferences_dialog = None
        
        #DBus
        DBusTaskWrapper(self.req, self)
        
    def __init_plugin_engine(self):
        self.pengine = PluginEngine(GTG.PLUGIN_DIR)
        # initializes the plugin api class
        self.plugin_api = PluginAPI(self.req, self)
        self.pengine.register_api(self.plugin_api)
        # checks the conf for user settings
        try:
            plugins_enabled = self.config["plugins"]["enabled"]
        except KeyError:
            plugins_enabled = []
        for plugin in self.pengine.get_plugins():
            plugin.enabled = plugin.module_name in plugins_enabled
        # initializes and activates each plugin (that is enabled)
        self.pengine.activate_plugins()
        
    ############## Browser #################################################

    def open_browser(self):
        if not self.browser:
            self.browser = TaskBrowser(self.req, self, self.config)

    #FIXME : the browser should not be the center of the universe.
    # In fact, we should build a system where view can register themselves
    # as "stay_alive" views. As long as at least one "stay_alive" view
    # is registered, gtg keeps running. It quit only when the last 
    # "stay_alive view" is closed (and then unregistered).
    # Currently, the browser is our only "stay_alive" view.
    def close_browser(self,sender=None):
        self.hide_browser()
        #may take a while to quit
        self.quit()

    def hide_browser(self,sender=None):
        self.browser.hide()

    def iconify_browser(self,sender=None):
        self.browser.iconify()

    def show_browser(self,sender=None):
        self.browser.show()
        
    def is_browser_visible(self,sender=None):
        return self.browser.is_visible()

    def get_browser(self):
        #used by the plugin api to hook in the browser
        return self.browser

    def start_browser_hidden(self):
        self.__start_browser_hidden = True

################# Task Editor ############################################

    def get_opened_editors(self):
        '''
        Returns a dict of task_uid -> TaskEditor, one for each opened editor
        window
        '''
        return self.opened_task

    def open_task(self, uid,thisisnew = False):
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
            tv = TaskEditor(
                requester = self.req, \
                vmanager = self, \
                task = t, \
                taskconfig = self.task_config, \
                thisisnew = thisisnew,\
                clipboard = self.clipboard)
            #registering as opened
            self.opened_task[uid] = tv
        return tv

    def close_task(self, tid):
        # When an editor is closed, it should de-register itself.
        if tid in self.opened_task:
            #the following line has the side effect of removing the 
            # tid key in the opened_task dictionary.
            editor = self.opened_task[tid]
            if editor:
                del self.opened_task[tid]
                #we have to remove the tid from opened_task first
                #else, it close_task would be called once again 
                #by editor.close
                editor.close()
#        else:
            #FIXME: this one should be a debug statement
#            print "the %s editor was already unregistered" %tid
            
################ Others dialog ############################################

    def open_preferences(self, config_priv, sender=None):
        if not hasattr(self, "preferences"):
            self.preferences = PreferencesDialog(self.config_obj)
        self.preferences.activate(config_priv)
        
    def ask_delete_tasks(self, tids):
        if not self.delete_dialog:
            self.delete_dialog = DeletionUI(self.req)
        if self.delete_dialog.delete_tasks(tids):
            for t in tids:
                if t in self.opened_task:
                    self.close_task(t)
            
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
        #FIXME: this code is replicated in the preference window.
        if len(self.pengine.plugins) > 0:
            self.config["plugins"] = {}
            self.config["plugins"]["disabled"] = \
              [p.module_name for p in self.pengine.get_plugins("disabled")]
            self.config["plugins"]["enabled"] = \
              [p.module_name for p in self.pengine.get_plugins("enabled")]
        # plugins are deactivated
        self.pengine.deactivate_plugins()

