#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2009 - Lionel Dricot & Bertrand Rousseau
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

from distutils.core import setup
import glob
import GTG
import os
import sys

### CONSTANTS ##################################################################

DATA_DIR        = "/usr/share/gtg"
GLOBAL_ICON_DIR = "/usr/share/icons/hicolor"

### TOOLS ######################################################################

def create_icon_list():
    fileList = []
    rootdir  = "data/icons"
    for root, subFolders, files in os.walk(rootdir):
        dirList = []
        for file in files:
            dirList.append(os.path.join(root,file))
        if len(dirList)!=0:
            fileList.append( (os.path.join(DATA_DIR,root),dirList) )
    return fileList

def create_data_files():
    data_files = []
    # icons
    icons = create_icon_list()
    data_files.extend(icons)
    # gtg .desktop icon
    data_files.append(('/usr/share/icons/hicolor/16x16/apps', ['data/icons/hicolor/16x16/apps/gtg.png']))
    data_files.append(('/usr/share/icons/hicolor/scalable/apps', ['data/icons/hicolor/scalable/apps/gtg.svg']))
    # misc
    data_files.append((DATA_DIR, ['data/firstrun_tasks.xml']))
    data_files.append(('/usr/share/applications', ['gtg.desktop']))
    return data_files
    
### SETUPT SCRIPT ##############################################################

author = 'The GTG Team'

setup(
  name         = 'gtg',
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

