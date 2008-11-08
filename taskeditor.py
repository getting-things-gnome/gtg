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
    import gtk.glade
    import gobject
except:
    sys.exit(1)

class TaskEditor :
    def __init__(self, task, refresh_callback=None) :
        self.gladefile = "gtd-gnome.glade"
        self.wTree = gtk.glade.XML(self.gladefile, "TaskEditor") 
        self.window = self.wTree.get_widget("TaskEditor")
        self.textview = self.wTree.get_widget("textview")
        self.task = task
        #self.window = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
        #self.window.set_default_size(150,150)
        self.refresh = refresh_callback
        buff = gtk.TextBuffer()
        texte = self.task.get_text()
        title = self.task.get_title()
        #the first line is the title
        #If we don't have text, it's also valid
        if texte :
            sepa = '\n'
            to_set = sepa.join([title,texte])
        else : 
            to_set = title
        buff.set_text(to_set)
        #self.textview = gtk.TextView(buffer=buff)
        self.textview.set_buffer(buff)
        #self.window.add(self.textview)
        self.window.connect("destroy", self.close)
        self.window.show_all()
        
    def save(self) :
        #the text buffer
        buff = self.textview.get_buffer()
        #the tag table
        table = buff.get_tag_table()
        #we get the text
        texte = buff.get_text(buff.get_start_iter(),buff.get_end_iter())
        #We should have a look at Tomboy Serialize function 
        #NoteBuffer.cs : line 1163
        #Currently, we are not saving the tag table.
        content = texte.partition('\n')
        self.task.set_title(content[0])
        self.task.set_text(content[2])
        if self.refresh :
            self.refresh()
        self.task.sync()
        
    def close(self,window) :
        #Save should be also called when buffer is modified
        self.save()
        #TODO : verify that destroy the window is enough ! 
        #We should also destroy the whole taskeditor object.
        self.window.destroy()
