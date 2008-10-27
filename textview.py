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
		window = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
		textview = gtk.TextView(buffer=None)
		window.add(textview)
		window.show_all()

	

if __name__ == "__main__":
	gobject.threads_init()
	tv = TaskEditor()
	gtk.main()
