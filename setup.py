#!/usr/bin/env python
# -*- coding:utf-8 -*-

from distutils.core import setup
import glob
import GTG
import os
import sys

### CONSTANTS ##################################################################

DATA_DIR = "/usr/share/gtg"

### TOOLS ######################################################################

def create_icon_list():
    fileList = []
    rootdir  = "data/icons"
    for root, subFolders, files in os.walk(rootdir):
        dirList = []
        for file in files:
            dirList.append(os.path.join(root,file))
        if len(dirList)!=0:
            fileList.append( (DATA_DIR+"/"+root,dirList) )
    return fileList

def create_data_files():
    data_files = []
    # icons
    icons = create_icon_list()
    data_files.extend(icons)
    # misc
    data_files.append((DATA_DIR, ['data/firstrun_tasks.xml']))
    return data_files
    
### SETUPT SCRIPT ##############################################################

author = 'The GTG Team'

setup(
  name         = 'GTG',
  version      = GTG.VERSION,
  url          = GTG.URL,
  author       = author,
  author_email = GTG.EMAIL,
  description  = 'GTG is a personal organizer for the GNOME desktop environment.',
  packages     = ['GTG','GTG.backends','GTG.core','GTG.taskbrowser','GTG.taskeditor','GTG.tools'],
  package_data = {'GTG.taskbrowser':['taskbrowser.glade'],'GTG.taskeditor':['taskeditor.glade']},
  data_files   = create_data_files(),
  scripts=['gtg',],
)

