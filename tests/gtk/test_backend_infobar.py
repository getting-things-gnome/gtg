from types import SimpleNamespace
from unittest import TestCase, skipUnless

from gi.repository import Gdk, Gtk

from GTG.backends.backend_signals import BackendSignals
from GTG.gtk.browser.backend_infobar import BackendInfoBar

try:
    _init_ok = Gtk.init_check()
except Exception:
    _init_ok = False
DISPLAY_OK = bool(_init_ok) and Gdk.Display.get_default() is not None


def _fake_app():
    backend = SimpleNamespace(get_human_name=lambda: 'TestService',
                              is_enabled=lambda: True)
    ds = SimpleNamespace(get_backend=lambda backend_id: backend)
    return SimpleNamespace(ds=ds)


@skipUnless(DISPLAY_OK, 'needs a display')
class BackendInfoBarTest(TestCase):
    """The backend infobar must build and populate on the new core
    and GTK 4 (regression tests for #784 / #901: any backend error
    used to crash before anything was shown)."""

    def test_error_banner_builds(self):
        bar = BackendInfoBar(None, _fake_app(), 'backend@1')
        bar.set_error_code(BackendSignals.ERRNO_AUTHENTICATION)
        self.assertIn('TestService', bar.label.get_label())
        self.assertEqual(Gtk.MessageType.ERROR, bar.get_message_type())

    def test_interaction_banner_builds(self):
        bar = BackendInfoBar(None, _fake_app(), 'backend@1')
        bar.set_interaction_request(
            'need something', BackendSignals().INTERACTION_INFORM, 'cb')
        self.assertEqual(Gtk.MessageType.INFO, bar.get_message_type())
        bar.response(Gtk.ResponseType.ACCEPT)
        self.assertFalse(bar.get_revealed())
