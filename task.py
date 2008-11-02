import sys, time, os, xml.dom.minidom
import string, threading

#Development variables. Should be removed
zefile = "mynote.xml"

#This class represent a project : a list of tasks sharing the same backend
class Project :
	def __init__(self, backend) :
		self.backend = backend
		
	def list_tasks(self):
		print "implement list_tasks in task.py"
		

#This class represent a task in GTG.
class Task :
	def __init__(self) :
		pass
		
	def get_text(self) :
		print "implement get_text"
		
	def set_text(self,texte) :
		print "implement set_text"
		
	
