
# Implementation of the org.gnome.GTG.Tasks interface

import datetime
import logging
import enum
from gi.repository import GLib
from GTG.core.search import parse_search_query, InvalidQuery
from GTG.core.dates import Date
from GTG.core.task import Task
from .dbus import DBusInterfaceImplService, DBusReturnError


__all__ = ('DBusImplTasks', 'InvalidTaskDict', 'TaskDict', 'TaskStatus')
log = logging.getLogger(__name__)


class TaskStatus(enum.IntEnum):
    """Task status for the DBus-Interface."""

    unknown = 0
    """Unknown status, normally you shouldn't use and see this."""
    active = 1
    """Task is still active (and is open)."""
    dismissed = 2
    """Task has been dismissed (and is closed)."""
    done = 3
    """Task has been completed (and is closed)."""

    @classmethod
    def status_to_enum(cls, status: str):
        _status_to_enum_map = {
            Task.STA_ACTIVE: cls.active,
            Task.STA_DISMISSED: cls.dismissed,
            Task.STA_DONE: cls.done,
        }
        return _status_to_enum_map.get(status, cls.unknown)

    @classmethod
    def enum_to_status(cls, e):
        _enum_to_status_map = {
            cls.active: Task.STA_ACTIVE,
            cls.dismissed: Task.STA_DISMISSED,
            cls.done: Task.STA_DONE,
        }
        return _enum_to_status_map.get(e, '')


class TaskDict(dict):
    """Helper class for managing a task dictionary."""

    @classmethod
    def from_task(cls, task: Task):
        """
        Converts the specified task to an task dictionary.
        """
        d = TaskDict()
        d["id"] = task.get_id()
        d["status"] = TaskStatus.status_to_enum(task.get_status())
        d["title"] = task.get_title()
        d["duedate"] = _date_to_string(task.get_due_date())
        d["startdate"] = _date_to_string(task.get_start_date())
        d["donedate"] = _date_to_string(task.get_closed_date())
        d["tags"] = task.get_tags_name()
        d["text"] = task.get_text()
        d["children"] = task.get_children()
        d["parents"] = task.get_parents()
        return d

    _to_variant_type = {
        "id": 's',
        "status": 'i',
        "title": 's',
        "duedate": 's',
        "startdate": 's',
        "donedate": 's',
        "tags": 'as',
        "text": 's',
        "children": 'as',
        "parents": 'as',
    }

    def to_variant(self) -> dict:
        """
        Convert an task dict to a variant dict to be submitted over DBus.
        """
        d = dict(self)
        for name, vtype in self._to_variant_type.items():
            if name in d:
                d[name] = GLib.Variant(vtype, d[name])
        return d
        # return GLib.Variant("a{sv}", d) breaks GLib.Variant('aa{sv}', [dv])


def _task_to_variant(task: Task) -> dict:
    """
    Convert an task object to a variant dict to be submitted over DBus.
    """
    return TaskDict.from_task(task).to_variant()


def _variant_to_task_dict(task_variant) -> TaskDict:
    """
    Convert an variant dict to a task dict.
    """
    return TaskDict(task_variant.unpack())


def _date_to_string(date: Date):
    """
    Convert a gtg date to either an english fuzzy string or to ISO format.
    """
    if date == Date.now():
        return "now"
    if date == Date.no_date():
        return ""
    if date == Date.soon():
        return "soon"
    if date == Date.someday():
        return "someday"
    return date.isoformat()  # Uses the wrapped python date object


_string_to_date_map = {
    "": Date.no_date(),
    "now": Date.now(),
    "soon": Date.soon(),
    "someday": Date.someday(),
}


def _string_to_date(sdate: str) -> Date:
    """
    Convert string to the correct a gtg date without localization.
    """
    try:
        return _string_to_date_map[sdate]
    except KeyError:
        try:
            return Date(datetime.date.fromisoformat(sdate))
        except ValueError:
            raise DBusReturnError("gtg.InvalidDateFormat",
                                  f"Invalid date format '{sdate}'")


class InvalidTaskDict(DBusReturnError):
    """
    Return DBus Error about an invalid type for a task dictionary.
    """
    def __init__(self, what, got, expected):
        got = got.__name__
        expected = expected.__name__
        super().__init__("gtg.InvalidTaskDict",
                         f"{what} is a {got}, but expected {expected}")


class DBusImplTasks(DBusInterfaceImplService):
    INTERFACE_NAME = 'org.gnome.GTG.Tasks'

    def __init__(self, req):
        super().__init__()
        self.req = req

        tree = req.get_main_view()
        # TODO: Register signals
        # tree.register_cllbck('node-added', lambda tid, _:
        #                           self.TaskAdded(tid))
        # tree.register_cllbck('node-modified', lambda tid, _:
        #                           self.TaskModified(tid))
        # tree.register_cllbck('node-deleted', lambda tid, _:
        #                           self.TaskDeleted(tid))

    def _get_task(self, tid):
        """
        Return task from a tid, otherwise return an not-found DBus error.
        """
        task = self.req.get_task(tid)
        if task is None:
            raise DBusReturnError("gtg.TaskNotFound",
                                  f"Task not found by id '{tid}'")
        return task

    def GetTasks(self, tids: list) -> list:
        log.debug(f"Doing GetTasks({tids})")
        return [_task_to_variant(self._get_task(tid)) for tid in tids]

    def GetActiveTaskIds(self) -> list:
        log.debug(f"Doing GetActiveTaskIds()")
        return self.GetTaskIdsFiltered(['active', 'workable'])

    def GetActiveTasks(self) -> list:
        log.debug(f"Doing GetActiveTasks()")
        return self.GetTasks(self.GetActiveTaskIds())

    def GetTaskIdsFiltered(self, filters: list) -> list:
        log.debug(f"Doing GetTasksFiltered({filters})")
        tree = self.req.get_tasks_tree().get_basetree()
        view = tree.get_viewtree(name=None)  # Anonymous viewtree
        last_index = len(filters) - 1
        for i, filter in enumerate(filters):
            is_last = i == last_index
            if filter[0] == '!':
                view.apply_filter(filter[1:], parameters={'negate': 1},
                                  refresh=is_last)
            else:
                view.apply_filter(filter, refresh=is_last)
        return list(view.get_all_nodes())

    def GetTasksFiltered(self, filters: list) -> list:
        log.debug(f"Doing GetTasksFiltered({filters})")
        return self.GetTasks(self.GetTaskIdsFiltered(filters))

    def SearchTaskIds(self, query: str) -> list:
        log.debug(f"Doing SearchTaskIds({query})")
        tree = self.req.get_tasks_tree().get_basetree()
        view = tree.get_viewtree()
        try:
            search = parse_search_query(query)
            view.apply_filter('search', parameters=search)
            tasks = view.get_all_nodes()
            if tasks:
                return tasks
        except InvalidQuery as e:
            raise DBusReturnError("gtg.InvalidQuery",
                                  f"Invalid Query '{query}': {e}")
        return []

    def SearchTasks(self, query: str) -> list:
        log.debug(f"Doing SearchTasks({query})")
        return self.GetTasks(self.SearchTaskIds(query))

    def HasTasks(self, tids: list) -> dict:
        log.debug(f"Doing HasTasks({tids})")
        return {tid: self.req.has_task(tid) for tid in tids}

    def DeleteTasks(self, tids: list) -> dict:
        log.debug(f"Doing DeleteTasks({tids})")
        d = {}
        for tid in tids:
            d[tid] = self.req.has_task(tid)
            if d[tid]:  # Task exists, so let's delete it
                self.req.delete_task(tid)
        return d

    def NewTasks(self, tasks: list) -> list:
        log.debug(f"Doing NewTasks({tasks})")
        r = []
        for new_task_dict in tasks:
            self._verify_task_dict(new_task_dict)
            new_task = self.req.new_task()
            self._modify_task(new_task, new_task_dict)
            r.append(_task_to_variant(new_task))
        return r

    def ModifyTasks(self, patches: list) -> list:
        log.debug(f"Doing ModifyTasks({patches})")
        r = []
        for patch in patches:
            if "id" not in patch:
                raise DBusReturnError("gtg.MissingTaskId",
                                      "No 'id' in task dict")
            self._verify_task_dict(patch)
            task = self._get_task(patch["id"])
            patched_task = self._modify_task(task, patch)
            r.append(_task_to_variant(patched_task))
        return r

    def _modify_task(self, task: Task, patch: dict) -> Task:
        """Modify a single task and return it"""
        if "title" in patch:
            task.set_title(patch["title"])
        if "text" in patch:
            task.set_text(patch["text"])
        if "duedate" in patch:
            task.set_due_date(_string_to_date(patch["duedate"]))
        if "startdate" in patch:
            task.set_start_date(_string_to_date(patch["startdate"]))
        if "status" in patch:
            task.set_status(TaskStatus.enum_to_status(patch["status"]))
        if "donedate" in patch:
            old_status = task.get_status()
            donedate = _string_to_date(patch["donedate"])
            task.set_status(old_status, donedate=donedate)
        if "tags" in patch:
            old_tags = set(task.get_tags_name())
            new_tags = set(patch["tags"])
            common_tags = old_tags & new_tags
            for removed_tag in old_tags - common_tags:
                task.remove_tag(removed_tag)
            for added_tag in new_tags - common_tags:
                task.add_tag(added_tag)
        if "children" in patch:
            log.debug("TODO: Implement patching subtask list")  # TODO
        if "parents" in patch:
            log.debug("TODO: Implement patching parents")  # TODO
        return task

    def _verify_task_dict_types(self, td: dict):
        """
        Check if an task dict has the correct types.
        """
        # Reusing TaskDict._to_variant_type because it already contains the
        # types it uses for serializing
        for key, vartype in TaskDict._to_variant_type.items():
            if key not in td:
                continue

            if vartype == 'i':
                expected_type = int
            elif vartype == 's':
                expected_type = str
            elif vartype[0] == 'a':
                expected_type = list
            else:
                raise RuntimeError("Unknown vartype")

            if type(td[key]) is not expected_type:
                raise InvalidTaskDict(f"'{key}'", type(td[key]), expected_type)

            if vartype[0] != 'a':
                continue

            if vartype[1] == 's':
                expected_type = str
            else:
                log.debug("Unknown vartype, can't verify children: %r",
                          vartype)
                continue
            for elem in td[key]:
                if type(elem) is not expected_type:
                    raise InvalidTaskDict(f"'{key}' element",
                                          type(elem), expected_type)

    def _verify_task_dict(self, td: dict):
        """
        Verify the types and whenever the values are valid for a task dict.
        """
        self._verify_task_dict_types(td)
        if "startdate" in td:
            date = _string_to_date(td["startdate"])
            if date.is_fuzzy() and date != Date.no_date():
                raise DBusReturnError("gtg.InvalidStartDate",
                                      f"Invalid start date '{td['startdate']}'")

        if "donedate" in td:  # TODO: What about status?
            date = _string_to_date(td["donedate"])
            if date.is_fuzzy() and date != Date.no_date():
                raise DBusReturnError("gtg.InvalidDoneDate",
                                      f"Invalid done date '{td['donedate']}'")

        if "status" in td:
            status = TaskStatus.enum_to_status(td["status"])
            if status == '':
                raise DBusReturnError("gtg.InvalidStatus",
                                      f"Invalid status {td['status']}")
