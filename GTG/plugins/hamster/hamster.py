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
    PLUGIN_NAME = 'Hamster Time Tracker Integration'
    PLUGIN_AUTHORS = 'Kevin Mehall <km@kevinmehall.net>'
    PLUGIN_VERSION = '0.1'
    PLUGIN_DESCRIPTION = 'Adds the ability to send a task to the Hamster time tracking applet'
    PLUGIN_ENABLED = False
        
    def sendTask(self, task):
        if task is None: return
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
            
        hamster_id=self.hamster.AddFact('%s,%s'%(activity, title), 0, 0)
        
        ids=get_hamster_ids(task)
        ids.append(str(hamster_id))
        set_hamster_ids(task, ids)
        
    def get_records(self, task):
        ids = get_hamster_ids(task)
        records=[]
        modified=False
        valid_ids=[]
        for i in ids:
            d=self.hamster.GetFactById(i)
            if d.get("id", None): # check if fact exists
                records.append(d)
                valid_ids.append(i)
            else:
                modified=True
                print "Removing invalid fact", i
        if modified:
            set_hamster_ids(task, valid_ids)
        return records

    def hamsterError(self):
        d=gtk.MessageDialog(buttons=gtk.BUTTONS_CANCEL)
        d.set_markup("<big>Error loading plugin</big>")
        d.format_secondary_markup("This plugin requires hamster-applet 2.27.3 or greater\n\
Please install hamster-applet and make sure the applet is added to the panel")
        d.run()
        d.destroy()

    # plugin engine methods    
    def activate(self, plugin_api):
        try:
            self.hamster=dbus.SessionBus().get_object('org.gnome.Hamster', '/org/gnome/Hamster')
            self.hamster.GetActivities()
        except:
            self.hamsterError()
            return False
        
        self.menu_item = gtk.MenuItem("Start task in Hamster")
        self.menu_item.connect('activate', self.browser_cb, plugin_api)
        
        self.button=gtk.ToolButton()
        self.button.set_label("Start")
        self.button.set_icon_name('hamster-applet')
        self.button.set_tooltip_text("Start a new activity in Hamster Time Tracker based on the selected task")
        self.button.connect('clicked', self.browser_cb, plugin_api)
        
        # add a menu item to the menu bar
        plugin_api.add_menu_item(self.menu_item)
                
        # saves the separator's index to later remove it
        self.separator = plugin_api.add_toolbar_item(gtk.SeparatorToolItem())
        # add a item (button) to the ToolBar
        plugin_api.add_toolbar_item(self.button)

    def onTaskOpened(self, plugin_api):
        # add a item (button) to the ToolBar
        self.taskbutton = gtk.ToolButton()
        self.taskbutton.set_label("Start")
        self.taskbutton.set_icon_name('hamster-applet')
        self.taskbutton.set_tooltip_text("Start a new activity in Hamster Time Tracker based on this task")
        self.taskbutton.connect('clicked', self.task_cb, plugin_api)
        plugin_api.add_task_toolbar_item(gtk.SeparatorToolItem())
        plugin_api.add_task_toolbar_item(self.taskbutton)
        
        task = plugin_api.get_task()
        records = self.get_records(task)
        
        if len(records):
            w = gtk.Table(rows=len(records)+1, columns=2)
            
            total = 0
            
            for offset,i in enumerate(records):
                t = calc_duration(i)    
                total += t
                
                dateLabel=gtk.Label(format_date(i))
                dateLabel.set_use_markup(True)
                dateLabel.set_alignment(xalign=0.0, yalign=0.5)
                w.attach(dateLabel,
                    left_attach=0, right_attach=1, top_attach=offset, bottom_attach=offset+1, xoptions=gtk.FILL, xpadding=20)
                
                durLabel=gtk.Label(format_duration(t))
                durLabel.set_alignment(xalign=1.0, yalign=0.5)
                w.attach(durLabel,
                    left_attach=1, right_attach=2, top_attach=offset, bottom_attach=offset+1, xoptions=gtk.FILL)
            offset+=1
            l=gtk.Label("<big><b>Total</b></big>")
            l.set_use_markup(True)
            l.set_alignment(xalign=0.0, yalign=0.5)
            w.attach(l,
                left_attach=0, right_attach=1, top_attach=offset, bottom_attach=offset+1, xoptions=gtk.FILL, xpadding=20)
            l=gtk.Label("<big><b>%s</b></big>"%format_duration(total))
            l.set_use_markup(True)
            l.set_alignment(xalign=1.0, yalign=0.5)
            w.attach(l,
                left_attach=1, right_attach=2, top_attach=offset, bottom_attach=offset+1, xoptions=gtk.FILL)
            
            plugin_api.add_task_window_region(w)
        
    def deactivate(self, plugin_api):
        plugin_api.remove_menu_item(self.menu_item)
        plugin_api.remove_toolbar_item(self.button)
        plugin_api.remove_toolbar_item(None, self.separator)
        
    def browser_cb(self, widget, plugin_api):
        self.sendTask(plugin_api.get_selected_task())
        
    def task_cb(self, widget, plugin_api):
        self.sendTask(plugin_api.get_task())
        
def get_hamster_ids(task):
    a = task.get_attribute("id-list", namespace="hamster-plugin")
    if not a: return []
    else: return a.split(',')
    
def set_hamster_ids(task, ids):
    task.set_attribute("id-list", ",".join(ids), namespace="hamster-plugin")
    
def format_date(task):
    return time.strftime("<b>%A, %b %e</b> %l:%M %p", time.gmtime(task['start_time']))
    

def calc_duration(fact):
    start=fact['start_time']
    end=fact['end_time']
    if not end: end=timegm(time.localtime())
    return end-start
    
# Based on hamster-applet -  hamster/stuff.py   
def format_duration(seconds):
    """formats duration in a human readable format.
    accepts # of seconds"""
    
    minutes = seconds / 60
        
    if not minutes:
        return ""
    
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
    

    
           
    
