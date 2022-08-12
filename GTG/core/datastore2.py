# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) The GTG Team
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

"""The datastore ties together all the basic type stores and backends."""

import os
import threading
import logging
import shutil
from datetime import datetime, timedelta
from time import time
import random
import string

from GTG.core.tasks2 import TaskStore, Filter
from GTG.core.tags2 import TagStore
from GTG.core.saved_searches import SavedSearchStore
from GTG.core import firstrun_tasks
from GTG.core.dates import Date
from GTG.backends.backend_signals import BackendSignals
from GTG.backends.generic_backend import GenericBackend
import GTG.core.info as info

from lxml import etree as et

from typing import Optional


log = logging.getLogger(__name__)


class Datastore2:

    #: Amount of backups to keep
    BACKUPS_NUMBER = 7


    def __init__(self) -> None:
        self.tasks = TaskStore()
        self.tags = TagStore()
        self.saved_searches = SavedSearchStore()
        self.xml_tree = None

        self._mutex = threading.Lock()
        self.backends = {}
        self._backend_signals = BackendSignals()

        # When a backup has to be used, this will be filled with
        # info on the backup used
        self.backup_info = {}

        # Flag when turned to true, all pending operation should be
        # completed and then GTG should quit
        self.please_quit = False

        # Count of tasks for each pane and each tag
        self.task_count = {
            'open': {'all': 0, 'untagged': 0},
            'actionable': {'all': 0, 'untagged': 0},
            'closed': {'all': 0, 'untagged': 0},
        }

        self.data_path = None


    @property
    def mutex(self) -> threading.Lock:
        return self._mutex


    def load_data(self, data: et.Element) -> None:
        """Load data from an lxml element object."""

        self.saved_searches.from_xml(data.find('searchlist'))
        self.tags.from_xml(data.find('taglist'))
        self.tasks.from_xml(data.find('tasklist'), self.tags)

        self.refresh_task_count()


    def load_file(self, path: str) -> None:
        """Load data from a file."""

        bench_start = 0

        if log.isEnabledFor(logging.DEBUG):
            bench_start = time()

        parser = et.XMLParser(remove_blank_text=True, strip_cdata=False)

        with open(path, 'rb') as stream:
            self.xml_tree = et.parse(stream, parser=parser)
            self.load_data(self.xml_tree)

        if log.isEnabledFor(logging.DEBUG):
            log.debug('Processed file %s in %.2fms',
                      path, (time() - bench_start) * 1000)

        # Store path, so we can call save() on it
        self.data_path = path


    def generate_xml(self) -> et.ElementTree:
        """Generate lxml element object with all data."""

        root = et.Element('gtgData')
        root.set('appVersion', info.VERSION)
        root.set('xmlVersion', '2')

        root.append(self.tags.to_xml())
        root.append(self.saved_searches.to_xml())
        root.append(self.tasks.to_xml())

        return et.ElementTree(root)


    def write_file(self, path: str) -> None:
        """Generate and write xml file."""

        tree = self.generate_xml()

        with open(path, 'wb') as stream:
            tree.write(stream, xml_declaration=True, pretty_print=True,
                       encoding='UTF-8')


    def save(self, path: Optional[str] = None) -> None:
        """Write GTG data file."""

        path = path or self.data_path
        temp_file = path + '__'
        bench_start = 0

        try:
            os.rename(path, temp_file)
        except IOError:
            log.error('Error renaming temp file %r', temp_file)

        if log.isEnabledFor(logging.DEBUG):
            bench_start = time()

        base_dir = os.path.dirname(path)

        try:
            os.makedirs(base_dir, exist_ok=True)
        except IOError as error:
            log.error("Error while creating directories: %r", error)

        try:
            self.write_file(path)
        except (IOError, FileNotFoundError):
            log.error('Could not write XML file at %r', path)
            return


        if log.isEnabledFor(logging.DEBUG):
            log.debug('Saved file %s in %.2fms',
                      path, (time() - bench_start) * 1000)

        try:
            os.remove(temp_file)
        except FileNotFoundError:
            pass

        self.write_backups(path)


    def print_info(self) -> None:
        """Print statistics and information on this datastore."""

        tasks = self.tasks.count()
        initialized = 'Initialized' if tasks > 0 else 'Empty'

        print(f'Datastore [{initialized}]')
        print(f'- Tags: {self.tags.count()}')
        print(f'- Saved Searches: {self.saved_searches.count()}')
        print(f'- Tasks: {self.tasks.count()}')


    def refresh_task_count(self) -> None:
        """Refresh task count dictionary."""

        def count_tasks(count: dict, tasklist: list):
            for task in tasklist:
                count['all'] += 1

                if not task.tags:
                    count['untagged'] += 1

                for tag in task.tags:
                    val = count.get(tag.name, 0)
                    count[tag.name] = val + 1

                if task.children:
                    count_tasks(count, task.children)

        # Reset task counts
        self.task_count = {
            'open': {'all': 0, 'untagged': 0},
            'actionable': {'all': 0, 'untagged': 0},
            'closed': {'all': 0, 'untagged': 0},
        }

        count_tasks(self.task_count['open'], 
                    self.tasks.filter(Filter.ACTIVE))

        count_tasks(self.task_count['closed'], 
                    self.tasks.filter(Filter.CLOSED))

        count_tasks(self.task_count['actionable'], 
                    self.tasks.filter(Filter.ACTIONABLE))


    def notify_tag_change(self, tag) -> None:
        """Notify tasks that this tag has changed."""
        
        for task in self.tasks.lookup.values():
            if tag in task.tags:
                task.notify('icons')
                task.notify('row_css')
                task.notify('tag_colors')
                task.notify('show_tag_colors')


    def first_run(self, path: str) -> et.Element:
        """Write initial data file."""

        self.xml_tree = firstrun_tasks.generate()
        self.load_data(self.xml_tree)
        self.save(path)


    @staticmethod
    def get_backup_path(path: str, i: int = None) -> str:
        """Get path of backups which are backup/ directory."""

        dirname, filename = os.path.split(path)
        backup_file = f"{filename}.bak.{i}" if i else filename

        return os.path.join(dirname, 'backup', backup_file)


    def write_backups(self, path: str) -> None:
        backup_name = self.get_backup_path(path)
        backup_dir = os.path.dirname(backup_name)

        # Make sure backup dir exists
        try:
            os.makedirs(backup_dir, exist_ok=True)

        except IOError:
            log.error('Backup dir %r cannot be created!', backup_dir)
            return

        # Cycle backups
        for current_backup in range(self.BACKUPS_NUMBER, 0, -1):
            older = f"{backup_name}.bak.{current_backup}"
            newer = f"{backup_name}.bak.{current_backup - 1}"

            try:
                shutil.move(newer, older)
            except FileNotFoundError:
                pass

        # bak.0 is always a fresh copy of the closed file
        # so that it's not touched in case of not opening next time
        bak_0 = f"{backup_name}.bak.0"
        shutil.copy(path, bak_0)

        # Add daily backup
        today = datetime.today().strftime('%Y-%m-%d')
        daily_backup = f'{backup_name}.{today}.bak'

        if not os.path.exists(daily_backup):
            shutil.copy(path, daily_backup)

        self.purge_backups(path)


    @staticmethod
    def purge_backups(path: str, days: int = 30) -> None:
        """Remove backups older than X days."""

        now = time()
        day_in_secs = 86_400
        basedir = os.path.dirname(path)

        for filename in os.listdir(basedir):
            filename = os.path.join(basedir, filename)
            filestamp = os.stat(filename).st_mtime
            filecompare = now - (days * day_in_secs)

            if filestamp < filecompare:
                os.remove(filename)


    def find_and_load_file(self, path: str) -> None:
        """Find an XML file to open

        If file could not be opened, try:
            - file__
            - file.bak.0
            - file.bak.1
            - .... until BACKUP_NUMBER

        If file doesn't exist, create a new file."""

        files = [
            path,            # Main file
            path + '__',     # Temp file
        ]

        # Add backup files
        files += [self.get_backup_path(path, i)
                  for i in range(self.BACKUPS_NUMBER)]


        for index, filepath in enumerate(files):
            try:
                log.debug('Opening file %s', filepath)
                self.load_file(filepath)

                timestamp = os.path.getmtime(filepath)
                mtime = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')

                # This was a backup. We should inform the user
                if index > 0:
                    self.backup_info = {
                        'name': filepath,
                        'time': mtime
                    }

                # We could open a file, let's stop this loop
                break

            except FileNotFoundError:
                log.debug('File not found: %r. Trying next.', filepath)
                continue

            except PermissionError:
                log.debug('Not allowed to open: %r. Trying next.', filepath)
                continue

            except et.XMLSyntaxError as error:
                log.debug('Syntax error in %r. %r. Trying next.',
                          filepath, error)
                continue

        # We couldn't open any file :(
        if not self.xml_tree:
            try:
                # Try making a new empty file and open it
                self.first_run(path)

            except IOError:
                raise SystemError(f'Could not write a file at {path}')


    def purge(self, max_days: int) -> None:
        """Remove closed tasks and unused tags."""

        log.debug("Deleting old tasks")

        today = Date.today()
        for task in self.tasks.data:
            if (today - task.date_closed).days > max_days:
                self.tasks.remove(task.id)

        log.debug("Deleting unused tags")

        for tag in self.tags.data:
            count_open = self.task_count['open'].get(tag.name, 0)
            count_closed = self.task_count['closed'].get(tag.name, 0)
            customized = tag.color or tag.icon

            if (count_open + count_closed) == 0 and not customized:
                self.tags.remove(tag.id)


    # --------------------------------------------------------------------------
    # BACKENDS
    # --------------------------------------------------------------------------

    def get_all_backends(self, disabled=False):
        """returns list of all registered backends for this DataStore.

        @param disabled: If disabled is True, attaches also the list of
                disabled backends
        @return list: a list of TaskSource objects
        """
        result = []
        for backend in self.backends.values():
            if backend.is_enabled() or disabled:
                result.append(backend)
        return result


    def get_backend(self, backend_id):
        """
        Returns a backend given its id.

        @param backend_id: a backend id
        @returns GTG.core.datastore.TaskSource or None: the requested backend,
                                                        or None
        """
        if backend_id in self.backends:
            return self.backends[backend_id]
        else:
            return None


    def register_backend(self, backend_dic):
        """
        Registers a TaskSource as a backend for this DataStore

        @param backend_dic: Dictionary object containing all the
                            parameters to initialize the backend
                            (filename...). It should also contain the
                            backend class (under "backend"), and its
                            unique id (under "pid")
        """
        if "backend" in backend_dic:
            if "pid" not in backend_dic:
                log.error("registering a backend without pid.")
                return None
            backend = backend_dic["backend"]
            first_run = backend_dic["first_run"]

            # Checking that is a new backend
            if backend.get_id() in self.backends:
                log.error("registering already registered backend")
                return None

            if first_run:
                backend.this_is_the_first_run(None)

            self.backends[backend.get_id()] = backend
            # we notify that a new backend is present
            self._backend_signals.backend_added(backend.get_id())
            # saving the backend in the correct dictionary (backends for
            # enabled backends, disabled_backends for the disabled ones)
            # this is useful for retro-compatibility
            if GenericBackend.KEY_ENABLED not in backend_dic:
                backend.set_parameter(GenericBackend.KEY_ENABLED, True)
            if GenericBackend.KEY_DEFAULT_BACKEND not in backend_dic:
                backend.set_parameter(GenericBackend.KEY_DEFAULT_BACKEND, True)
            # if it's enabled, we initialize it
            if backend.is_enabled() and \
                    (self.is_default_backend_loaded or backend.is_default()):

                backend.initialize(connect_signals=False)
                # Filling the backend
                # Doing this at start is more efficient than
                # after the GUI is launched
                backend.start_get_tasks()

            return backend
        else:
            log.error("Tried to register a backend without a pid")


    def _activate_non_default_backends(self, sender=None):
        """
        Non-default backends have to wait until the default loads before
        being  activated. This function is called after the first default
        backend has loaded all its tasks.

        @param sender: not used, just here for signal compatibility
        """

        self.is_default_backend_loaded = True
        for backend in self.backends.values():
            if backend.is_enabled() and not backend.is_default():
                self._backend_startup(backend)


    def _backend_startup(self, backend):
        """
        Helper function to launch a thread that starts a backend.

        @param backend: the backend object
        """

        def __backend_startup(self, backend):
            """
            Helper function to start a backend

            @param backend: the backend object
            """
            backend.initialize()
            backend.start_get_tasks()
            self.flush_all_tasks(backend.get_id())

        thread = threading.Thread(target=__backend_startup,
                                  args=(self, backend))
        thread.setDaemon(True)
        thread.start()


    def set_backend_enabled(self, backend_id, state):
        """
        The backend corresponding to backend_id is enabled or disabled
        according to "state".
        Disable:
        Quits a backend and disables it (which means it won't be
        automatically loaded next time GTG is started)
        Enable:
        Reloads a disabled backend. Backend must be already known by the
        Datastore

        @param backend_id: a backend id
        @param state: True to enable, False to disable
        """
        if backend_id in self.backends:
            backend = self.backends[backend_id]
            current_state = backend.is_enabled()
            if current_state is True and state is False:
                # we disable the backend
                # FIXME!!!
                threading.Thread(target=backend.quit,
                                 kwargs={'disable': True}).start()
            elif current_state is False and state is True:
                if self.is_default_backend_loaded is True:
                    self._backend_startup(backend)
                else:
                    # will be activated afterwards
                    backend.set_parameter(GenericBackend.KEY_ENABLED,
                                          True)


    def remove_backend(self, backend_id):
        """
        Removes a backend, and forgets it ever existed.

        @param backend_id: a backend id
        """
        if backend_id in self.backends:
            backend = self.backends[backend_id]
            if backend.is_enabled():
                self.set_backend_enabled(backend_id, False)
            # FIXME: to keep things simple, backends are not notified that they
            #       are completely removed (they think they're just
            #       deactivated). We should add a "purge" call to backend to
            #       let them know that they're removed, so that they can
            #       remove all the various files they've created. (invernizzi)

            # we notify that the backend has been deleted
            self._backend_signals.backend_removed(backend.get_id())
            del self.backends[backend_id]


    def backend_change_attached_tags(self, backend_id, tag_names):
        """
        Changes the tags for which a backend should store a task

        @param backend_id: a backend_id
        @param tag_names: the new set of tags. This should not be a tag object,
                          just the tag name.
        """
        backend = self.backends[backend_id]
        backend.set_attached_tags(tag_names)


    def flush_all_tasks(self, backend_id):
        """
        This function will cause all tasks to be checked against the backend
        identified with backend_id. If tasks need to be added or removed, it
        will be done here.
        It has to be run after the creation of a new backend (or an alteration
        of its "attached tags"), so that the tasks which are already loaded in
        the Tree will be saved in the proper backends

        @param backend_id: a backend id
        """

        def _internal_flush_all_tasks():
            backend = self.backends[backend_id]
            for task in self.tasks.data:
                if self.please_quit:
                    break
                backend.queue_set_task(task.id)
        t = threading.Thread(target=_internal_flush_all_tasks)
        t.start()
        self.backends[backend_id].start_get_tasks()


    # --------------------------------------------------------------------------
    # TESTING AND UTILS
    # --------------------------------------------------------------------------

    def fill_with_samples(self, tasks_count: int) -> None:
        """Fill the Datastore with sample data."""

        def random_date(start: datetime = None):
            start = start or datetime.now()
            end = start + timedelta(days=random.randint(1, 365 * 5))

            return start + (end - start)


        def random_boolean() -> bool:
            return bool(random.getrandbits(1))


        def random_word(length: int) -> str:
            letters = string.ascii_lowercase
            return ''.join(random.choice(letters) for _ in range(length))


        if tasks_count == 0:
            return


        tags_count = random.randint(tasks_count // 10, tasks_count)
        search_count = random.randint(0, tasks_count // 10)
        task_sizes = [random.randint(0, 200) for _ in range(10)]
        randint = random.randint
        tag_words = [random_word(randint(2, 14)) for _ in range(tags_count)]

        # Generate saved searches
        for _ in range(search_count):
            name = random_word(randint(2, 10))
            query = random_word(randint(2, 10))
            self.saved_searches.new(name, query)

        # Generate tags
        for tag_name in tag_words:
            tag = self.tags.new(tag_name)
            tag.actionable = random_boolean()
            tag.color = self.tags.generate_color()


        # Parent the tags
        for tag in self.tags.data:
            if bool(random.getrandbits(1)):
                parent = random.choice(self.tags.data)

                if tag.id == parent.id:
                    continue

                self.tags.parent(tag.id, parent.id)


        # Generate tasks
        for _ in range(tasks_count):
            title = ''
            content = ''
            content_size = random.choice(task_sizes)

            for _ in range(random.randint(1, 15)):
                word = random_word(randint(4, 20))

                if word in tag_words:
                    word = '@' + word

                title += word + ' '

            task = self.tasks.new(title)

            for _ in range(random.randint(0, 10)):
                tag = self.tags.find(random.choice(tag_words))
                task.add_tag(tag)

            if random_boolean():
                task.toggle_active()

            if random_boolean():
                task.toggle_dismiss()

            for _ in range(random.randint(0, content_size)):
                word = random_word(randint(4, 20))

                if word in tag_words:
                    word = '@' + word

                content += word + ' '
                content += '\n' if random_boolean() else ''

            task.content = content

            if random_boolean():
                task.date_start = random_date()

            if random_boolean():
                task.date_due = Date(random_date())


        # Parent the tasks
        for task in self.tasks.data:
            if bool(random.getrandbits(1)):
                parent = random.choice(self.tasks.data)

                if task.id == parent.id:
                    continue

                self.tasks.parent(task.id, parent.id)
