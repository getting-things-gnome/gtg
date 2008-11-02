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
	def __init__(self, task) :
		self.task = task
		self.window = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
		self.window.set_default_size(150,150)
		buff = gtk.TextBuffer()
		buff.set_text(self.task.get_text())
		self.textview = gtk.TextView(buffer=buff)
		self.window.add(self.textview)
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
		self.task.set_text(texte)
		
	def close(self,window) :
		#Save should be also called when buffer is modified
		self.save()
		gtk.main_quit()
