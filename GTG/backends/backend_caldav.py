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
import re
from collections import defaultdict
from datetime import date, datetime
from gettext import gettext as _
from hashlib import md5

import caldav
from dateutil.tz import UTC
from GTG.backends.backend_signals import BackendSignals
from GTG.backends.generic_backend import GenericBackend
from GTG.backends.periodic_import_backend import PeriodicImportBackend
from GTG.core.dates import LOCAL_TIMEZONE, Accuracy, Date
from GTG.core.interruptible import interruptible
from GTG.core.task import DisabledSyncCtx, Task
from vobject import iCalendar

logger = logging.getLogger(__name__)
# found elsewhere, should be factorized
TAG_REGEX = re.compile(r'\B@\w+[-_\w]*')
MAX_CALENDAR_DEPTH = 500
DAV_TAG_PREFIX = 'DAV_'

# Set of fields whose change alone won't trigger a sync up
DAV_IGNORE = {'last-modified',  # often updated alone by GTG
              'sequence',  # internal DAV value, only set by translator
              'percent-complete',  # calculated on subtask and status
              'completed',  # GTG date is constrained
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
        if self._parameters["is-first-run"] or not self._cache.initialized:
            logger.warning("not loaded yet, ignoring set_task")
            return
        with self.datastore.get_backend_mutex():
            return self._set_task(task)

    @interruptible
    def remove_task(self, tid: str) -> None:
        if self._parameters["is-first-run"] or not self._cache.initialized:
            logger.warning("not loaded yet, ignoring set_task")
            return
        if not tid:
            logger.warning("no task id passed to remove_task call, ignoring")
            return
        with self.datastore.get_backend_mutex():
            return self._remove_task(tid)

    #
    # real main methods
    #

    def _do_periodic_import(self) -> None:
        logger.info("Running periodic import")
        start = datetime.now()
        self._refresh_calendar_list()
        # browsing calendars
        counts = {'created': 0, 'updated': 0, 'unchanged': 0, 'deleted': 0}
        for cal_url, calendar in self._cache.calendars:
            # retrieving todos and updating various cache
            logger.info('Fetching todos from %r', cal_url)
            self._import_calendar_todos(calendar, start, counts)
        if logger.isEnabledFor(logging.INFO):
            for key in counts:
                if counts.get(key):
                    logger.info('LOCAL %s %d tasks', key, counts[key])
        self._parameters["is-first-run"] = False
        self._cache.initialized = True

    def _set_task(self, task: Task) -> None:
        logger.debug('set_task todo for %r', task.get_uuid())
        with DisabledSyncCtx(task, sync_on_exit=False):
            seq_value = SEQUENCE.get_gtg(task, self.namespace)
            SEQUENCE.write_gtg(task, seq_value + 1, self.namespace)
        todo, calendar = self._get_todo_and_calendar(task)
        if not calendar:
            logger.info("%r has no calendar to be synced with", task)
            return
        if todo and todo.parent.url != calendar.url:  # switch calendar
            self._remove_todo(UID_FIELD.get_dav(todo), todo)
            self._create_todo(task, calendar)
        elif todo:  # found one, saving it
            if not Translator.should_sync(task, self.namespace, todo):
                logger.debug('insufficient change, ignoring set_task call')
                return
            # updating vtodo content
            Translator.fill_vtodo(task, calendar.name, self.namespace,
                                  todo.instance.vtodo)
            logger.info('SYNCING updating todo %r', todo)
            try:
                todo.save()
            except caldav.lib.error.DAVError:
                logger.exception('Something went wrong while updating '
                                 '%r => %r', task, todo)
        else:  # creating from task
            self._create_todo(task, calendar)

    def _remove_task(self, tid: str) -> None:
        todo = self._cache.get_todo(tid)
        if todo:
            self._remove_todo(tid, todo)
        else:
            logger.error("Could not find todo for task(%s)", tid)

    #
    # Dav functions
    #

    def _create_todo(self, task: Task, calendar: iCalendar):
        logger.info('SYNCING creating todo for %r', task)
        new_todo, new_vtodo = None, Translator.fill_vtodo(
            task, calendar.name, self.namespace)
        try:
            new_todo = calendar.add_todo(new_vtodo.serialize())
        except caldav.lib.error.DAVError:
            logger.exception('Something went wrong while creating '
                             '%r => %r', task, new_todo)
            return
        uid = UID_FIELD.get_dav(todo=new_todo)
        self._cache.set_todo(new_todo, uid)

    def _remove_todo(self, uid: str, todo: iCalendar) -> None:
        logger.info('SYNCING removing todo for Task(%s)', uid)
        self._cache.del_todo(uid)  # cleaning cache
        try:  # deleting through caldav
            todo.delete()
        except caldav.lib.error.DAVError:
            logger.exception('Something went wrong while deleting %r => %r',
                             uid , todo)

    def _refresh_calendar_list(self):
        """Will browse calendar list available after principal call and cache
        them"""
        try:
            principal = self._dav_client.principal()
        except caldav.lib.error.AuthorizationError as error:
            message = _(
                "You need a correct login to CalDAV"
                "Configure CalDAV with login information. Error:"
            )
            BackendSignals().interaction_requested(
                self.get_id(), "%s %r" % (message, error),
                BackendSignals().INTERACTION_INFORM, "on_continue_clicked")
            raise error
        for calendar in principal.calendars():
            self._cache.set_calendar(calendar)

    def _clean_task_missing_from_backend(self, uid: str,
                                         calendar_tasks: dict, counts: dict,
                                         import_started_on: datetime):
        """For a given UID will decide if we remove it from GTG or ignore the
        fact that it's missing"""
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
            __, calendar = self._get_todo_and_calendar(task)
            if not calendar:
                logger.warning("Couldn't find calendar for %r", task)
                return
            try:  # fetching missing todo from server
                todo = calendar.todo_by_uid(uid)
            except caldav.lib.error.NotFoundError:
                do_delete = True
            else:
                result = self._update_task(task, todo, force=True)
                counts[result] += 1
                return
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

        for todo in self.__sort_todos(todos):
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
                result = self._update_task(task, todo)
                counts[result] += 1
            if __debug__:
                if Translator.should_sync(task, self.namespace, todo):
                    logger.warning("Shouldn't be diff for %r", uid)

    def _update_task(self, task: Task, todo: iCalendar, force: bool = False):
        if not force:
            task_seq = SEQUENCE.get_gtg(task, self.namespace)
            todo_seq = SEQUENCE.get_dav(todo)
            if task_seq >= todo_seq:
                return 'unchanged'
        Translator.fill_task(todo, task, self.namespace)
        return 'updated'

    def __sort_todos(self, todos: list, max_depth: int = 500):
        """For a given list of todos, will return first the one without parent
        and then go deeper in the tree by browsing the tree."""
        loop = 0
        known_todos = set()  # type: set
        while len(known_todos) < len(todos):
            loop += 1
            for todo in todos:
                uid = UID_FIELD.get_dav(todo)
                if uid in known_todos:
                    continue
                parents = PARENT_FIELD.get_dav(todo)
                if (not parents  # no parent mean no relationship on build
                        or parents[0] in known_todos  # already known parent
                        or self.datastore.get_task(uid)):  # already known uid
                    yield todo
                    known_todos.add(uid)
            if loop >= MAX_CALENDAR_DEPTH:
                logger.error("Too deep, %dth recursion isn't allowed", loop)
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

    def _get_todo_and_calendar(self, task: Task):
        """For a given task, try to get the todo out of the cache and figures
        out its calendar if one is linked to it"""
        todo, calendar = self._cache.get_todo(UID_FIELD.get_gtg(task)), None
        # lookup by task
        for __, calendar in self._cache.calendars:
            if CATEGORIES.has_calendar_tag(task, calendar):
                logger.debug('Found from task tag %r and %r',
                                todo, calendar)
                return todo, calendar
        cname = task.get_attribute('calendar_name', namespace=self.namespace)
        curl = task.get_attribute("calendar_url", namespace=self.namespace)
        if curl or cname:
            calendar = self._cache.get_calendar(name=cname, url=curl)
            if calendar:
                logger.debug('Found from task attr %r and %r', todo, calendar)
                return todo, calendar
        if todo and getattr(todo, 'parent', None):
            logger.debug('Found from todo %r and %r', todo, todo.parent)
            return todo, todo.parent
        return None, None

    @property
    def namespace(self):
        return "caldav:%s" % self._parameters['service-url']


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

    def clean_dav(self, vtodo: iCalendar):
        """Will remove existing conflicting value from vTodo object"""
        vtodo.contents.pop(self.dav_name, None)

    def write_dav(self, vtodo: iCalendar, value):
        """will clean and write new value to vtodo object"""
        self.clean_dav(vtodo)
        vtodo_val = vtodo.add(self.dav_name)
        vtodo_val.value = value
        return vtodo_val

    def set_dav(self, task: Task, vtodo: iCalendar, namespace: str) -> None:
        """Will extract value from GTG.core.task.Task and set it to vTodo"""
        value = self.get_gtg(task, namespace)
        if self._is_value_allowed(value):
            self.write_dav(vtodo, value)
        else:
            self.clean_dav(vtodo)

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

    def is_equal(self, task: Task, namespace: str, todo=None, vtodo=None):
        assert todo is not None or vtodo is not None
        dav = self.get_dav(todo, vtodo)
        gtg = self.get_gtg(task, namespace)
        if dav != gtg:
            logger.debug('%r has differing values (DAV) %r!=%r (GTG)',
                         self, gtg, dav)
            return False
        return True

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
    FUZZY_MARK = 'GTGFUZZY'

    def __init__(self, dav_name: str,
                 task_get_func_name: str, task_set_func_name: str):
        super().__init__(
            dav_name, task_get_func_name, task_set_func_name,
            ['', None, 'None', Date.no_date()])

    @staticmethod
    def _normalize(value):
        try:
            if value.year == 9999:
                return None
            if getattr(value, 'microsecond'):
                value = value.replace(microsecond=0)
        except AttributeError:
            pass
        return value

    @staticmethod
    def _get_dt_for_dav_writing(value):
        if isinstance(value, Date):
            if value.accuracy is Accuracy.fuzzy:
                return str(value), value.dt_by_accuracy(Accuracy.date)
            if value.accuracy in {Accuracy.timezone, Accuracy.datetime,
                                  Accuracy.date}:
                return '', value.dt_value
        return '', value

    def write_dav(self, vtodo: iCalendar, value):
        "Writing datetime as UTC naive"
        fuzzy_value, value = self._get_dt_for_dav_writing(value)
        if isinstance(value, datetime):
            value = self._normalize(value)
            if not value.tzinfo:  # considering naive is local tz
                value = value.replace(tzinfo=LOCAL_TIMEZONE)
            if value.tzinfo != UTC:  # forcing UTC for value to write on dav
                value = (value - value.utcoffset()).replace(tzinfo=UTC)
        vtodo_val = super().write_dav(vtodo, value)
        if isinstance(value, date) and not isinstance(value, datetime):
            vtodo_val.params['VALUE'] = ['DATE']
        if fuzzy_value:
            vtodo_val.params[self.FUZZY_MARK] = [fuzzy_value]
        return vtodo_val

    def get_dav(self, todo=None, vtodo=None):
        """Transforming to local naive,
        if original value MAY be naive and IS assuming UTC"""
        value = super().get_dav(todo, vtodo)
        if todo:
            vtodo = todo.instance.vtodo
        todo_value = vtodo.contents.get(self.dav_name)
        if todo_value and todo_value[0].params.get(self.FUZZY_MARK):
            return Date(todo_value[0].params[self.FUZZY_MARK][0])
        if isinstance(value, (date, datetime)):
            value = self._normalize(value)
        try:
            return Date(value)
        except ValueError:
            logger.error("Coudln't translate value %r", value)
            return Date.no_date()

    def get_gtg(self, task: Task, namespace: str = None):
        gtg_date = super().get_gtg(task, namespace)
        if isinstance(gtg_date, Date):
            if gtg_date.accuracy in {Accuracy.date, Accuracy.timezone,
                                     Accuracy.datetime}:
                return Date(self._normalize(gtg_date.dt_value))
            return gtg_date
        return Date(self._normalize(gtg_date))


class UTCDateTimeField(DateField):

    @staticmethod
    def _get_dt_for_dav_writing(value):
        if isinstance(value, Date):
            if value.accuracy is Accuracy.timezone:
                return '', value.dt_value
            if value.accuracy is Accuracy.fuzzy:
                return str(value), value.dt_by_accuracy(Accuracy.timezone)
        else:
            value = Date(value)
        return '', value.dt_by_accuracy(Accuracy.timezone)


class Status(Field):
    DEFAULT_STATUS = (Task.STA_ACTIVE, 'NEEDS-ACTION')
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
        for subtask in self._browse_subtasks(task):
            if subtask.get_status() == Task.STA_ACTIVE:
                active += 1
            elif subtask.get_status() == Task.STA_DONE:
                done += 1
            if active and done:
                return 'IN-PROCESS'
        if active:
            return 'NEEDS-ACTION'
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
        for subtask in self._browse_subtasks(task):
            if subtask.get_status() != Task.STA_DISMISSED:
                total_cnt += 1
                if subtask.get_status() == Task.STA_DONE:
                    done_cnt += 1
        if total_cnt:
            return str(int(100 * done_cnt / total_cnt))
        return '0'


class Categories(Field):
    CAT_SPACE = '_'

    @classmethod
    def to_tag(cls, category, prefix=''):
        return '%s%s' % (prefix, category.replace(' ', cls.CAT_SPACE))

    def get_gtg(self, task: Task, namespace: str = None) -> list:
        return [tag_name.lstrip('@').replace(self.CAT_SPACE, ' ')
                for tag_name in super().get_gtg(task)
                if not tag_name.lstrip('@').startswith(DAV_TAG_PREFIX)]

    def get_dav(self, todo=None, vtodo=None):
        if todo:
            vtodo = todo.instance.vtodo
        categories = []
        for sub_value in vtodo.contents.get(self.dav_name, []):
            for category in sub_value.value:
                if self._is_value_allowed(category):
                    categories.append(category)
        return categories

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
    HASH_PARAM = 'GTGCNTMD5'
    XML_TAGS = ['<content>', '</content>', '<tag>', '</tag>']

    @staticmethod
    def _get_content_hash(content: str) -> str:
        return md5(content.encode('utf8')).hexdigest()

    def get_dav(self, todo=None, vtodo=None) -> tuple:
        if todo:
            vtodo = todo.instance.vtodo
        desc = vtodo.contents.get(self.dav_name)
        if desc:
            hash_val = desc[0].params.get(self.HASH_PARAM)
            hash_val = hash_val[0] if hash_val else None
            return hash_val, desc[0].value
        return None, ''

    def get_gtg(self, task: Task, namespace: str = None) -> tuple:
        description = self._extract_plain_text(task)
        return self._get_content_hash(description), description

    def is_equal(self, task: Task, namespace: str, todo=None, vtodo=None):
        gtg_hash, gtg_value = self.get_gtg(task, namespace)
        dav_hash, dav_value = self.get_dav(todo, vtodo)
        if dav_hash == gtg_hash:
            logger.debug('%r calculated hash matches', self)
            return True
        if gtg_value == dav_value:
            logger.debug('%r matching values', self)
            return True
        logger.debug('%r differing (%r!=%r) and (%r!=%r)',
                     self, gtg_hash, dav_hash, gtg_value, dav_value)
        return False

    def write_gtg(self, task: Task, value, namespace: str = None):
        hash_, text = value
        if hash_ and hash_ == self._get_content_hash(task.get_text()):
            logger.debug('not writing %r from vtodo, hash matches', task)
            return
        return super().write_gtg(task, text)

    @classmethod
    def __clean_first_line(cls, line):
        """Removing tags and commas after them from first line of content"""
        new_line = ''
        for split in TAG_REGEX.split(line):
            if split is None:
                continue
            if split.startswith(','):  # removing commas
                split = split[1:]
            if split.strip():
                if new_line:
                    new_line += ' '
                new_line += split.strip()
        return new_line

    def _extract_plain_text(self, task: Task) -> str:
        """Will extract plain text from task content, replacing subtask
        referenced in the text by their proper titles"""
        result, content = '', task.get_text()
        for line_no, line in enumerate(content.splitlines()):
            for tag in self.XML_TAGS:
                while tag in line:
                    line = line.replace(tag, '')

            if line_no == 0:  # is first line, striping all tags on first line
                new_line = self.__clean_first_line(line)
                if new_line:
                    result += new_line + '\n'
            elif line.startswith('{!') and line.endswith('!}'):
                subtask = task.req.get_task(line[2:-2].strip())
                if not subtask:
                    continue
                result += '[%s] %s\n' % (
                    'x' if subtask.get_status() == Task.STA_DONE else ' ',
                    subtask.get_title())
            else:
                result += line.strip() + '\n'
        return result.strip()

    def write_dav(self, vtodo: iCalendar, value: tuple):
        hash_, content = value
        vtodo_val = super().write_dav(vtodo, content)
        vtodo_val.params[self.HASH_PARAM] = [hash_]
        return vtodo_val


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

    def write_dav(self, vtodo: iCalendar, value):
        self.clean_dav(vtodo)
        for related_uid in value:
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

    @staticmethod
    def __sort_key(uids):
        def wrap(uid):
            if uid not in uids:
                return 0
            return uids.index(uid)
        return wrap

    def set_gtg(self, todo: iCalendar, task: Task,
                namespace: str = None) -> None:
        if self.get_dav(todo) == self.get_gtg(task, namespace):
            return  # do not edit if equal
        target_uids = self.get_dav(todo)
        gtg_uids = set(self.get_gtg(task, namespace))
        for value in set(target_uids).difference(gtg_uids):
            if not self.write_gtg(task, value, namespace):
                logger.error('FAILED writing Task.%s(%r, %r)',
                             self.task_set_func_name, task, value)
        if self.task_remove_func_name:
            for value in gtg_uids.difference(target_uids):
                getattr(task, self.task_remove_func_name)(value)
        task.children.sort(key=self.__sort_key(target_uids))

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
            return self.write_dav(vtodo, str(parent_index))


class Recurrence(Field):
    DAV_DAYS = ['SU', 'MO', 'TU', 'WE', 'TH', 'FR', 'SA']

    def get_gtg(self, task: Task, namespace: str = None) -> tuple:
        return task.get_recurring(), task.get_recurring_term()

    def get_dav(self, todo=None, vtodo=None) -> tuple:
        if todo:
            vtodo = todo.instance.vtodo
        value = vtodo.contents.get(self.dav_name)
        if not value:
            return False, None
        interval = value[0].params.get('INTERVAL')
        freq = value[0].params.get('FREQ')
        if interval and freq and interval[0] == '2' and freq[0] == 'DAILY':
            return True, 'other-day'
        if freq:
            return True, freq[0].lower()[:-2]
        return False, None

    def write_dav(self, vtodo: iCalendar, value: tuple):
        enabled, term = value
        self.clean_dav(vtodo)
        if not enabled:
            return
        assert term in {'day', 'other-day', 'week', 'month', 'year'}
        rrule = vtodo.add(self.dav_name)
        if term == 'other-day':
            rrule.params['FREQ'] = ['DAILY']
            rrule.params['INTERVAL'] = ['2']
        else:
            rrule.params['FREQ'] = [term.upper() + 'LY']
            start_date = DTSTART.get_dav(vtodo=vtodo)
            if term == 'week' and start_date:
                index = int(start_date.strftime('%w'))
                rrule.params['BYDAY'] = self.DAV_DAYS[index]

    def write_gtg(self, task: Task, value, namespace: str = None):
        return getattr(task, self.task_set_func_name)(*value)


DTSTART = DateField('dtstart', 'get_start_date', 'set_start_date')
UID_FIELD = Field('uid', 'get_uuid', 'set_uuid')
SEQUENCE = Sequence('sequence', '<fake attribute>', '')
CATEGORIES = Categories('categories', 'get_tags_name', 'set_tags',
                        ignored_values=[[]])
PARENT_FIELD = RelatedTo('related-to', 'get_parents', 'set_parent',
                         task_remove_func_name='remove_parent',
                         reltype='parent')
CHILDREN_FIELD = RelatedTo('related-to', 'get_children', 'add_child',
                           task_remove_func_name='remove_child',
                           reltype='child')
SORT_ORDER = OrderField('x-apple-sort-order', '', '')


class Translator:
    GTG_PRODID = "-//Getting Things Gnome//CalDAV Backend//EN"
    DTSTAMP_FIELD = UTCDateTimeField('dtstamp', '', '')
    fields = [Field('summary', 'get_title', 'set_title'),
              Description('description', 'get_excerpt', 'set_text'),
              DateField('due', 'get_due_date_constraint', 'set_due_date'),
              UTCDateTimeField(
                  'completed', 'get_closed_date', 'set_closed_date'),
              DTSTART,
              Recurrence('rrule', 'get_recurring_term', 'set_recurring'),
              Status('status', 'get_status', 'set_status'),
              PercentComplete('percent-complete', 'get_status', ''),
              SEQUENCE, UID_FIELD, CATEGORIES, CHILDREN_FIELD,
              UTCDateTimeField('created', 'get_added_date', 'set_added_date'),
              UTCDateTimeField(
                  'last-modified', 'get_modified', 'set_modified')]

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
            if not field.is_equal(task, namespace, todo, vtodo):
                yield field

    @classmethod
    def should_sync(cls, task: Task, namespace: str, todo=None, vtodo=None):
        for field in cls.changed_attrs(task, namespace, todo, vtodo):
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
        logger.error('no calendar for %r or %r', name, url)

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
