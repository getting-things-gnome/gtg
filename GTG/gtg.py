#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 - Lionel Dricot & Bertrand Rousseau
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
# Getting things GNOME!: a gtd-inspired organizer for GNOME
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
#   For example : 21@2 is the 21st task of the 2nd project
#   This way, we are sure that a tid is unique accross multiple projects
#
#==============================================================================

"""This is the top-level exec script for running GTG"""

#=== IMPORT ===================================================================
import os
import sys
import logging
import dbus

# our own imports
from GTG.backends import BackendFactory
from GTG import _
from GTG.core import CoreConfig
from GTG.core.datastore import DataStore
from GTG.gtk.manager import Manager
from GTG.tools.logger import Log

#=== OBJECTS ==================================================================

# code borrowed from Specto. Avoid having multiples instances of gtg
# reading the same tasks
# that's why we put the pid file in the data directory :
# we allow one instance of gtg by data directory.


def check_instance(directory, uri_list=[]):
    """
    Check if gtg is already running.
    If so, open the tasks whose ids are in the uri_list
    """
    pidfile = os.path.join(directory, "gtg.pid")
    if not os.path.exists(pidfile):
        open(pidfile, "w").close()
        os.chmod(pidfile, 0600)

    # see if gtg is already running
    pid = open(pidfile, "r").readline()
    if pid:
        p = os.system("/bin/ps %s >/dev/null" % pid)
        p_name = os.popen("/bin/ps -f %s" % pid).read()
        if p == 0 and "gtg" in p_name:
            print _("gtg is already running!")
            try:
                d = dbus.SessionBus().get_object(CoreConfig.BUSNAME,
                                                 CoreConfig.BUSINTERFACE)
                d.ShowTaskBrowser()
                # if the user has specified a task to open, do that
                for uri in uri_list:
                    if uri.startswith("gtg://"):
                        d.OpenTaskEditor(uri[6:])
                raise SystemExit
            except dbus.exceptions.DBusException:
                # If we cant't connect to the interface (e.g. changed interface
                # between GTG versions), we won't do anything more
                raise SystemExit

    # write the pid file
    with open(pidfile, "w") as f:
        f.write(repr(os.getpid()))


def remove_pidfile(directory):
    """ Remove the pid file """
    pidfile = os.path.join(directory, "gtg.pid")
    try:
        os.remove(pidfile)
    except OSError:
        # Ignore missing PID file
        pass

#=== MAIN CLASS ===============================================================


def main(options=None, args=None):
    '''
    Calling this starts the full GTG experience  ( :-D )
    '''
    ds, req = core_main_init(options, args)
    # Launch task browser
    manager = Manager(req)
    # main loop
    # To be more user friendly and get the logs of crashes, we show an apport
    # hooked window upon crashes
    if not options.no_crash_handler:
        from GTG.gtk.crashhandler import signal_catcher
        with signal_catcher(manager.close_browser):
            manager.main(once_thru=options.boot_test, uri_list=args)
    else:
        manager.main(once_thru=options.boot_test, uri_list=args)
    core_main_quit(req, ds)


def core_main_init(options=None, args=None):
    '''
    Part of the main function prior to the UI initialization.
    '''
    # Debugging subsystem initialization
    if options.debug:
        Log.setLevel(logging.DEBUG)
        Log.debug("Debug output enabled.")
    else:
        Log.setLevel(logging.INFO)
    Log.set_debugging_mode(options.debug)
    config = CoreConfig()
    check_instance(config.get_data_dir(), args)
    backends_list = BackendFactory().get_saved_backends_list()
    # Load data store
    ds = DataStore(config)
    # Register backends
    for backend_dic in backends_list:
        ds.register_backend(backend_dic)
    # save the backends directly to be sure projects.xml is written
    ds.save(quit=False)

    # Launch task browser
    req = ds.get_requester()
    return ds, req


def core_main_quit(req, ds):
    '''
    Last bits of code executed in GTG, after the UI has been shut off.
    Currently, it's just saving everything.
    '''
    # Ideally we should load window geometry configuration from a config
    # backend like gconf at some point, and restore the appearance of the
    # application as the user last exited it.
    #
    # Ending the application: we save configuration
    req.save_config()
    ds.save(quit=True)
    config = req.get_global_config()
    remove_pidfile(config.get_data_dir())
    sys.exit(0)


#=== EXECUTION ================================================================

if __name__ == "__main__":
    main()
