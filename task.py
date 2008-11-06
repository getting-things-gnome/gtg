import sys, time, os
import string, threading


#This class represent a task in GTG.
class Task :
	def __init__(self, ze_id) :
		#the id of this task in the project
		self.tid = ze_id
		self.content = None
		
	def get_id(self) :
		return self.tid
		
	def get_text(self) :
		return self.content
		
	def set_text(self,texte) :
		self.content = texte
		
#This class represent a project : a list of tasks sharing the same backend
class Project :
	def __init__(self, name) :
		self.name = name
		
	def list_tasks(self):
		print "implement list_tasks in task.py"
		
	def get_task(self,ze_id) :
		return self.backend.get_task(ze_id)
		
	def __getbackend(self,name) :
		#currently not much done but the backend should depend on the name
		return Backend()
		
	
