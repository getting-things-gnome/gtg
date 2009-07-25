# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Hamster Task Tracker Plugin for Gettings Things Gnome!
# Copyright (c) 2009 Kevin Mehall
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
import gtk, pygtk
import os
import dbus

class hamsterPlugin:
    PLUGIN_NAME = 'Hamster Time Tracker Integration'
    PLUGIN_AUTHORS = 'Kevin Mehall <km@kevinmehall.net>'
    PLUGIN_VERSION = '0.1'
    PLUGIN_DESCRIPTION = 'Adds the ability to send a task to the Hamster time tracking applet'
    PLUGIN_ENABLED = False

    def __init__(self):
        self.hamster=dbus.SessionBus().get_object('org.gnome.Hamster', '/org/gnome/Hamster')
        
    def sendTask(self, task):
        title=task.get_title()
        tags=task.get_tags_name()
        
        hamster_activities=set([unicode(x[0]) for x in self.hamster.GetActivities()])
        tags=[t.lstrip('@').lower() for t in tags]
        activity_candidates=hamster_activities.intersection(set(tags))
        
        if len(activity_candidates)>=1:
            activity=list(activity_candidates)[0]
            #TODO: if >1, how to choose best one?
        else:
            #TODO: is there anything more reasonable that can be done?
            activity=tags[0]
            
        self.hamster.AddFact('%s,%s'%(activity, title), 0, 0)

    # plugin engine methods    
    def activate(self, plugin_api):
        self.menu_item = gtk.MenuItem("Start task in Hamster")
        self.menu_item.connect('activate', self.browser_cb, plugin_api)
        
        self.tb_button=gtk.ToolButton()
        self.tb_button.set_label("Start")
        self.tb_button.set_icon_name('hamster-applet')
        self.tb_button.set_tooltip_text("Start a new activity in Hamster Time Tracker based on the selected task")
        self.tb_button.connect('clicked', self.browser_cb, plugin_api)
        
        # add a menu item to the menu bar
        plugin_api.AddMenuItem(self.menu_item)
                
        # saves the separator's index to later remove it
        self.separator = plugin_api.AddToolbarItem(gtk.SeparatorToolItem())
        # add a item (button) to the ToolBar
        plugin_api.AddToolbarItem(self.tb_button)

    def onTaskOpened(self, plugin_api):
        # add a item (button) to the ToolBar
        self.tb_Taskbutton = gtk.ToolButton()
        self.tb_Taskbutton.set_label("Start")
        self.tb_Taskbutton.set_icon_name('hamster-applet')
        self.tb_Taskbutton.set_tooltip_text("Start a new activity in Hamster Time Tracker based on this task")
        self.tb_Taskbutton.connect('clicked', self.task_cb, plugin_api)
        plugin_api.AddTaskToolbarItem(gtk.SeparatorToolItem())
        plugin_api.AddTaskToolbarItem(self.tb_Taskbutton)
        
    def deactivate(self, plugin_api):
        plugin_api.RemoveMenuItem(self.menu_item)
        plugin_api.RemoveToolbarItem(self.tb_button)
        plugin_api.RemoveToolbarItem(None, self.separator)
        
    def browser_cb(self, widget, plugin_api):
        self.sendTask(plugin_api.get_selected_task())
        
    def task_cb(self, widget, plugin_api):
        self.sendTask(plugin_api.get_task())
           
    
