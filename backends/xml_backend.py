import sys, time, os, xml.dom.minidom
import string, threading

from task import Project,Task
#Development variables. Should be removed
zefile = "mynote.xml"

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
			for task in self.project[0].childNodes:
				print task.getAttribute("id")
		
		#the file didn't exist, create it now
		else :
			doc = xml.dom.minidom.Document()
			self.project = doc.createElement("project")
			doc.appendChild(self.project)
			#then we create the file
			f = open(zefile, mode='a+')
			f.write(doc.toxml().encode("utf-8"))
			f.close()
			
	def get_task(self,ze_id) :
		#not optimal. Should relearn python xml methods
		for task in self.project[0].childNodes:
			if task.getAttribute("id") == ze_id :
				my_task = Task(ze_id)
				
		return None
		
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
		task = doc.createElement("task")
		doc.appendChild(task)
		content = doc.createElement("content")
		task.appendChild(content)
		content.appendChild(doc.createTextNode(texte))
		#it's maybe not optimal to open/close the file each time we sync
		# but I'm not sure that those operations are so frequent
		# might be changed in the future.
		f = open(zefile, mode='w+')
		f.write(doc.toprettyxml().encode("utf-8"))
		f.close()
