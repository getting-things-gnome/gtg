from unittest import TestCase
from uuid import uuid4

from GTG.core.tasks import Task


class TaskEqualityTest(TestCase):
    """Task.__eq__ must follow the Python contract: comparing with a
    foreign type (e.g. a bare UUID used as a dict key) must not raise
    (regression test for #1273)."""

    def test_equality_with_task(self):
        tid = uuid4()
        self.assertEqual(Task(id=tid, title='a'), Task(id=tid, title='b'))
        self.assertNotEqual(Task(id=tid, title='a'),
                            Task(id=uuid4(), title='a'))

    def test_equality_with_foreign_type_does_not_raise(self):
        task = Task(id=uuid4(), title='a')
        self.assertFalse(task == uuid4())
        self.assertFalse(task == 'not-a-task')
