import sys, time, os
import string, threading
#subfolders are added to the path
sys.path[1:1]=["backends"]

from task import Task,Project
from taskeditor import TaskEditor
from xml_backend import Backend

if __name__ == "__main__":
	gobject.threads_init()
	backend = Backend() 
	zeproject = Project(zebackend)
	# "1" is just the ID of the task
	zetask = zeproject.get_task(1)
	tv = TaskEditor(zetask)
	gtk.main()
