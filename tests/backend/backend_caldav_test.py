import re
from datetime import date, datetime
from unittest import TestCase

import vobject
from caldav.lib.error import NotFoundError
from dateutil.tz import UTC
from GTG.backends.backend_caldav import (CATEGORIES, CHILDREN_FIELD,
                                         DAV_IGNORE, PARENT_FIELD, UID_FIELD,
                                         Backend, Translator)
from GTG.core.datastore import DataStore
from GTG.core.dates import LOCAL_TIMEZONE, Date
from GTG.core.task import Task
from mock import Mock, patch
from tests.test_utils import MockTimer

NAMESPACE = 'unittest'
VTODO_ROOT = """BEGIN:VTODO\r
CATEGORIES:my first category,my second category\r
COMPLETED:20201212T172558Z\r
CREATED:20201212T092155Z\r
DESCRIPTION;GTGCNTMD5=d48ef99fb21adab7cf5ddd85a4ecf343:my description\r
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
DUE;VALUE=DATE:20201224\r
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

    @staticmethod
    def _setup_backend():
        datastore = DataStore()
        parameters = {'pid': 'favorite', 'service-url': 'color',
                      'username': 'blue', 'password': 'no red', 'period': 1}
        backend = Backend(parameters)
        datastore.register_backend({'backend': backend, 'pid': 'backendid',
                                    'first_run': True})
        return datastore, backend

    @staticmethod
    def _mock_calendar(name='my calendar', url='https://my.fa.ke/calendar'):
        calendar = Mock()
        calendar.name, calendar.url = name, url
        return calendar

    def test_translate_from_vtodo(self):
        DESCRIPTION = Translator.fields[1]
        self.assertEqual(DESCRIPTION.dav_name, 'description')
        todo = self._get_todo(VTODO_GRAND_CHILD)
        self.assertEqual(todo.instance.vtodo.serialize(), VTODO_GRAND_CHILD)
        self.assertEqual(date(2020, 12, 24),
                         todo.instance.vtodo.contents['due'][0].value)
        uid = UID_FIELD.get_dav(todo)
        self.assertTrue(isinstance(uid, str), "should be str is %r" % uid)
        self.assertEqual(uid, UID_FIELD.get_dav(vtodo=todo.instance.vtodo))
        task = Task(uid, Mock())
        Translator.fill_task(todo, task, NAMESPACE)
        self.assertEqual('date', task.get_due_date().accuracy.value)
        vtodo = Translator.fill_vtodo(task, todo.parent.name, NAMESPACE)
        for field in Translator.fields:
            if field.dav_name in DAV_IGNORE:
                continue
            self.assertTrue(field.is_equal(task, NAMESPACE, todo))
            self.assertTrue(field.is_equal(task, NAMESPACE, vtodo=vtodo.vtodo))
        vtodo.vtodo.contents['description'][0].value = 'changed value'
        self.assertTrue(DESCRIPTION.is_equal(task, NAMESPACE, todo), 'same '
                        'hashes should prevent changes on vTodo to be noticed')
        task.set_text(task.get_text() + 'more content')
        self.assertFalse(DESCRIPTION.is_equal(task, NAMESPACE, todo))

    def test_translate_from_task(self):
        now, today = datetime.now(), date.today()
        task = Task('uuid', Mock())
        task.set_title('holy graal')
        task.set_text('the knights who says ni')
        task.set_recurring(True, 'other-day')
        task.set_start_date(today)
        task.set_due_date('soon')
        task.set_closed_date(now)
        vtodo = Translator.fill_vtodo(task, 'My Calendar Name', NAMESPACE)
        for field in Translator.fields:
            self.assertTrue(field.is_equal(task, NAMESPACE, vtodo=vtodo.vtodo),
                            '%r has differing values' % field)
        serialized = vtodo.serialize()
        self.assertTrue(f"DTSTART;VALUE=DATE:{today.strftime('%Y%m%d')}"
                        in serialized, f"missing from {serialized}")
        self.assertTrue(re.search(r"COMPLETED:[0-9]{8}T[0-9]{6}Z",
                                  serialized), f"missing from {serialized}")
        self.assertTrue("DUE;GTGFUZZY=soon" in serialized,
                        f"missing from {serialized}")
        # trying to fill utc only with fuzzy
        task.set_closed_date('someday')
        vtodo = Translator.fill_vtodo(task, 'My Calendar Name', NAMESPACE)
        serialized = vtodo.serialize()
        self.assertTrue("COMPLETED;GTGFUZZY=someday:" in serialized,
                        f"missing from {serialized}")
        # trying to fill utc only with date
        task.set_closed_date(today)
        vtodo = Translator.fill_vtodo(task, 'My Calendar Name', NAMESPACE)
        serialized = vtodo.serialize()
        today_in_utc = now.replace(hour=0, minute=0, second=0)\
            .replace(tzinfo=LOCAL_TIMEZONE).astimezone(UTC)\
            .strftime('%Y%m%dT%H%M%SZ')
        self.assertTrue(f"COMPLETED:{today_in_utc}" in serialized,
                        f"missing {today_in_utc} from {serialized}")
        # emptying date by setting None or no_date
        task.set_closed_date(Date.no_date())
        task.set_due_date(None)
        task.set_start_date('')
        vtodo = Translator.fill_vtodo(task, 'My Calendar Name', NAMESPACE)
        serialized = vtodo.serialize()
        self.assertTrue("CATEGORIES:" not in serialized)
        self.assertTrue("COMPLETED:" not in serialized)
        self.assertTrue("DUE:" not in serialized)
        self.assertTrue("DTSTART:" not in serialized)

    def test_translate(self):
        datastore = DataStore()
        root_task = datastore.task_factory('root-task', newtask=True)
        root_task.add_tag('@my-tag')
        root_task.add_tag('@my-other-tag')
        root_task.set_title('my task')
        datastore.push_task(root_task)
        child_task = datastore.task_factory('child-task', newtask=True)
        child_task.set_title('my first child')
        child_task.add_tag('@my-tag')
        child_task.add_tag('@my-other-tag')
        child_task.set_text("@my-tag, @my-other-tag, \n\ntask content")
        datastore.push_task(child_task)
        root_task.add_child(child_task.get_id())
        child2_task = datastore.task_factory('done-child-task', newtask=True)
        child2_task.set_title('my done child')
        child2_task.add_tag('@my-tag')
        child2_task.add_tag('@my-other-tag')
        child2_task.set_text("@my-tag, @my-other-tag, \n\nother task txt")
        child2_task.set_status(Task.STA_DONE)
        datastore.push_task(child2_task)
        root_task.add_child(child2_task.get_id())
        root_task.set_text(f"@my-tag, @my-other-tag\n\nline\n"
                           f"{{!{child_task.get_id()}!}}\n"
                           f"{{!{child2_task.get_id()}!}}\n")
        self.assertEqual([child_task.get_id(), child2_task.get_id()],
                         root_task.get_children())
        self.assertEqual([root_task.get_id()], child_task.get_parents())
        self.assertEqual([], PARENT_FIELD.get_gtg(root_task, NAMESPACE))
        self.assertEqual(['child-task', 'done-child-task'],
                         CHILDREN_FIELD.get_gtg(root_task, NAMESPACE))
        self.assertEqual(['root-task'],
                         PARENT_FIELD.get_gtg(child_task, NAMESPACE))
        self.assertEqual([], CHILDREN_FIELD.get_gtg(child_task, NAMESPACE))
        root_vtodo = Translator.fill_vtodo(root_task, 'calname', NAMESPACE)
        child_vtodo = Translator.fill_vtodo(child_task, 'calname', NAMESPACE)
        child2_vtodo = Translator.fill_vtodo(child2_task, 'calname', NAMESPACE)
        self.assertEqual([], PARENT_FIELD.get_dav(vtodo=root_vtodo.vtodo))
        self.assertEqual(['child-task', 'done-child-task'],
                         CHILDREN_FIELD.get_dav(vtodo=root_vtodo.vtodo))
        self.assertEqual(['root-task'],
                         PARENT_FIELD.get_dav(vtodo=child_vtodo.vtodo))
        self.assertEqual([], CHILDREN_FIELD.get_dav(vtodo=child_vtodo.vtodo))
        self.assertTrue('\r\nRELATED-TO;RELTYPE=CHILD:child-task\r\n'
                        in root_vtodo.serialize())
        self.assertTrue('\r\nRELATED-TO;RELTYPE=PARENT:root-task\r\n'
                        in child_vtodo.serialize())
        root_contents = root_vtodo.contents['vtodo'][0].contents
        child_cnt = child_vtodo.contents['vtodo'][0].contents
        child2_cnt = child2_vtodo.contents['vtodo'][0].contents
        for cnt in root_contents, child_cnt, child2_cnt:
            self.assertEqual(['my-tag', 'my-other-tag'],
                             cnt['categories'][0].value)
        self.assertEqual('my first child', child_cnt['summary'][0].value)
        self.assertEqual('my done child', child2_cnt['summary'][0].value)
        self.assertEqual('task content', child_cnt['description'][0].value)
        self.assertEqual('other task txt', child2_cnt['description'][0].value)
        self.assertEqual('line\n[ ] my first child\n[x] my done child',
                         root_contents['description'][0].value)

    @patch('GTG.backends.periodic_import_backend.threading.Timer',
           autospec=MockTimer)
    @patch('GTG.backends.backend_caldav.caldav.DAVClient')
    def test_do_periodic_import(self, dav_client, threading_pid):
        calendar = self._mock_calendar()

        todos = [self._get_todo(VTODO_CHILD_PARENT, calendar),
                 self._get_todo(VTODO_ROOT, calendar),
                 self._get_todo(VTODO_CHILD, calendar),
                 self._get_todo(VTODO_GRAND_CHILD, calendar)]
        calendar.todos.return_value = todos
        dav_client.return_value.principal.return_value.calendars.return_value \
            = [calendar]
        datastore, backend = self._setup_backend()

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

        for uid, parents, children in (
                ('ROOT', [], ['CHILD', 'CHILD-PARENT']),
                ('CHILD', ['ROOT'], []),
                ('CHILD-PARENT', ['ROOT'], ['GRAND-CHILD'])):
            task = datastore.get_task(uid)
            self.assertEqual(children, CHILDREN_FIELD.get_dav(get_todo(uid)),
                             "children should've been written by sync down")
            self.assertEqual(children, task.get_children(),
                             "children missing from task")
            self.assertEqual(parents, PARENT_FIELD.get_dav(get_todo(uid)),
                             "parent on todo aren't consistent")
            self.assertEqual(parents, task.get_parents(),
                             "parent missing from task")

        calendar.todo_by_uid.return_value = todos[-1]
        todos = todos[:-1]
        child_todo = todos[-1]
        child_todo.instance.vtodo.contents['summary'][0].value = 'new summary'
        calendar.todos.return_value = todos

        # syncing with missing and updated todo, no change
        task = datastore.get_task(child_todo.instance.vtodo.uid.value)
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

    @patch('GTG.backends.periodic_import_backend.threading.Timer',
           autospec=MockTimer)
    @patch('GTG.backends.backend_caldav.caldav.DAVClient')
    def test_switch_calendar(self, dav_client, threading_pid):
        calendar1 = self._mock_calendar()
        calendar2 = self._mock_calendar('other calendar', 'http://no.whe.re/')

        todo = self._get_todo(VTODO_ROOT, calendar1)
        calendar1.todos.return_value = [todo]
        calendar2.todos.return_value = []
        dav_client.return_value.principal.return_value.calendars.return_value \
            = [calendar1, calendar2]
        datastore, backend = self._setup_backend()
        self.assertEqual(1, len(datastore.get_all_tasks()))
        task = datastore.get_task(UID_FIELD.get_dav(todo))
        self.assertTrue(CATEGORIES.has_calendar_tag(task, calendar1))
        self.assertFalse(CATEGORIES.has_calendar_tag(task, calendar2))

        task.remove_tag(CATEGORIES.get_calendar_tag(calendar1))
        task.add_tag(CATEGORIES.get_calendar_tag(calendar2))
        self.assertFalse(CATEGORIES.has_calendar_tag(task, calendar1))
        self.assertTrue(CATEGORIES.has_calendar_tag(task, calendar2))

        calendar2.add_todo.return_value = todo
        backend.set_task(task)
        calendar1.add_todo.assert_not_called()
        calendar2.add_todo.assert_called_once()
        todo.delete.assert_called_once()

    @patch('GTG.backends.periodic_import_backend.threading.Timer',
           autospec=MockTimer)
    @patch('GTG.backends.backend_caldav.caldav.DAVClient')
    def test_task_mark_as_done_from_backend(self, dav_client, threading_pid):
        calendar = self._mock_calendar()
        todo = self._get_todo(VTODO_ROOT, calendar)
        calendar.todos.return_value = [todo]
        dav_client.return_value.principal.return_value.calendars.return_value \
            = [calendar]
        datastore, backend = self._setup_backend()
        uid = UID_FIELD.get_dav(todo)
        self.assertEqual(1, len(datastore.get_all_tasks()))
        task = datastore.get_task(uid)
        self.assertEqual(Task.STA_ACTIVE, task.get_status())
        calendar.todos.assert_called_once()
        calendar.todo_by_uid.assert_not_called()
        calendar.todos.reset_mock()

        todo.instance.vtodo.contents['status'][0].value = 'COMPLETED'
        calendar.todos.return_value = []
        calendar.todo_by_uid.return_value = todo
        backend.do_periodic_import()
        calendar.todos.assert_called_once()
        calendar.todo_by_uid.assert_called_once()

        self.assertEqual(1, len(datastore.get_all_tasks()))
        task = datastore.get_task(uid)
        self.assertEqual(Task.STA_DONE, task.get_status())
