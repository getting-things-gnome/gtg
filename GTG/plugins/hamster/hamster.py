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
import time
from calendar import timegm

class hamsterPlugin:
    PLUGIN_NAMESPACE = 'hamster-plugin'
    
    #### Interaction with Hamster
    def sendTask(self, task):
        """Send a gtg task to hamster-applet"""
        if task is None: return
        title=task.get_title()
        tags=task.get_tags_name()
        
        hamster_activities=set([unicode(x[0]) for x in self.hamster.GetActivities()])
        tags=[t.lstrip('@').lower() for t in tags]
        activity_candidates=hamster_activities.intersection(set(tags))
        
        if len(activity_candidates)>=1:
            activity=list(activity_candidates)[0]
            #TODO: if >1, how to choose best one?
        elif len(tags):
            #TODO: is there anything more reasonable that can be done?
            activity=tags[0]
        else:
            activity = "Other"
            
        hamster_id=self.hamster.AddFact('%s,%s'%(activity, title), 0, 0)
        
        ids=self.get_hamster_ids(task)
        ids.append(str(hamster_id))
        self.set_hamster_ids(task, ids)
        
    def get_records(self, task):
        """Get a list of hamster facts for a task"""
        ids = self.get_hamster_ids(task)
        records=[]
        modified=False
        valid_ids=[]
        for i in ids:
            d=self.hamster.GetFactById(i)
            if d.get("id", None): # check if fact still exists
                records.append(d)
                valid_ids.append(i)
            else:
                modified=True
                print "Removing invalid fact", i
        if modified:
            self.set_hamster_ids(task, valid_ids)
        return records
    
    #### Datastore  
    def get_hamster_ids(self, task):
        a = task.get_attribute("id-list", namespace=self.PLUGIN_NAMESPACE)
        if not a: return []
        else: return a.split(',')
        
    def set_hamster_ids(self, task, ids):
        task.set_attribute("id-list", ",".join(ids), namespace=self.PLUGIN_NAMESPACE)

    #### Plugin api methods   
    def activate(self, plugin_api):
        # connect to hamster-applet
        try:
            self.hamster=dbus.SessionBus().get_object('org.gnome.Hamster', '/org/gnome/Hamster')
            self.hamster.GetActivities()
        except:
            self.hamsterError()
            return False
        
        # add menu item
        self.menu_item = gtk.MenuItem("Start task in Hamster")
        self.menu_item.connect('activate', self.browser_cb, plugin_api)
        plugin_api.add_menu_item(self.menu_item)
        
        # and button
        self.button=gtk.ToolButton()
        self.button.set_label("Start")
        self.button.set_icon_name('hamster-applet')
        self.button.set_tooltip_text("Start a new activity in Hamster Time Tracker based on the selected task")
        self.button.connect('clicked', self.browser_cb, plugin_api)
        # saves the separator's index to later remove it
        self.separator = plugin_api.add_toolbar_item(gtk.SeparatorToolItem()) 
        plugin_api.add_toolbar_item(self.button)
        self.task_separator = gtk.SeparatorToolItem()

    def onTaskOpened(self, plugin_api):
        # add button
        self.taskbutton = gtk.ToolButton()
        self.taskbutton.set_label("Start")
        self.taskbutton.set_icon_name('hamster-applet')
        self.taskbutton.set_tooltip_text("Start a new activity in Hamster Time Tracker based on this task")
        self.taskbutton.connect('clicked', self.task_cb, plugin_api)
        plugin_api.add_task_toolbar_item(self.task_separator)
        plugin_api.add_task_toolbar_item(self.taskbutton)
        
        task = plugin_api.get_task()
        records = self.get_records(task)
        
        if len(records):
            # add section to bottom of window
            self.vbox = gtk.VBox()
            inner_table = gtk.Table(rows=len(records), columns=2)
            if len(records)>8:
                s = gtk.ScrolledWindow()
                s.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
                v=gtk.Viewport()
                v.add(inner_table)
                s.add(v)
                v.set_shadow_type(gtk.SHADOW_NONE)
                s.set_size_request(-1, 150)
            else:
                s=inner_table
            
            outer_table = gtk.Table(rows=1, columns=2)
            self.vbox.pack_start(s)
            self.vbox.pack_start(outer_table)
            self.vbox.pack_end(gtk.HSeparator())
            
            total = 0
            
            def add(w, a, b, offset):
                dateLabel=gtk.Label(a)
                dateLabel.set_use_markup(True)
                dateLabel.set_alignment(xalign=0.0, yalign=0.5)
                dateLabel.set_size_request(200, -1)
                w.attach(dateLabel, left_attach=0, right_attach=1, top_attach=offset, 
                    bottom_attach=offset+1, xoptions=gtk.FILL, xpadding=20, yoptions=0)
                
                durLabel=gtk.Label(b)
                durLabel.set_use_markup(True)
                durLabel.set_alignment(xalign=0.0, yalign=0.5)
                w.attach(durLabel, left_attach=1, right_attach=2, top_attach=offset, 
                bottom_attach=offset+1, xoptions=gtk.FILL, yoptions=0)
            
            for offset,i in enumerate(records):
                t = calc_duration(i)    
                total += t
                add(inner_table, format_date(i), format_duration(t), offset)
                
            add(outer_table, "<big><b>Total</b></big>", "<big><b>%s</b></big>"%format_duration(total), 1)
            
            plugin_api.add_widget_to_taskeditor(self.vbox)
        
    def deactivate(self, plugin_api):
        plugin_api.remove_menu_item(self.menu_item)
        plugin_api.remove_toolbar_item(self.button)
        plugin_api.remove_toolbar_item(None, self.separator)
        plugin_api.remove_task_toolbar_item(self.task_separator)
        plugin_api.remove_task_toolbar_item(self.taskbutton)
        plugin_api.remove_widget_from_taskeditor(self.vbox)
        
    def browser_cb(self, widget, plugin_api):
        self.sendTask(plugin_api.get_selected_task())
        
    def task_cb(self, widget, plugin_api):
        self.sendTask(plugin_api.get_task())
        
    def hamsterError(self):
        """Display error dialog"""
        d=gtk.MessageDialog(buttons=gtk.BUTTONS_CANCEL)
        d.set_markup("<big>Error loading plugin</big>")
        d.format_secondary_markup("This plugin requires hamster-applet 2.27.3 or greater\n\
Please install hamster-applet and make sure the applet is added to the panel")
        d.run()
        d.destroy()
        
#### Helper Functions  
def format_date(task):
    return time.strftime("<b>%A, %b %e</b> %l:%M %p", time.gmtime(task['start_time']))
    
def calc_duration(fact):
    start=fact['start_time']
    end=fact['end_time']
    if not end: end=timegm(time.localtime())
    return end-start

def format_duration(seconds):
    # Based on hamster-applet code -  hamster/stuff.py   
    """formats duration in a human readable format."""
    
    minutes = seconds / 60
        
    if not minutes:
        return "0min"
    
    hours = minutes / 60
    minutes = minutes % 60
    formatted_duration = ""
    
    if minutes % 60 == 0:
        # duration in round hours
        formatted_duration += "%dh" % (hours)
    elif hours == 0:
        # duration less than hour
        formatted_duration += "%dmin" % (minutes % 60.0)
    else:
        # x hours, y minutes
        formatted_duration += "%dh %dmin" % (hours, minutes % 60)

    return formatted_duration
   
