#!/usr/bin/env python
# -*- coding:utf-8 -*-

from distutils.core import setup
import glob
import GTG

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
  data_files   = [
    ('/usr/share/gtg', ['data/icons','data/firstrun_tasks.xml']),
                 ],
  scripts=['gtg',],
)
