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

import logging
import threading
from datetime import datetime
from gettext import gettext as _

import caldav
from GTG.backends.backend_signals import BackendSignals
from GTG.backends.generic_backend import GenericBackend
from GTG.backends.periodic_import_backend import PeriodicImportBackend
from GTG.core.interruptible import interruptible
from GTG.core.logger import log
from GTG.core.task import Task
from GTG.core.dates import Date
from functools import wraps
from vobject import iCalendar

GTG_PRODID = "-//Getting Things Gnome//CalDAV Backend//EN"
GTG_UID_KEY = 'gtg-task-uid'
GTG_ID_KEY = 'gtg-task-id'
GTG_START_KEY = 'gtg-start-date'
# Dictionaries to translate GTG tasks in CalDAV ones
_GTG_TO_CALDAV_STATUS = \
    {Task.STA_ACTIVE: 'NEEDS-ACTION',
     Task.STA_DONE: 'COMPLETED',
     Task.STA_DISMISSED: 'CANCELLED'}

_CALDAV_TO_GTG_STATUS = \
    {'NEEDS-ACTION': Task.STA_ACTIVE,
     'IN-PROCESS': Task.STA_ACTIVE,
     'COMPLETED': Task.STA_DONE,
     'CANCELLED': Task.STA_DISMISSED}


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
        log.info("%r: Running periodic import", self)
        with self.datastore.get_backend_mutex():
            with self._get_lock('calendar-listing', raise_if_absent=False):
                self._refresh_calendar_list()
            self._todos_by_gtg_id.clear()
            self._todos_by_gtg_uid.clear()
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
                    log.info('%r: Fetching todos from %r', self, calendar.url)
                    todos = {todo.instance.vtodo.uid.value: todo
                             for todo in calendar.todos()}
                    self._todos_by_uid[cal_url].update(todos)
                    for todo in todos.values():
                        tid = self._extract_from_todo(todo, GTG_ID_KEY)
                        if tid:
                            self._todos_by_gtg_id[tid] = todo
                        uid = self._extract_from_todo(todo, GTG_UID_KEY)
                        if uid:
                            self._todos_by_gtg_uid[uid] = todo

            # Updating and creating task according to todos
            task_by_uid = self._get_task_cache()
            task_ids = set()
            created, updated = 0, 0
            for todo in self._cached_todos:
                task = self._get_task(todo, task_by_uid)
                if not task:  # not found, creating it
                    task = self.datastore.task_factory(
                        todo.instance.vtodo.uid.value)
                    created += 1
                    log.debug('Creating task %r from %r', task, self)
                else:
                    updated += 1
                    log.debug('Creating task %r from %r', task, self)
                task_ids.add(task.get_id())
                self._populate_task(task, todo)
                self.datastore.push_task(task)
            log.info('%r: Created %d new task, %d existing ones from backend',
                     self, created, updated)

            # removing task we didn't see during listing
            all_tids = {task_id
                        for task_id in self.datastore.get_all_tasks()}
            deleted = 0
            for task_id in all_tids.difference(task_ids):
                deleted += 1
                self.datastore.request_task_deletion(task_id)
            log.info('%r: Deleted %d task absent from backend', self, deleted)

    @interruptible
    def set_task(self, task: Task) -> None:
        # TODO filter task, not syncing children task
        log.info('%r: set_task todo for %r', self, task)
        todo = self._get_todo(task=task)
        if todo:
            calendar = todo.parent
        else:
            calendar = self._get_calendar(task=task)
        calendar_url = str(calendar.url)
        with self._get_lock(calendar_url):
            if todo:  # found one, saving it
                for dav_key, get, __ in self._iter_translations(task):
                    if dav_key == 'uid':
                        continue  # do not override uid on update
                    todo.instance.vtodo.contents.pop(dav_key, None)
                    todo.instance.vtodo.add(dav_key).value = get()

                # updating dtstamp
                todo.instance.vtodo.contents.pop('dtstamp', None)
                todo.instance.vtodo.add('dtstamp').value = datetime.now()
                # updating sequence
                sequence = todo.instance.vtodo.contents.pop('sequence', '0')
                sequence = str(int(sequence) + 1)
                todo.instance.vtodo.add('sequence').value = sequence
                # saving new todo
                log.debug('%r: updating todo %r', self, todo)
                if log.isEnabledFor(logging.DEBUG):
                    log.debug(todo.instance.vtodo.serialize())
                todo.save()
            else:  # creating from task
                new_vtodo = self._task_to_new_vtodo(task)
                log.debug('%r: creating todo for %r', self, task)
                new_todo = calendar.add_todo(new_vtodo.serialize())
                self._todos_by_uid[calendar_url][new_todo.uid] = new_todo
                task.add_remote_id(self.get_id(), task.get_uuid())

    @interruptible
    def remove_task(self, tid: str) -> None:
        if not tid:
            return
        log.info('%r: removing todo for Task(%s)', self, tid)
        todo = self._todos_by_gtg_id.pop(tid, None)
        if todo:
            with self._get_lock(str(todo.parent.url)):
                uid = todo.instance.vtodo.uid.value
                # cleaning cache
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

    @classmethod
    def _task_to_new_vtodo(cls, task: Task) -> iCalendar:
        vcal = iCalendar()
        vcal.prodid.value = GTG_PRODID
        vtodo = vcal.add('vtodo')
        vtodo.add('sequence').value = "0"
        for dav_key, get, __ in cls._iter_translations(task):
            vtodo.add(dav_key).value = get()
        return vcal

    #
    # Utility methods
    #

    @staticmethod
    def _extract_from_todo(todo, key: str, default=None) -> str:
        value = todo.instance.vtodo.contents.get(key)
        if value:
            return value[0].value
        return default

    @staticmethod
    def _iter_translations(task: Task, with_uuid: bool = True):
        def get_date(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                if isinstance(result, Date):
                    return result.datetime
                return result
            return wrapper

        def set_only_if_not_none(func):
            @wraps(func)
            def wrapper(value):
                if value is not None:
                    return func(value)
            return wrapper
        yield 'summary', task.get_title, task.set_title
        yield 'description', task.get_text, task.set_text
        yield ('created',
               get_date(task.get_added_date),
               set_only_if_not_none(task.set_added_date))
        yield ('last-modified', get_date(task.get_modified),
               set_only_if_not_none(task.set_modified))
        yield ('due', get_date(task.get_due_date_constraint),
               set_only_if_not_none(task.set_due_date))
        yield ('completed', get_date(task.get_closed_date),
               set_only_if_not_none(task.set_closed_date))
        yield ('status',
               lambda: _GTG_TO_CALDAV_STATUS[task.get_status()],
               lambda status: task.set_status(
                   _CALDAV_TO_GTG_STATUS.get(status, Task.STA_ACTIVE)))
        yield GTG_ID_KEY, task.get_id, lambda tid: setattr(task, 'tid', tid)
        yield GTG_UID_KEY, task.get_uuid, task.set_uuid
        yield 'uid', task.get_uuid, task.set_uuid
        yield (GTG_START_KEY, task.get_start_date,
               set_only_if_not_none(task.set_start_date))
        yield ('percent-complete',
               lambda: ('100' if task.get_status() == Task.STA_DONE else '0'),
               lambda _: None)
        yield ('categories',
               lambda: [tag.replace('@', '', 1).replace('_', ' ')
                        for tag in task.get_tags_name()],
               lambda tags: task.set_only_these_tags(
                   "@%s" % tag.replace(' ', '_') for tag in tags or []))

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
        # if the todo has the task id registered, we look it up
        if task_id in self._todos_by_gtg_id:
            return self._todos_by_gtg_id[task_id]
        # if the uuid is the same for the todo and the task
        tuid = task.get_uuid()
        for calendar in self._dav_calendars:
            cal_url = str(calendar.url)
            if tuid in self._todos_by_uid[cal_url]:
                return self._todos_by_uid[cal_url][tuid]
        # if the task has remote id for that backend
        remote_id = task.get_remote_ids().get(self.get_id())
        for todo in self._cached_todos:
            vtodo = todo.instance.vtodo
            if remote_id and vtodo.uid.value == remote_id:
                return todo
            if (GTG_ID_KEY in vtodo.contents
                    and vtodo.contents[GTG_ID_KEY][0].value == task_id):
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
        tid = self._extract_from_todo(todo, GTG_ID_KEY)
        if tid:  # vtodo has a task id, requesting datastore with it
            return self.datastore.get_task(tid)
        # trying to look up todo through uuid
        task = cache_uid.get(todo.instance.vtodo.uid.value)
        if task:
            return task
        return cache_uid.get(self._extract_from_todo(todo, GTG_UID_KEY))

    def _get_calendar(self, task: Task) -> caldav.Calendar:
        calendar_url = task.get_attribute("calendar_url",
                                          namespace=self.get_namespace())
        calendar = self._calendars_by_url.get(calendar_url)
        if calendar:
            return calendar
        default_calendar_name = self._parameters['default-calendar-name']
        return self._calendars_by_name[default_calendar_name]

    def get_namespace(self):
        url = self._parameters['service-url']
        return f"caldav:{url}"

    def _populate_task(self, task, todo):
        """
        Copies the content of a VTODO in a Task
        """
        for dav_key, __, set_val in self._iter_translations(task):
            set_val(self._extract_from_todo(todo, dav_key, ''))

        # attributes
        task.set_attribute("url", str(todo.url),
                           namespace=self.get_namespace())
        task.set_attribute("calendar_url", str(todo.parent.url),
                           namespace=self.get_namespace())
        task.set_attribute("calendar_name", todo.parent.name,
                           namespace=self.get_namespace())

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
