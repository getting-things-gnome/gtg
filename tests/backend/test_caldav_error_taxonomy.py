# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) - The Getting Things GNOME Team
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

"""CalDAV backend error handling: a failing sync must report a clear
error to the GUI (a BackendSignals errno the info bar knows how to show)
and never let the exception kill the sync thread, and it must not even
try while the machine is offline (#1322, #1324)."""

from unittest import TestCase
from unittest.mock import patch

import caldav
import requests

from GTG.backends.backend_caldav import Backend, _dav_failure_errno
from GTG.backends.backend_signals import BackendSignals
from GTG.core.datastore import Datastore


class DavFailureErrnoTest(TestCase):
    """The exception -> errno classifier."""

    def test_authorization_error_is_authentication(self):
        err = caldav.lib.error.AuthorizationError(url='u', reason='Unauthorized')
        self.assertEqual(_dav_failure_errno(err),
                         BackendSignals.ERRNO_AUTHENTICATION)

    def test_connection_error_is_network(self):
        err = requests.exceptions.ConnectionError('name resolution failed')
        self.assertEqual(_dav_failure_errno(err),
                         BackendSignals.ERRNO_NETWORK)

    def test_other_dav_error_is_network(self):
        # AuthorizationError is a DAVError subclass, so a plain DAVError
        # must still fall through to the network branch, not authentication.
        self.assertEqual(_dav_failure_errno(caldav.lib.error.DAVError()),
                         BackendSignals.ERRNO_NETWORK)

    def test_unknown_error_propagates(self):
        # Anything unexpected returns None so do_periodic_import re-raises it.
        self.assertIsNone(_dav_failure_errno(ValueError('boom')))


class DoPeriodicImportErrorHandlingTest(TestCase):
    """do_periodic_import turns a raised failure into a reported error."""

    @staticmethod
    def _backend(dav_client):
        datastore = Datastore()
        parameters = {'pid': 'favorite', 'service-url': 'x',
                      'username': 'u', 'password': 'p', 'period': 1,
                      'is-first-run': False}
        backend = Backend(parameters)
        backend.register_datastore(datastore)
        backend.initialize()
        return backend

    @patch('GTG.backends.backend_caldav.is_connection_up', new=lambda: True)
    @patch('GTG.backends.periodic_import_backend.threading.Timer')
    @patch('GTG.backends.backend_caldav.caldav.DAVClient')
    def test_auth_failure_is_reported_not_raised(self, dav_client, timer):
        backend = self._backend(dav_client)
        dav_client.return_value.principal.side_effect = \
            caldav.lib.error.AuthorizationError(url='u', reason='Unauthorized')
        signals = BackendSignals()
        with patch.object(signals, 'backend_failed') as failed:
            backend.do_periodic_import()  # must not raise
        failed.assert_called_once_with(backend.get_id(),
                                       BackendSignals.ERRNO_AUTHENTICATION)

    @patch('GTG.backends.backend_caldav.is_connection_up', new=lambda: True)
    @patch('GTG.backends.periodic_import_backend.threading.Timer')
    @patch('GTG.backends.backend_caldav.caldav.DAVClient')
    def test_network_failure_is_reported_not_raised(self, dav_client, timer):
        backend = self._backend(dav_client)
        dav_client.return_value.principal.side_effect = \
            requests.exceptions.ConnectionError('temporary failure in name '
                                                'resolution')
        signals = BackendSignals()
        with patch.object(signals, 'backend_failed') as failed:
            backend.do_periodic_import()  # must not raise
        failed.assert_called_once_with(backend.get_id(),
                                       BackendSignals.ERRNO_NETWORK)

    @patch('GTG.backends.backend_caldav.is_connection_up', new=lambda: True)
    @patch('GTG.backends.periodic_import_backend.threading.Timer')
    @patch('GTG.backends.backend_caldav.caldav.DAVClient')
    def test_unexpected_error_still_propagates(self, dav_client, timer):
        backend = self._backend(dav_client)
        dav_client.return_value.principal.side_effect = ValueError('boom')
        signals = BackendSignals()
        with patch.object(signals, 'backend_failed') as failed:
            with self.assertRaises(ValueError):
                backend.do_periodic_import()
        failed.assert_not_called()

    @patch('GTG.backends.backend_caldav.is_connection_up', new=lambda: False)
    @patch('GTG.backends.periodic_import_backend.threading.Timer')
    @patch('GTG.backends.backend_caldav.caldav.DAVClient')
    def test_offline_skips_the_import_entirely(self, dav_client, timer):
        backend = self._backend(dav_client)
        with patch.object(backend, '_do_periodic_import') as inner:
            backend.do_periodic_import()  # offline: must be a no-op
        inner.assert_not_called()
        dav_client.return_value.principal.assert_not_called()
