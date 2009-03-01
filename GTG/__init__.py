# -*- coding:utf-8 -*-
import os

URL             = "http://gtg.fritalk.com"
EMAIL           = "gtg@lists.launchpad.net"
VERSION         = '0.1'
LOCAL_ROOTDIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) 
DIST_ROOTDIR    = "/usr/share/gtg"

if not os.path.isdir( os.path.join(LOCAL_ROOTDIR,'data') ) :
    DATA_DIR = os.path.join(DIST_ROOTDIR,'data')
else:
    DATA_DIR = os.path.join(LOCAL_ROOTDIR,'data')
