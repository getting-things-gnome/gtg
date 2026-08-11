"""The CalDAV sync must not overwrite closed dates with the current day.

Regression test for the mass closed-date stamping: filling a task from
a VTODO whose STATUS is COMPLETED (or CANCELLED) must leave the task
with the historical COMPLETED date carried by the payload, not with
Date.today().
"""

from unittest import TestCase
from unittest.mock import Mock

import vobject

from GTG.backends.backend_caldav import Translator, UID_FIELD, uid_to_task_id
from GTG.core.datastore import Datastore
from GTG.core.tasks import Task, TaskStore, Status
from GTG.core.tags import TagStore

NAMESPACE = 'unittest'

VTODO_DONE_OLD = """BEGIN:VTODO\r
COMPLETED:20201212T172558Z\r
CREATED:20201210T092155Z\r
DTSTAMP:20201212T172830Z\r
LAST-MODIFIED:20201212T172558Z\r
STATUS:COMPLETED\r
SUMMARY:done long ago\r
UID:DONE-OLD\r
END:VTODO\r\n"""

VTODO_CANCELLED_OLD = """BEGIN:VTODO\r
COMPLETED:20190301T101500Z\r
CREATED:20190201T092155Z\r
DTSTAMP:20190301T101600Z\r
LAST-MODIFIED:20190301T101500Z\r
STATUS:CANCELLED\r
SUMMARY:dismissed long ago\r
UID:CANCELLED-OLD\r
END:VTODO\r\n"""


def _get_todo(raw):
    todo = Mock()
    todo.instance.vtodo = vobject.readOne(raw)
    todo.parent.name = 'My Calendar'
    return todo


class TestClosedDateStamping(TestCase):

    def _fill(self, raw):
        todo = _get_todo(raw)
        uid = UID_FIELD.get_dav(todo)
        task = Task(id=uid_to_task_id(uid), title='')
        Translator.fill_task(todo, task, NAMESPACE, Datastore())
        return task

    def test_done_keeps_historical_closed_date(self):
        task = self._fill(VTODO_DONE_OLD)
        self.assertEqual(Status.DONE, task.status)
        self.assertTrue(str(task.date_closed).startswith('2020-12-12'),
                        'closed date was stamped over during fill_task')

    def test_cancelled_keeps_historical_closed_date(self):
        task = self._fill(VTODO_CANCELLED_OLD)
        self.assertEqual(Status.DISMISSED, task.status)
        self.assertTrue(str(task.date_closed).startswith('2019-03-01'),
                        'closed date was stamped over during fill_task')

    def test_closed_date_survives_save_and_reload(self):
        """Full cycle: fill from VTODO, serialize to XML, reload."""
        store = TaskStore()
        todo = _get_todo(VTODO_DONE_OLD)
        uid = UID_FIELD.get_dav(todo)
        task = Task(id=uid_to_task_id(uid), title='')
        Translator.fill_task(todo, task, NAMESPACE, Datastore())
        store.add(task)

        reloaded = TaskStore()
        reloaded.from_xml(store.to_xml(), TagStore())
        back = reloaded.lookup[task.id]
        self.assertEqual(Status.DONE, back.status)
        self.assertTrue(str(back.date_closed).startswith('2020-12-12'),
                        'closed date lost across save/reload')
