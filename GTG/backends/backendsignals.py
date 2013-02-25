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
# -----------------------------------------------------------------------------

import gobject

from GTG.tools.borg import Borg


class BackendSignals(Borg):
    '''
    This class handles the signals that involve backends.
    In particular, it's a wrapper Borg class around a _BackendSignalsGObject
    class, and all method of the wrapped class can be used as if they were part
    of this class
    '''

    # error codes to send along with the BACKEND_FAILED signal
    ERRNO_AUTHENTICATION = "authentication failed"
    ERRNO_NETWORK = "network is down"
    ERRNO_DBUS = "DBus interface cannot be connected"

    def __init__(self):
        '''Checks that this is the only instance, and instantiates the
        gobject'''
        super(BackendSignals, self).__init__()
        if hasattr(self, "_gobject"):
            return
        self._gobject = _BackendSignalsGObject()

    def __getattr__(self, attr):
        '''
        From outside the class, there should be no difference between self's
        attributes and self._gobject's attributes.
        '''
        if attr == "_gobject" and not "_gobject" in self.__dict__:
            raise AttributeError
        return getattr(self._gobject, attr)


def signal_type_factory(*args):
    '''
    Simply returns a gobject signal type

    @returns: tuple
    '''
    return (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, args)


class _BackendSignalsGObject(gobject.GObject):

    # signal name constants
    BACKEND_STATE_TOGGLED = 'backend-state-toggled'  # emitted when a
                                                    # backend is
                                                    # enabled or disabled
    BACKEND_RENAMED = 'backend-renamed'  # emitted when a backend is renamed
    BACKEND_ADDED = 'backend-added'
    BACKEND_REMOVED = 'backend-added'  # when a backend is deleted
    DEFAULT_BACKEND_LOADED = 'default-backend-loaded'  # emitted after all
                                                     # tasks have been
                                                     # loaded from the
                                                     # default backend
    BACKEND_FAILED = 'backend-failed'  # something went wrong with a backend
    BACKEND_SYNC_STARTED = 'backend-sync-started'
    BACKEND_SYNC_ENDED = 'backend-sync-ended'
    INTERACTION_REQUESTED = 'user-interaction-requested'

    INTERACTION_CONFIRM = 'confirm'
    INTERACTION_TEXT = 'text'

    __gsignals__ = {BACKEND_STATE_TOGGLED: signal_type_factory(str),
                    BACKEND_RENAMED: signal_type_factory(str),
                    BACKEND_ADDED: signal_type_factory(str),
                    BACKEND_REMOVED: signal_type_factory(str),
                    BACKEND_SYNC_STARTED: signal_type_factory(str),
                    BACKEND_SYNC_ENDED: signal_type_factory(str),
                    DEFAULT_BACKEND_LOADED: signal_type_factory(),
                    BACKEND_FAILED: signal_type_factory(str, str),
                    INTERACTION_REQUESTED: signal_type_factory(str, str,
                                                               str, str)}

    def __init__(self):
        super(_BackendSignalsGObject, self).__init__()
        self.backends_currently_syncing = []

    ############# Signals #########
    # connecting to signals is fine, but keep an eye if you should emit them.
    # As a general rule, signals should only be emitted in the GenericBackend
    # class
    def _emit_signal(self, signal, backend_id):
        gobject.idle_add(self.emit, signal, backend_id)

    def backend_state_changed(self, backend_id):
        self._emit_signal(self.BACKEND_STATE_TOGGLED, backend_id)

    def backend_renamed(self, backend_id):
        self._emit_signal(self.BACKEND_RENAMED, backend_id)

    def backend_added(self, backend_id):
        self._emit_signal(self.BACKEND_ADDED, backend_id)

    def backend_removed(self, backend_id):
        self._emit_signal(self.BACKEND_REMOVED, backend_id)

    def default_backend_loaded(self):
        gobject.idle_add(self.emit, self.DEFAULT_BACKEND_LOADED)

    def backend_failed(self, backend_id, error_code):
        gobject.idle_add(self.emit, self.BACKEND_FAILED, backend_id,
                         error_code)

    def interaction_requested(self, backend_id, description,
                              interaction_type, callback_str):
        gobject.idle_add(self.emit, self.INTERACTION_REQUESTED,
                         backend_id, description, interaction_type,
                         callback_str)

    def backend_sync_started(self, backend_id):
        self._emit_signal(self.BACKEND_SYNC_STARTED, backend_id)
        self.backends_currently_syncing.append(backend_id)

    def backend_sync_ended(self, backend_id):
        self._emit_signal(self.BACKEND_SYNC_ENDED, backend_id)
        try:
            self.backends_currently_syncing.remove(backend_id)
        except:
            pass

    def is_backend_syncing(self, backend_id):
        return backend_id in self.backends_currently_syncing
