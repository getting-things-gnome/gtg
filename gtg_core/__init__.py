#This is the core package. It contains the core of GTG.

#Current files are :

#datastore.py
#------------
#datastore contain the list of projects currently in use by the user.
#For each project, datastore link a backend.

#task.py
#-------
#task.py contains the Task and Project object. A task represent, guess what,
#a task. A project is a group of task meant to achieve one goal.

#=== IMPORT ====================================================================
import sys, os, xml.dom.minidom
from xdg.BaseDirectory import *
from tools import cleanxml

class CoreConfig:
    #The projects and tasks are of course DATA !
    #We then use XDG_DATA for them
    #Don't forget the "/" at the end.
    DATA_DIR = os.path.join(xdg_data_home,'gtg/')
    DATA_FILE = "projects.xml"
    DATA_FILE_TEMPLATE = "<?xml version=\"1.0\" ?><config></config>"
    #We currently have no real config
    
    def get_backends_list(self) :
        backends_fn = []

        # Check if config dir exists, if not create it
        if not os.path.exists(self.DATA_DIR):
            os.mkdir(self.DATA_DIR)

        # Read configuration file, if it does not exist, create one
        if os.path.exists(self.DATA_DIR + self.DATA_FILE) :
            f = open(self.DATA_DIR + self.DATA_FILE,mode='r')
            # sanitize the pretty XML
            doc=xml.dom.minidom.parse(self.DATA_DIR + self.DATA_FILE)
            cleanxml.cleanDoc(doc,"\t","\n")
            xmlproject = doc.getElementsByTagName("backend")
            # collect configred backends
            for xp in xmlproject:
                zefile = str(xp.getAttribute("filename"))
                backends_fn.append(str(zefile))
            f.close()
        else:
            print "No config file found! Creating one."
            f = open(self.DATA_DIR + self.DATA_FILE,mode='w')
            f.write(self.DATA_FILE_TEMPLATE)
            f.close()
            
        return backends_fn
  
    
    def save_datastore(self,ds) :
        s = "<?xml version=\"1.0\" ?><config>\n"
        for b in ds.get_all_backends():
            s = s + "\t<backend filename=\"%s\"/>\n" % b.get_filename()
        s = s + "</config>\n"
        f = open(self.DATA_DIR + self.DATA_FILE,mode='w')
        f.write(s)
        f.close()
