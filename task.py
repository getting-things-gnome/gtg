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
		
	
