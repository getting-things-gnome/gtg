from types import SimpleNamespace
from unittest import TestCase
from uuid import uuid4

import pytest

# python-dbus is an optional dependency (the Hamster plugin's): skip
# this whole module where it isn't installed, e.g. on the CI runner
dbus = pytest.importorskip('dbus')

from GTG.core.tasks import Status, Task  # noqa: E402
from GTG.plugins.hamster.hamster import HamsterPlugin  # noqa: E402
from GTG.plugins.hamster.helper import FactBuilder  # noqa: E402


class HamsterPluginTest(TestCase):
    """The Hamster plugin must speak the new core and survive a
    vanishing service (follow-up to #1286, see #998)."""

    def _task(self, title='Inspect the hive'):
        task = Task(id=uuid4(), title=title)
        return task

    def test_factbuilder_speaks_the_new_core(self):
        fake_hamster = SimpleNamespace(GetTags=lambda only_visible: [])
        builder = FactBuilder(
            fake_hamster, dict(HamsterPlugin.DEFAULT_PREFERENCES))
        fact = builder.build(self._task())
        self.assertIn('Inspect the hive', fact)

    def test_completing_a_task_does_not_nameerror(self):
        plugin = HamsterPlugin()
        task = self._task()
        task.status = Status.DONE
        plugin.on_task_modified(None, task)

    def test_get_active_id_survives_a_dead_service(self):
        plugin = HamsterPlugin()

        def boom():
            raise dbus.DBusException('gone')
        plugin.hamster = SimpleNamespace(GetTodaysFacts=boom)
        self.assertIsNone(plugin.get_active_id())
