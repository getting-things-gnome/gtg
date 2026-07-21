from unittest import TestCase
from unittest.mock import Mock

from GTG.core.datastore import Datastore


class DatastoreRemovalSyncTest(TestCase):
    """Removing a task locally must be propagated to the enabled
    backends via queue_remove_task, so the deletion is pushed to the
    server instead of the task reappearing on the next import
    (follow-up to #1265, which only wired the 'set' direction)."""

    def setUp(self):
        self.ds = Datastore()
        self.backend = Mock()
        self.backend.is_enabled.return_value = True
        self.ds.backends['test-backend'] = self.backend

    def test_removing_a_task_queues_its_removal(self):
        task = self.ds.tasks.new('a task')
        tid = task.id
        self.ds.tasks.remove(tid)
        self.backend.queue_remove_task.assert_called_once_with(tid)

    def test_removing_a_parent_queues_every_descendant(self):
        parent = self.ds.tasks.new('parent')
        child_a = self.ds.tasks.new('child a', parent=parent.id)
        child_b = self.ds.tasks.new('child b', parent=parent.id)
        self.backend.queue_remove_task.reset_mock()

        self.ds.tasks.remove(parent.id)

        removed = [c.args[0]
                   for c in self.backend.queue_remove_task.call_args_list]
        self.assertEqual(3, len(removed))
        self.assertEqual({parent.id, child_a.id, child_b.id}, set(removed))
        # children are cascaded before their parent
        self.assertEqual(parent.id, removed[-1])

    def test_disabled_backend_is_not_notified(self):
        self.backend.is_enabled.return_value = False
        task = self.ds.tasks.new('a task')
        self.ds.tasks.remove(task.id)
        self.backend.queue_remove_task.assert_not_called()
