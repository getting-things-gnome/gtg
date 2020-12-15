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

# features:
#  * registering task relation through RELATED-TO params        : OK
#     * handle percent complete                                 : OK
#     * ensure compatibility with tasks.org                     : OK
#  * push proper categories to dav                              : OK
#  * handle DAV collection switch (CREATE + DELETE)             : KO
#  * handle GTG task creation while DAV is updating             : OK
#  * support recurring events                                   : KO
#  * push proper task content                                   : KO

import logging
from collections import defaultdict
from datetime import datetime
from gettext import gettext as _

import caldav
from GTG.backends.backend_signals import BackendSignals
from GTG.backends.generic_backend import GenericBackend
from GTG.backends.periodic_import_backend import PeriodicImportBackend
from GTG.core.dates import LOCAL_TIMEZONE, Date
from GTG.core.interruptible import interruptible
from GTG.core.logger import log
from GTG.core.task import DisabledSyncCtx, Task
from vobject import iCalendar

DAV_TAG_PREFIX = 'DAV-'
DAV_IGNORE = {'last-modified',  # often updated alone by GTG
              'sequence',  # internal DAV value, only set by translator
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
            GenericBackend.PARAM_DEFAULT_VALUE: 15},
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

    #
    # Backend standard methods
    #

    def __init__(self, parameters):
        """
        See GenericBackend for an explanation of this function.
        Re-loads the saved state of the synchronization
        """
        super().__init__(parameters)
        self._dav_client = None
        self._cache = TodoCache()

    def initialize(self) -> None:
        super().initialize()
        self._dav_client = caldav.DAVClient(
            url=self._parameters['service-url'],
            username=self._parameters['username'],
            password=self._parameters['password'])

    @interruptible
    def do_periodic_import(self) -> None:
        with self.datastore.get_backend_mutex():
            self._do_periodic_import()

    @interruptible
    def set_task(self, task: Task) -> None:
        with DisabledSyncCtx(task, sync_on_exit=False):
            seq_value = SEQUENCE.get_gtg(task, self.namespace)
            SEQUENCE.write_gtg(task, seq_value + 1, self.namespace)
        if self._parameters["is-first-run"] or not self._cache.initialized:
            log.warning("not loaded yet, ignoring set_task")
            return
        with self.datastore.get_backend_mutex():
            self._set_task(task)

    @interruptible
    def remove_task(self, tid: str) -> None:
        if self._parameters["is-first-run"] or not self._cache.initialized:
            log.warning("not loaded yet, ignoring set_task")
            return
        if not tid:
            log.warning("no task id passed to remove_task call, ignoring")
            return
        with self.datastore.get_backend_mutex():
            self._remove_task(tid)

    #
    # real main methods
    #

    def _do_periodic_import(self) -> None:
        log.info("Running periodic import")
        start = datetime.now()
        self._refresh_calendar_list()
        # browsing calendars
        counts = {'created': 0, 'updated': 0, 'unchanged': 0, 'deleted': 0}
        for cal_url, calendar in self._cache.calendars:
            # retrieving todos and updating various cache
            log.info('Fetching todos from %r', cal_url)
            self._import_calendar_todos(calendar, start, counts)
        if log.isEnabledFor(logging.INFO):
            for key in counts:
                if counts.get(key):
                    log.info('LOCAL %s %d tasks', key, counts['created'])
        self._parameters["is-first-run"] = False
        self._cache.initialized = True

    def _set_task(self, task: Task) -> None:
        log.debug('set_task todo for %r', task.get_uuid())
        todo = self._get_todo(task=task)
        if todo:
            calendar = todo.parent
        else:
            calendar = self._get_calendar(task=task)
        if todo:  # found one, saving it
            if not Translator.should_sync(task, self.namespace, todo):
                log.debug('insufficient change, ignoring set_task call')
                return
            Translator.fill_vtodo(task, calendar.name, self.namespace,
                                  todo.instance.vtodo)
            # saving new todo
            log.info('SYNCING updating todo %r', todo)
            try:
                todo.save()
            except caldav.lib.error.DAVError:
                log.exception('Something went wrong while updating %r => %r',
                              task, todo)
        else:  # creating from task
            new_todo, new_vtodo = None, Translator.fill_vtodo(
                task, calendar.name, self.namespace)
            log.info('SYNCING creating todo for %r', task)
            try:
                new_todo = calendar.add_todo(new_vtodo.serialize())
            except caldav.lib.error.DAVError:
                log.exception('Something went wrong while creating %r => %r',
                              task, new_todo)
            uid = UID_FIELD.get_dav(todo=new_todo)
            self._cache.set_todo(new_todo, uid)

    def _remove_task(self, tid: str) -> None:
        log.info('SYNCING removing todo for Task(%s)', tid)
        todo = self._cache.get_todo(tid)
        if todo:
            # cleaning cache
            self._cache.del_todo(tid)
            try:  # deleting through caldav
                todo.delete()
            except caldav.lib.error.DAVError:
                log.exception('Something went wrong while deleting %r => %r',
                              tid, todo)
        else:
            log.error("Could not find todo for task(%s)", tid)

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
        seen_calendars_names = set()
        for calendar in principal.calendars():
            self._cache.set_calendar(calendar)
            seen_calendars_names.add(calendar.name)
        def_cal_name = self._parameters.get('default-calendar-name')
        if not def_cal_name or def_cal_name not in seen_calendars_names:
            self._notify_user_about_default_calendar()

    def _clean_task_missing_from_backend(self, uid: str,
                                         calendar_tasks: dict, counts: dict,
                                         import_started_on: datetime):
        task, do_delete = None, False
        task = calendar_tasks[uid]
        if import_started_on < task.get_added_date():
            return
        # if first run, we're getting all task, including completed
        # if we miss one, we delete it
        if not self._cache.initialized:
            do_delete = True
        # if cache is initialized, it's normal we missed completed
        # task, but we should have seen active ones
        elif task.get_status() == Task.STA_ACTIVE:
            calendar = self._get_calendar(task=task)
            if not calendar:
                log.warning("Couldn't find calendar for %r", task)
                return
            try:  # fetching missing todo from server
                calendar.todo_by_uid(uid)
            except caldav.lib.error.NotFoundError:
                do_delete = True
        if do_delete:  # the task was missing for a good reason
            counts['deleted'] += 1
            self._cache.del_todo(uid)
            self.datastore.request_task_deletion(uid)

    @staticmethod
    def _denorm_children_on_vtodos(todos: list):
        # NOTE: GTG.core.task.Task.set_parent seems buggy so we can't use it
        # Default caldav specs usually only specifies parent, here we use it
        # to mark all the children
        children_by_parent = defaultdict(list)
        for todo in todos:
            parent = PARENT_FIELD.get_dav(todo)
            if parent:
                children_by_parent[parent[0]].append(todo)
        todos_by_uid = {UID_FIELD.get_dav(todo): todo for todo in todos}
        for uid, children in children_by_parent.items():
            if uid not in todos_by_uid:
                continue
            vtodo = todos_by_uid[uid].instance.vtodo
            children.sort(key=lambda v: str(SORT_ORDER.get_dav(v)) or '')
            CHILDREN_FIELD.write_dav(vtodo, [UID_FIELD.get_dav(child)
                                             for child in children])

    def _import_calendar_todos(self, calendar: iCalendar,
                               import_started_on: datetime, counts: dict):
        todos = calendar.todos(include_completed=not self._cache.initialized)
        todo_uids = {UID_FIELD.get_dav(todo) for todo in todos}

        # browsing all task linked to current calendar,
        # removing missed ones we don't see in fetched todos
        calendar_tasks = dict(self._get_calendar_tasks(calendar))
        for uid in set(calendar_tasks).difference(todo_uids):
            self._clean_task_missing_from_backend(uid, calendar_tasks, counts,
                                                  import_started_on)

        self._denorm_children_on_vtodos(todos)

        known_todos = set()  # type: set
        for todo in self.__sort_todos(todos, known_todos):
            uid = UID_FIELD.get_dav(todo)
            self._cache.set_todo(todo, uid)
            # Updating and creating task according to todos
            task = self.datastore.get_task(uid)
            if not task:  # not found, creating it
                task = self.datastore.task_factory(uid)
                Translator.fill_task(todo, task, self.namespace)
                self.datastore.push_task(task)
                counts['created'] += 1
            else:
                task_seq = SEQUENCE.get_gtg(task, self.namespace)
                todo_seq = SEQUENCE.get_dav(todo)
                if task_seq >= todo_seq:
                    counts['unchanged'] += 1
                    continue
                Translator.fill_task(todo, task, self.namespace)
                counts['updated'] += 1
            if __debug__:
                if Translator.should_sync(task, self.namespace, todo):
                    log.warning("Shouldn't be diff for %r", uid)

    def __sort_todos(self, todos: list, known_todos: set, max_depth=500):
        loop_nb = 0
        while len(known_todos) < len(todos):
            loop_nb += 1
            for todo in todos:
                uid = UID_FIELD.get_dav(todo)
                if uid in known_todos:
                    continue
                parents = PARENT_FIELD.get_dav(todo)
                if (not parents  # no parent mean no relationship on build
                        or parents[0] in known_todos  # browsed relationship
                        or self.datastore.get_task(uid)):  # already known uid
                    yield todo
                    known_todos.add(uid)
            if loop_nb >= max_depth:
                log.error("Too deep, %r recursion isn't supported", max_depth)
                break

    def _get_calendar_tasks(self, calendar: iCalendar):
        """Getting all tasks that has the calendar tag"""
        for uid in self.datastore.get_all_tasks():
            task = self.datastore.get_task(uid)
            if CATEGORIES.has_calendar_tag(task, calendar):
                yield uid, task

    #
    # Utility methods
    #

    @staticmethod
    def _update_cache(new_values: dict, cache: dict) -> None:
        for key in new_values:
            if key not in cache:
                cache[key] = new_values[key]
        for key in list(cache):
            if key not in new_values:
                cache.pop(key)

    def _get_todo(self, task: Task) -> caldav.Todo:
        return self._cache.get_todo(UID_FIELD.get_gtg(task))

    def _get_calendar(self, task: Task) -> caldav.Calendar:
        # lookup by UID
        for uid in task.get_id(), task.get_uuid():
            todo = self._cache.get_todo(uid)
            if todo and getattr(todo, 'parent', None):
                return todo.parent
        calendar = None
        # lookup by task attributes
        cname = task.get_attribute('calendar_name', namespace=self.namespace)
        curl = task.get_attribute("calendar_url", namespace=self.namespace)
        if curl or cname:
            calendar = self._cache.get_calendar(name=cname, url=curl)
        # lookup by task
        if not calendar:
            for tag in CATEGORIES.get_gtg(task):
                calendar = self._cache.get_calendar(name=tag)
                if calendar:
                    break
        if calendar:
            return calendar
        default_calendar_name = self._parameters['default-calendar-name']
        return self._cache.get_calendar(name=default_calendar_name)

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
    """ Basic field representation.

    Allows to extract neutral values from GTG Task (attributes in integer or
    tags without '@' for example) and from vTodo (translated datetime).
    """

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
        "Extract value from GTG.core.task.Task according to specified getter"
        return getattr(task, self.task_get_func_name)()

    def clean_dav(self, todo: iCalendar):
        """Will remove existing conflicting value from vTodo object"""
        todo.contents.pop(self.dav_name, None)

    def write_dav(self, vtodo: iCalendar, value):
        """Will clean and write new value to vTodo object"""
        self.clean_dav(vtodo)
        vtodo.add(self.dav_name).value = value

    def set_dav(self, task: Task, vtodo: iCalendar, namespace: str) -> None:
        """Will extract value from GTG.core.task.Task and set it to vTodo"""
        value = self.get_gtg(task, namespace)
        if self._is_value_allowed(value):
            self.write_dav(vtodo, value)

    def get_dav(self, todo=None, vtodo=None):
        "Extract value from vTodo according to specified dav key name"
        if todo:
            vtodo = todo.instance.vtodo
        value = vtodo.contents.get(self.dav_name)
        if value:
            return value[0].value

    def write_gtg(self, task: Task, value, namespace: str = None):
        """Will write new value to GTG.core.task.Task"""
        return getattr(task, self.task_set_func_name)(value)

    def set_gtg(self, todo: iCalendar, task: Task,
                namespace: str = None) -> None:
        """Will extract value from vTodo and set it to GTG.core.task.Task"""
        if not self.task_set_func_name:
            return
        value = self.get_dav(todo)
        if self._is_value_allowed(value):
            self.write_gtg(task, value, namespace)

    def __repr__(self):
        return "<%s(%r)>" % (self.__class__.__name__, self.dav_name)

    @classmethod
    def _browse_subtasks(cls, task: Task):
        yield task
        for subtask in task.get_subtasks():
            yield from cls._browse_subtasks(subtask)


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
        if not value.tzinfo:  # assumring is LOCAL_TIMEZONEd
            value = value.replace(tzinfo=LOCAL_TIMEZONE)
        value = (value - value.utcoffset()).replace(tzinfo=None)
        return super().write_dav(todo, value)

    def get_dav(self, todo=None, vtodo=None):
        """Transforming to local naive,
        if original value MAY be naive and IS assuming UTC"""
        value = super().get_dav(todo, vtodo)
        if not isinstance(value, datetime):
            try:
                value = Date(value).datetime
            except ValueError:
                log.error("Coudln't translate value %r", value)
                return
        if value.tzinfo:  # if timezoned, translate to UTC
            value = value - value.utcoffset()
        value = value.replace(tzinfo=LOCAL_TIMEZONE)  # zoning to local
        value = value + value.utcoffset()  # adding local offset
        return self._normalize(value)  # return naive

    def get_gtg(self, task: Task, namespace: str = None):
        return self._normalize(super().get_gtg(task, namespace))


class Status(Field):
    DEFAULT_STATUS = (Task.STA_ACTIVE, 'NEEDS-ACTIONS')
    _status_mapping = ((Task.STA_ACTIVE, 'NEEDS-ACTION'),
                       (Task.STA_ACTIVE, 'IN-PROCESS'),
                       (Task.STA_DISMISSED, 'CANCELLED'),
                       (Task.STA_DONE, 'COMPLETED'))

    def _translate(self, gtg_value=None, dav_value=None):
        for gtg_status, dav_status in self._status_mapping:
            if gtg_value == gtg_status or dav_value == dav_status:
                return gtg_status, dav_status
        return self.DEFAULT_STATUS

    def write_dav(self, vtodo: iCalendar, value):
        self.clean_dav(vtodo)
        vtodo.add(self.dav_name).value = value

    def get_gtg(self, task: Task, namespace: str = None) -> str:
        active, done = 0, 0
        for task in self._browse_subtasks(task):
            if task.get_status() == Task.STA_ACTIVE:
                active += 1
            elif task.get_status() == Task.STA_DONE:
                done += 1
            if active and done:
                return 'IN-PROCESS'
        if active:
            return 'NEEDS-ACTIONS'
        if done:
            return 'COMPLETED'
        return 'CANCELLED'

    def get_dav(self, todo=None, vtodo=None) -> str:
        return self._translate(dav_value=super().get_dav(todo, vtodo))[1]

    def write_gtg(self, task: Task, value, namespace: str = None):
        value = self._translate(dav_value=value, gtg_value=value)[0]
        return super().write_gtg(task, value, namespace)


class PercentComplete(Field):

    def get_gtg(self, task: Task, namespace: str = None) -> str:
        total_cnt, done_cnt = 0, 0
        for task in self._browse_subtasks(task):
            if task.get_status() != Task.STA_DISMISSED:
                total_cnt += 1
                if task.get_status() == Task.STA_DONE:
                    done_cnt += 1
        if total_cnt:
            return str(int(100 * done_cnt / total_cnt))
        return '0'


class Categories(Field):

    @staticmethod
    def to_tag(category, prefix=''):
        return '@%s%s' % (prefix, category.replace(' ', '_'))

    def get_gtg(self, task: Task, namespace: str = None) -> list:
        return [tag_name.replace('@', '', 1).replace('_', ' ')
                for tag_name in super().get_gtg(task)
                if not tag_name.startswith('@' + DAV_TAG_PREFIX)]

    def get_dav(self, todo=None, vtodo=None):
        if todo:
            vtodo = todo.instance.vtodo
        categories = []
        for sub_value in vtodo.contents.get(self.dav_name, []):
            for category in sub_value.value:
                if self._is_value_allowed(category):
                    categories.append(category)
        return categories

    def write_dav(self, vtodo: iCalendar, categories):
        super().write_dav(vtodo, [cat for cat in categories
                                  if not cat.startswith(DAV_TAG_PREFIX)])

    def set_gtg(self, todo: iCalendar, task: Task,
                namespace: str = None) -> None:
        remote_tags = [self.to_tag(categ) for categ in self.get_dav(todo)]
        local_tags = set(tag_name for tag_name in super().get_gtg(task))
        for to_add in set(remote_tags).difference(local_tags):
            task.add_tag(to_add)
        for to_delete in local_tags.difference(remote_tags):
            task.remove_tag(to_delete)
        task.tags.sort(key=remote_tags.index)

    def get_calendar_tag(self, calendar) -> str:
        return self.to_tag(calendar.name, DAV_TAG_PREFIX)

    def has_calendar_tag(self, task, calendar):
        return self.get_calendar_tag(calendar) in task.get_tags_name()


class AttributeField(Field):

    def get_gtg(self, task: Task, namespace: str = None) -> str:
        return task.get_attribute(self.dav_name, namespace=namespace)

    def write_gtg(self, task: Task, value, namespace: str = None):
        task.set_attribute(self.dav_name, value, namespace=namespace)

    def set_gtg(self, todo: iCalendar, task: Task,
                namespace: str = None) -> None:
        value = self.get_dav(todo)
        if self._is_value_allowed(value):
            self.write_gtg(task, value, namespace)


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
            self.write_dav(vtodo, str(self.get_gtg(task, namespace)))
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
        return super().get_dav(todo, vtodo) or ''

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


class RelatedTo(Field):
    # when related-to reltype isn't specified, assuming :
    DEFAULT_RELTYPE = 'PARENT'

    def __init__(self, *args, task_remove_func_name: str = None, reltype: str,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.task_remove_func_name = task_remove_func_name
        self.reltype = reltype.upper()

    def _fit_reltype(self, sub_value):
        reltype = sub_value.params.get('RELTYPE') or [self.DEFAULT_RELTYPE]
        return len(reltype) == 1 and reltype[0] == self.reltype

    def clean_dav(self, vtodo: iCalendar):
        value = vtodo.contents.get(self.dav_name)
        if value:
            index_to_remove = []
            for index, sub_value in enumerate(value):
                if self._fit_reltype(sub_value):
                    index_to_remove.append(index)
            for index in sorted(index_to_remove, reverse=True):
                value.pop(index)

    def write_dav(self, vtodo: iCalendar, related_uids):
        self.clean_dav(vtodo)
        for related_uid in related_uids:
            related = vtodo.add(self.dav_name)
            related.value = related_uid
            related.params['RELTYPE'] = [self.reltype]

    def get_dav(self, todo=None, vtodo=None):
        if todo:
            vtodo = todo.instance.vtodo
        value = vtodo.contents.get(self.dav_name)
        result = []
        if value:
            for sub_value in value:
                if self._fit_reltype(sub_value):
                    result.append(sub_value.value)
        return result

    def set_gtg(self, todo: iCalendar, task: Task,
                namespace: str = None) -> None:
        if self.get_dav(todo) == self.get_gtg(task, namespace):
            return  # do not edit if equal
        target_uids = self.get_dav(todo)
        gtg_uids = set(self.get_gtg(task, namespace))
        for value in set(target_uids).difference(gtg_uids):
            if not self.write_gtg(task, value, namespace):
                log.error('FAILED writing Task.%s(%r, %r)',
                          self.task_set_func_name, task, value)
        if self.task_remove_func_name:
            for value in gtg_uids.difference(target_uids):
                getattr(task, self.task_remove_func_name)(value)
        task.children.sort(key=target_uids.index)

    def __repr__(self):
        return "<%s(%r, %r)>" % (self.__class__.__name__,
                                 self.reltype, self.dav_name)


class OrderField(Field):

    def get_gtg(self, task: Task, namespace: str = None):
        parents = task.get_parents()
        if not parents or not parents[0]:
            return
        parent = task.req.get_task(parents[0])
        uid = UID_FIELD.get_gtg(task, namespace)
        return parent.get_child_index(uid)

    def set_dav(self, task: Task, vtodo: iCalendar, namespace: str) -> None:
        parent_index = self.get_gtg(task, namespace)
        if parent_index is not None:
            return self.write_dav(vtodo, parent_index)


UID_FIELD = Field('uid', 'get_uuid', 'set_uuid')
SEQUENCE = Sequence('sequence', '<fake attribute>', '')
CATEGORIES = Categories('categories', 'get_tags_name', 'set_tags')
PARENT_FIELD = RelatedTo('related-to', 'get_parents', 'set_parent',
                         task_remove_func_name='remove_parent',
                         reltype='parent')
CHILDREN_FIELD = RelatedTo('related-to', 'get_children', 'add_child',
                           task_remove_func_name='remove_child',
                           reltype='child')
SORT_ORDER = OrderField('x-apple-sort-order', '', '')


class Translator:
    GTG_PRODID = "-//Getting Things Gnome//CalDAV Backend//EN"
    DTSTAMP_FIELD = DateField('dtstamp', '', '')
    fields = [Field('summary', 'get_title', 'set_title'),
              Description('description', 'get_excerpt', 'set_text'),
              DateField('due', 'get_due_date_constraint', 'set_due_date'),
              DateField('completed', 'get_closed_date', 'set_closed_date'),
              DateField('dtstart', 'get_start_date', 'set_start_date'),
              Status('status', 'get_status', 'set_status'),
              PercentComplete('percent-complete', 'get_status', ''),
              SEQUENCE, UID_FIELD, CATEGORIES, CHILDREN_FIELD,
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
        # always write a DTSTAMP field to the `now`
        cls.DTSTAMP_FIELD.write_dav(vtodo, datetime.now(LOCAL_TIMEZONE))
        for field in cls.fields:
            if field.dav_name == 'uid' and UID_FIELD.get_dav(vtodo=vtodo):
                # not overriding if already set from cache
                continue
            field.set_dav(task, vtodo, namespace)
        # NOTE: discarding related-to parent from sync down
        # due to bug on set_parent
        PARENT_FIELD.set_dav(task, vtodo, namespace)
        SORT_ORDER.set_dav(task, vtodo, namespace)
        return vcal

    @classmethod
    def fill_task(cls, todo: iCalendar, task: Task, namespace: str):
        nmspc = {'namespace': namespace}
        with DisabledSyncCtx(task):
            for field in cls.fields:
                field.set_gtg(todo, task, **nmspc)
            task.set_attribute("url", str(todo.url), **nmspc)
            task.set_attribute("calendar_url", str(todo.parent.url), **nmspc)
            task.set_attribute("calendar_name", todo.parent.name, **nmspc)
            if not CATEGORIES.has_calendar_tag(task, todo.parent):
                task.add_tag(CATEGORIES.get_calendar_tag(todo.parent))
        return task

    @classmethod
    def changed_attrs(cls, task: Task, namespace: str, todo=None, vtodo=None):
        for field in cls.fields:
            task_value = field.get_gtg(task, namespace)
            todo_value = field.get_dav(todo, vtodo)
            if todo_value != task_value:
                yield field, task_value, todo_value

    @classmethod
    def should_sync(cls, task: Task, namespace: str, todo=None, vtodo=None):
        fields = cls.changed_attrs(task, namespace, todo, vtodo)
        if log.isEnabledFor(logging.DEBUG):
            fields = list(fields)
            for field, task_v, todo_v in fields:
                log.debug('changed %r Task(%r) != vTodo(%r)',
                          field, task_v, todo_v)
        for field, __, __ in fields:
            if field.dav_name not in DAV_IGNORE:
                return True
        return False


class TodoCache:

    def __init__(self):
        self.calendars_by_name = {}
        self.calendars_by_url = {}
        self.todos_by_uid = {}
        self._initialized = False

    @property
    def initialized(self):
        return self._initialized

    @initialized.setter
    def initialized(self, value):
        if not value:
            raise ValueError("Can't uninitialize")
        self._initialized = True

    def get_calendar(self, name=None, url=None):
        assert name or url
        if name is not None:
            calendar = self.calendars_by_name.get(name)
            if calendar:
                return calendar
        if url is not None:
            calendar = self.calendars_by_name.get(url)
            if calendar:
                return calendar
        log.error('no calendar for %r or %r', name, url)

    @property
    def calendars(self):
        for url, calendar in self.calendars_by_url.items():
            yield url, calendar

    def set_calendar(self, calendar):
        self.calendars_by_url[str(calendar.url)] = calendar
        self.calendars_by_name[calendar.name] = calendar

    def get_todo(self, uid):
        return self.todos_by_uid.get(uid)

    def set_todo(self, todo, uid):
        self.todos_by_uid[uid] = todo

    def del_todo(self, uid):
        self.todos_by_uid.pop(uid, None)
