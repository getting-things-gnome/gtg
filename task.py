import sys, time, os
import string, threading
#subfolders are added to the path
sys.path[1:1]=["backends"]

#This class represent a project : a list of tasks sharing the same backend
class Project :
	def __init__(self, name) :
		self.name = name
		#Each project can have its own backend
		self.backend = self.__getbackend(self.name)
		
	def list_tasks(self):
		print "implement list_tasks in task.py"
		
	def get_task(self,id) :
		print "implement get_task"
		
	def __getbackend(name) :
		#currently not much done
		return Backend()
		

#This class represent a task in GTG.
class Task :
	def __init__(self) :
		pass
		
	def get_text(self) :
		print "implement get_text"
		
	def set_text(self,texte) :
		print "implement set_text"
		
	
