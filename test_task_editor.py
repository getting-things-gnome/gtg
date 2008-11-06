import sys, time, os
import string, threading

#subfolders are added to the path
sys.path[1:1]=["backends"]

from xml_backend import Backend

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

from task import Task, Project
from taskeditor import TaskEditor

if __name__ == "__main__":
	my_backend = Backend()
	zeproject = my_backend.get_project()
	# "1" is just the ID of the task
	zetask = zeproject.get_task(1)
	zetask.set_sync_func(my_backend.sync_task)
	tv = TaskEditor(zetask)
	## callback here to sync ?
	gtk.main()
