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
		
	def close(self,window) :
		print self.textview.get_buffer()
		gtk.main_quit()

	

if __name__ == "__main__":
	gobject.threads_init()
	tv = TaskEditor()
	gtk.main()
