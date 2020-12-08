# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
# Copyright (c) 2020 - Mildred Ki'Lya
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

"""
Backend for storing/loading tasks in CalDAV Tasks
"""

import threading
from datetime import datetime, timezone
from gettext import gettext as _

import caldav
from GTG.backends.backend_signals import BackendSignals
from GTG.backends.generic_backend import GenericBackend
from GTG.backends.periodic_import_backend import PeriodicImportBackend
from GTG.core.interruptible import interruptible
from GTG.core.logger import log
from GTG.core.task import Task
from GTG.core.dates import Date, LOCAL_TIMEZONE
from vobject import iCalendar

GTG_UID_KEY = 'gtg-task-uid'
GTG_ID_KEY = 'gtg-task-id'
GTG_START_KEY = 'gtg-start-date'
DAV_IGNORE = {'last-modified',  # often updated alone by GTG
              'sequence',  # internal DAV value, only set by translator
              GTG_ID_KEY, GTG_UID_KEY,  # remote ids, not worthy of sync alone
              'percent-complete',  # calculated on subtask and status
              }


class Backend(PeriodicImportBackend):
    """
    CalDAV backend
    """

    _general_description = {
        GenericBackend.BACKEND_NAME: 'backend_caldav',
        GenericBackend.BACKEND_ICON: 'applications-internet',
        GenericBackend.BACKEND_HUMAN_NAME: _('CalDAV tasks'),
        GenericBackend.BACKEND_AUTHORS: ['Mildred Ki\'Lya',
                                         'François Schmidts'],
        GenericBackend.BACKEND_TYPE: GenericBackend.TYPE_READWRITE,
        GenericBackend.BACKEND_DESCRIPTION:
        _('Lets you synchronize your GTG tasks with CalDAV tasks'),
    }

    _static_parameters = {
        "period": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_INT,
            GenericBackend.PARAM_DEFAULT_VALUE: 0.25},
        "username": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE: _('insert your username')},
        "password": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_PASSWORD,
            GenericBackend.PARAM_DEFAULT_VALUE: ''},
        "service-url": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE: 'https://example.com/webdav/'},
        "default-calendar-name": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE: ''},
        "is-first-run": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_BOOL,
            GenericBackend.PARAM_DEFAULT_VALUE: True},
    }

###############################################################################
# Backend standard methods ####################################################
###############################################################################
    def __init__(self, parameters):
        """
        See GenericBackend for an explanation of this function.
        Re-loads the saved state of the synchronization
        """
        super().__init__(parameters)
        self._locks = {}
        self._dav_client = None
        self._calendars_by_name = {}
        self._calendars_by_url = {}
        self._todos_by_uid = {}
        self._todos_by_gtg_id = {}
        self._todos_by_gtg_uid = {}

    def initialize(self) -> None:
        super().initialize()
        self._dav_client = caldav.DAVClient(
            url=self._parameters['service-url'],
            username=self._parameters['username'],
            password=self._parameters['password'])

    @interruptible
    def do_periodic_import(self) -> None:
        log.info("Running periodic import")
        with self.datastore.get_backend_mutex():
            with self._get_lock('calendar-listing', raise_if_absent=False):
                self._refresh_calendar_list()
            self._todos_by_gtg_id = {}
            self._todos_by_gtg_uid = {}
            # browsing calendars
            # TODO filter task, not syncing children task
            for calendar in self._dav_calendars:
                cal_url = str(calendar.url)
                with self._get_lock(cal_url, raise_if_absent=False):
                    # retrieving todos and updating various cache
                    if cal_url not in self._todos_by_uid:
                        self._todos_by_uid[cal_url] = {}
                    else:
                        self._todos_by_uid[cal_url].clear()
                    log.info('Fetching todos from %r', calendar.url)
                    todos = {UID_FIELD.get_dav(todo): todo
                             for todo in calendar.todos()}
                    self._todos_by_uid[cal_url] = todos
                    for uid, todo in todos.items():
                        self._todos_by_gtg_uid[uid] = todo
                        tid = GTG_ID_FIELD.get_dav(todo)
                        if tid:
                            self._todos_by_gtg_id[tid] = todo

            # Updating and creating task according to todos
            task_by_uid = self._get_task_cache()
            seen_task_ids = set()
            created, updated, unchanged = 0, 0, 0
            for todo in self._cached_todos:
                task = self._get_task(todo, task_by_uid)
                todo_uid = UID_FIELD.get_dav(todo)
                if not task:  # not found, creating it
                    task = self.datastore.task_factory(todo_uid)
                    created += 1
                else:
                    task_seq = SEQUENCE.get_gtg(task, self.namespace)
                    todo_seq = SEQUENCE.get_dav(todo)
                    if task_seq == todo_seq:
                        unchanged += 1
                        seen_task_ids.add(task.get_id())
                        continue
                    updated += 1
                seen_task_ids.add(task.get_id())
                Translator.fill_task(todo, task, self.namespace)
                self.datastore.push_task(task)
            log.info('Created %d new task, updated %d ones from backend '
                     '(ignored %d unchanged)', created, updated, unchanged)

            # removing task we didn't see during listing
            all_tids = {task_id
                        for task_id in self.datastore.get_all_tasks()}
            deleted = 0
            for task_id in all_tids.difference(seen_task_ids):
                deleted += 1
                self.datastore.request_task_deletion(task_id)
            log.info('Deleted %d task absent from backend', deleted)
            self._parameters["is-first-run"] = False

    @interruptible
    def set_task(self, task: Task) -> None:
        if self._parameters["is-first-run"]:
            log.warning("not loaded yet, ignoring set_task")
            return
        # TODO filter task, not syncing children task
        log.info('set_task todo for %r', task.get_id())
        todo = self._get_todo(task=task)
        if todo:
            calendar = todo.parent
        else:
            calendar = self._get_calendar(task=task)
        calendar_url = str(calendar.url)
        with self._get_lock(calendar_url):
            if todo:  # found one, saving it
                if not Translator.should_sync(task, self.namespace, todo):
                    return
                for field, task_value, todo_value in Translator.changed_attrs(
                        task, self.namespace, todo):
                    log.debug('changed %s(%r != %r)', field,
                              task_value, todo_value)

                Translator.fill_vtodo(task, calendar.name, self.namespace,
                                      todo.instance.vtodo)
                # saving new todo
                log.info('updating todo %r', todo)
                self._log(task, todo=todo)
                todo.save()
            else:  # creating from task
                new_vtodo = Translator.fill_vtodo(
                    task, calendar.name, self.namespace)
                log.info('creating todo for %r', task)
                self._log(task, vtodo=new_vtodo.vtodo)
                new_todo = calendar.add_todo(new_vtodo.serialize())
                self._todos_by_uid[calendar_url][new_todo.uid] = new_todo
                self._todos_by_gtg_id[task.get_id()] = new_todo
                self._todos_by_gtg_uid[task.get_uuid()] = new_todo
                task.add_remote_id(self.get_id(), task.get_uuid())

    def _log(self, task, todo=None, vtodo=None):
        Translator.is_changed(task, self.namespace, todo, vtodo)
        if todo:
            vtodo = todo.instance.vtodo
        for key in vtodo.contents:
            log.debug("%s:%r", key, vtodo.contents[key])
        log.debug(vtodo.serialize())

    @interruptible
    def remove_task(self, tid: str) -> None:
        if self._parameters["is-first-run"]:
            log.warning("not loaded yet, ignoring set_task")
            return
        if not tid:
            return
        log.info('removing todo for Task(%s)', tid)
        todo = self._todos_by_gtg_id.pop(tid, None)
        if todo:
            with self._get_lock(str(todo.parent.url)):
                uid = UID_FIELD.get_dav(todo)
                # cleaning cache
                self._todos_by_gtg_id.pop(tid, None)
                self._todos_by_gtg_uid.pop(uid, None)
                self._todos_by_uid.pop(uid, None)
                # deleting through caldav
                todo.delete()

    #
    # Dav functions
    #

    def _refresh_calendar_list(self):
        try:
            principal = self._dav_client.principal()
        except caldav.lib.error.AuthorizationError as error:
            message = _(
                "You need a correct login to CalDAV"
                "Configure CalDAV with login information. Error:"
            )
            BackendSignals().interaction_requested(
                self.get_id(), message + " " + str(error),
                BackendSignals().INTERACTION_INFORM, "on_continue_clicked")
            raise error
        calendars = principal.calendars()
        self._update_cache({str(cal.url): cal for cal in calendars},
                           self._calendars_by_url)
        self._update_cache({cal.name: cal for cal in calendars},
                           self._calendars_by_name)
        def_cal_name = self._parameters.get('default-calendar-name')
        if not def_cal_name or def_cal_name not in self._calendars_by_name:
            self._notify_user_about_default_calendar()

    #
    # Utility methods
    #

    def _get_lock(self, name: str, raise_if_absent: bool = False):
        if name not in self._locks:
            if raise_if_absent:
                raise RuntimeError('lock for %r should be present' % name)
            self._locks[name] = threading.Lock()
        return self._locks[name]

    @staticmethod
    def _update_cache(new_values: dict, cache: dict) -> None:
        for key in new_values:
            if key not in cache:
                cache[key] = new_values[key]
        for key in list(cache):
            if key not in new_values:
                cache.pop(key)

    @property
    def _dav_calendars(self):
        seen_urls = set()
        for calendar in self._calendars_by_name.values():
            yield calendar
            seen_urls.add(str(calendar.url))
        for calendar in self._calendars_by_url.values():
            if str(calendar.url) not in seen_urls:
                yield calendar
                log.warning("async cache ?")

    @property
    def _cached_todos(self):
        for cal_url in self._todos_by_uid:
            yield from self._todos_by_uid[cal_url].values()

    def _get_todo(self, task: Task) -> caldav.Todo:
        task_id = task.get_id()
        # log.debug('lookup in _todos_by_gtg_id by gtg id for id %r', task_id)
        # if the todo has the task id registered, we look it up
        todo = self._todos_by_gtg_id.get(task_id)
        if todo:
            return todo
        # if the uuid is the same for the todo and the task
        tuid = task.get_uuid()
        # log.debug('lookup in _todos_by_gtg_uid with uid %r', tuid)
        todo = self._todos_by_gtg_uid.get(tuid)
        if todo:
            return todo
        for calendar in self._dav_calendars:
            cal_url = str(calendar.url)
            # log.debug('lookup in _todos_by_uid[%s] with uid %r',
            #           cal_url, tuid)
            if tuid in self._todos_by_uid[cal_url]:
                return self._todos_by_uid[cal_url][tuid]
        # if the task has remote id for that backend
        remote_id = task.get_remote_ids().get(self.get_id())
        # log.debug('browsing _cached_todos for remote_id:%r and tid:%r',
        #           remote_id, task_id)
        for todo in self._cached_todos:
            if remote_id and UID_FIELD.get_dav(todo) == remote_id:
                return todo
            if GTG_ID_FIELD.get_dav(todo=todo) == task_id:
                return todo
        return None

    def _get_task_cache(self) -> dict:
        task_by_uid = {}
        for task_id in self.datastore.get_all_tasks():
            task = self.datastore.get_task(task_id)
            task_by_uid[task.get_uuid()] = task
        for task in list(task_by_uid.values()):
            remote_id = task.get_remote_ids().get(self.get_id())
            if remote_id:
                task_by_uid[remote_id] = task
        return task_by_uid

    def _get_task(self, todo, cache_uid: dict):
        tid = GTG_ID_FIELD.get_dav(todo)
        if tid:  # vtodo has a task id, requesting datastore with it
            return self.datastore.get_task(tid)
        # trying to look up todo through uuid
        task = cache_uid.get(UID_FIELD.get_dav(todo))
        if task:
            return task
        return cache_uid.get(GTG_UID_FIELD.get_dav(todo))

    def _get_calendar(self, task: Task) -> caldav.Calendar:
        calendar_url = task.get_attribute("calendar_url",
                                          namespace=self.namespace)
        calendar = self._calendars_by_url.get(calendar_url)
        if calendar:
            return calendar
        default_calendar_name = self._parameters['default-calendar-name']
        return self._calendars_by_name[default_calendar_name]

    @property
    def namespace(self):
        return "caldav:%s" % self._parameters['service-url']

    def _notify_user_about_default_calendar(self):
        """ This function causes the infobar to show up with the message
        about default calendar.
        """
        default_name = self._parameters['default-calendar-name']
        message = _(
            f"Could not find calendar {default_name}"
            "Configure CalDAV to save in a calendar from this list : \n"
        ) + '\n'.join(list(self._calendars_by_name))
        BackendSignals().interaction_requested(
            self.get_id(), message,
            BackendSignals().INTERACTION_INFORM, "on_continue_clicked")


class Field:

    def __init__(self, dav_name: str,
                 task_get_func_name: str, task_set_func_name: str,
                 ignored_values: list = None):
        self.dav_name = dav_name
        self.task_get_func_name = task_get_func_name
        self.task_set_func_name = task_set_func_name
        self.ignored_values = ignored_values or ['', 'None', None]

    def _is_value_allowed(self, value):
        return value not in self.ignored_values

    def get_gtg(self, task: Task, namespace: str = None):
        return getattr(task, self.task_get_func_name)()

    def clean_dav(self, todo: iCalendar):
        todo.contents.pop(self.dav_name, None)

    def write_dav(self, vtodo: iCalendar, value):
        self.clean_dav(vtodo)
        vtodo.add(self.dav_name).value = value

    def set_dav(self, task: Task, vtodo: iCalendar, namespace: str) -> None:
        value = self.get_gtg(task, namespace)
        if self._is_value_allowed(value):
            self.write_dav(vtodo, value)

    def get_dav(self, todo=None, vtodo=None):
        if todo:
            vtodo = todo.instance.vtodo
        value = vtodo.contents.get(self.dav_name)
        if value:
            return value[0].value

    def set_gtg(self, todo: iCalendar, task: Task,
                namespace: str = None) -> None:
        if not self.task_set_func_name:
            return
        value = self.get_dav(todo)
        if self._is_value_allowed(value):
            set_func = getattr(task, self.task_set_func_name)
            set_func(value)


class DateField(Field):
    """Offers translation for datetime field.
    Datetime are :
     * naive and at local timezone when in GTG
     * naive or not at UTC timezone from CalDAV
    """

    def __init__(self, dav_name: str,
                 task_get_func_name: str, task_set_func_name: str):
        return super().__init__(
            dav_name, task_get_func_name, task_set_func_name,
            ['', None, 'None', Date.no_date(), Date.someday()])

    @staticmethod
    def _normalize(value):
        if isinstance(value, Date):
            value = value.datetime
        try:
            if value.year == 9999:
                return None
            return value.replace(microsecond=0, tzinfo=None)
        except AttributeError:
            return value

    def write_dav(self, todo: iCalendar, value):
        "Writing datetime as UTC naive"
        if not value.tzinfo:
            value = value - LOCAL_TIMEZONE.utcoffset(value)
        else:
            value = value - value.tzinfo.utcoffset(value)
            value = value.replace(tzinfo=None)
        return super().write_dav(todo, value)

    def get_dav(self, todo=None, vtodo=None):
        """Transforming to local naive,
        if original value is naive, assuming UTC naive"""
        value = super().get_dav(todo, vtodo)
        if value:
            return self._normalize(value.replace(tzinfo=LOCAL_TIMEZONE)
                                   + LOCAL_TIMEZONE.utcoffset(value))

    def get_gtg(self, task: Task, namespace: str = None):
        return self._normalize(super().get_gtg(task, namespace))


class Status(Field):
    DEFAULT_CALDAV_STATUS = 'NEEDS-ACTIONS'
    GTG_TO_CALDAV_STATUS = {Task.STA_ACTIVE: 'NEEDS-ACTION',
                            Task.STA_DONE: 'COMPLETED',
                            Task.STA_DISMISSED: 'CANCELLED'}
    CALDAV_TO_GTG_STATUS = {'NEEDS-ACTION': Task.STA_ACTIVE,
                            'IN-PROCESS': Task.STA_ACTIVE,
                            'COMPLETED': Task.STA_DONE,
                            'CANCELLED': Task.STA_DISMISSED}

    def write_dav(self, todo: iCalendar, value):
        self.clean_dav(todo)
        todo.add(self.dav_name).value = self.GTG_TO_CALDAV_STATUS.get(
            value, self.DEFAULT_CALDAV_STATUS)

    def get_gtg(self, task: Task, namespace: str = None) -> str:
        try:
            return super().get_gtg(task, namespace) or Task.STA_ACTIVE
        except ValueError:
            return Task.STA_ACTIVE

    def get_dav(self, todo=None, vtodo=None) -> str:
        return self.CALDAV_TO_GTG_STATUS.get(super().get_dav(todo, vtodo),
                                             Task.STA_ACTIVE)


class Percent(Field):

    def get_gtg(self, task: Task, namespace: str = None) -> str:
        return '100' if task.get_status() == Task.STA_DONE else '0'


class Categories(Field):

    @staticmethod
    def to_categ(tag):
        return tag.replace('@', '', 1).replace('_', ' ')

    @staticmethod
    def to_tag(category):
        return '@%s' % category.replace(' ', '_')

    def get_gtg(self, task: Task, namespace: str = None) -> list:
        return [self.to_categ(tag.get_name()) for tag in super().get_gtg(task)]

    def get_dav(self, todo=None, vtodo=None):
        if todo:
            vtodo = todo.instance.vtodo
        for sub_value in vtodo.contents.get(self.dav_name, []):
            for category in sub_value.value:
                if self._is_value_allowed(category):
                    yield category

    def ensure_tags(self, task: Task, todo: iCalendar):
        calendar_name = todo.parent.name
        remote_cats = {self.to_categ(cat) for cat in self.get_dav(todo)}
        remote_cats.add(self.to_tag(calendar_name))
        local_tags = set(tag.get_name() for tag in super().get_gtg(task))
        for to_delete in local_tags.difference(remote_cats):
            task.remove_tag(to_delete)
        for to_add in remote_cats.difference(local_tags):
            task.add_tag(to_add)


class AttributeField(Field):

    def get_gtg(self, task: Task, namespace: str = None) -> str:
        return task.get_attribute(self.dav_name, namespace=namespace)

    def set_gtg(self, todo: iCalendar, task: Task,
                namespace: str = None) -> None:
        value = self.get_dav(todo)
        if self._is_value_allowed(value):
            task.set_attribute(self.dav_name, str(value), namespace=namespace)


class Sequence(AttributeField):

    def get_gtg(self, task: Task, namespace: str = None):
        try:
            return int(super().get_gtg(task, namespace) or '0')
        except ValueError:
            return 0

    def get_dav(self, todo=None, vtodo=None):
        try:
            return int(super().get_dav(todo, vtodo) or 0)
        except ValueError:
            return 0

    def set_dav(self, task: Task, vtodo: iCalendar, namespace: str):
        try:
            self.write_dav(vtodo, str(self.get_gtg(task, namespace) + 1))
        except ValueError:
            self.write_dav(vtodo, '1')


class Description(Field):
    CONTENT_OPEN = '<content>'
    LEN_CONTENT_OPEN = len(CONTENT_OPEN)
    CONTENT_CLOSE = '</content>'
    LEN_CONTENT_CLOSE = len(CONTENT_CLOSE)
    TAG_OPEN = '<tag>'
    TAG_CLOSE = '</tag>'
    LEN_TAG_CLOSE = len(TAG_CLOSE)
    LEN_LINE_RET = 2

    def get_dav(self, todo=None, vtodo=None) -> str:
        value = super().get_dav(todo, vtodo) or ''
        # TODO handle subtask
        return value

    def get_gtg(self, task: Task, namespace: str = None) -> str:
        cnt = task.content
        if cnt.startswith(self.CONTENT_OPEN):
            cnt = cnt[self.LEN_CONTENT_OPEN:]
        while True:
            tag_open = cnt.find(self.TAG_OPEN)
            if tag_open == -1:
                break
            tag_close = cnt.find(self.TAG_CLOSE)
            if tag_close == -1:
                break
            cnt = cnt[:tag_open] + cnt[tag_close + self.LEN_TAG_CLOSE:]
        if cnt.startswith('\n\n'):
            # four for two \n which to be randomly added
            cnt = cnt[2:]
        if cnt.endswith(self.CONTENT_CLOSE):
            cnt = cnt[:-self.LEN_CONTENT_CLOSE]
        return cnt


UID_FIELD = Field('uid', 'get_uuid', 'set_uuid')
GTG_ID_FIELD = Field(GTG_ID_KEY, 'get_id', '')
GTG_UID_FIELD = Field(GTG_UID_KEY, 'get_uuid', '')
SEQUENCE = Sequence('sequence', '<fake attribute>', '')
CATEGORIES = Categories('categories', 'get_tags', '')
DTSTAMP_FIELD = DateField('dtstamp', '', '')


class Translator:
    GTG_PRODID = "-//Getting Things Gnome//CalDAV Backend//EN"
    fields = [Field('summary', 'get_title', 'set_title'),
              Description('description', 'get_excerpt', 'set_text'),
              DateField('due', 'get_due_date_constraint', 'set_due_date'),
              DateField('completed', 'get_closed_date', 'set_closed_date'),
              DateField(GTG_START_KEY, 'get_start_date', 'set_start_date'),
              Status('status', 'get_status', 'set_status'),
              Percent('percent-complete', 'get_status', ''),
              GTG_ID_FIELD, GTG_UID_FIELD, SEQUENCE, UID_FIELD,
              DateField('created', 'get_added_date', 'set_added_date'),
              DateField('last-modified', 'get_modified', 'set_modified')]

    @classmethod
    def _get_new_vcal(cls) -> iCalendar:
        vcal = iCalendar()
        vcal.add('PRODID').value = cls.GTG_PRODID
        vcal.add('vtodo')
        return vcal

    @classmethod
    def fill_vtodo(cls, task: Task, calendar_name: str, namespace: str,
                   vtodo: iCalendar = None) -> iCalendar:
        vcal = None
        if vtodo is None:
            vcal = cls._get_new_vcal()
            vtodo = vcal.vtodo
        # updating dtstamp
        DTSTAMP_FIELD.write_dav(vtodo, datetime.now())
        CATEGORIES.clean_dav(vtodo)
        for field in cls.fields:
            if field.dav_name == 'uid' and UID_FIELD.get_dav(vtodo=vtodo):
                # not overriding if already set from cache
                continue
            field.set_dav(task, vtodo, namespace)
        return vcal

    @classmethod
    def fill_task(cls, todo: iCalendar, task: Task, namespace: str):
        for field in cls.fields:
            field.set_gtg(todo, task, namespace)
        task.set_attribute("url", str(todo.url), namespace=namespace)
        task.set_attribute("calendar_url", str(todo.parent.url),
                           namespace=namespace)
        task.set_attribute("calendar_name", todo.parent.name,
                           namespace=namespace)
        CATEGORIES.ensure_tags(task, todo)
        return task

    @classmethod
    def changed_attrs(cls, task: Task, namespace: str, todo=None, vtodo=None):
        for field in cls.fields:
            task_value = field.get_gtg(task, namespace)
            todo_value = field.get_dav(todo, vtodo)
            if todo_value != task_value:
                yield field.dav_name, task_value, todo_value

    @classmethod
    def should_sync(cls, task: Task, namespace: str,  todo=None, vtodo=None):
        for field, __, __ in cls.changed_attrs(task, namespace, todo, vtodo):
            if field not in DAV_IGNORE:
                return True
        return False

    @classmethod
    def is_changed(cls, task: Task, namespace: str, todo=None, vtodo=None):
        return bool(list(cls.changed_attrs(task, namespace, todo, vtodo)))
        return any(cls.changed_attrs(task, namespace, todo, vtodo))
