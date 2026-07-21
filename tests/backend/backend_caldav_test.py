import re
import unittest
from datetime import date, datetime, timedelta
from unittest import TestCase

import vobject
from caldav.lib.error import NotFoundError
from dateutil.tz import UTC
from GTG.backends.backend_caldav import (CATEGORIES, CHILDREN_FIELD,
                                         DAV_IGNORE, PARENT_FIELD, UID_FIELD,
                                         Backend, DueDateField, SORT_ORDER,
                                         Translator, uid_to_task_id)
from GTG.core.datastore import Datastore
from GTG.core.dates import LOCAL_TIMEZONE, Date
from GTG.core.tasks import Task
from unittest.mock import Mock, patch
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
DESCRIPTION:my descriptio\r
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


@unittest.skip('TODO Ignoring CalDAV for now')
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
        datastore = Datastore()
        parameters = {'pid': 'favorite', 'service-url': 'color',
                      'username': 'blue', 'password': 'no red', 'period': 1}
        backend = Backend(parameters)
        datastore.register_backend({'backend': backend, 'pid': 'backendid',
                                    'first_run': True})
        return datastore, backend

    @staticmethod
    def _mock_calendar(name='my calendar', url='https://my.fa.ke/calendar'):
        calendar = Mock()
        calendar.name = 'My Calendar'
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
        self.assertTrue(isinstance(uid, str), f"should be str is {uid!r}")
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
                            f'{field!r} has differing values')
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
        datastore = Datastore()
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

    def test_due_date_caldav_restriction(self):
        task = Task('uid', Mock())
        later = datetime(2021, 11, 24, 21, 52, 45)
        before = later - timedelta(days=1)
        task.set_start_date(later)
        task.set_due_date(before)
        field = DueDateField('due', 'get_due_date_constraint', 'set_due_date')
        self.assertEqual(later, field.get_gtg(task, '').dt_value)

        task.set_start_date(before)
        task.set_due_date(later)
        self.assertEqual(later, field.get_gtg(task, '').dt_value)


class NonUuidUidRegressionTest(TestCase):
    """CalDAV UIDs are opaque unique strings (RFC 5545): servers and
    clients are not required to produce UUID-shaped values.

    Regression test for the ValueError('badly formed hexadecimal UUID
    string') reported while testing PR #1265."""

    NON_UUID_UID = '19960401T080045Z-4000F192713@example.com'
    VTODO_NON_UUID = ("BEGIN:VTODO\r\n"
                      "CREATED:20201212T092155Z\r\n"
                      "DTSTAMP:20201212T172830Z\r\n"
                      "LAST-MODIFIED:20201212T172558Z\r\n"
                      "STATUS:NEEDS-ACTION\r\n"
                      "SUMMARY:todo with a non-uuid uid\r\n"
                      "UID:" + NON_UUID_UID + "\r\n"
                      "END:VTODO\r\n")

    @staticmethod
    def _todo(raw):
        todo = Mock()
        todo.instance.vtodo = vobject.readOne(raw)
        todo.parent.name = 'My Calendar'
        return todo

    @staticmethod
    def _backend():
        parameters = {'pid': 'test', 'service-url': 'unittest',
                      'username': 'u', 'password': 'p', 'period': 1}
        backend = Backend(parameters)
        backend.datastore = Datastore()
        return backend

    def test_import_todo_with_non_uuid_uid(self):
        backend = self._backend()
        calendar = Mock()
        calendar.name = 'My Calendar'
        calendar.todos.return_value = [self._todo(self.VTODO_NON_UUID)]
        counts = {'created': 0, 'updated': 0, 'unchanged': 0, 'deleted': 0}
        start = datetime.now(LOCAL_TIMEZONE)
        backend._import_calendar_todos(calendar, start, counts)
        self.assertEqual(1, counts['created'])
        self.assertEqual(1, len(backend.datastore.tasks.lookup))
        task = next(iter(backend.datastore.tasks.lookup.values()))
        self.assertEqual('todo with a non-uuid uid', task.title)
        # importing again must neither crash, duplicate nor delete
        counts2 = {'created': 0, 'updated': 0, 'unchanged': 0, 'deleted': 0}
        backend._import_calendar_todos(calendar, start, counts2)
        self.assertEqual(0, counts2['created'])
        self.assertEqual(0, counts2['deleted'])
        self.assertEqual(1, len(backend.datastore.tasks.lookup))

    VTODO_NO_CREATED = ("BEGIN:VTODO\r\n"
                        "DTSTAMP:20201212T172830Z\r\n"
                        "LAST-MODIFIED:20201212T172558Z\r\n"
                        "STATUS:NEEDS-ACTION\r\n"
                        "SUMMARY:todo without a created date\r\n"
                        "UID:no-created@example.org\r\n"
                        "END:VTODO\r\n")

    def test_import_todo_without_created_date(self):
        """CREATED is optional in RFC 5545. A task imported without one
        must still get an added date: the core serializes an empty
        <added> and then refuses to reload the file."""
        backend = self._backend()
        calendar = Mock()
        calendar.name = 'My Calendar'
        calendar.todos.return_value = [self._todo(self.VTODO_NO_CREATED)]
        counts = {'created': 0, 'updated': 0, 'unchanged': 0, 'deleted': 0}
        start = datetime.now(LOCAL_TIMEZONE)
        backend._import_calendar_todos(calendar, start, counts)
        self.assertEqual(1, counts['created'])
        task = next(iter(backend.datastore.tasks.lookup.values()))
        self.assertTrue(task.date_added,
                        'task imported without CREATED has no added date, '
                        'it will be saved as an empty <added> element')
        self.assertNotEqual('', str(task.date_added))

    def _imported_child(self):
        backend = self._backend()
        calendar = Mock()
        calendar.name = 'My Calendar'
        calendar.todos.return_value = [self._todo(VTODO_ROOT),
                                       self._todo(VTODO_CHILD)]
        counts = {'created': 0, 'updated': 0, 'unchanged': 0, 'deleted': 0}
        backend._import_calendar_todos(calendar, datetime.now(LOCAL_TIMEZONE),
                                       counts)
        self.assertEqual(2, counts['created'])
        child = backend.datastore.tasks.lookup[uid_to_task_id('CHILD')]
        self.assertIsNotNone(child.parent, 'hierarchy was not imported')
        return backend, child

    def test_push_subtask_does_not_call_the_old_core_api(self):
        """OrderField used the pre-rewrite get_child_index(): pushing
        any subtask raised AttributeError, so hierarchy only ever
        synced from the server, never to it."""
        backend, child = self._imported_child()
        vtodo = Translator.fill_vtodo(child, 'My Calendar', backend.namespace)
        self.assertEqual('0', SORT_ORDER.get_dav(vtodo=vtodo.vtodo))

    def test_export_related_to_carries_the_server_uid(self):
        """RELATED-TO must carry the UID the server issued, not the GTG
        id derived from it: uid_to_task_id() is one-way, so a mapped
        uuid5 means nothing to the server and the link is dropped."""
        backend, child = self._imported_child()
        vtodo = Translator.fill_vtodo(child, 'My Calendar', backend.namespace)
        self.assertEqual(['ROOT'], PARENT_FIELD.get_dav(vtodo=vtodo.vtodo),
                         'the server would not recognize this parent UID')

    def test_calendar_tag_is_parsable_back_by_the_core(self):
        """A calendar named "Deck: Server" used to yield the tag
        DAV_Deck:_Server, which the editor re-read as @DAV_Deck and
        re-added as a second, truncated tag on every open."""
        backend = self._backend()
        calendar = Mock()
        calendar.name = 'Deck: Server'
        calendar.todos.return_value = [self._todo(self.VTODO_NO_CREATED)]
        calendar.todos.return_value[0].parent.name = 'Deck: Server'
        counts = {'created': 0, 'updated': 0, 'unchanged': 0, 'deleted': 0}
        backend._import_calendar_todos(calendar, datetime.now(LOCAL_TIMEZONE),
                                       counts)
        task = next(iter(backend.datastore.tasks.lookup.values()))
        dav_tags = [t.name for t in task.tags if t.name.startswith('DAV_')]
        self.assertEqual(1, len(dav_tags), dav_tags)
        tag = dav_tags[0]
        editor_re = re.compile(
            r'(?<!\/|\w)\@\w+(\.*[\-\w+\+\%\$\\(\)\[\]\{\}\^\=\/\*])*')
        match = editor_re.match('@' + tag)
        self.assertIsNotNone(match)
        self.assertEqual('@' + tag, match.group(0),
                         'the editor truncates this tag and will fork it')
        self.assertIsNotNone(re.compile(r'^\B\@\w+(\-\w+)*\,*.*')
                             .match('@' + tag))

    def test_extract_plain_text_with_subtask_reference(self):
        """Task content can reference subtasks as {!<task id>!} lines:
        extraction must resolve them through the new core API."""
        from types import SimpleNamespace
        from uuid import uuid4
        from GTG.core.tasks import Status as TaskStatus
        field = [f for f in Translator.fields
                 if f.dav_name == 'description'][0]
        child_id = uuid4()
        child = SimpleNamespace(id=child_id, title='my subtask',
                                status=TaskStatus.DONE)
        parent = SimpleNamespace(
            content='first line\n{!' + str(child_id) + '!}\nlast line',
            children=[child])
        text = field._extract_plain_text(parent)
        self.assertIn('[x] my subtask', text)
        self.assertIn('last line', text)

    ROOT_NO_CATEG = "".join(
        line + "\r\n" for line in VTODO_ROOT.splitlines()
        if not line.startswith("CATEGORIES"))

    def test_import_parent_child_hierarchy(self):
        """RELATED-TO hierarchy must be wired with real Task objects,
        never raw UID strings (regression for PR #1265 re-test)."""
        backend = self._backend()
        calendar = Mock()
        calendar.name = 'My Calendar'
        calendar.todos.return_value = [self._todo(self.ROOT_NO_CATEG),
                                       self._todo(VTODO_CHILD)]
        counts = {'created': 0, 'updated': 0, 'unchanged': 0, 'deleted': 0}
        backend._import_calendar_todos(
            calendar, datetime.now(LOCAL_TIMEZONE), counts)
        self.assertEqual(2, counts['created'])
        parent = next(t for t in backend.datastore.tasks.lookup.values()
                      if t.title == 'my summary')
        child = next(t for t in backend.datastore.tasks.lookup.values()
                     if t.title == 'my child summary')
        for c in parent.children:
            self.assertIsInstance(c, Task)
        self.assertEqual([child], list(parent.children))
        self.assertIs(parent, child.parent)

    def test_import_categories_as_real_tags(self):
        """CATEGORIES must become real Tag objects from the datastore."""
        backend = self._backend()
        calendar = Mock()
        calendar.name = 'My Calendar'
        calendar.todos.return_value = [self._todo(VTODO_ROOT)]
        counts = {'created': 0, 'updated': 0, 'unchanged': 0, 'deleted': 0}
        backend._import_calendar_todos(
            calendar, datetime.now(LOCAL_TIMEZONE), counts)
        self.assertEqual(1, counts['created'])
        task = next(iter(backend.datastore.tasks.lookup.values()))
        names = {tag.name for tag in task.tags}
        self.assertIn(CATEGORIES.to_tag('my first category'), names)
        self.assertIn(CATEGORIES.to_tag('my second category'), names)

    def test_uid_mapping_is_stable(self):
        from uuid import UUID as _UUID
        from GTG.backends.backend_caldav import uid_to_task_id
        once = uid_to_task_id(self.NON_UUID_UID)
        self.assertEqual(once, uid_to_task_id(self.NON_UUID_UID))
        self.assertNotEqual(once, uid_to_task_id('another-opaque-uid'))
        canonical = '1f0ac2a2-2e44-4f9c-89e2-6dd00b78ef34'
        self.assertEqual(_UUID(canonical),
                         uid_to_task_id(canonical.upper()))

    def test_non_uuid_uid_alone_does_not_trigger_a_push(self):
        """The task id is the uuid5 mapping of a non-UUID server UID,
        so the two sides legitimately never match. That identity
        difference used to count as a change: every set_task rewrote
        the unchanged todo and inflated its SEQUENCE forever."""
        parameters = {'pid': 'test', 'service-url': 'unittest',
                      'username': 'u', 'password': 'p', 'period': 1,
                      'is-first-run': False}
        backend = Backend(parameters)
        backend.datastore = Datastore()
        calendar = Mock()
        calendar.name = 'My Calendar'
        todo = self._todo(self.VTODO_NON_UUID)
        todo.parent = calendar
        calendar.todos.return_value = [todo]
        counts = {'created': 0, 'updated': 0, 'unchanged': 0, 'deleted': 0}
        backend._import_calendar_todos(
            calendar, datetime.now(LOCAL_TIMEZONE), counts)
        backend._cache.initialized = True
        task = next(iter(backend.datastore.tasks.lookup.values()))

        backend.set_task(task)

        todo.save.assert_not_called()
        calendar.add_todo.assert_not_called()


class LocalDeletionPushTest(TestCase):
    """Deleting a task in GTG must delete the matching todo on the
    CalDAV server, otherwise it reappears on the next import.

    Follow-up to #1265, whose scope note read "this PR does not cover
    pushing local deletions to the server": the public remove_task
    used to mutate GTG's own store (the exact inverse of a push)
    while the real DAV deletion, _remove_task, had no caller."""

    UUID_UID = '5241ab4d-05ef-4b2e-ab1e-1699ba222eef'
    VTODO_UUID = ("BEGIN:VTODO\r\n"
                  "CREATED:20201212T092155Z\r\n"
                  "DTSTAMP:20201212T172830Z\r\n"
                  "LAST-MODIFIED:20201212T172558Z\r\n"
                  "STATUS:NEEDS-ACTION\r\n"
                  "SUMMARY:todo to be deleted\r\n"
                  "UID:" + UUID_UID + "\r\n"
                  "END:VTODO\r\n")
    NON_UUID_UID = '19960401T080045Z-4000F192713@example.com'
    VTODO_NON_UUID = ("BEGIN:VTODO\r\n"
                      "CREATED:20201212T092155Z\r\n"
                      "DTSTAMP:20201212T172830Z\r\n"
                      "LAST-MODIFIED:20201212T172558Z\r\n"
                      "STATUS:NEEDS-ACTION\r\n"
                      "SUMMARY:todo with a non-uuid uid\r\n"
                      "UID:" + NON_UUID_UID + "\r\n"
                      "END:VTODO\r\n")

    @staticmethod
    def _todo(raw):
        todo = Mock()
        todo.instance.vtodo = vobject.readOne(raw)
        todo.parent.name = 'My Calendar'
        return todo

    @staticmethod
    def _backend():
        parameters = {'pid': 'test', 'service-url': 'unittest',
                      'username': 'u', 'password': 'p', 'period': 1,
                      'is-first-run': False}
        backend = Backend(parameters)
        backend.datastore = Datastore()
        return backend

    def _synced_backend(self, raw_vtodo):
        """A backend whose cache holds one imported todo."""
        backend = self._backend()
        calendar = Mock()
        calendar.name = 'My Calendar'
        todo = self._todo(raw_vtodo)
        calendar.todos.return_value = [todo]
        counts = {'created': 0, 'updated': 0, 'unchanged': 0, 'deleted': 0}
        backend._import_calendar_todos(
            calendar, datetime.now(LOCAL_TIMEZONE), counts)
        backend._cache.initialized = True  # done by _do_periodic_import
        self.assertEqual(1, counts['created'])
        task = next(iter(backend.datastore.tasks.lookup.values()))
        return backend, todo, task

    def test_remove_task_deletes_the_remote_todo(self):
        backend, todo, task = self._synced_backend(self.VTODO_UUID)
        backend.remove_task(str(task.id))
        todo.delete.assert_called_once_with()
        self.assertIsNone(backend._cache.get_todo(str(task.id)))

    def test_remove_task_does_not_touch_the_local_store(self):
        # regression: the old remove_task deleted the task from GTG's
        # own store instead of pushing the deletion to the server
        backend, todo, task = self._synced_backend(self.VTODO_UUID)
        backend.remove_task(str(task.id))
        self.assertIn(task.id, backend.datastore.tasks.lookup)

    def test_remove_task_accepts_a_uuid_object(self):
        # regression: the queue hands over task.id (a UUID object)
        # while the todo cache is keyed by str(task.id)
        backend, todo, task = self._synced_backend(self.VTODO_UUID)
        backend.remove_task(task.id)
        todo.delete.assert_called_once_with()

    def test_remove_task_with_non_uuid_server_uid(self):
        backend, todo, task = self._synced_backend(self.VTODO_NON_UUID)
        backend.remove_task(task.id)
        todo.delete.assert_called_once_with()
        self.assertIsNone(backend._cache.get_todo(str(task.id)))

    def test_remove_task_for_unknown_tid_is_a_noop(self):
        backend, todo, task = self._synced_backend(self.VTODO_UUID)
        backend.remove_task('11111111-2222-3333-4444-555555555555')
        todo.delete.assert_not_called()

    def test_remove_task_before_cache_is_ready_is_ignored(self):
        backend = self._backend()
        # cache not initialized: nothing to look up, must not raise
        backend.remove_task('5241ab4d-05ef-4b2e-ab1e-1699ba222eef')

    def test_deleting_an_already_gone_todo_is_a_success(self):
        # DELETE must be idempotent: a 404 means the goal (the todo
        # no longer exists server-side) is already reached
        backend, todo, task = self._synced_backend(self.VTODO_UUID)
        todo.delete.side_effect = NotFoundError('410 Gone')
        # assertNoLogs is Python 3.10+ and CI runs 3.9: capture the
        # records and check none is error-level instead
        with self.assertLogs('GTG.backends.backend_caldav',
                             level='INFO') as captured:
            backend.remove_task(task.id)  # must not raise
        self.assertFalse(
            [r.getMessage() for r in captured.records
             if r.levelname in ('ERROR', 'CRITICAL')])
        self.assertIsNone(backend._cache.get_todo(str(task.id)))


class ServerSideSubtaskDeletionTest(TestCase):
    """A subtask deleted on the server must be removed locally too.

    _get_calendar_tasks used to iterate tasks.data, which only holds
    toplevel tasks: subtasks were invisible to the import's deletion
    detection and lived on in GTG forever."""

    @staticmethod
    def _todo(raw, calendar):
        todo = Mock()
        todo.instance.vtodo = vobject.readOne(raw)
        todo.parent = calendar
        return todo

    @patch('GTG.backends.periodic_import_backend.threading.Timer')
    @patch('GTG.backends.backend_caldav.caldav.DAVClient')
    def test_subtask_deleted_on_server_is_deleted_locally(
            self, dav_client, timer):
        calendar = Mock()
        calendar.name, calendar.url = 'my calendar', 'https://my.fa.ke/cal'
        root = self._todo(VTODO_ROOT, calendar)
        child = self._todo(VTODO_CHILD, calendar)
        calendar.todos.return_value = [root, child]
        dav_client.return_value.principal.return_value.calendars\
            .return_value = [calendar]
        parameters = {'pid': 'test', 'service-url': 'unittest',
                      'username': 'u', 'password': 'p', 'period': 1,
                      'is-first-run': False}
        backend = Backend(parameters)
        backend.register_datastore(Datastore())
        backend.initialize()
        backend.do_periodic_import()
        self.assertEqual(2, len(backend.datastore.tasks.lookup))
        child_id = uid_to_task_id('CHILD')
        self.assertIsNotNone(
            backend.datastore.tasks.lookup[child_id].parent,
            'the subtask must be attached under its parent')

        # the subtask disappears from the server
        calendar.todos.return_value = [root]
        calendar.todo_by_uid.side_effect = NotFoundError
        backend.do_periodic_import()
        self.assertNotIn(child_id, backend.datastore.tasks.lookup,
                         'a subtask deleted on the server must not '
                         'survive the next import')
