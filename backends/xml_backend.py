"import sys, time, os, xml.dom.minidom
import string, threading

from task import Task, Project
#Development variables. Should be removed
zefile = "mynote.xml"


#todo : Backend should only provide one big "project" object and should 
#not provide get_task and stuff like that.
class Backend :
	def __init__(self) :
		if os.path.exists(zefile) :
			f = open(zefile,mode='r')
			# sanitize the pretty XML
			stringed = f.read().replace('\n','').replace('\t','')
			try :
				doc = xml.dom.minidom.parseString(stringed)
			except :
				return 0
			self.project = doc.getElementsByTagName("project")
		
		#the file didn't exist, create it now
		else :
			doc = xml.dom.minidom.Document()
			self.project = doc.createElement("project")
			doc.appendChild(self.project)
			#then we create the file
			f = open(zefile, mode='a+')
			f.write(doc.toxml().encode("utf-8"))
			f.close()
			
			
	def get_project(self) :
		#TODO
		
	#This function will
	def sync_project(self) :

	def sync_task(self) :
		
	
###################### OLD #############################		
					
	
	#to remove
	def get_task(self,ze_id) :
		
		t = self.__get_xmltask(ze_id)
		my_task = Task(ze_id)
		content = t.getElementsByTagName("content")
		if content[0].hasChildNodes():
			texte = content[0].childNodes[0].nodeValue
			my_task.set_text(texte)
			return my_task
		else :		
			return None
		
	#to remove
	def __get_xmltask(self,ze_id) :
		#not optimal. Should relearn python xml methods
		for t in self.project[0].childNodes:
			cur_id = "%s" %t.getAttribute("id")
			my_id = "%s" %ze_id
			if cur_id == my_id :
				return t
		
	
	#this is old code that doesn't work. To adapt !
	def save(self) :
	
		#the text buffer
		buff = self.textview.get_buffer()
		#the tag table
		table = buff.get_tag_table()
		#we get the text
		texte = buff.get_text(buff.get_start_iter(),buff.get_end_iter())
		#We should have a look at Tomboy Serialize function 
		#NoteBuffer.cs : line 1163
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
