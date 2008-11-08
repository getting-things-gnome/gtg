import sys, time, os
import string, threading


#This class represent a task in GTG.
class Task :
	def __init__(self, ze_id) :
		#the id of this task in the project
		#tid is a string ! (we have to choose a type and stick to it)
		self.tid = str(ze_id)
		self.content = None
		self.sync_func = None
		self.title = None
				
	def get_id(self) :
		return self.tid
		
	def get_title(self) :
	    return self.title
	
	def set_title(self,title) :
	    self.title = title
		
	def get_text(self) :
		return self.content
		
	def set_text(self,texte) :
		self.content = texte
		
	#This is a callback. The "sync" function has to be set
	def set_sync_func(self,sync) :
		self.sync_func = sync
		
	def sync(self) :
		self.sync_func()
		
#This class represent a project : a list of tasks sharing the same backend
class Project :
	def __init__(self, name) :
		self.name = name
		self.list = {}
		
	def list_tasks(self):
		result = self.list.keys()
		#we must ensure that we not return a None
		if not result :
			result = []
		return result
		
	def get_task(self,ze_id) :
		return self.list[str(ze_id)]
		
	def add_task(self,task) :
		tid = task.get_id()
		self.list[str(tid)] = task
		
	
