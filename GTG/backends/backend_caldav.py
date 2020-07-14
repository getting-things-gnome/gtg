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

from dateutil.tz import tzutc, tzlocal
import datetime
import os
import time
import uuid
import threading

import caldav
from vobject.icalendar import dateTimeToString, stringToDate

from GTG.backends.backend_signals import BackendSignals
from GTG.backends.generic_backend import GenericBackend
from GTG.backends.periodic_import_backend import PeriodicImportBackend
from GTG.backends.sync_engine import SyncEngine, SyncMeme
from GTG.core.tag import ALLTASKS_TAG
from GTG.core.task import Task
from gettext import gettext as _
from GTG.core.dates import Date
from GTG.core.interruptible import interruptible
from GTG.core.logger import log
from GTG.core.tag import extract_tags_from_text

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
        GenericBackend.BACKEND_NAME: "backend_caldav",
        GenericBackend.BACKEND_ICON: "applications-internet",
        GenericBackend.BACKEND_HUMAN_NAME: _("CalDAV tasks"),
        GenericBackend.BACKEND_AUTHORS: ["Mildred Ki'Lya"],
        GenericBackend.BACKEND_TYPE: GenericBackend.TYPE_READWRITE,
        GenericBackend.BACKEND_DESCRIPTION:
        _("Lets you synchronize your GTG tasks with CalDAV tasks"),
    }

    _static_parameters = {
        "period": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_INT,
            GenericBackend.PARAM_DEFAULT_VALUE: 0.25, },
        "username": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE: 'insert your username', },
        "password": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_PASSWORD,
            GenericBackend.PARAM_DEFAULT_VALUE: '', },
        "service-url": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE: 'https://example.com/webdav/', },
        "default-calendar-name": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE: '', },
        "is-first-run": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_BOOL,
            GenericBackend.PARAM_DEFAULT_VALUE: True, },
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
        # loading the saved state of the synchronization, if any
        self.data_path_url = os.path.join('caldav', 'sync_engine-url-' + self.get_id())
        self.sync_engine_url = self._load_pickled_file(self.data_path_url, SyncEngine())
        self._mutex = threading.Lock()

    def save_state(self):
        """Saves the state of the synchronization"""
        self._store_pickled_file(self.data_path_url, self.sync_engine_url)

    def initialize(self):
        super().initialize()
        self._dav = caldav.DAVClient(
                url=self._parameters['service-url'],
                username=self._parameters['username'],
                password=self._parameters['password'])
        self._calendars = None
        self._cached_todos = {}

    def dav_principal(self):
        try:
            return self._dav.principal()
        except caldav.lib.error.AuthorizationError as e:
            message = _(
                "You need a correct login to CalDAV"
                f"Configure CalDAV with login information. Error: {e}"
            )
            BackendSignals().interaction_requested(
                self.get_id(), message,
                BackendSignals().INTERACTION_INFORM, "on_continue_clicked")
            raise e

    def dav_calendars(self, refresh=False):
        if refresh or self._calendars is None:
            self._calendars = self.dav_principal().calendars()
        return self._calendars

    def get_namespace(self):
        url = self._parameters['service-url']
        return f"caldav:{url}"

###############################################################################
# Import tasks ################################################################
###############################################################################

    def do_periodic_import(self):
        """
        See PeriodicImportBackend for an explanation of this function.
        """

        # If it's the very first time the backend is run, it's possible that
        # the user already synced his tasks in some way (but we don't know
        # that). Therefore, we attempt to induce those tasks relationships
        # matching the url attribute.
        if self._parameters["is-first-run"]:
            with self._mutex:
                for tid in self.datastore.get_all_tasks():
                    try:
                        url = self.sync_engine_url.get_remote_id(tid)
                    except KeyError:
                        continue

                    task = self.datastore.get_task(tid)
                    url = task.get_attribute("url", namespace=self.get_namespace())
                    todo = self._get_todo(url) # network lookup
                    if todo is None:
                        continue

                    meme = SyncMeme(task.get_modified() or Date.no_date(),
                                    todo.get_modified() or Date.no_date(),
                                    "GTG")
                    self.sync_engine_url.record_relationship(
                        local_id=tid,
                        remote_id=str(todo.url),
                        meme=meme)
                # a first run has been completed successfully
                self._parameters["is-first-run"] = False

        with self._mutex:
            cals = self.dav_calendars(refresh=True)
        for cal in cals:
            with self._mutex:
                todos = cal.todos(include_completed=True)
                self._update_cache(cal, todos)
            for todo in todos:
                self._process_todo(Todo(todo))

    def _process_todo(self, todo):
        with self._mutex:
            is_syncable = self._todo_is_syncable_per_attached_tags(todo)
            action, tid = self.sync_engine_url.analyze_remote_id(
                    str(todo.url),
                    lambda tid: self._has_local_task(tid),
                    lambda url: self._has_remote_task(url, use_cache=True),
                    is_syncable)
            log.debug(f"GTG<-CalDAV set task url={todo.url} ({action} {is_syncable}) tid={tid}")

            if action is None:
                return

            elif action == SyncEngine.ADD:
                if todo.get_status() != Task.STA_ACTIVE:
                    # OPTIMIZATION:
                    # we don't sync tasks that have already been closed before we
                    # even synced them once
                    return
                tid = str(uuid.uuid4())
                task = self.datastore.task_factory(tid)
                self._populate_task(task, todo)
                meme = SyncMeme(task.get_modified() or Date.no_date(),
                                todo.get_modified() or Date.no_date(),
                                "CalDAV")
                self.sync_engine_url.record_relationship(
                    local_id=tid,
                    remote_id=str(todo.url),
                    meme=meme)
                self.datastore.push_task(task)

            elif action == SyncEngine.UPDATE:
                task = self.datastore.get_task(tid)
                with self.datastore.get_backend_mutex():
                    meme = self.sync_engine_url.get_meme_from_remote_id(str(todo.url))
                    newest = meme.which_is_newest(task.get_modified(),
                                                  todo.get_modified())
                    if newest == "remote":
                        self._populate_task(task, todo)
                        meme.set_remote_last_modified(todo.get_modified())
                        meme.set_local_last_modified(task.get_modified())
                    else:
                        # we skip saving the state
                        return

            elif action == SyncEngine.REMOVE:
                parent_url = str(todo.parent_url)
                todo_url = str(todo.url)
                todo_uid = todo.uid
                todo.delete()
                del self._cached_todos[parent_url]['urls'][todo_url]
                del self._cached_todos[parent_url]['uids'][todo_uid]
                try:
                    self.sync_engine_url.break_relationship(remote_id=todo_url)
                except KeyError:
                    pass

            elif action == SyncEngine.LOST_SYNCABILITY:
                self._exec_lost_syncability(tid, todo)

            self.save_state()

    def _populate_task(self, task, todo):
        """
        Copies the content of a VTODO in a Task
        """
        task.set_title(todo.get_title() or '')
        task.set_text(todo.get_text() or '')

        # attributes
        task.set_attribute("url", todo.url, namespace=self.get_namespace())
        task.set_attribute("id", todo.id, namespace=self.get_namespace())
        task.set_attribute("calendar_url", todo.parent_url, namespace=self.get_namespace())
        task.set_attribute("calendar_name", todo.parent_name, namespace=self.get_namespace())

        # status
        status = todo.get_vstatus()
        if _GTG_TO_CALDAV_STATUS[task.get_status()] != status:
            task.set_status(todo.get_status())

        # dates
        task.set_due_date(todo.get_due_date())
        task.set_added_date(todo.get_added_date())
        task.set_closed_date(todo.get_closed_date())
        task.set_start_date(todo.get_start_date())

        # parent relationship
        related = todo.vtodo.contents['related-to'] if 'related-to' in todo.vtodo.contents else None
        todo_parents = set(todo.get_parents(from_id=lambda parent_url, uid: self._id_to_tid(parent_url, uid)))
        local_parents = set(task.get_parents())

        for parent in todo_parents.difference(local_parents):
            task.add_parent(parent)
        for parent in local_parents.difference(todo_parents):
            local.remove_parent(parent)

        # tags
        tags = set([self._tag_to_gtg(tag) for tag in todo.get_tags()])
        gtg_tags = set([t.get_name() for t in task.get_tags()])
        # tags to remove
        for tag in gtg_tags.difference(tags):
            task.remove_tag(tag)
        # tags to add
        task.add_tag(self._tag_to_gtg(todo.parent_name))
        for tag in tags.difference(gtg_tags):
            task.add_tag(tag)

    def _tag_to_gtg(self, tag):
        tag = tag.replace(' ', '_')
        return f"@{tag}"

    def _update_cache(self, cal, todos):
        urls = {}
        uids = {}
        for todo in todos:
            urls[str(todo.url)] = todo.instance.vtodo.uid.value
            uids[todo.instance.vtodo.uid.value] = str(todo.url)
        self._cached_todos[str(cal.url)] = {
            'urls': urls,
            'uids': uids
        }

    def _add_to_cache(self, todo):
        if todo.parent_url not in self._cached_todos:
            self._cached_todos[todo.parent_url] = {'urls': {}, 'uids': {}}
        self._cached_todos[todo.parent_url]['urls'][todo.url] = todo.uid
        self._cached_todos[todo.parent_url]['uids'][todo.uid] = todo.url

###############################################################################
# Process tasks ###############################################################
###############################################################################

    @interruptible
    def remove_task(self, tid):
        """
        See GenericBackend for an explanation of this function.
        """
        with self._mutex:
            try:
                url = self.sync_engine_url.get_remote_id(tid)
            except KeyError:
                task = self.datastore.get_task(tid)
                url  = task.get_attribute("url", namespace=self.get_namespace())
            log.debug(f"GTG<-CalDAV remove_task({tid}) url={url}")
            try:
                ev = self._get_todo(url) # network lookup
                if ev != None: ev.delete()
            finally:
                try:
                    self.sync_engine_url.break_relationship(local_id=tid)
                except KeyError:
                    pass

    @interruptible
    def set_task(self, task):
        """
        See GenericBackend for an explanation of this function.
        """
        with self._mutex:
            tid = task.get_id()
            is_syncable = self._gtg_task_is_syncable_per_attached_tags(task)
            action, url = self.sync_engine_url.analyze_local_id(
                tid,
                lambda tid: self._has_local_task(tid),
                lambda url: self._has_remote_task(url, use_cache=True),
                is_syncable)
            log.debug(f'GTG->CalDAV set task tid={tid} ({action}, {is_syncable}) url={url}')

            if action is None:
                return

            elif action == SyncEngine.ADD:
                with self.datastore.get_backend_mutex():
                    todo = self._create_todo(task)
                    self._populate_todo(task, todo, save_new=True)
                    meme = SyncMeme(task.get_modified() or Date.no_date(),
                                    todo.get_modified() or Date.no_date(),
                                    "GTG")
                    self.sync_engine_url.record_relationship(
                        local_id=tid, remote_id=str(todo.url),
                        meme=meme)
                    self._add_to_cache(todo)

            elif action == SyncEngine.UPDATE:
                with self.datastore.get_backend_mutex():
                    todo = self._get_todo(url) # network lookup
                    meme = self.sync_engine_url.get_meme_from_local_id(task.get_id())
                    newest = meme.which_is_newest(task.get_modified(),
                                                  todo.get_modified() or Date.no_date())
                    if newest == "local":
                        self._populate_todo(task, todo, save_new=False)
                        meme.set_remote_last_modified(todo.get_modified())
                        meme.set_local_last_modified(task.get_modified())
                    else:
                        # we skip saving the state
                        return

            elif action == SyncEngine.REMOVE:
                self.datastore.request_task_deletion(tid)
                try:
                    self.sync_engine_url.break_relationship(local_id=tid)
                except KeyError:
                    pass

            elif action == SyncEngine.LOST_SYNCABILITY:
                todo = self._get_todo(url) # network lookup TODO: try to avoid it
                self._exec_lost_syncability(tid, todo)

            self.save_state()

    def _populate_todo(self, task, todo, save_new=None):
        # Title
        todo.set_title(task.get_title())

        # Text
        text = task.get_excerpt(strip_tags=True, strip_subtasks=True)
        if todo.get_text() != text:
            todo.set_text(text)

        # Parents
        parents = task.get_parents()
        todo.set_parents(parents, to_id=lambda tid: self._tid_to_id(tid))

        # dates
        todo.set_modified(task.get_modified())
        todo.set_due_date(task.get_due_date())
        todo.set_added_date(task.get_added_date())
        todo.set_closed_date(task.get_closed_date())
        todo.set_start_date(task.get_start_date())
        todo.set_modified(task.get_modified())

        # Status
        status = task.get_status()
        if _CALDAV_TO_GTG_STATUS[todo.get_vstatus()] != status:
            todo.set_status(status)

        # Tags
        cal_name = todo.parent_name
        gtg_tags = set([self._tag_from_gtg(tag.get_name()) for tag in task.get_tags()])
        todo_tags = set(todo.get_tags())
        # tags to add
        for tag in gtg_tags.difference(todo_tags):
            if tag != cal_name:
                todo.add_tag(tag)
        # tags to remove
        for tag in todo_tags.difference(gtg_tags):
            todo.remove_tag(tag)


        try:
            todo.save(save_new=save_new)
        except:
            log.debug(f'_populate_todo todo.instance={todo.instance}')
            raise

    def _tag_from_gtg(self, tag):
        tag = tag.replace('@', '', 1).replace('_', ' ')
        return tag

    def _exec_lost_syncability(self, tid, todo):
        """
        Executed when a relationship between tasks loses its syncability
        property. See SyncEngine for an explanation of that.

        @param tid: a GTG task tid
        @param note: a Todo
        """
        self.cancellation_point()
        meme = self.sync_engine.get_meme_from_local_id(tid)
        # First of all, the relationship is lost
        self.sync_engine.break_relationship(local_id=tid)
        if meme.get_origin() == "GTG":
            todo.delete()
        else:
            self.datastore.request_task_deletion(tid)

###############################################################################
# Helper methods ##############################################################
###############################################################################

    def _calendar_names(self):
        return [cal.name for cal in self.dav_calendars()]

    def _find_event_by_url(self, url):
        try:
            cal = self._find_calendar_matching_url(url)
            return None if cal is None else cal.event_by_url(url) # TODO: avoid lookup
        except caldav.lib.error.NotFoundError:
            return None

    def _get_todo(self, url):
        try:
            ev = self._find_event_by_url(url) # network lookup
            if ev is None: return None
            return Todo(ev)
        except caldav.lib.error.NotFoundError:
            return None

    def _has_local_task(self, tid):
        res = self.datastore.has_task(tid)
        log.debug(f"_has_local_task({tid}) -> {res}")
        return res

    def _has_remote_task(self, url, use_cache=False):
        if use_cache:
            for cal_url in self._cached_todos:
                if url.startswith(cal_url):
                    return url in self._cached_todos[cal_url]['urls']
            return False
        else:
            ev = self._find_event_by_url(url) # lookup
            return ev != None and 'vtodo' in ev.instance.contents

    def _find_calendar_by_name(self, cal_name):
        for cal in self.dav_calendars():
            if cal.name == cal_name:
                return cal
        return None

    def _find_calendar_matching_url(self, url):
        for cal in self.dav_calendars():
            if str(url).startswith(str(cal.url)):
                return cal
        return None

    def _calendar_name_for_task(self, task, include_default=True):
        def find_roots(task, datastore):
            parent_ids = task.get_parents()
            if len(parent_ids) == 0:
                return [task]
            res = []
            for parent_id in parent_ids:
                res += find_roots(datastore.get_task(parent_id), datastore)
            return res

        roots = find_roots(task, self.datastore)

        for root_task in roots:
            name = root_task.get_attribute("calendar_name", namespace=self.get_namespace())
            if name is not None and name in self._calendar_names():
                return name

        for root_task in roots:
            tags = set([self._tag_from_gtg(tag.get_name()) for tag in root_task.get_tags()])
            cals = list(tags.intersection(set(self._calendar_names())))
            if len(cals) > 0:
                return cals[0]

        if include_default:
            return self._parameters['default-calendar-name']

        return None

    def _gtg_task_is_syncable_per_attached_tags(self, task):
        cal_name = self._calendar_name_for_task(task)
        if cal_name is None or cal_name == '':
            return False

        return super()._gtg_task_is_syncable_per_attached_tags(task)

    def _todo_is_syncable_per_attached_tags(self, todo):
        """
        Helper function which checks if the given task satisfies the filtering
        imposed by the tags attached to the backend.
        That means, if a user wants a backend to sync only tasks tagged @works,
        this function should be used to check if that is verified.

        @returns bool: True if the task should be synced
        """
        attached_tags = self.get_attached_tags()
        if ALLTASKS_TAG in attached_tags:
            return True

        tags = [todo.parent_name] + todo.get_tags()
        for tag in [self._tag_to_gtg(tag) for tag in tags]:
            if tag in attached_tags:
                return True

        return False

    def _create_todo(self, task):
        tid = task.get_id()
        uid = str(uuid.uuid4())

        cal_name = self._calendar_name_for_task(task)
        cal = self._find_calendar_by_name(cal_name)

        # Add tag if there is a default
        cal_name_tag = self._tag_to_gtg(cal_name)
        if cal_name_tag not in [tag.get_name() for tag in task.get_tags()]:
            task.add_tag(cal_name_tag)

        return Todo(cal.add_todo(f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Getting Things Gnome//CalDAV Backend//EN
BEGIN:VTODO
UID:{uid}
END:VTODO
END:VCALENDAR"""))

    def _notify_user_about_default_calendar(self):
        """ This function causes the infobar to show up with the message
        about default calendar.
        """
        default_name = self._parameters['default-calendar-name']
        message = _(
            f"Could not find calendar {default_name}"
            "Configure CalDAV to save in a calendar from this list : \n"
        ) + self._calendar_names_info()
        BackendSignals().interaction_requested(
            self.get_id(), message,
            BackendSignals().INTERACTION_INFORM, "on_continue_clicked")

    def on_continue_clicked(self, *args):
        """ Callback when the user clicks continue in the infobar
        """
        pass

    def _calendar_names_info(self):
        return ','.join(self._calendar_names())

    def _id_to_tid(self, parent_url, uid, use_cache=True):
        cal = self._find_calendar_matching_url(parent_url)
        url = None
        if use_cache:
            try:
                cache = self._cached_todos[parent_url]
                url = cache['uids'][uid]
            except KeyError:
                pass
        if url is None:
            todo = cal.todo_by_uid(uid) # network lookup
            url = str(todo.url)
        return self.sync_engine_url.get_local_id(url)

    def _tid_to_id(self, tid, use_cache=True):
        try:
            url = self.sync_engine_url.get_remote_id(tid)
        except KeyError:
            return None, None
        parent_url = None
        uid = None
        if use_cache:
            for cal_url in self._cached_todos:
                if url.startswith(cal_url):
                    parent_url = cal_url
                    try:
                        uid = self._cached_todos[cal_url]['urls'][url]
                    except KeyError:
                        pass
                    break
        if parent_url is None or uid is None:
            ev = self._find_event_by_url(url) # network lookup
            try:
                parent_url = ev.parent.url
                uid = ev.instance.vtodo.uid.value
            except AttributeError:
                parent_url = None
                uid = None
        return parent_url, uid

class Todo():
    def __init__(self, todo):
        self._event = todo
        self.url = todo.url
        self.instance = todo.instance
        self.vtodo = self.instance.vtodo
        self.uid = self.vtodo.uid.value
        self.parent_url = str(todo.parent.url)
        self.parent_name = todo.parent.name
        self.id = "#".join([self.parent_url, self.uid])

    def delete(self):
        data = self._event.data
        log.debug(f"Delete {data}")
        return self._event.delete()

    def save(self, save_new=None):
        self._event.save()
        log.debug(f"Save save_new={save_new} {self._event.data}")

    def get_modified(self):
        try:
            return self._datetime_to_gtg(self.vtodo.last_modified.value)
        except AttributeError:
            return Date.no_date()

    def set_modified(self, gtg_date):
        self._vtodo_replace('last-modified', self._gtg_to_datetime(gtg_date))

    def set_title(self, value):
        self._vtodo_replace('summary', value)

    def get_title(self):
        try:
            return self.vtodo.summary.value
        except AttributeError:
            return None

    def set_text(self, value):
        self._vtodo_replace('description', value)

    def get_text(self):
        try:
            return self.vtodo.description.value
        except AttributeError:
            return None

    def set_due_date(self, gtg_date):
        self._vtodo_replace('due', self._gtg_to_datetime(gtg_date))

    def get_due_date(self):
        try:
            return self._datetime_to_gtg(self.vtodo.due.value)
        except AttributeError:
            return Date.no_date()

    def set_vstatus(self, value):
        self._vtodo_replace('status', value)

    def get_vstatus(self):
        try:
            return self.vtodo.status.value
        except AttributeError:
            return 'NEEDS-ACTION'

    def set_status(self, value):
        self.set_vstatus(_GTG_TO_CALDAV_STATUS[value])

    def get_status(self):
        status = self.get_vstatus()
        if status in _CALDAV_TO_GTG_STATUS:
            return _CALDAV_TO_GTG_STATUS[status]
        else:
            return Task.STA_ACTIVE

    def get_closed_date(self):
        try:
            return self._datetime_to_gtg(self.vtodo.completed.value)
        except AttributeError:
            return Date.no_date()

    def set_closed_date(self, dt):
        self._vtodo_replace('completed', self._gtg_to_datetime(dt))

    def get_start_date(self):
        try:
            return self._datetime_to_gtg(self.vtodo.x_gtg_start_date.value)
        except AttributeError:
            return Date.no_date()

    def set_start_date(self, dt):
        self._vtodo_replace('x-gtg-start-date', self._gtg_to_datetime_str(dt))

    def get_added_date(self):
        try:
            return self._datetime_to_gtg(self.vtodo.x_gtg_added_date.value)
        except AttributeError:
            return Date.no_date()

    def set_added_date(self, dt):
        self._vtodo_replace('x-gtg-added-date', self._gtg_to_datetime_str(dt))

    def set_tags(self, value):
        self._vtodo_replace('categories', value)

    def get_tags(self):
        try:
            return self.vtodo.categories.value
        except AttributeError:
            return []

    def add_tag(self, tag):
        if 'categories' not in self.vtodo.contents:
            self.vtodo.add('categories').value = []
        self.vtodo.categories.value = self.get_tags() + [tag]

    def remove_tag(self, tag):
        if 'categories' not in self.vtodo.contents:
            self.vtodo.add('categories').value = []
        self.vtodo.categories.value = [t for t in self.get_tags() if t != tag]

    def get_parent_todo_uid(self):
        try:
            return self.vtodo.related_to.value
        except AttributeError:
            return None

    def set_parents(self, parents, to_id):
        if 'related-to' in self.vtodo.contents:
            del self.vtodo.contents['related-to']
        for parent in parents:
            cal_url, parent_id = to_id(parent)
            if parent_id is not None and cal_url == self.parent_url:
                self.vtodo.add('related-to').value = parent_id

    def get_parents(self, from_id):
        if 'related-to' not in self.vtodo.contents:
            return []
        else:
            return [from_id(self.parent_url, rel.value) for rel in self.vtodo.contents['related-to']]

    def _datetime_to_gtg(self, dt):
        if dt is None:
            return Date.no_date()
        elif type(dt) == datetime.datetime:
            dt.replace(tzinfo=None)
            dt = dt.date()
        elif type(dt) == datetime.date:
            pass
        elif type(dt) == str:
            dt = stringToDate(dt)
        else:
            assert False, type(dt)
        return Date(dt)

    def _gtg_to_datetime(self, gtg_date):
        if gtg_date is None or gtg_date == Date.no_date():
            return None
        elif isinstance(gtg_date, datetime.datetime):
            return gtg_date
        elif isinstance(gtg_date, datetime.date):
            return datetime.datetime.combine(gtg_date, datetime.time(0))
        elif isinstance(gtg_date, Date):
            return datetime.datetime.combine(gtg_date.date(), datetime.time(0))
        else:
            raise NotImplementedError

    def _gtg_to_datetime_str(self, gtg_date):
        dt = self._gtg_to_datetime(gtg_date)
        if dt is None:
            return None
        return dateTimeToString(dt.replace(tzinfo=tzutc()), True)

    def _vtodo_replace(self, key, value):
        if key in self.vtodo.contents:
            del self.vtodo.contents[key]
        if value is not None:
            self.vtodo.add(key).value = value

    def __str__(self):
        return str(self.instance)
