#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This is the TaskEditor
#
#It's the window you see when you double-clic on a Task
#The main text widget is a home-made TextView called TaskView (see taskview.py)
#The rest are the logic of the widget : date changing widgets, buttons, ...

import sys, time, os
import string, threading
from task import Task
from taskview import TaskView

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

class TaskEditor :
    def __init__(self, task, refresh_callback=None,delete_callback=None,close_callback=None) :
        self.gladefile = "gtd-gnome.glade"
        self.wTree = gtk.glade.XML(self.gladefile, "TaskEditor")
        self.cal_tree = gtk.glade.XML(self.gladefile, "calendar")
        #Create our dictionay and connect it
        dic = {
                "mark_as_done_clicked"  : self.change_status,
                "delete_clicked"        : self.delete_task,
                "on_duedate_pressed"    : self.on_duedate_pressed,
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
        self.textview       = TaskView()
        self.textview.show()
        self.textview.refresh_callback(self.refresh_editor)
        scrolled.add(self.textview)
        #Voila! it's done
        self.calendar       = self.cal_tree.get_widget("calendar")
        self.duedate_widget = self.wTree.get_widget("duedate_entry")
        self.dayleft_label  = self.wTree.get_widget("dayleft")
        
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
            
        self.window.connect("destroy", self.close)
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
            zedate = duedate.replace("-","/")
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
            
        
    def on_duedate_pressed(self, widget):
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
        self.calendar.connect('button-press-event', self.__focus_out)
        
    def day_selected(self,widget) :
        y,m,d = widget.get_date()
        self.task.set_due_date("%s-%s-%s"%(y,m+1,d))
        self.refresh_editor()
    
    def day_selected_double(self,widget) :
        self.__close_calendar()
        
    def nodate_pressed(self,widget) :
        self.task.set_due_date(None)
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
    
    def save(self) :
        #the text buffer
        buff = self.textview.get_buffer()
        #the tag table
        #Currently, we are not saving the tag table
        table = buff.get_tag_table()
        #we get the text
        texte = buff.get_text(buff.get_start_iter(),buff.get_end_iter())
        
        #We should have a look at Tomboy Serialize function 
        #NoteBuffer.cs : line 1163
        stripped = texte.strip(' \n\t')
        content = texte.partition('\n')
        #We don't have an empty task
        #We will find for the first line as the title
        if stripped :
            while not content[0] :
                content = content[2].partition('\n')
        self.task.set_title(content[0])
        self.task.set_text(content[2]) 
        if self.refresh :
            self.refresh()
        self.task.sync()
    
    #This will bring the Task Editor to front    
    def present(self) :
        self.window.present()
        
    #We define dummy variable for when close is called from a callback
    def close(self,window,a=None,b=None,c=None) :
        #Save should be also called when buffer is modified
        self.save()
        self.closing(self.task.get_id())
        #TODO : verify that destroy the window is enough ! 
        #We should also destroy the whole taskeditor object.
        self.window.destroy()
        
        
############# Private functions #################
        
    
    def __focus_out(self,w=None,e=None) :
        #We should only close if the pointer clic is out of the calendar !
        p = self.calendar.window.get_pointer()
        s = self.calendar.get_size()
        if  not(0 <= p[0] <= s[0] and 0 <= p[1] <= s[1]) :
            self.__close_calendar()
        
    
    def __close_calendar(self,widget=None,e=None) :
        self.calendar.hide()
        gtk.gdk.pointer_ungrab()
        self.calendar.grab_remove()
        

    

