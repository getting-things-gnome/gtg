import sys, time, os, xml.dom.minidom
import string, threading

try:
 	import pygtk
  	pygtk.require("2.0")
except:
  	pass
try:
	import gtk
  	import gtk.glade
	import gobject
except:
	sys.exit(1)
	
zefile = "mynote.xml"

class TaskEditor :
	def __init__(self) :
		self.window = gtk.Window(type=gtk.WINDOW_TOPLEVEL)
		self.window.set_default_size(150,150)
		#We open the note file or create it if it doesn't exist
		if os.path.exists(zefile) :
			f = open(zefile,mode='r')
			# sanitize the pretty XML
			stringed = f.read().replace('\n','').replace('\t','')
			try :
				doc = xml.dom.minidom.parseString(stringed)
			except :
				return 0
			content = doc.getElementsByTagName("content")
			if content[0].hasChildNodes():
				texte = content[0].childNodes[0].nodeValue
				buff = gtk.TextBuffer()
				buff.set_text(texte)
			else :
				buff = None
			
		#the file didn't exist, create it now
		else :
			doc = xml.dom.minidom.Document()
			task = doc.createElement("task")
			doc.appendChild(task)
			#then we create the file
			f = open(zefile, mode='a+')
			f.write(doc.toxml().encode("utf-8"))
			f.close()
		
		self.textview = gtk.TextView(buffer=buff)
		self.window.add(self.textview)
		self.window.connect("destroy", self.close)
		self.window.show_all()
		
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
		
	def close(self,window) :
		#Save should be also called when buffer is modified
		self.save()
		gtk.main_quit()

	

if __name__ == "__main__":
	gobject.threads_init()
	tv = TaskEditor()
	gtk.main()
