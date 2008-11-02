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

from task import Task
from project import Project
from taskeditor import TaskEditor

if __name__ == "__main__":
	zeproject = Project("my_project")
	# "1" is just the ID of the task
	zetask = zeproject.get_task(1)
	tv = TaskEditor(zetask)
	gtk.main()
