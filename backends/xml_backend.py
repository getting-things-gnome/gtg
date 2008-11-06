import sys, time, os, xml.dom.minidom
import string, threading

from task import Task, Project
#Development variables. Should be removed
zefile = "mynote.xml"


#todo : Backend should only provide one big "project" object and should 
#not provide get_task and stuff like that.
class Backend :
	def __init__(self) :
		self.project = Project("project")
		if os.path.exists(zefile) :
			f = open(zefile,mode='r')
			# sanitize the pretty XML
			stringed = f.read().replace('\n','').replace('\t','')
			try :
				doc = xml.dom.minidom.parseString(stringed)
			except :
				return 0
			self.__xmlproject = doc.getElementsByTagName("project")
		
		#the file didn't exist, create it now
		else :
			doc = xml.dom.minidom.Document()
			self.__xmlproject = doc.createElement("project")
			doc.appendChild(self.project)
			#then we create the file
			f = open(zefile, mode='a+')
			f.write(doc.toxml().encode("utf-8"))
			f.close()
			
		
	#This function should return a project object with all the current tasks in it.
	def get_project(self) :
		#t is the xml of each task
		for t in self.__xmlproject[0].childNodes:
			cur_id = "%s" %t.getAttribute("id")
			cur_task = Task(cur_id)
			#we will fill the task with its content
			content = t.getElementsByTagName("content")
			if content[0].hasChildNodes():
				texte = content[0].childNodes[0].nodeValue
				cur_task.set_text(texte)
			#adding task to the project
			self.project.add_task(cur_task)
		return self.project
		
	#This function will
	def sync_project(self) :
		for tid in self.project.list_tasks():
			print tid

	def sync_task(self) :
		self.sync_project()
		
	
###################### OLD #############################		
					
		
	
	#this is old code that doesn't work. To adapt !
	def save(self) :
	

		#Currently, we are not saving the tag table.
		doc = xml.dom.minidom.Document()
		t = doc.createElement("task")
		doc.appendChild(t)
		content = doc.createElement("content")
		t.appendChild(content)
		content.appendChild(doc.createTextNode(texte))
		#it's maybe not optimal to open/close the file each time we sync
		# but I'm not sure that those operations are so frequent
		# might be changed in the future.
		f = open(zefile, mode='w+')
		f.write(doc.toprettyxml().encode("utf-8"))
		f.close()
