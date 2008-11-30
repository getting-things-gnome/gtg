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
import os
from xdg.BaseDirectory import *

class CoreConfig:
    #The projects and tasks are of course DATA !
    #We then use XDG_DATA for them
    #Don't forget the "/" at the end.
    DATA_DIR = os.path.join(xdg_data_home,'gtg/')
    DATA_FILE = "projects.xml"
    DATA_FILE_TEMPLATE = "<?xml version=\"1.0\" ?><config></config>"
    #We currently have no real config
