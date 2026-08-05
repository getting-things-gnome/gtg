#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
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

""" Communicate with Network Manager """

import logging
import weakref

from gi.repository import Gio # type: ignore[import-untyped]

log = logging.getLogger(__name__)

# Backends that want their pending writes retried when connectivity comes
# back. Weak so a deleted backend drops out on its own.
_retry_registry = weakref.WeakSet()
_watching_network = False


def is_connection_up():
    """ Returns True if GTG can access the Internet """

    network_monitor = Gio.NetworkMonitor.get_default()
    return network_monitor.get_network_available()


def register_for_retry(backend):
    """Register a backend to be retried when connectivity returns.

    On the next 'network is back up' event, backend.retry_pending_sync()
    is called so tasks edited offline are pushed without waiting for the
    next local change. See GenericBackend.retry_pending_sync.
    """
    _retry_registry.add(backend)
    _ensure_network_watch()


def _ensure_network_watch():
    """Connect to NetworkMonitor::network-changed exactly once."""
    global _watching_network
    if _watching_network:
        return
    try:
        Gio.NetworkMonitor.get_default().connect('network-changed',
                                                 _on_network_changed)
        _watching_network = True
    except Exception:
        # No usable network monitor: retries just won't be automatic.
        log.warning("Could not watch network state; offline writes will be "
                    "retried on the next local change instead.")


def _on_network_changed(_monitor, available):
    if available:
        _notify_network_available()


def _notify_network_available():
    """Ask every registered backend with queued writes to retry now."""
    for backend in list(_retry_registry):
        try:
            backend.retry_pending_sync()
        except Exception:
            log.exception("Failed to retry pending sync for a backend")


if __name__ == "__main__":
    print("is_connection_up() == %s" % is_connection_up())
