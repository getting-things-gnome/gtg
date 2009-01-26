#This is the core package. It contains the core of GTG.

#Current files are :

#datastore.py
#------------
#datastore is the heart of GTG. It contains a list of "TagSource".
#Each TagSource is a proxy between a backend and the datastore itself
#
#tagstore.py
#-----------
#Tagstore is to tag as datastore is to task. Of course, the tagstore is easier
#The Tag object is also provided in this file.
#
#task.py
#-------
#task.py contains the Task. A task represent, guess what,a task. 
#
#requester.py
#---------
#In order to not interact directly with the datastore, we provide "requesters"
#The requester is only an interface and there can be as many requester as 
#you want as long as they are all from the same datastore.
#Requester also provides an interface for the tagstore

#=== IMPORT ====================================================================
import os
from xdg.BaseDirectory import *
from tools             import cleanxml
from tools.configobj   import ConfigObj

class CoreConfig:
    
    #The projects and tasks are of course DATA !
    #We then use XDG_DATA for them
    #Don't forget the "/" at the end.
    DATA_DIR  = os.path.join(xdg_data_home,'gtg/')
    DATA_FILE = "projects.xml"
    CONF_DIR = os.path.join(xdg_config_home,'gtg/')
    CONF_FILE = "gtg.conf"
    conf_dict = None
    
    def __init__(self):
        if not os.path.exists(self.CONF_DIR) :
            os.mkdir(self.CONF_DIR)
        if not os.path.exists(self.CONF_DIR + self.CONF_FILE):
            f = open(self.CONF_DIR + self.CONF_FILE, "w")
            f.close()
        self.conf_dict = ConfigObj(self.CONF_DIR + self.CONF_FILE)
    
    def save_config(self):
        self.conf_dict.write()
    
    def get_backends_list(self) :
        backend_fn = []

        # Check if config dir exists, if not create it
        if not os.path.exists(self.DATA_DIR):
            os.mkdir(self.DATA_DIR)

        # Read configuration file, if it does not exist, create one
        datafile = self.DATA_DIR + self.DATA_FILE
        doc, configxml = cleanxml.openxmlfile(datafile,"config") #pylint: disable-msg=W0612
        xmlproject = doc.getElementsByTagName("backend")
        # collect configred backends
        pid = 1
        for xp in xmlproject:
            dic = {}
            #We have some retrocompatibility code
            #A backend without the module attribute is pre-rev.105
            #and is considered as "filename"
            if xp.hasAttribute("module") :
                dic["module"] = str(xp.getAttribute("module"))
                dic["pid"] = str(xp.getAttribute("pid"))
            #The following "else" could be removed later
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
        #Remember that b is a dictionnary
        for b in backend_fn :
            #We dynamically import modules needed
            module_name = "backends.%s"%b["module"]
            #FIXME : we should throw an error if the backend is not importable
            module = __import__(module_name)
            classobj = getattr(module, b["module"])
            b["parameters"] = classobj.get_parameters()
            xp = b.pop("xmlobject")
            #We will try to get the parameters
            for key in b["parameters"] :
                if xp.hasAttribute(key) :
                    b[key] = str(xp.getAttribute(key))
            back = classobj.Backend(b)
            #We put the backend itself in the dic
            b["backend"] = back
            
        return backend_fn
  
    
    def save_datastore(self,ds) :
        doc,xmlconfig = cleanxml.emptydoc("config")
    
        for b in ds.get_all_backends():
            param = b.get_parameters()
            t_xml = doc.createElement("backend")
            for key in param :
                #We dont want parameters,backend,xmlobject
                if key not in ["backend","parameters","xmlobject"] :
                    t_xml.setAttribute(key,param[key])
            #Saving all the projects at close
            xmlconfig.appendChild(t_xml)
            b.quit()

        datafile = self.DATA_DIR + self.DATA_FILE
        cleanxml.savexml(datafile,doc,backup=True)

        #Saving the tagstore
        ts = ds.get_tagstore()
        ts.save()
