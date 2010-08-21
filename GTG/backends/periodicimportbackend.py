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

'''
Contains PeriodicImportBackend, a GenericBackend specialized for checking the
remote backend in polling.
'''

import threading

from GTG.backends.genericbackend import GenericBackend
from GTG.backends.backendsignals import BackendSignals
from GTG.tools.interruptible     import interruptible



class PeriodicImportBackend(GenericBackend):
    '''
    This class can be used in place of GenericBackend when a periodic import is
    necessary, as the remote service providing tasks does not signals the
    changes.
    To use this, only two things are necessary:
        - using do_periodic_import instead of start_get_tasks
        - having in _static_parameters a "period" key, as in 
            "period": { \
                GenericBackend.PARAM_TYPE: GenericBackend.TYPE_INT, \
                GenericBackend.PARAM_DEFAULT_VALUE: 2, },
          This specifies the time that must pass between consecutive imports
          (in minutes)
    '''

    def __init__(self, parameters):
        super(PeriodicImportBackend, self).__init__(parameters)
        self.running_iteration = False

    @interruptible
    def start_get_tasks(self):
        '''
        This function launches the first periodic import, and schedules the
        next ones.
        '''
        #if we're already importing, we skip this import cycle.
        if not self.running_iteration:
            try:
                #if an iteration was scheduled, we cancel it
                if self.import_timer:
                    self.import_timer.cancel()
            except:
                pass
            self.running_iteration = True
            self._start_get_tasks()
            self.running_iteration = False
            self.cancellation_point()

        if self.is_enabled() == False:
            return
        self.import_timer = threading.Timer( \
                                self._parameters['period'] * 60.0, \
                                self.start_get_tasks)
        self.import_timer.start()

    def _start_get_tasks(self):
        '''
        This function executes an imports and schedules the next
        '''
        self.cancellation_point()
        BackendSignals().backend_sync_started(self.get_id())
        self.do_periodic_import()
        BackendSignals().backend_sync_ended(self.get_id())

    def quit(self, disable = False):
        '''
        Called when GTG quits or disconnects the backend.
        '''
        super(PeriodicImportBackend, self).quit(disable)
        try:
            self.import_timer.cancel()
        except Exception:
            pass
        try:
            self.import_timer.join()
        except Exception:
            pass

