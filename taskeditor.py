import sys, time, os
import string, threading
from task import Task

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
        self.textview       = self.wTree.get_widget("textview")
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
        self.buff = gtk.TextBuffer()
        self.__tags = []
        texte = self.task.get_text()
        title = self.task.get_title()
        #the first line is the title
        self.buff.set_text("%s\n"%title)
        #How to insert a link ? 
        #self.insert_with_anchor("Fritalk link\n","http://fritalk.com")
        
        ##########Tag we will use #######
        #We use the tag table (tag are defined here but set in self.modified)
        table = self.buff.get_tag_table()
        #tag test for title
        title_tag = self.buff.create_tag("title",foreground="#12F",scale=1.6,underline=1)
        title_tag.set_property("pixels-above-lines",10)
        title_tag.set_property("pixels-below-lines",10)
        #start = self.buff.get_start_iter()
        end = self.buff.get_end_iter()
        #We have to find a way to keep this tag for the first line
        #Even when the task is edited
        
        #we insert the rest of the task
        if texte : 
            self.buff.insert(end,"%s"%texte)
    
        #The signal emitted each time the buffer is modified
        self.modi_signal = self.buff.connect("modified_changed",self._modified)
        #The signal emitted each time we move the mouse in the text view window
        self.textview.connect('motion-notify-event', self._motion)
        #pas l'air de fonctionner celui-la
        #self.textview.connect('insert-at-cursor',self._insert_at_cursor)
        self.buff.connect('insert-text',self._insert_at_cursor)

        
        self.textview.set_buffer(self.buff)
        self.window.connect("destroy", self.close)
        self.refresh_editor()

        self.window.show()
        self.buff.set_modified(False)
    
    #Insert a link (anchor) in the textview
    def insert_with_anchor(self, text, anchor=None, _iter=None):
        if _iter is None:
            _iter = self.buff.get_end_iter()
        if anchor is None:
            anchor = text

        tag = self.buff.create_tag(None,foreground="blue",underline=1)
        tag.set_property("background","red")
        tag.set_data('is_anchor', True)
        tag.connect('event', self._tag_event, text, anchor)
        self.__tags.append(tag)
        self.buff.insert_with_tags(_iter, text, tag)

        
    #Function that will transform the cursor if we are above a link
    #A lot of code was stolen here : http://trac.atzm.org/index.cgi/wiki/PyGTK
    def _motion(self, view, ev):
        window = ev.window
        x, y, _ = window.get_pointer()
        x, y = view.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT, x, y)
        tags = view.get_iter_at_location(x, y).get_tags()
        for tag in tags:
            if tag.get_data('is_anchor'):
                for t in set(self.__tags) - set([tag]):
                    self.__tag_reset(t, window)
                self.__set_anchor(window, tag, gtk.gdk.Cursor(gtk.gdk.HAND2),None)
                break
        else:
            tag_table = self.textview.get_buffer().get_tag_table()
            tag_table.foreach(self.__tag_reset, window)
            
    def _tag_event(self, tag, view, ev, _iter, text, anchor):
        _type = ev.type
        if _type == gtk.gdk.MOTION_NOTIFY:
            return
        elif _type in [gtk.gdk.BUTTON_PRESS, gtk.gdk.BUTTON_RELEASE]:
            button = ev.button
            cursor = gtk.gdk.Cursor(gtk.gdk.HAND2)
            if _type == gtk.gdk.BUTTON_RELEASE:
                print "anchor clicked : %s" %anchor
                #self.textview.emit('anchor-clicked', text, anchor, button)
                #self.textview.__set_anchor(ev.window, tag, cursor, self.get_property('hover'))
            #elif button in [1, 2]:
                #pass
                #self.__set_anchor(ev.window, tag, cursor, self.get_property('active'))

    def __tag_reset(self, tag, window):
        if tag.get_data('is_anchor'):
            self.__set_anchor(window, tag, None, None)

    def __set_anchor(self, window, tag, cursor, prop):
        window.set_cursor(cursor)
        if prop :
            for key, val in prop.iteritems():
                tag.set_property(key, val)
        
    #The buffer was modified, let reflect this
    def _modified(self,a=None) :
        start = self.buff.get_start_iter()
        end = self.buff.get_end_iter()
        #Here we apply the title tag on the first line
        line_nbr = 1
        linecount = self.buff.get_line_count()
        if linecount > line_nbr :
            #Applying title on the first line
            end_title = self.buff.get_iter_at_line(line_nbr)
            stripped = self.buff.get_text(start,end_title).strip('\n\t ')
            while line_nbr <= linecount and not stripped :
                line_nbr += 1
                end_title = self.buff.get_iter_at_line(line_nbr)
                stripped = self.buff.get_text(start,end_title).strip('\n\t ')
            self.buff.apply_tag_by_name('title', start, end_title)
            self.buff.remove_tag_by_name('title',end_title,end)
            #title of the window  (we obviously remove \t and \n)
            self.window.set_title(self.buff.get_text(start,end_title).strip('\n\t'))
        #Or to all the buffer if there is only one line
        else :
            self.buff.apply_tag_by_name('title', start, end)
            #title of the window 
            self.window.set_title(self.buff.get_text(start,end))
                        
        #Do we want to save the text at each modification ?
        
        #Ok, we took care of the modification
        self.buff.set_modified(False)
        
    def _insert_at_cursor(self,tv,itera,tex,leng) :
        #New line : the user pressed enter !
        if tex == '\n' :
            #The nbr just before the \n
            line_nbr = itera.get_line()
            start_line = itera.copy()
            start_line.set_line(line_nbr)
            end_line = itera.copy()
            #We add a bullet list but not on the first line
            if line_nbr > 0 :
                line = start_line.get_slice(end_line)
                #Python 2.5 should allow both tests in one
                if line.startswith('-') or line.startswith(' -') :
                    line = line.lstrip(' -')
                    #From Tomboy : ('\u2022\u2218\u2023')
                    #bullet = '%s%s%s' %(unichr(2022),unichr(2218),unichr(2023))
                    bullet = unichr(2192)
                    newline = '%s%s' %(bullet,line)
                    newline.encode('utf-8')
                    self.buff.delete(start_line,end_line)
                    self.buff.insert(start_line,newline)
    
    def refresh_editor(self) :
        #title of the window 
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
