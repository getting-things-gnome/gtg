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
#
#==============================================================================
#
# Getting things Gnome!: a gtd-inspired organizer for GNOME
#
# @author : B. Rousseau, L. Dricot
# @date   : November 2008
#
#   main.py contains the configuration and data structures loader
#   taskbrowser.py contains the main GTK interface for the tasklist
#   task.py contains the implementation of a task and a project
#   taskeditor contains the GTK interface for task editing
#       (it's the window you see when writing a task)
#   backends/xml_backend.py is the way to store tasks and project in XML
#
#   tid stand for "Task ID"
#   pid stand for "Project ID"
#   uid stand for "Universal ID" which is generally the tuple [pid,tid]
#
#   Each id are *strings*
#   tid are the form "X@Y" where Y is the pid.
#   For example : 21@2 is the 21th task of the 2nd project
#   This way, we are sure that a tid is unique accross multiple projects
#
#==============================================================================

"""This is the top-level exec script for running GTG"""

#=== IMPORT ===================================================================
from __future__ import with_statement

import sys
import os
import dbus
import logging
import signal
from contextlib import contextmanager

#our own imports
from GTG                     import _
from GTG.viewmanager.manager import Manager
from GTG.core.datastore      import DataStore
from GTG.core                import CoreConfig
from GTG.tools.logger        import Log
from GTG.tools               import gtkcrashhandler
from GTG                     import info

#=== OBJECTS ==================================================================

#code borrowed from Specto. Avoid having multiples instances of gtg
#reading the same tasks
#that's why we put the pid file in the data directory :
#we allow one instance of gtg by data directory.

def check_instance(directory):
    """Check if gtg is already running."""
    pidfile = os.path.join(directory, "gtg.pid")
    if not os.path.exists(pidfile):
        open(pidfile, "w").close()
        os.chmod(pidfile, 0600)

    #see if gtg is already running
    pid = open(pidfile, "r").readline()
    if pid:
        p = os.system("/bin/ps %s >/dev/null" % pid)
        p_name = os.popen("/bin/ps -f %s" % pid).read()
        if p == 0 and "gtg" in p_name:
            print _("gtg is already running!")
            d=dbus.SessionBus().get_object(CoreConfig.BUSNAME,\
                                           CoreConfig.BUSINTERFACE)
            d.show_task_browser()
            sys.exit(0)
            
    #write the pid file
    with open(pidfile, "w") as f:
        f.write(`os.getpid()`)

#=== MAIN CLASS ===============================================================

def main(options=None, args=None):
    # Debugging subsystem initialization
    if options.debug:
        Log.setLevel(logging.DEBUG)
        Log.debug("Debug output enabled.")
    
    config = CoreConfig()
    check_instance(config.DATA_DIR)
    backends_list = config.get_backends_list()

    #initialize Apport hook for crash handling
    gtkcrashhandler.initialize(app_name = "Getting Things GNOME!", message  =  \
          "GTG" + info.VERSION + _(" has crashed. Please report the bug on <a "\
          "href=\"http://bugs.edge.launchpad.net/gtg\">our Launchpad page</a>."\
          " If you have Apport installed, it will be started for you."),       \
          use_apport = True)
    
    # Load data store
    ds = DataStore()
    
    for backend_dic in backends_list:
        ds.register_backend(backend_dic)
    
    #save directly the backends to be sure to write projects.xml
    config.save_datastore(ds)
        
    # Launch task browser
    req = ds.get_requester()
    manager = Manager(req, config)
 
    #we listen for signals from the system in order to save our configuration
    # if GTG is forcefully terminated (e.g.: on shutdown).
    @contextmanager
    def signal_catcher():
        #if TERM or ABORT are caught, we close the browser
        for s in [signal.SIGABRT, signal.SIGTERM]:
            signal.signal(s, lambda a,b: manager.close_browser())
        yield

    #main loop
    with signal_catcher():
        manager.main()
      
    # Ideally we should load window geometry configuration from a config.
    # backend like gconf at some point, and restore the appearance of the
    # application as the user last exited it.

    # Ending the application: we save configuration
    config.save_config()
    config.save_datastore(ds)

#=== EXECUTION ================================================================

if __name__ == "__main__":
    main()
