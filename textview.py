import sys, time, os
import string, threading

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
	def __init__(self) :
		self.window = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
		self.window.set_default_size(150,150)
		self.textview = gtk.TextView(buffer=None)
		self.window.add(self.textview)
		self.window.connect("destroy", self.close)
		self.window.show_all()
		
	def save(self) :
		#the text buffer
		buff = self.textview.get_buffer()
		#the tag table
		table = buff.get_tag_table()
		#We need two iterators to get the text
		start = buff.get_start_iter()
		end = buff.get_end_iter()
		#we get the text
		texte = buff.get_text(start,end)
		print table
		print texte
		
	def close(self,window) :
		#Save should be also called when buffer is modified
		self.save()
		gtk.main_quit()

	

if __name__ == "__main__":
	gobject.threads_init()
	tv = TaskEditor()
	gtk.main()
