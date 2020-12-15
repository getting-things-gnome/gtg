from datetime import datetime
from unittest import TestCase

import vobject
from GTG.backends.backend_caldav import DAV_IGNORE, UID_FIELD, Translator
from GTG.core.task import Task
from mock import Mock

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
UID:2771444325910370883\r
X-APPLE-SORT-ORDER:629421506\r
END:VTODO\r
"""

VTODO_CHILDREN = """BEGIN:VCALENDAR\r
VERSION:2.0\r
PRODID:+//IDN tasks.org//android-100401//EN\r
BEGIN:VTODO\r
COMPLETED:20201212T172558Z\r
CREATED:20201212T092155Z\r
DTSTAMP:20201212T172830Z\r
LAST-MODIFIED:20201212T172558Z\r
PERCENT-COMPLETE:10\r
PRIORITY:9\r
RELATED-TO;RELTYPE=PARENT:2771444325910370883\r
SEQUENCE:1\r
STATUS:COMPLETED\r
SUMMARY:my summary\r
UID:1424529770309495136\r
X-APPLE-SORT-ORDER:629421506\r
END:VTODO\r
END:VCALENDAR\r
"""


class TestQuickAddParse(TestCase):

    @staticmethod
    def _get_todo(vtodo_raw):
        vtodo = vobject.readOne(vtodo_raw)
        todo = Mock()
        todo.instance.vtodo = vtodo
        todo.parent.name = 'My Calendar'
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
