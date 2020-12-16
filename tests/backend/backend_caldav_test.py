from datetime import datetime
from unittest import TestCase

import vobject
from caldav.lib.error import NotFoundError
from GTG.backends.backend_caldav import (CATEGORIES, CHILDREN_FIELD,
                                         DAV_IGNORE, UID_FIELD, Backend,
                                         Translator, PARENT_FIELD)
from GTG.core.datastore import DataStore
from GTG.core.task import Task
from mock import Mock, patch
from tests.test_utils import MockTimer

NAMESPACE = 'unittest'
VTODO_ROOT = """BEGIN:VTODO\r
CATEGORIES:my first category, my second category\r
COMPLETED:20201212T172558Z\r
CREATED:20201212T092155Z\r
DESCRIPTION:my description\r
DTSTAMP:20201212T172830Z\r
LAST-MODIFIED:20201212T172558Z\r
STATUS:NEEDS-ACTION\r
SUMMARY:my summary\r
UID:ROOT\r
END:VTODO\r\n"""
VTODO_CHILD = """BEGIN:VTODO\r
COMPLETED:20201212T172558Z\r
CREATED:20201212T092155Z\r
DTSTAMP:20201212T172830Z\r
LAST-MODIFIED:20201212T172558Z\r
RELATED-TO;RELTYPE=PARENT:ROOT\r
SEQUENCE:1
STATUS:NEEDS-ACTION\r
SUMMARY:my child summary\r
UID:CHILD\r
X-APPLE-SORT-ORDER:1\r
END:VTODO\r\n"""
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
END:VTODO\r\n"""
VTODO_GRAND_CHILD = """BEGIN:VTODO\r
COMPLETED:20201212T172558Z\r
CREATED:20201212T092155Z\r
DTSTAMP:20201212T172830Z\r
LAST-MODIFIED:20201212T172558Z\r
RELATED-TO;RELTYPE=PARENT:CHILD-PARENT\r
STATUS:NEEDS-ACTION\r
SUMMARY:my child summary\r
UID:GRAND-CHILD\r
END:VTODO\r\n"""
VTODO_NEW_CHILD = """BEGIN:VTODO\r
COMPLETED:20201212T172558Z\r
CREATED:20201212T092155Z\r
DTSTAMP:20201212T172830Z\r
LAST-MODIFIED:20201212T172558Z\r
RELATED-TO;RELTYPE=PARENT:ROOT\r
SEQUENCE:1
STATUS:NEEDS-ACTION\r
SUMMARY:my new child summary\r
UID:NEW-CHILD\r
X-APPLE-SORT-ORDER:1\r
END:VTODO\r\n"""


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

    def test_translate_parent_field(self):
        datastore = DataStore()
        root_task = datastore.task_factory('root-task', newtask=True)
        datastore.push_task(root_task)
        child_task = datastore.task_factory('child-task', newtask=True)
        datastore.push_task(child_task)
        root_task.add_child(child_task.get_id())
        self.assertEqual([child_task.get_id()], root_task.get_children())
        self.assertEqual([root_task.get_id()], child_task.get_parents())
        self.assertEqual([], PARENT_FIELD.get_gtg(root_task, NAMESPACE))
        self.assertEqual(['child-task'],
                         CHILDREN_FIELD.get_gtg(root_task, NAMESPACE))
        self.assertEqual(['root-task'],
                         PARENT_FIELD.get_gtg(child_task, NAMESPACE))
        self.assertEqual([], CHILDREN_FIELD.get_gtg(child_task, NAMESPACE))
        root_vtodo = Translator.fill_vtodo(root_task, 'calname', NAMESPACE)
        child_vtodo = Translator.fill_vtodo(child_task, 'calname', NAMESPACE)
        self.assertEqual([], PARENT_FIELD.get_dav(vtodo=root_vtodo.vtodo))
        self.assertEqual(['child-task'],
                         CHILDREN_FIELD.get_dav(vtodo=root_vtodo.vtodo))
        self.assertEqual(['root-task'],
                         PARENT_FIELD.get_dav(vtodo=child_vtodo.vtodo))
        self.assertEqual([], CHILDREN_FIELD.get_dav(vtodo=child_vtodo.vtodo))
        self.assertTrue('\r\nRELATED-TO;RELTYPE=CHILD:child-task\r\n'
                        in root_vtodo.serialize())
        self.assertTrue('\r\nRELATED-TO;RELTYPE=PARENT:root-task\r\n'
                        in child_vtodo.serialize())

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
                      'username': 'blue', 'password': 'no red', 'period': 1}
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

        todos = todos[:-1]
        child_todo = todos[-1]
        child_todo.instance.vtodo.contents['summary'][0].value = 'new summary'
        calendar.todos.return_value = todos
        task = datastore.get_task(child_todo.instance.vtodo.uid.value)

        # syncing with missing and updated todo, no change
        backend.do_periodic_import()
        self.assertEqual(4, len(datastore.get_all_tasks()),
                         "no not found raised, no reason to remove tasks")
        self.assertEqual('my child summary', task.get_title(), "title shoul"
                         "dn't have change because sequence wasn't updated")

        # syncing with same data, delete one and edit remaining
        calendar.todo_by_uid.side_effect = NotFoundError
        child_todo.instance.vtodo.contents['sequence'][0].value = '2'
        backend.do_periodic_import()
        self.assertEqual(3, len(datastore.get_all_tasks()))
        self.assertEqual('new summary', task.get_title())

        # set_task no change, no update
        backend.set_task(task)
        child_todo.save.assert_not_called()
        child_todo.delete.assert_not_called()
        calendar.add_todo.assert_not_called()
        # set_task, with ignorable changes
        task.set_status(task.STA_DONE)
        backend.set_task(task)
        child_todo.save.assert_called_once()
        calendar.add_todo.assert_not_called()
        child_todo.delete.assert_not_called()
        child_todo.save.reset_mock()
        # no update
        backend.set_task(task)
        child_todo.save.assert_not_called()
        calendar.add_todo.assert_not_called()
        child_todo.delete.assert_not_called()

        # creating task, refused : no tag
        task = datastore.task_factory('NEW-CHILD')
        datastore.push_task(task)
        backend.set_task(task)
        child_todo.save.assert_not_called()
        calendar.add_todo.assert_not_called()
        child_todo.delete.assert_not_called()
        # creating task, accepted, new tag found
        task.add_tag(CATEGORIES.get_calendar_tag(calendar))
        calendar.add_todo.return_value = child_todo
        backend.set_task(task)
        child_todo.save.assert_not_called()
        calendar.add_todo.assert_called_once()
        child_todo.delete.assert_not_called()
        calendar.add_todo.reset_mock()

        backend.remove_task('uid never seen before')
        child_todo.save.assert_not_called()
        calendar.add_todo.assert_not_called()
        child_todo.delete.assert_not_called()

        backend.remove_task('CHILD')
        child_todo.save.assert_not_called()
        calendar.add_todo.assert_not_called()
        child_todo.delete.assert_called_once()
