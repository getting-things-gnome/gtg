from types import SimpleNamespace
from unittest import TestCase, skipUnless

import gi
gi.require_version('Gdk', '4.0')
gi.require_version('Gtk', '4.0')

from gi.repository import Gdk, Gtk

from GTG.gtk.backends.backendstree import BackendsTree
from GTG.gtk.backends.configurepanel import ConfigurePanel

try:
    _init_ok = Gtk.init_check()
except Exception:
    _init_ok = False
DISPLAY_OK = bool(_init_ok) and Gdk.Display.get_default() is not None


def _fake_backend(backend_id='backend@1'):
    return SimpleNamespace(
        get_id=lambda: backend_id,
        get_icon=lambda: 'gtg-symbolic',
        get_human_name=lambda: 'TestService',
        is_enabled=lambda: True,
        is_default=lambda: False,
        get_attached_tags=lambda: [])


@skipUnless(DISPLAY_OK, 'needs a display')
class BackendsTreeStateChangeGuardTest(TestCase):
    """on_backend_state_changed must survive a backend that vanished.

    The row can still be listed while the backend itself is already
    gone from the datastore (a failed CalDAV account being torn down,
    #1322). get_backend() then returns None and the callback used to
    call None.get_human_name(), crashing the backends dialog. The other
    callbacks in this file (add_backend, on_backend_added) already guard
    against a missing backend; this one now does too."""

    def _tree(self):
        live = {'backend': _fake_backend()}
        ds = SimpleNamespace(
            get_all_backends=lambda disabled=False: (
                [live['backend']] if live['backend'] else []),
            get_backend=lambda backend_id: live['backend'],
            tags=SimpleNamespace(find=lambda name: None))
        tree = BackendsTree(SimpleNamespace(ds=ds))
        return tree, live

    def test_state_change_on_present_backend(self):
        tree, _live = self._tree()
        # Sanity: the row was built and refreshed during construction.
        self.assertIn('backend@1', tree.backendid_to_iter)

    def test_state_change_after_backend_removed(self):
        tree, live = self._tree()
        live['backend'] = None  # datastore no longer knows this backend
        # Must not raise even though the row id is still tracked.
        tree.on_backend_state_changed(None, 'backend@1')


@skipUnless(DISPLAY_OK, 'needs a display')
class ConfigurePanelSignalGuardTest(TestCase):
    """The configure panel's global signal handlers must tolerate the
    'no backend selected yet' state.

    BACKEND_SYNC_STARTED / _ENDED (and rename / state-toggle) are global
    signals: a CalDAV account syncing in the background fires them for
    every open panel, including one whose set_backend() has not run yet.
    self.backend was then undefined and each callback raised
    AttributeError in a flood (#1323, #1324). self.backend now defaults
    to None and every handler bails out cleanly."""

    def _panel(self):
        ds = SimpleNamespace()
        return ConfigurePanel(SimpleNamespace(ds=ds), ds)

    def test_backend_defaults_to_none(self):
        panel = self._panel()
        self.assertIsNone(panel.backend)

    def test_sync_started_without_backend(self):
        panel = self._panel()
        panel.on_sync_started(None, 'backend@1')

    def test_sync_ended_without_backend(self):
        panel = self._panel()
        panel.on_sync_ended(None, 'backend@1')

    def test_refresh_title_without_backend(self):
        panel = self._panel()
        panel.refresh_title()

    def test_refresh_sync_status_without_backend(self):
        panel = self._panel()
        panel.refresh_sync_status()
