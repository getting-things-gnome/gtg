from datetime import datetime
from unittest import TestCase

import vobject
from mock import Mock, patch
from caldav.lib.error import NotFoundError

from tests.test_utils import MockTimer

from GTG.backends.backend_caldav import (DAV_IGNORE, UID_FIELD, Backend,
                                         Translator, CHILDREN_FIELD)
from GTG.core.datastore import DataStore
from GTG.core.task import Task

NAMESPACE = 'unittest'
VTODO_ROOT = """BEGIN:VTODO\r
CATEGORIES:my first category, my second category\r
COMPLETED:20201212T172558Z\r
CREATED:20201212T092155Z\r
DESCRIPTION:my description\r
DTSTAMP:20201212T172830Z\r
LAST-MODIFIED:20201212T172558Z\r
STATUS:NEEDS-ACTIONS\r
SUMMARY:my summary\r
UID:ROOT\r
END:VTODO\r
"""

VTODO_CHILD = """BEGIN:VTODO\r
COMPLETED:20201212T172558Z\r
CREATED:20201212T092155Z\r
DTSTAMP:20201212T172830Z\r
LAST-MODIFIED:20201212T172558Z\r
RELATED-TO;RELTYPE=PARENT:ROOT\r
STATUS:NEEDS-ACTION\r
SUMMARY:my child summary\r
UID:CHILD\r
X-APPLE-SORT-ORDER:1\r
END:VTODO\r
"""

VTODO_CHILD_PARENT = """BEGIN:VTODO\r
COMPLETED:20201212T172558Z\r
CREATED:20201212T092155Z\r
DTSTAMP:20201212T172830Z\r
LAST-MODIFIED:20201212T172558Z\r
RELATED-TO;RELTYPE=PARENT:ROOT\r
RELATED-TO;RELTYPE=CHILD:GRAND-CHILD\r
SEQUENCE:1\r
STATUS:COMPLETED\r
SUMMARY:my child summary\r
X-APPLE-SORT-ORDER:2\r
UID:CHILD-PARENT\r
END:VTODO\r
"""

VTODO_GRAND_CHILD = """BEGIN:VTODO\r
COMPLETED:20201212T172558Z\r
CREATED:20201212T092155Z\r
DTSTAMP:20201212T172830Z\r
LAST-MODIFIED:20201212T172558Z\r
RELATED-TO;RELTYPE=PARENT:CHILD-PARENT\r
STATUS:NEEDS-ACTION\r
SUMMARY:my child summary\r
UID:GRAND-CHILD\r
END:VTODO\r
"""


class CalDAVTest(TestCase):

    @staticmethod
    def _get_todo(vtodo_raw, parent=None):
        vtodo = vobject.readOne(vtodo_raw)
        todo = Mock()
        todo.instance.vtodo = vtodo
        if parent is None:
            todo.parent.name = 'My Calendar'
        else:
            todo.parent = parent
        return todo

    def test_translate_from_vtodo(self):
        todo = self._get_todo(VTODO_ROOT)
        self.assertEqual(todo.instance.vtodo.serialize(), VTODO_ROOT)
        uid = UID_FIELD.get_dav(todo)
        self.assertTrue(isinstance(uid, str), "should be str is %r" % uid)
        self.assertEqual(uid, UID_FIELD.get_dav(vtodo=todo.instance.vtodo))
        task = Task(uid, Mock())
        Translator.fill_task(todo, task, NAMESPACE)
        vtodo = Translator.fill_vtodo(task, todo.parent.name, NAMESPACE)
        for field in Translator.fields:
            if field.dav_name in DAV_IGNORE:
                continue
            task_value = field.get_gtg(task, NAMESPACE)
            todo_value = field.get_dav(todo)
            vtodo_value = field.get_dav(vtodo=vtodo.vtodo)
            self.assertEqual(task_value, todo_value,
                             '%r has differing values' % field)
            self.assertEqual(task_value, vtodo_value,
                             '%r has differing values' % field)

    def test_translate_from_task(self):
        task = Task('uuid', Mock())
        task.set_title('holy graal')
        task.set_text('the knights who says ni')
        task.set_due_date(datetime.now())
        vtodo = Translator.fill_vtodo(task, 'My Calendar Name', NAMESPACE)
        for field in Translator.fields:
            task_value = field.get_gtg(task, NAMESPACE)
            vtodo_value = field.get_dav(vtodo=vtodo.vtodo)
            self.assertEqual(task_value, vtodo_value,
                             '%r has differing values' % field)

    @patch('GTG.backends.periodic_import_backend.threading.Timer',
           autospec=MockTimer)
    @patch('GTG.backends.backend_caldav.caldav.DAVClient')
    def test_do_periodic_import(self, dav_client, threading_pid):
        calendar = Mock(name='my calendar')

        todos = [self._get_todo(VTODO_CHILD_PARENT, calendar),
                 self._get_todo(VTODO_ROOT, calendar),
                 self._get_todo(VTODO_CHILD, calendar),
                 self._get_todo(VTODO_GRAND_CHILD, calendar)]
        calendar.todos.return_value = todos
        datastore = DataStore()
        parameters = {'pid': 'favorite', 'service-url': 'color',
                      'username': 'blue', 'password': 'no red', 'period': 1,
                      'default-calendar-name': calendar.name}
        backend = Backend(parameters)
        dav_client.return_value.principal.return_value.calendars.return_value \
            = [calendar]
        datastore.register_backend({'backend': backend, 'pid': 'backendid'})

        self.assertEqual(4, len(datastore.get_all_tasks()))
        task = datastore.get_task('ROOT')
        self.assertIsNotNone(task)
        self.assertEqual(['CHILD', 'CHILD-PARENT'],
                         [subtask.get_id() for subtask in task.get_subtasks()])
        self.assertEqual(
            0, len(datastore.get_task('CHILD').get_subtasks()))
        self.assertEqual(
            1, len(datastore.get_task('CHILD-PARENT').get_subtasks()))

        def get_todo(uid):
            return next(todo for todo in todos
                        if UID_FIELD.get_dav(todo) == uid)

        self.assertEqual(['CHILD', 'CHILD-PARENT'],
                         CHILDREN_FIELD.get_dav(get_todo('ROOT')),
                         "todos should've been updated with children")

        self.assertEqual(['GRAND-CHILD'],
                         CHILDREN_FIELD.get_dav(get_todo('CHILD-PARENT')),
                         "todos should've been updated with children")

        calendar.todos.return_value = todos[:-1]
        backend.do_periodic_import()
        self.assertEqual(4, len(datastore.get_all_tasks()),
                         "no not found raised, no reason to remove tasks")
        calendar.todo_by_uid.side_effect = NotFoundError
        backend.do_periodic_import()
        self.assertEqual(3, len(datastore.get_all_tasks()))
