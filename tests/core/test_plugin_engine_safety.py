from types import SimpleNamespace
from unittest import TestCase

from GTG.core.plugins.engine import PluginEngine


class _RaisingInstance:
    def activate(self, api):
        raise RuntimeError('boom')


class _RecordingInstance:
    def __init__(self):
        self.activated = False

    def activate(self, api):
        self.activated = True


def _stub_plugin(instance, dbus_depends=None):
    return SimpleNamespace(enabled=True, error=False, active=False,
                           instance=instance, module_name='stub',
                           dbus_depends=dbus_depends or [],
                           missing_dbus=[])


def _engine():
    engine = PluginEngine.__new__(PluginEngine)
    engine.plugin_apis = [SimpleNamespace(is_editor=lambda: False)]
    return engine


class PluginEngineSafetyTest(TestCase):
    """A broken or unsatisfied plugin must never break startup
    (regression tests for #998 / #683 / #1248)."""

    def test_raising_plugin_does_not_propagate(self):
        plugin = _stub_plugin(_RaisingInstance())
        _engine().activate_plugins([plugin])
        self.assertTrue(plugin.error)
        self.assertFalse(plugin.active)
        self.assertFalse(plugin.enabled)

    def test_missing_dbus_service_blocks_activation(self):
        instance = _RecordingInstance()
        plugin = _stub_plugin(
            instance,
            dbus_depends=['org.gnome.NoSuchService:/org/gnome/NoSuch'])
        _engine().activate_plugins([plugin])
        self.assertTrue(plugin.error)
        self.assertFalse(instance.activated)
        self.assertFalse(plugin.enabled)
        # the plugins dialog unpacks (name, path) pairs: keep that shape
        self.assertEqual([('org.gnome.NoSuchService', '/org/gnome/NoSuch')],
                         plugin.missing_dbus)
