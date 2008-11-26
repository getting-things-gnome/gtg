#=== IMPORT ====================================================================
import os
from xdg.BaseDirectory import *

class GtgConfig:
    #The projects and tasks are of course DATA !
    #We then use XDG_DATA for them
    #Don't forget the "/" at the end.
    DATA_DIR = os.path.join(xdg_data_home,'gtg/')
    DATA_FILE = "projects.xml"
    DATA_FILE_TEMPLATE = "<?xml version=\"1.0\" ?><config></config>"
    #We currently have no real config.
