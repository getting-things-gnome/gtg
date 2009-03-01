#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personnal organizer for the GNOME desktop
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
