# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
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

#This is the TaskEditor
#
#It's the window you see when you double-clic on a Task
#The main text widget is a home-made TextView called TaskView (see taskview.py)
#The rest are the logic of the widget : date changing widgets, buttons, ...
import sys
import time
from datetime import date

from GTG import _
from GTG import PLUGIN_DIR
from GTG import DATA_DIR
from GTG.taskeditor          import GnomeConfig
from GTG.tools               import dates
from GTG.taskeditor.taskview import TaskView
from GTG.core.plugins.engine import PluginEngine
from GTG.core.plugins.api    import PluginAPI
try:
    import pygtk
    pygtk.require("2.0")
except: # pylint: disable-msg=W0702
    sys.exit(1)
try:
    import gtk
    from gtk import gdk
except: # pylint: disable-msg=W0702
    sys.exit(1)
    
date_separator = "/"

class TaskEditor :
    def __init__(self, requester, task, plugins,
                delete_callback=None, close_callback=None,opentask_callback=None, 
                tasktitle_callback=None, notes=False) :
        self.req = requester
        self.time = None
        self.gladefile = GnomeConfig.GLADE_FILE
        self.wTree = gtk.glade.XML(self.gladefile, "TaskEditor")
        self.cal_tree = gtk.glade.XML(self.gladefile, "calendar")
        self.donebutton = self.wTree.get_widget("mark_as_done_editor")
        self.dismissbutton = self.wTree.get_widget("dismiss_editor")
        self.deletebutton = self.wTree.get_widget("delete_editor")
        self.deletebutton.set_tooltip_text(GnomeConfig.DELETE_TOOLTIP)
        self.deletebutton = self.wTree.get_widget("insert_subtask")
        self.deletebutton.set_tooltip_text(GnomeConfig.SUBTASK_TOOLTIP)
        self.deletebutton = self.wTree.get_widget("inserttag")
        self.deletebutton.set_tooltip_text(GnomeConfig.TAG_TOOLTIP)
        #Create our dictionay and connect it
        dic = {
                "mark_as_done_clicked"  : self.change_status,
                "on_dismiss"            : self.dismiss,
                "on_keepnote_clicked"   : self.keepnote,
                "delete_clicked"        : self.delete_task,
                "on_duedate_pressed"    : (self.on_date_pressed,"due"),
                "on_startdate_pressed"    : (self.on_date_pressed,"start"),
                "close_clicked"         : self.close,
                "startingdate_changed" : (self.date_changed,"start"),
                "duedate_changed" : (self.date_changed,"due"),
                "on_insert_subtask_clicked" : self.insert_subtask,
                "on_inserttag_clicked" : self.inserttag_clicked,
              }
        self.wTree.signal_autoconnect(dic)
        cal_dic = {
                "on_nodate"             : self.nodate_pressed,
                #"on_dayselected"        : self.day_selected,
                #"on_month_changed"      : self.month_changed,
                "on_dayselected_double" : self.day_selected_double,
        }
        self.cal_tree.signal_autoconnect(cal_dic)
        self.window         = self.wTree.get_widget("TaskEditor")
        #Removing the Normal textview to replace it by our own
        #So don't try to change anything with glade, this is a home-made widget
        textview = self.wTree.get_widget("textview")
        scrolled = self.wTree.get_widget("scrolledtask")
        scrolled.remove(textview)
        self.open_task  = opentask_callback
        self.task_title = tasktitle_callback
        self.textview   = TaskView(self.req)
        self.textview.show()
        self.textview.set_subtask_callback(self.new_subtask)
        self.textview.open_task_callback(self.open_task)
        self.textview.tasktitle_callback(self.task_title)
        self.textview.set_left_margin(7)
        self.textview.set_right_margin(5)
        scrolled.add(self.textview)
        #Voila! it's done
        self.calendar       = self.cal_tree.get_widget("calendar")
        self.cal_widget       = self.cal_tree.get_widget("calendar1")
        #self.cal_widget.set_property("no-month-change",True)
        self.sigid = None
        self.sigid_month = None
        #Do we have to close the calendar when date is changed ?
        #This is a ugly hack to close the calendar on the first click
        self.close_when_changed = True
        self.duedate_widget = self.wTree.get_widget("duedate_entry")
        self.startdate_widget = self.wTree.get_widget("startdate_entry")
        self.dayleft_label  = self.wTree.get_widget("dayleft")
        self.inserttag_button = self.wTree.get_widget("inserttag")
        self.tasksidebar = self.wTree.get_widget("tasksidebar")
        self.keepnote_button = self.wTree.get_widget("keepnote")
        if not notes :
            self.keepnote_button.hide()
            separator = self.wTree.get_widget("separator_note")
            separator.hide()
        #We will keep the name of the opened calendar
        #Empty means that no calendar is opened
        self.__opened_date = ''
        
        # Define accelerator keys
        self.init_accelerators()
        
        self.task = task
        tags = task.get_tags()
        self.textview.subtasks_callback(task.get_subtask_tids)
        self.textview.removesubtask_callback(task.remove_subtask)
        self.textview.set_get_tagslist_callback(task.get_tags_name)
        self.textview.set_add_tag_callback(task.add_tag)
        self.textview.set_remove_tag_callback(task.remove_tag)
        self.textview.save_task_callback(self.light_save)
        self.delete  = delete_callback
        self.closing = close_callback

        texte = self.task.get_text()
        title = self.task.get_title()
        #the first line is the title
        self.textview.set_text("%s\n"%title)
        #we insert the rest of the task
        if texte :
            self.textview.insert("%s"%texte)
        else :
            #If not text, we insert tags
            if tags :
                for t in tags :
                    self.textview.insert_text("%s, "%t.get_name())
                self.textview.insert_text("\n")
            #If we don't have text, we still need to insert subtasks if any
            subtasks = task.get_subtask_tids()
            if subtasks :
                self.textview.insert_subtasks(subtasks)
        #We select the title if it's a new task
        if self.task.is_new() :
            self.textview.select_title()
        self.textview.modified(full=True)
        self.window.connect("destroy", self.destruction)
        
        # plugins
        self.plugins = plugins
        self.pengine = PluginEngine(PLUGIN_DIR)
        self.te_plugin_api = PluginAPI(self.window, None, DATA_DIR, self.wTree, 
                                       self.req, None, None, None, None, task, 
                                       self.textview)
        self.pengine.onTaskLoad(self.plugins, self.te_plugin_api)
        
        #Putting the refresh callback at the end make the start a lot faster
        self.textview.refresh_callback(self.refresh_editor)
        self.refresh_editor()
        self.textview.grab_focus()

        self.window.show()

    # Define accelerator-keys for this dialog
    # TODO: undo/redo
    def init_accelerators(self):
        agr = gtk.AccelGroup()
        self.window.add_accel_group(agr)
        
        # Escape and Ctrl-W close the dialog. It's faster to call close
        # directly, rather than use the close button widget
        key, modifier = gtk.accelerator_parse('Escape')
        agr.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.close)
        
        key, modifier = gtk.accelerator_parse('<Control>w')
        agr.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.close)
        
        # Ctrl-N creates a new task
        key, modifier = gtk.accelerator_parse('<Control>n')
        agr.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.new_task)
        
        # Ctrl-Shift-N creates a new subtask
        insert_subtask = self.wTree.get_widget("insert_subtask")
        key, mod       = gtk.accelerator_parse("<Control><Shift>n")
        insert_subtask.add_accelerator('clicked', agr, key, mod, gtk.ACCEL_VISIBLE)
        
        # Ctrl-D marks task as done
        mark_as_done_editor = self.wTree.get_widget('mark_as_done_editor')
        key, mod = gtk.accelerator_parse('<Control>d')
        mark_as_done_editor.add_accelerator('clicked', agr, key, mod, gtk.ACCEL_VISIBLE)
        
        # Ctrl-I marks task as dismissed
        dismiss_editor = self.wTree.get_widget('dismiss_editor')
        key, mod = gtk.accelerator_parse('<Control>i')
        dismiss_editor.add_accelerator('clicked', agr, key, mod, gtk.ACCEL_VISIBLE)
        
    
    #Can be called at any time to reflect the status of the Task
    #Refresh should never interfer with the TaskView
    #If a title is passed as a parameter, it will become
    #The new window title. If not, we will look for the task title
    #Refreshtext is wheter or not we should refresh the TaskView
    #(doing it all the time is dangerous if the task is empty)
    def refresh_editor(self, title=None, refreshtext=False):
        to_save = False
        #title of the window 
        if title :
            self.window.set_title(title)
            to_save = True
        else :
            self.window.set_title(self.task.get_title())
           
        status = self.task.get_status() 
        if status == "Dismiss":
            self.donebutton.set_label(GnomeConfig.MARK_DONE)
            self.donebutton.set_tooltip_text(GnomeConfig.MARK_DONE_TOOLTIP)
            self.donebutton.set_icon_name("gtg-task-done")
            self.dismissbutton.set_label(GnomeConfig.MARK_UNDISMISS)
            self.dismissbutton.set_tooltip_text(GnomeConfig.MARK_UNDISMISS_TOOLTIP)
            self.dismissbutton.set_icon_name("gtg-task-undismiss")
        elif status == "Done":
            self.donebutton.set_label(GnomeConfig.MARK_UNDONE)
            self.donebutton.set_tooltip_text(GnomeConfig.MARK_UNDONE_TOOLTIP)
            self.donebutton.set_icon_name("gtg-task-undone")
            self.dismissbutton.set_label(GnomeConfig.MARK_DISMISS)
            self.dismissbutton.set_tooltip_text(GnomeConfig.MARK_DISMISS_TOOLTIP)
            self.dismissbutton.set_icon_name("gtg-task-dismiss")
        else:
            self.donebutton.set_label(GnomeConfig.MARK_DONE)
            self.donebutton.set_tooltip_text(GnomeConfig.MARK_DONE_TOOLTIP)
            self.donebutton.set_icon_name("gtg-task-done")
            self.dismissbutton.set_label(GnomeConfig.MARK_DISMISS)
            self.dismissbutton.set_tooltip_text(GnomeConfig.MARK_DISMISS_TOOLTIP)
            self.dismissbutton.set_icon_name("gtg-task-dismiss")
            
        if status == "Note":
            self.donebutton.hide()
            self.tasksidebar.hide()
            self.keepnote_button.set_label(GnomeConfig.MAKE_TASK)
        else :
            self.donebutton.show()
            self.tasksidebar.show()
            self.keepnote_button.set_label(GnomeConfig.KEEP_NOTE)
            
        #refreshing the due date field
        duedate = self.task.get_due_date()
        if duedate:
            zedate = duedate.replace("-", date_separator)
            if zedate != self.duedate_widget.get_text():
                self.duedate_widget.set_text(zedate)
                #refreshing the day left label
                result = self.task.get_days_left()
                if result == 1:
                    txt = _("Due tomorrow !")
                elif result > 0:
                    txt = _("%s days left") %result
                elif result == 0:
                    txt = _("Due today !")
                elif result == -1:
                    txt = _("Due yesterday")
                elif result < 0:
                    txt = _("Was %s days ago") % -result
                self.dayleft_label.set_markup("<span color='#666666'>"+txt+"</span>")    
        elif self.duedate_widget.get_text() != '':
            self.dayleft_label.set_text('')
            self.duedate_widget.set_text('')
        startdate = self.task.get_start_date()
        if startdate:
            zedate = startdate.replace("-",date_separator)
            if zedate != self.startdate_widget.get_text():
                self.startdate_widget.set_text(zedate)
        elif self.startdate_widget.get_text() != '':
            self.startdate_widget.set_text('')
            
        #Refreshing the tag list in the insert tag button
        taglist = self.req.get_used_tags()
        menu = gtk.Menu()
        tag_count = 0
        for t in taglist :
            tt = t.get_name()
            if not self.task.has_tags(tag_list=[t]) :
                tag_count += 1
                mi = gtk.MenuItem(label=tt)
                mi.connect("activate",self.inserttag,tt)
                mi.show()
                menu.append(mi)
        if tag_count > 0 :
            self.inserttag_button.set_menu(menu)

        if refreshtext:
            self.textview.modified(refresheditor=False)            
        if to_save:
            self.save()
            
        
    def date_changed(self,widget,data):
        text = widget.get_text()
        datetoset = None
        validdate = False
        if not text :
            validdate = True
        else :
            dateobject = dates.strtodate(text)
            if dateobject :
                validdate = True
                datetoset = text
                
        if validdate :
            #If the date is valid, we write with default color in the widget
            # "none" will set the default color.
            widget.modify_text(gtk.STATE_NORMAL, None)
            widget.modify_base(gtk.STATE_NORMAL, None)
            if data == "start" :
                self.task.set_start_date(datetoset)
            elif data == "due" :
                self.task.set_due_date(datetoset)
        else :
            #We should write in red in the entry if the date is not valid
            widget.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse("#F00"))
            widget.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#F88"))


        
        
    def on_date_pressed(self, widget,data): 
        """Called when the due button is clicked."""
        rect = widget.get_allocation()
        x, y = widget.window.get_origin()
        cal_width, cal_height = self.calendar.get_size() #pylint: disable-msg=W0612
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
        if self.__opened_date == "due" :
            toset = self.task.get_due_date()
        elif self.__opened_date == "start" :
            toset = self.task.get_start_date()
        if toset :
            y,m,d = toset.split("-")
        else :
            dd = date.today()
            y = dd.year
            m = dd.month
            d = dd.day
        #Else, we set the widget to today's date
        
        self.cal_widget.select_month(int(m)-1,int(y))
        self.cal_widget.select_day(int(d))
        self.calendar.connect('button-press-event', self.__focus_out)
        self.sigid = self.cal_widget.connect("day-selected",self.day_selected)
        self.sigid_month = self.cal_widget.connect("month-changed",self.month_changed)
        
    def day_selected(self,widget) :
        y,m,d = widget.get_date()
        if self.__opened_date == "due" :
            self.task.set_due_date("%s-%s-%s"%(y,m+1,d))
        elif self.__opened_date == "start" :
            self.task.set_start_date("%s-%s-%s"%(y,m+1,d))
        if self.close_when_changed :
            self.__close_calendar()
        else :
            self.close_when_changed = True
        self.refresh_editor()
        
    def month_changed(self,widget) :
        #This is a ugly hack to close the calendar on the first click
        self.close_when_changed = False
    
    def day_selected_double(self,widget) : #pylint: disable-msg=W0613
        self.__close_calendar()
        
    def nodate_pressed(self,widget) : #pylint: disable-msg=W0613
        if self.__opened_date == "due" :
            self.task.set_due_date(None)
        elif self.__opened_date == "start" :
            self.task.set_start_date(None)
        self.refresh_editor()
        self.__close_calendar()
        
    def dismiss(self,widget) : #pylint: disable-msg=W0613
        stat = self.task.get_status()
        if stat == "Dismiss":
            self.task.set_status("Active")
            self.refresh_editor()
        else:
            self.task.set_status("Dismiss")
            self.close(None)
    
    def keepnote(self,widget) : #pylint: disable-msg=W0613
        stat = self.task.get_status()
        toset = "Note"
        if stat == "Note" :
            toset = "Active"
        self.task.set_status(toset)
        self.refresh_editor()
    
    def change_status(self,widget) : #pylint: disable-msg=W0613
        stat = self.task.get_status()
        if stat == "Done":
            self.task.set_status("Active")
            self.refresh_editor()
        else:
            self.task.set_status("Done")
            self.close(None)
    
    def delete_task(self,widget) :
        if self.delete :
            result = self.delete(widget,self.task.get_id())
        #if the task was deleted, we close the window
        if result : self.window.destroy()

    
    #Take the title as argument and return the subtask ID
    def new_subtask(self,title) :
        subt = self.task.new_subtask()
        subt.set_title(title)
        tid = subt.get_id()
        return tid

    # Create a new task
    def new_task(self, *args):
        task = self.req.new_task(tags=None, newtask=True)
        task_id = task.get_id()
        self.open_task(task_id)
        
    def insert_subtask(self,widget) : #pylint: disable-msg=W0613
        self.textview.insert_newtask()
        self.textview.grab_focus()
        
    def inserttag_clicked(self,widget) : #pylint: disable-msg=W0613
        itera = self.textview.get_insert()
        if itera.starts_line() :
            self.textview.insert_text("@",itera)
        else :
            self.textview.insert_text(" @",itera)
        self.textview.grab_focus()
        
    def inserttag(self,widget,tag) : #pylint: disable-msg=W0613
        self.textview.insert_tags([tag])
        self.textview.grab_focus()
    
    def save(self) :
        self.task.set_title(self.textview.get_title())
        self.task.set_text(self.textview.get_text()) 
        self.task.sync()
        self.time = time.time()
    #light_save save the task without refreshing every 30seconds
    #We will reduce the time when the get_text will be in another thread
    def light_save(self) :
        #if self.time is none, we never called any save
        if self.time:
            diff = time.time() - self.time
            tosave = diff > GnomeConfig.SAVETIME
        else:
            self.time = 1
            tosave = False
            diff = None
        if tosave:
            #We don't want to save a new empty task
            #so we check for the content
            empty = "<content/>"
            actual = self.textview.get_text()
            isempty = (actual == empty or actual == "" or not actual)
            if not self.task.is_new() or not isempty:
                #commented the following line because I don't know
                #why we have it
                #self.task.set_text(actual)
                self.task.sync()
                self.time = time.time()
        
        
    #This will bring the Task Editor to front    
    def present(self):
        self.window.present()
    def move(self,x,y):
        try:
            xx=int(x)
            yy=int(y)
            print "move to %s %s"%(xx,yy)
            self.window.move(xx,yy)
        except:
            pass
    def get_position(self):
        return self.window.get_position()
        
    #We define dummy variable for when close is called from a callback
    def close(self,window=None,a=None,b=None,c=None) : #pylint: disable-msg=W0613
        #We should also destroy the whole taskeditor object.
        self.window.destroy()
    
    #The destroy signal is linked to the "close" button. So if we call
    #destroy in the close function, this will cause the close to be called twice
    #To solve that, close will just call "destroy" and the destroy signal
    #Will be linked to this destruction method that will save the task
    def destruction(self,a=None) :#pylint: disable-msg=W0613
        #Save should be also called when buffer is modified
        self.pengine.onTaskClose(self.plugins, self.te_plugin_api)
        tid = self.task.get_id()
        if self.task.is_new():
            self.req.delete_task(tid)
        else:
            self.save()
        self.closing(tid)
        
############# Private functions #################
        
    
    def __focus_out(self,w=None,e=None) : #pylint: disable-msg=W0613
        #We should only close if the pointer clic is out of the calendar !
        p = self.calendar.window.get_pointer()
        s = self.calendar.get_size()
        if  not(0 <= p[0] <= s[0] and 0 <= p[1] <= s[1]) :
            self.__close_calendar()
        
    
    def __close_calendar(self,widget=None,e=None) : #pylint: disable-msg=W0613
        self.calendar.hide()
        self.__opened_date = ''
        gtk.gdk.pointer_ungrab()
        self.calendar.grab_remove()
        if self.sigid :
            self.cal_widget.disconnect(self.sigid)
            self.sigid = None
        if self.sigid_month :
            self.cal_widget.disconnect(self.sigid_month)
            self.sigid_month = None
        

    

