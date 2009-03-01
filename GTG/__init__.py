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
import os

URL             = "http://gtg.fritalk.com"
EMAIL           = "gtg@lists.launchpad.net"
VERSION         = '0.0.9rc3'
LOCAL_ROOTDIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) 
DIST_ROOTDIR    = "/usr/share/gtg"

if not os.path.isdir( os.path.join(LOCAL_ROOTDIR,'data') ) :
    #DATA_DIR = os.path.join(DIST_ROOTDIR,'data')
    DATA_DIR = DIST_ROOTDIR
else:
    DATA_DIR = os.path.join(LOCAL_ROOTDIR,'data')
