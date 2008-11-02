import sys, time, os
import string, threading

#subfolders are added to the path
sys.path[1:1]=["backends"]

from xml_backend import Backend

#This class represent a project : a list of tasks sharing the same backend
class Project :
	def __init__(self, name) :
		self.name = name
		#Each project can have its own backend
		self.backend = self.__getbackend(self.name)
		
	def list_tasks(self):
		print "implement list_tasks in task.py"
		
	def get_task(self,ze_id) :
		return self.backend.get_task(ze_id)
		
	def __getbackend(self,name) :
		#currently not much done but the backend should depend on the name
		return Backend()
		
