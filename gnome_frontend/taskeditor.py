#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This is the TaskEditor
#
#It's the window you see when you double-clic on a Task
#The main text widget is a home-made TextView called TaskView (see taskview.py)
#The rest are the logic of the widget : date changing widgets, buttons, ...

import sys, time, os
import string, threading
from gtg_core.task import Task
from gnome_frontend.taskview import TaskView
from gnome_frontend import GnomeConfig

try:
    import pygtk
    pygtk.require("2.0")
except:
      pass
try:
    import gtk
    from gtk import gdk
    import gtk.glade
    import gobject
except:
    sys.exit(1)
    
date_separator="/"

class TaskEditor :
    def __init__(self, task, refresh_callback=None,delete_callback=None,
                close_callback=None,opentask_callback=None, tasktitle_callback=None) :
        self.gladefile = GnomeConfig.GLADE_FILE
        self.wTree = gtk.glade.XML(self.gladefile, "TaskEditor")
        self.cal_tree = gtk.glade.XML(self.gladefile, "calendar")
        #Create our dictionay and connect it
        dic = {
                "mark_as_done_clicked"  : self.change_status,
                "delete_clicked"        : self.delete_task,
                "on_duedate_pressed"    : (self.on_date_pressed,"due"),
                "on_startdate_pressed"    : (self.on_date_pressed,"start"),
                "close_clicked"         : self.close
              }
        self.wTree.signal_autoconnect(dic)
        cal_dic = {
                "on_nodate"             : self.nodate_pressed,
                "on_dayselected"        : self.day_selected,
                "on_dayselected_double" : self.day_selected_double,
        }
        self.cal_tree.signal_autoconnect(cal_dic)
        self.window         = self.wTree.get_widget("TaskEditor")
        #Removing the Normal textview to replace it by our own
        #So don't try to change anything with glade, this is a home-made widget
        textview = self.wTree.get_widget("textview")
        scrolled = self.wTree.get_widget("scrolledtask")
        scrolled.remove(textview)
        self.open_task = opentask_callback
        self.task_title = tasktitle_callback
        self.textview       = TaskView()
        self.textview.show()
        self.textview.refresh_callback(self.refresh_editor)
        self.textview.set_subtask_callback(self.new_subtask)
        self.textview.open_task_callback(self.open_task)
        self.textview.tasktitle_callback(self.task_title)
        scrolled.add(self.textview)
        #Voila! it's done
        self.calendar       = self.cal_tree.get_widget("calendar")
        self.duedate_widget = self.wTree.get_widget("duedate_entry")
        self.startdate_widget = self.wTree.get_widget("startdate_entry")
        self.dayleft_label  = self.wTree.get_widget("dayleft")
        #We will keep the name of the opened calendar
        #Empty means that no calendar is opened
        self.__opened_date = ''
        
        #We will intercept the "Escape" button
        accelgroup = gtk.AccelGroup()
        key, modifier = gtk.accelerator_parse('Escape')
        #Escape call close()
        accelgroup.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.close)
        self.window.add_accel_group(accelgroup)
     
        self.task = task
        self.refresh = refresh_callback
        self.delete  = delete_callback
        self.closing = close_callback
        texte = self.task.get_text()
        title = self.task.get_title()
        #the first line is the title
        self.textview.set_text("%s\n"%title)
        #we insert the rest of the task
        if texte : 
            self.textview.insert("%s"%texte)
            
        self.window.connect("destroy", self.destruction)
        self.refresh_editor()

        self.window.show()

    #Can be called at any time to reflect the status of the Task
    #Refresh should never interfer with the TaskView
    #If a title is passed as a parameter, it will become
    #The new window title. If not, we will look for the task title
    def refresh_editor(self,title=None) :
        #title of the window 
        if title :
            self.window.set_title(title)
        else :
            self.window.set_title(self.task.get_title())
        #refreshing the due date field
        duedate = self.task.get_due_date()
        if duedate :
            zedate = duedate.replace("-",date_separator)
            self.duedate_widget.set_text(zedate)
            #refreshing the day left label
            result = self.task.get_days_left()
            if result == 1 :
                txt = "Due tomorrow !"
            elif result > 0 :
                txt = "%s days left" %result
            elif result == 0 :
                txt = "Due today !"
            elif result == -1 :
                txt = "Due for yesterday"
            elif result < 0 :
                txt = "Was %s days ago" %result
            self.dayleft_label.set_markup("<span color='#666666'>"+txt+"</span>") 
                
        else :
            self.dayleft_label.set_text('')
            self.duedate_widget.set_text('')
        startdate = self.task.get_start_date()
        if startdate :
            self.startdate_widget.set_text(startdate.replace("-",date_separator))
        else :
            self.startdate_widget.set_text('')
        
    def on_date_pressed(self, widget,data):
        """Called when the due button is clicked."""
        rect = widget.get_allocation()
        x, y = widget.window.get_origin()
        cal_width, cal_height = self.calendar.get_size()
        self.calendar.move((x + rect.x - cal_width + rect.width)
                                            , (y + rect.y + rect.height))
        self.calendar.show()
        """Because some window managers ignore move before you show a window."""
        self.calendar.move((x + rect.x - cal_width + rect.width)
                                            , (y + rect.y + rect.height))
        
        self.calendar.grab_add()
        #We grab the pointer in the calendar
        gdk.pointer_grab(self.calendar.window, True,gdk.BUTTON1_MASK|gdk.MOD2_MASK)
        #we will close the calendar if the user clic outside
        self.__opened_date = data
        self.calendar.connect('button-press-event', self.__focus_out)
        
    def day_selected(self,widget) :
        y,m,d = widget.get_date()
        if self.__opened_date == "due" :
            self.task.set_due_date("%s-%s-%s"%(y,m+1,d))
        elif self.__opened_date == "start" :
            self.task.set_start_date("%s-%s-%s"%(y,m+1,d))
        self.refresh_editor()
    
    def day_selected_double(self,widget) :
        self.__close_calendar()
        
    def nodate_pressed(self,widget) :
        if self.__opened_date == "due" :
            self.task.set_due_date(None)
        elif self.__opened_date == "start" :
            self.task.set_start_date(None)
        self.refresh_editor()
        self.__close_calendar()
    
    def change_status(self,widget) :
        stat = self.task.get_status()
        if stat == "Active" :
            toset = "Done"
        elif stat == "Done" :
            toset = "Active"
        self.task.set_status(toset)
        self.close(None)
        self.refresh()
    
    def delete_task(self,widget) :
        if self.delete :
            result = self.delete(widget,self.task.get_id())
        else :
            print "No callback to delete"
        #if the task was deleted, we close the window
        if result : self.window.destroy()
    
    #Take the title as argument and return the subtask ID
    def new_subtask(self,title) :
        subt = self.task.new_subtask()
        subt.set_title(title)
        tid = subt.get_id()
        return tid
    
    def save(self) :
        self.task.set_title(self.textview.get_title())
        self.task.set_text(self.textview.get_text()) 
        if self.refresh :
            self.refresh()
        self.task.sync()
    
    #This will bring the Task Editor to front    
    def present(self) :
        self.window.present()
        
    #We define dummy variable for when close is called from a callback
    def close(self,window,a=None,b=None,c=None) :
        #TODO : verify that destroy the window is enough ! 
        #We should also destroy the whole taskeditor object.
        self.window.destroy()
    
    #The destroy signal is linked to the "close" button. So if we call
    #destroy in the close function, this will cause the close to be called twice
    #To solve that, close will just call "destroy" and the destroy signal
    #Will be linked to this destruction method that will save the task
    def destruction(self,a=None) :
        #Save should be also called when buffer is modified
        self.save()
        self.closing(self.task.get_id())
        
        
############# Private functions #################
        
    
    def __focus_out(self,w=None,e=None) :
        #We should only close if the pointer clic is out of the calendar !
        p = self.calendar.window.get_pointer()
        s = self.calendar.get_size()
        if  not(0 <= p[0] <= s[0] and 0 <= p[1] <= s[1]) :
            self.__close_calendar()
        
    
    def __close_calendar(self,widget=None,e=None) :
        self.calendar.hide()
        self.__opened_date = ''
        gtk.gdk.pointer_ungrab()
        self.calendar.grab_remove()
        

    

