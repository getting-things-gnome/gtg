import sys, time, os
import string, threading

from task import Task,Project
from taskeditor import TaskEditor

if __name__ == "__main__":
	zeproject = Project("my_project")
	# "1" is just the ID of the task
	zetask = zeproject.get_task(1)
	tv = TaskEditor(zetask)
	gtk.main()
