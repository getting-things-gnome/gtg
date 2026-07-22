import re
import unittest
from datetime import date, datetime, timedelta
from unittest import TestCase
from uuid import uuid4

import vobject
from caldav.lib.error import NotFoundError
from dateutil.tz import UTC
from GTG.backends.backend_caldav import (CATEGORIES, CHILDREN_FIELD,
                                         Recurrence,
                                         DAV_IGNORE, PARENT_FIELD, UID_FIELD,
                                         Backend, DueDateField, SORT_ORDER,
                                         Translator, uid_to_task_id)
from GTG.core.datastore import Datastore
from GTG.core.dates import LOCAL_TIMEZONE, Date
from GTG.core.tasks import Task, Status
from unittest.mock import Mock, patch

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


class CalDAVTest(TestCase):
    """The historical CalDAV test suite, migrated to the new core API.

    Same scenarios and intent as the original old-core tests; where the
    behavior of the backend genuinely changed with the new core port,
    the new behavior is pinned and commented."""

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
    @patch('GTG.backends.periodic_import_backend.threading.Timer')
    @patch('GTG.backends.backend_caldav.caldav.DAVClient')
    def _setup_backend(calendars, dav_client, timer):
        """A backend wired to a fresh datastore, first import done.

        The original helper went through datastore.register_backend,
        which nowadays persists the backend configuration to the real
        user config and spawns startup threads. Wiring the backend
        directly and running the first import synchronously keeps the
        tests deterministic and side-effect free (timers are inert
        mocks: every import cycle is an explicit call); the registration
        machinery has its own coverage in test_backend_persistence.
        """
        datastore = Datastore()
        parameters = {'pid': 'favorite', 'service-url': 'color',
                      'username': 'blue', 'password': 'no red', 'period': 1,
                      'is-first-run': False}
        backend = Backend(parameters)
        backend.register_datastore(datastore)
        dav_client.return_value.principal.return_value.calendars\
            .return_value = calendars
        backend.initialize()
        backend.do_periodic_import()
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
        self.assertTrue(isinstance(uid, str), f"should be str is {uid!r}")
        self.assertEqual(uid, UID_FIELD.get_dav(vtodo=todo.instance.vtodo))
        datastore = Datastore()
        task = Task(id=uid_to_task_id(uid), title='')
        Translator.fill_task(todo, task, NAMESPACE, datastore)
        self.assertEqual('2020-12-24', str(task.date_due))
        vtodo = Translator.fill_vtodo(task, todo.parent.name, NAMESPACE)
        for field in Translator.fields:
            if field.dav_name in DAV_IGNORE:
                continue
            self.assertTrue(field.is_equal(task, NAMESPACE, todo),
                            f'{field!r} has differing values')
            self.assertTrue(field.is_equal(task, NAMESPACE,
                                           vtodo=vtodo.vtodo),
                            f'{field!r} has differing values')
        vtodo.vtodo.contents['description'][0].value = 'changed value'
        self.assertTrue(DESCRIPTION.is_equal(task, NAMESPACE, todo), 'same '
                        'hashes should prevent changes on vTodo to be noticed')
        task.content = task.content + 'more content'
        self.assertFalse(DESCRIPTION.is_equal(task, NAMESPACE, todo))

    def test_translate_from_task(self):
        now, today = datetime.now(), date.today()
        task = Task(id=uuid4(), title='holy graal')
        task.content = 'the knights who says ni'
        task.set_recurring(True, 'other-day')
        task.date_start = Date(today)
        task.date_due = Date('soon')
        task.date_closed = Date(now)
        vtodo = Translator.fill_vtodo(task, 'My Calendar Name', NAMESPACE)
        for field in Translator.fields:
            if field.dav_name in DAV_IGNORE:
                continue
            self.assertTrue(field.is_equal(task, NAMESPACE, vtodo=vtodo.vtodo),
                            f'{field!r} has differing values')
        serialized = vtodo.serialize()
        self.assertTrue(f"DTSTART;VALUE=DATE:{today.strftime('%Y%m%d')}"
                        in serialized, f"missing from {serialized}")
        self.assertTrue("DUE;GTGFUZZY=soon" in serialized,
                        f"missing from {serialized}")
        # trying to fill utc only with fuzzy
        task.date_closed = Date('someday')
        vtodo = Translator.fill_vtodo(task, 'My Calendar Name', NAMESPACE)
        serialized = vtodo.serialize()
        self.assertTrue("COMPLETED;GTGFUZZY=someday:" in serialized,
                        f"missing from {serialized}")
        # trying to fill utc only with date
        task.date_closed = Date(today)
        vtodo = Translator.fill_vtodo(task, 'My Calendar Name', NAMESPACE)
        serialized = vtodo.serialize()
        today_in_utc = now.replace(hour=0, minute=0, second=0)\
            .replace(tzinfo=LOCAL_TIMEZONE).astimezone(UTC)\
            .strftime('%Y%m%dT%H%M%SZ')
        self.assertTrue(f"COMPLETED:{today_in_utc}" in serialized,
                        f"missing {today_in_utc} from {serialized}")
        # emptying date by setting None or no_date
        task.date_closed = Date.no_date()
        task.date_due = Date.no_date()
        task.date_start = Date.no_date()
        vtodo = Translator.fill_vtodo(task, 'My Calendar Name', NAMESPACE)
        serialized = vtodo.serialize()
        self.assertTrue("CATEGORIES:" not in serialized)
        self.assertTrue("COMPLETED:" not in serialized)
        self.assertTrue("DUE:" not in serialized)
        self.assertTrue("DTSTART:" not in serialized)

    def test_translate(self):
        datastore = Datastore()
        my_tag = datastore.tags.new('my-tag')
        other_tag = datastore.tags.new('my-other-tag')
        root_task = datastore.tasks.new('my task')
        root_task.add_tag(my_tag)
        root_task.add_tag(other_tag)
        child_task = datastore.tasks.new('my first child', parent=root_task.id)
        child_task.add_tag(my_tag)
        child_task.add_tag(other_tag)
        child_task.content = "task content"
        child2_task = datastore.tasks.new('my done child',
                                          parent=root_task.id)
        child2_task.add_tag(my_tag)
        child2_task.add_tag(other_tag)
        child2_task.content = "other task txt"
        child2_task.set_status(Status.DONE)
        root_task.content = (f"line\n"
                             f"{{!{child_task.id}!}}\n"
                             f"{{!{child2_task.id}!}}\n")
        self.assertEqual([child_task, child2_task], root_task.children)
        self.assertEqual(root_task, child_task.parent)
        self.assertEqual([], PARENT_FIELD.get_gtg(root_task, NAMESPACE))
        self.assertEqual([str(child_task.id), str(child2_task.id)],
                         CHILDREN_FIELD.get_gtg(root_task, NAMESPACE))
        self.assertEqual([str(root_task.id)],
                         PARENT_FIELD.get_gtg(child_task, NAMESPACE))
        self.assertEqual([], CHILDREN_FIELD.get_gtg(child_task, NAMESPACE))
        root_vtodo = Translator.fill_vtodo(root_task, 'calname', NAMESPACE)
        child_vtodo = Translator.fill_vtodo(child_task, 'calname', NAMESPACE)
        child2_vtodo = Translator.fill_vtodo(child2_task, 'calname',
                                             NAMESPACE)
        self.assertEqual([], PARENT_FIELD.get_dav(vtodo=root_vtodo.vtodo))
        self.assertEqual([str(child_task.id), str(child2_task.id)],
                         CHILDREN_FIELD.get_dav(vtodo=root_vtodo.vtodo))
        self.assertEqual([str(root_task.id)],
                         PARENT_FIELD.get_dav(vtodo=child_vtodo.vtodo))
        self.assertEqual([], CHILDREN_FIELD.get_dav(vtodo=child_vtodo.vtodo))
        self.assertTrue(f'\r\nRELATED-TO;RELTYPE=CHILD:{child_task.id}\r\n'
                        in root_vtodo.serialize())
        self.assertTrue(f'\r\nRELATED-TO;RELTYPE=PARENT:{root_task.id}\r\n'
                        in child_vtodo.serialize())
        root_contents = root_vtodo.contents['vtodo'][0].contents
        child_cnt = child_vtodo.contents['vtodo'][0].contents
        child2_cnt = child2_vtodo.contents['vtodo'][0].contents
        for cnt in root_contents, child_cnt, child2_cnt:
            self.assertEqual(['my-other-tag', 'my-tag'],
                             sorted(cnt['categories'][0].value))
        self.assertEqual('my first child', child_cnt['summary'][0].value)
        self.assertEqual('my done child', child2_cnt['summary'][0].value)
        self.assertEqual('task content', child_cnt['description'][0].value)
        self.assertEqual('other task txt', child2_cnt['description'][0].value)
        self.assertEqual('line\n[ ] my first child\n[x] my done child',
                         root_contents['description'][0].value)

    def test_do_periodic_import(self):
        calendar = self._mock_calendar()
        todos = [self._get_todo(VTODO_CHILD_PARENT, calendar),
                 self._get_todo(VTODO_ROOT, calendar),
                 self._get_todo(VTODO_CHILD, calendar),
                 self._get_todo(VTODO_GRAND_CHILD, calendar)]
        calendar.todos.return_value = todos
        datastore, backend = self._setup_backend([calendar])

        self.assertEqual(4, len(datastore.tasks.lookup))
        task = datastore.tasks.lookup[uid_to_task_id('ROOT')]
        self.assertEqual([uid_to_task_id('CHILD'),
                          uid_to_task_id('CHILD-PARENT')],
                         [subtask.id for subtask in task.children])
        self.assertEqual(
            0, len(datastore.tasks.lookup[uid_to_task_id('CHILD')].children))
        self.assertEqual(
            1, len(datastore.tasks.lookup[
                uid_to_task_id('CHILD-PARENT')].children))

        def get_todo(uid):
            return next(todo for todo in todos
                        if UID_FIELD.get_dav(todo) == uid)

        for uid, parents, children in (
                ('ROOT', [], ['CHILD', 'CHILD-PARENT']),
                ('CHILD', ['ROOT'], []),
                ('CHILD-PARENT', ['ROOT'], ['GRAND-CHILD'])):
            task = datastore.tasks.lookup[uid_to_task_id(uid)]
            self.assertEqual(children, CHILDREN_FIELD.get_dav(get_todo(uid)),
                             "children should've been written by sync down")
            self.assertEqual([uid_to_task_id(child) for child in children],
                             [c.id for c in task.children],
                             "children missing from task")
            self.assertEqual(parents, PARENT_FIELD.get_dav(get_todo(uid)),
                             "parent on todo aren't consistent")
            parent_ids = [task.parent.id] if task.parent else []
            self.assertEqual([uid_to_task_id(p) for p in parents], parent_ids,
                             "parent missing from task")

        calendar.todo_by_uid.return_value = todos[-1]
        todos = todos[:-1]
        child_todo = todos[-1]
        child_todo.instance.vtodo.contents['summary'][0].value = 'new summary'
        calendar.todos.return_value = todos

        # syncing with missing and updated todo, no change: the title
        # edit is ignored because the SEQUENCE was not bumped, and the
        # missing grand-child gets refetched from the server
        task = datastore.tasks.lookup[
            uid_to_task_id(child_todo.instance.vtodo.uid.value)]
        backend.do_periodic_import()
        self.assertEqual(4, len(datastore.tasks.lookup),
                         "no not found raised, no reason to remove tasks")
        self.assertEqual('my child summary', task.title, "title shouldn't "
                         "have changed because sequence wasn't updated")

        # syncing with same data, delete one and edit remaining
        calendar.todo_by_uid.side_effect = NotFoundError
        child_todo.instance.vtodo.contents['sequence'][0].value = '2'
        backend.do_periodic_import()
        self.assertEqual(3, len(datastore.tasks.lookup))
        self.assertEqual('new summary', task.title)

        # set_task with no change: no update pushed
        backend.set_task(task)
        child_todo.save.assert_not_called()
        child_todo.delete.assert_not_called()
        calendar.add_todo.assert_not_called()
        # set_task with a change: one update pushed
        task.set_status(Status.DONE)
        backend.set_task(task)
        child_todo.save.assert_called_once()
        calendar.add_todo.assert_not_called()
        child_todo.delete.assert_not_called()
        child_todo.save.reset_mock()
        # pushing again without further change: no update
        backend.set_task(task)
        child_todo.save.assert_not_called()
        calendar.add_todo.assert_not_called()
        child_todo.delete.assert_not_called()

        # creating a task without any calendar tag: the new backend
        # falls back on the default calendar instead of refusing
        # (questionable when several calendars exist, tracked
        # separately, but it is the current contract)
        task = datastore.tasks.new('brand new task')
        calendar.add_todo.return_value = child_todo
        backend.set_task(task)
        child_todo.save.assert_not_called()
        calendar.add_todo.assert_called_once()
        child_todo.delete.assert_not_called()
        calendar.add_todo.reset_mock()

        backend.remove_task('11111111-2222-3333-4444-555555555555')
        child_todo.save.assert_not_called()
        calendar.add_todo.assert_not_called()
        child_todo.delete.assert_not_called()

        backend.remove_task(str(uid_to_task_id('CHILD')))
        child_todo.save.assert_not_called()
        calendar.add_todo.assert_not_called()
        child_todo.delete.assert_called_once()

    def test_switch_calendar(self):
        calendar1 = self._mock_calendar()
        calendar2 = self._mock_calendar('other calendar', 'http://no.whe.re/')
        todo = self._get_todo(VTODO_ROOT, calendar1)
        calendar1.todos.return_value = [todo]
        calendar2.todos.return_value = []
        datastore, backend = self._setup_backend([calendar1, calendar2])
        self.assertEqual(1, len(datastore.tasks.lookup))
        task = datastore.tasks.lookup[
            uid_to_task_id(UID_FIELD.get_dav(todo))]
        self.assertTrue(CATEGORIES.has_calendar_tag(task, calendar1))
        self.assertFalse(CATEGORIES.has_calendar_tag(task, calendar2))

        task.remove_tag(CATEGORIES.get_calendar_tag(calendar1))
        task.add_tag(
            datastore.tags.new(CATEGORIES.get_calendar_tag(calendar2)))
        self.assertFalse(CATEGORIES.has_calendar_tag(task, calendar1))
        self.assertTrue(CATEGORIES.has_calendar_tag(task, calendar2))

        calendar2.add_todo.return_value = todo
        backend.set_task(task)
        calendar1.add_todo.assert_not_called()
        calendar2.add_todo.assert_called_once()
        todo.delete.assert_called_once()

    def test_task_mark_as_done_from_backend(self):
        calendar = self._mock_calendar()
        todo = self._get_todo(VTODO_ROOT, calendar)
        calendar.todos.return_value = [todo]
        datastore, backend = self._setup_backend([calendar])
        uid = UID_FIELD.get_dav(todo)
        self.assertEqual(1, len(datastore.tasks.lookup))
        task = datastore.tasks.lookup[uid_to_task_id(uid)]
        self.assertEqual(Status.ACTIVE, task.status)
        calendar.todos.assert_called_once()
        calendar.todo_by_uid.assert_not_called()
        calendar.todos.reset_mock()

        todo.instance.vtodo.contents['status'][0].value = 'COMPLETED'
        calendar.todos.return_value = []
        calendar.todo_by_uid.return_value = todo
        backend.do_periodic_import()
        calendar.todos.assert_called_once()
        calendar.todo_by_uid.assert_called_once()

        self.assertEqual(1, len(datastore.tasks.lookup))
        task = datastore.tasks.lookup[uid_to_task_id(uid)]
        self.assertEqual(Status.DONE, task.status)

    def test_due_date_caldav_restriction(self):
        task = Task(id=uuid4(), title='')
        later = datetime(2021, 11, 24, 21, 52, 45)
        before = later - timedelta(days=1)
        task.date_start = Date(later)
        task.date_due = Date(before)
        field = DueDateField('due', 'get_due_date_constraint', 'set_due_date')
        self.assertEqual(later, field.get_gtg(task, '').dt_value)

        task.date_start = Date(before)
        task.date_due = Date(later)
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

    def test_missing_active_todo_is_refetched_by_its_server_uid(self):
        """A task imported from a non-UUID server keeps that UID as an
        attribute; its GTG id is a one-way uuid5 of it. When the todo is
        absent from a later fetch, the backend refetches it to decide
        whether to delete the task -- and must ask the server by the UID
        the server actually knows (remote_uid), not the GTG id. Asking
        by the GTG id always raises NotFoundError, so the task gets
        deleted on every import (silent data loss)."""
        backend = self._backend()
        calendar = Mock()
        calendar.name = 'My Calendar'
        todo = self._todo(self.VTODO_NON_UUID)
        todo.parent = calendar
        calendar.todos.return_value = [todo]
        counts = {'created': 0, 'updated': 0, 'unchanged': 0, 'deleted': 0}
        start = datetime.now(LOCAL_TIMEZONE)
        backend._import_calendar_todos(calendar, start, counts)
        backend._cache.initialized = True
        self.assertEqual(1, len(backend.datastore.tasks.lookup))
        task = next(iter(backend.datastore.tasks.lookup.values()))
        # make the task look older than the import so it is a deletion
        # candidate rather than a just-created one
        task.date_added = Date(datetime(2000, 1, 1, tzinfo=LOCAL_TIMEZONE))

        # next import: the todo is gone from the fetch. The server still
        # has it under its real UID, so refetch must find it and NOT delete.
        calendar.todos.return_value = []
        calendar.todo_by_uid.return_value = todo
        backend._import_calendar_todos(
            calendar, datetime.now(LOCAL_TIMEZONE), counts)

        calendar.todo_by_uid.assert_called_once_with(self.NON_UUID_UID)
        self.assertEqual(1, len(backend.datastore.tasks.lookup),
                         'the task must survive: the server still has it')



class RecurrenceRRuleTest(TestCase):
    """The CalDAV Recurrence field maps between iCalendar RRULE FREQ and
    GTG recurring terms. Reading a DAILY rule used to go through
    freq.lower()[:-2], which turns 'WEEKLY'->'week' but 'DAILY'->'dai',
    a term GTG's date parser doesn't know. Every FREQ we write must read
    back as a term GTG actually accepts."""

    GTG_TERMS = {'day', 'other-day', 'week', 'month', 'year'}

    def _vtodo_with_rrule(self, **params):
        cal = vobject.iCalendar()
        todo = cal.add('vtodo')
        rrule = todo.add('rrule')
        rrule.params = {k: (v if isinstance(v, list) else [v])
                        for k, v in params.items()}
        return todo

    def test_daily_reads_back_as_a_valid_gtg_term(self):
        field = Recurrence('rrule', 'get_recurring_term', 'set_recurring')
        vtodo = self._vtodo_with_rrule(FREQ='DAILY')
        enabled, term = field.get_dav(vtodo=vtodo)
        self.assertTrue(enabled)
        self.assertEqual('day', term)
        self.assertIn(term, self.GTG_TERMS)

    def test_every_freq_maps_to_a_term_gtg_accepts(self):
        field = Recurrence('rrule', 'get_recurring_term', 'set_recurring')
        for freq in ('DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY'):
            vtodo = self._vtodo_with_rrule(FREQ=freq)
            enabled, term = field.get_dav(vtodo=vtodo)
            self.assertTrue(enabled, f'{freq} should be recurring')
            self.assertIn(term, self.GTG_TERMS,
                          f'{freq} read back as {term!r}, not a GTG term')

    def test_every_other_day_is_recognised(self):
        field = Recurrence('rrule', 'get_recurring_term', 'set_recurring')
        vtodo = self._vtodo_with_rrule(FREQ='DAILY', INTERVAL='2')
        enabled, term = field.get_dav(vtodo=vtodo)
        self.assertTrue(enabled)
        self.assertEqual('other-day', term)

    def test_unsupported_freq_is_ignored_not_mangled(self):
        field = Recurrence('rrule', 'get_recurring_term', 'set_recurring')
        vtodo = self._vtodo_with_rrule(FREQ='HOURLY')
        enabled, term = field.get_dav(vtodo=vtodo)
        self.assertFalse(enabled)
        self.assertIsNone(term)



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
