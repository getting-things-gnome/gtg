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
import os, xml.dom.minidom
from xdg.BaseDirectory import *
from tools import cleanxml

class CoreConfig:
    #The projects and tasks are of course DATA !
    #We then use XDG_DATA for them
    #Don't forget the "/" at the end.
    DATA_DIR = os.path.join(xdg_data_home,'gtg/')
    DATA_FILE = "projects.xml"
    #We currently have no real config
    
    def get_backends_list(self) :
        backend_fn = []

        # Check if config dir exists, if not create it
        if not os.path.exists(self.DATA_DIR):
            os.mkdir(self.DATA_DIR)

        # Read configuration file, if it does not exist, create one
        conffile = self.DATA_DIR + self.DATA_FILE
        doc, configxml = cleanxml.openxmlfile(conffile,"config")
        xmlproject = doc.getElementsByTagName("backend")
        # collect configred backends
        for xp in xmlproject:
            dic = {}
            pid = 1
            #We have some retrocompatibility code
            #A backend without the module attribute is pre-rev.105
            #and is considered as "filename"
            if xp.hasAttribute("module") :
                dic["module"] = str(xp.getAttribute("module"))
                dic["pid"] = str(xp.getAttribute("pid"))
                
            #The following else could be remove later
            else :
                dic["module"] = "localfile"
                dic["pid"] = str(pid)
            
            dic["xmlobject"] = xp
                
            pid += 1
            backend_fn.append(dic)
                
        #If no backend available, we create a new using localfile
        if len(backend_fn) == 0 :
            dic = {}
            dic["module"] = "localfile"
            dic["pid"] = 1
            backend_fn.append(dic)
            
        #Now that the backend list is build, we will construct them
        
        for b in backend_fn :
            #We dynamically import modules needed
            module_name = "backends.%s"%b["module"]
            module = __import__(module_name)
            classobj = getattr(module, b["module"])
            back = classobj.Backend(b)
            #We put the backend itself in the dic
            b["backend"] = back
            b["parameters"] = classobj.get_parameters()
            xp = b.pop("xmlobject")
            #We will try to get the parameters
            for key in b["parameters"] :
                if xp.hasAttribute(key) :
                    b[key] = str(xp.hasAttribute(key))
            
        return backend_fn
  
    
    def save_datastore(self,ds) :
        s = "<?xml version=\"1.0\" ?><config>\n"
        for b in ds.get_all_backends():
            param = b.get_parameters()
            #FIXME : we have to be generic here !
            s = s + "\t<backend filename=\"%s\"/>\n" % param["filename"]
            #Saving all the projects at close
            b.quit()
        s = s + "</config>\n"
        f = open(self.DATA_DIR + self.DATA_FILE,mode='w')
        f.write(s)
        f.close()
        #Saving the tagstore
        ts = ds.get_tagstore()
        ts.save()
