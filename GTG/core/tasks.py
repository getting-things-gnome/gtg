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

"""Everything related to tasks."""


from gi.repository import GObject, Gio, Gtk, Gdk
from gettext import gettext as _

from uuid import uuid4, UUID
import logging
from typing import Callable, Any, Optional
from enum import Enum
import re
import datetime
from operator import attrgetter

from lxml.etree import Element, SubElement, CDATA

from GTG.core.base_store import BaseStore
from GTG.core.tags import Tag, TagStore
from GTG.core.dates import Date

log = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# REGEXES
# ------------------------------------------------------------------------------

TAG_REGEX = re.compile(r'^\B\@\w+(\-\w+)*\,*')
SUB_REGEX = re.compile(r'\{\!.+\!\}')


# ------------------------------------------------------------------------------
# TASK STATUS
# ------------------------------------------------------------------------------

class Status(Enum):
    """Status for a task."""

    ACTIVE = 'Active'
    DONE = 'Done'
    DISMISSED = 'Dismissed'


class Filter(Enum):
    """Types of filters."""

    ACTIVE = 'Active'
    ACTIONABLE = 'Actionable'
    CLOSED = 'Closed'
    STATUS = 'Status'
    TAG = 'Tag'
    PARENT = 'Parent'
    CHILDREN = 'Children'


# ------------------------------------------------------------------------------
# TASK
# ------------------------------------------------------------------------------

DEFAULT_TITLE = _('New Task')


class Task(GObject.Object):
    """A single task."""

    __gtype_name__ = 'gtg_Task'

    def __init__(self, id: UUID, title: str) -> None:
        self.id = id
        self.raw_title = title.strip('\t\n')
        self.content =  ''
        self.tags = set()
        self.children = []
        self.status = Status.ACTIVE
        self.parent = None

        self._date_added = Date.no_date()
        self._date_due = Date.no_date()
        self._date_start = Date.no_date()
        self._date_closed = Date.no_date()
        self._date_modified = Date(datetime.datetime.now())

        self._has_date_due = False
        self._has_date_start = False

        self._date_due_str = ''
        self._date_start_str = ''
        self._is_active = True

        self._is_recurring = False
        self.recurring_term = None
        self.recurring_updated_date = datetime.datetime.now()
        
        self.attributes = {}

        self.duplicate_cb = NotImplemented

        super(Task, self).__init__()


    @GObject.Property(type=bool, default=True)
    def is_actionable(self) -> bool:
        """Determine if this task is actionable."""

        actionable_tags = all(t.actionable for t in self.tags)
        active_children = all(t.status != Status.ACTIVE for t in self.children)
        days_left = self._date_start.days_left()
        can_start = True if not days_left else days_left <= 0

        return (self.status == Status.ACTIVE
                and self._date_due != Date.someday()
                and actionable_tags
                and active_children
                and can_start)


    def toggle_active(self, propagated: bool = False) -> None:
        """Toggle between possible statuses."""

        if self.status is Status.ACTIVE:
            status = Status.DONE

        else:
            status = Status.ACTIVE

        self.set_status(status, propagated)


    def toggle_dismiss(self, propagated: bool = False) -> None:
        """Set this task to be dismissed."""

        if self.status is Status.ACTIVE:
            status = Status.DISMISSED

        else:
            status = Status.ACTIVE

        self.set_status(status, propagated)


    def set_status(self, status: Status, propagated: bool = False) -> None:
        """Set status for task."""

        if self.status == Status.ACTIVE:
            for t in self.tags:
                t.task_count_open -= 1
            
            if self.is_actionable:
                for t in self.tags:
                    t.task_count_actionable -= 1

        else:
            for t in self.tags:
                t.task_count_closed -= 1

        self.status = status
        self.is_active = (status == Status.ACTIVE)

        if status != Status.ACTIVE:
            self.date_closed = Date.today()

            # If the task is recurring, it must be duplicate with
            # another task id and the next occurence of the task
            # while preserving child/parent relations.
            # For a task to be duplicated, it must satisfy 3 rules.
            #   1- It is recurring.
            #   2- It has no parent or no recurring parent.
            #   3- It was directly marked as done (not by propagation from its parent).
            if (self._is_recurring and not propagated and 
                 not self.is_parent_recurring()):
                self.duplicate_cb(self)
            
        else:
            self.date_closed = Date.no_date()

            if self.parent and self.parent.status is not Status.ACTIVE:
                self.parent.set_status(status, propagated=True)

        if status == Status.ACTIVE:
            for t in self.tags:
                t.task_count_open += 1
            
            if self.is_actionable:
                for t in self.tags:
                    t.task_count_actionable += 1

        else:
            for t in self.tags:
                t.task_count_closed += 1

            
        for child in self.children:
            child.set_status(status, propagated=True)


    @property
    def date_due(self) -> Date:
        return self._date_due


    @date_due.setter
    def date_due(self, value: Date) -> None:
        self._date_due = value
        self.has_date_due = bool(value)
        
        if value:
            self.date_due_str = self._date_due.to_readable_string()
        else:
            self.date_due_str = ''

        for tag in self.tags:
            if self.is_actionable:
                tag.task_count_actionable += 1 
            else:
                tag.task_count_actionable -= 1 

        if not value or value.is_fuzzy():
            return

        for child in self.children:
            if (child.date_due
               and not child.date_due.is_fuzzy()
               and child.date_due > value):

                child.date_due = value

        if (self.parent
           and self.parent.date_due
           and self.parent.date_due.is_fuzzy()
           and self.parent.date_due < value):
            self.parent.date_due = value


    @property
    def date_added(self) -> Date:
        return self._date_added


    @date_added.setter
    def date_added(self, value: Any) -> None:
        self._date_added = Date(value)


    @property
    def date_start(self) -> Date:
        return self._date_start


    @date_start.setter
    def date_start(self, value: Any) -> None:
        if isinstance(value, str):
            self._date_start = Date.parse(value)
        else:
            self._date_start = Date(value)

        self.has_date_start = bool(value)
        self.date_start_str = self._date_start.to_readable_string()


    @property
    def date_closed(self) -> Date:
        return self._date_closed


    @date_closed.setter
    def date_closed(self, value: Any) -> None:
        self._date_closed = Date(value)


    @property
    def date_modified(self) -> Date:
        return self._date_modified


    @date_modified.setter
    def date_modified(self, value: Any) -> None:
        self._date_modified = Date(value)


    @GObject.Property(type=str)
    def title(self) -> str:
        return self.raw_title


    @title.setter
    def title(self, value) -> None:
        self.raw_title = value.strip('\t\n') or _('(no title)')


    @GObject.Property(type=str)
    def excerpt(self) -> str:
        if not self.content:
            return ''

        # Strip tags
        txt = TAG_REGEX.sub('', self.content)

        # Strip subtasks
        txt = SUB_REGEX.sub('', txt)

        # Strip blank lines and set within char limit
        return f'{txt.strip()[:50]}…'


    def add_tag(self, tag: Tag) -> None:
        """Add a tag to this task."""

        if isinstance(tag, Tag):
            if tag not in self.tags:
                self.tags.add(tag)

                if self.status == Status.ACTIVE:
                    tag.task_count_open += 1
                else: 
                    tag.task_count_closed += 1
                
                if self.is_actionable:
                    tag.task_count_actionable += 1
        else:
            raise ValueError


    def remove_tag(self, tag_name: str) -> None:
        """Remove a tag from this task."""

        for t in self.tags.copy():
            if t.name == tag_name:
                self.tags.remove(t)

                if self.status == Status.ACTIVE:
                    t.task_count_open -= 1
                else: 
                    t.task_count_closed -= 1
                
                if self.is_actionable:
                    t.task_count_actionable -= 1

                self.content = (self.content.replace(f'{tag_name}\n\n', '')
                                            .replace(f'{tag_name},', '')
                                            .replace(f'{tag_name}', ''))


    def rename_tag(self, old_tag_name: str, new_tag_name: str) -> None:
        """Replace a tag's name in the content."""

        self.content = (self.content.replace(f'@{old_tag_name}', 
                                             f'@{new_tag_name}'))


    @property
    def days_left(self) -> Optional[Date]:
        return self.date_due.days_left()


    def update_modified(self) -> None:
        """Update the modified property."""

        self._date_modified = Date(datetime.datetime.now())


    def set_recurring(self, recurring: bool, recurring_term: str = None, newtask=False):
        """Sets a task as recurring or not, and its recurring term.

        Like anything related to dates, repeating tasks are subtle and complex
        when creating a new task, the due date is calculated from either the
        current date or the start date, while we get the next occurrence of a
        task not from the current date but from the due date itself.
        
        However when we are retrieving the task from the XML files, we should
        only set the the recurring_term.

        There are 4 cases to acknowledge when setting a task to recurring:
          - if repeating but the term is invalid: it will be set to False.
          - if repeating and the term is valid: we set it to True.
          - if not repeating and the term is valid: we set the bool attr to True and set the term.
          - if not repeating and the term is invalid: we set it to False and keep the previous term.

        Setting a task as recurrent implies that the children of a recurrent
        task will be also set to recurrent and will inherit their parent's
        recurring term

        Args:
            recurring (bool): True if the task is recurring and False if not.
            recurring_term (str, optional): the recurring period of a task (every Monday, day..).
                                            Defaults to None.
            newtask (bool, optional): if this is a new task, we must set the due_date.
                                      Defaults to False.
        """
        def is_valid_term():
            """ Verify if the term is valid and returns the appropriate Due date.

            Return a tuple of (bool, Date)
            """
            if recurring_term is None:
                return False, None

            try:
                # If a start date is already set,
                # we should calculate the next date from that day.
                if self.date_start == Date.no_date():
                    start_from = Date(datetime.datetime.now())
                else:
                    start_from = self.date_start

                newdate = start_from.parse_from_date(recurring_term, newtask)

                return True, newdate

            except ValueError:
                return False, None

        self._is_recurring = recurring

        # We verifiy if the term passed is valid
        valid, newdate = is_valid_term()
        recurring_term = recurring_term if valid else None

        if self._is_recurring:
            if not valid:
                self.recurring_term = None
                self._is_recurring = False
            else:
                self.recurring_term = recurring_term
                self.recurring_updated_date = datetime.datetime.now()

                if newtask:
                    self.date_due = newdate
        else:
            if valid:
                self.recurring_term = recurring_term
                self.recurring_updated_date = datetime.datetime.now()

        # setting its children to recurrent
        for child in self.children:
            if child.status is Status.ACTIVE:
                child.set_recurring(self._is_recurring, self.recurring_term)

                if self._is_recurring:
                    child.date_due = newdate
        
        self.notify('is_recurring')


    def toggle_recurring(self):
        """ Toggle a task's recurrency ON/OFF. Use this function to toggle, not set_recurring"""

        # If there is no recurring_term, We assume it to recur every day.
        newtask = False

        if self.recurring_term is None:
            self.recurring_term = 'day'
            newtask = True

        self.set_recurring(not self._is_recurring, self.recurring_term, newtask)


    def inherit_recursion(self):
        """ Inherits the recurrent state of the parent.
                If the task has a recurrent parent, it must be set to recur, itself.
        """
        if self.parent and self.parent._is_recurring:
            self.set_recurring(True, self.parent.recurring_term)
            self.date_due = self.parent.date_due
        else:
            self._is_recurring = False


    def is_parent_recurring(self):
        """Determine if the parent task is recurring."""
        
        return (self.parent and 
                self.parent.status == Status.ACTIVE 
                and self.parent._is_recurring)


    def get_next_occurrence(self):
        """Calcutate the next occurrence of a recurring task

        To know which is the correct next occurrence there are two rules:
        - if the task was marked as done before or during the open period (before the duedate);
          in this case, we need to deal with the issue of tasks that recur on the same date.
          example: due_date is 09/09 and done_date is 09/09
        - if the task was marked after the due date, we need to figure out the next occurrence
          after the current date(today).

        Raises:
            ValueError: if the recurring_term is invalid

        Returns:
            Date: the next due date of a task
        """

        today = datetime.date.today()
        
        if today <= self.date_due:
            try:
                nextdate = self.date_due.parse_from_date(self.recurring_term, newtask=False)

                while nextdate <= self.date_due:
                    nextdate = nextdate.parse_from_date(self.recurring_term, newtask=False)

                return nextdate

            except Exception:
                raise ValueError(f'Invalid recurring term {self.recurring_term}')

        elif today > self.date_due:
            try:
                next_date = self.date_due.parse_from_date(self.recurring_term, newtask=False)

                while next_date < datetime.date.today():
                    next_date = next_date.parse_from_date(self.recurring_term, newtask=False)
                    
                return next_date

            except Exception:
                raise ValueError(f'Invalid recurring term {self.recurring_term}')

    # -----------------------------------------------------------------------
    # Bind Properties
    #
    # Since PyGobject doesn't support bind_property_full() yet
    # we can't do complex binds. These props below serve as a 
    # workaround so that we can use them with the regular 
    # bind_property().
    # -----------------------------------------------------------------------

    @GObject.Property(type=bool, default=False)
    def is_recurring(self) -> bool:
        return self._is_recurring


    @GObject.Property(type=bool, default=False)
    def has_date_due(self) -> bool:
        return self._has_date_due


    @has_date_due.setter
    def set_has_date_due(self, value) -> None:
        self._has_date_due = value


    @GObject.Property(type=bool, default=False)
    def has_date_start(self) -> bool:
        return self._has_date_start


    @has_date_start.setter
    def set_has_date_start(self, value) -> None:
        self._has_date_start = value


    @GObject.Property(type=str)
    def date_start_str(self) -> str:
        return self._date_start_str


    @date_start_str.setter
    def set_date_start_str(self, value) -> None:
        self._date_start_str = value


    @GObject.Property(type=str)
    def date_due_str(self) -> str:
        return self._date_due_str


    @date_due_str.setter
    def set_date_due_str(self, value) -> None:
        self._date_due_str = value


    @GObject.Property(type=bool, default=True)
    def is_active(self) -> bool:
        return self._is_active


    @is_active.setter
    def set_is_active(self, value) -> None:
        self._is_active = value


    @GObject.Property(type=bool, default=False)
    def has_children(self) -> bool:
        return bool(len(self.children))


    @GObject.Property(type=str)
    def icons(self) -> str:
        icons_text = ''
        for t in self.tags:
            if t.icon:
                icons_text += t.icon

        return icons_text


    @GObject.Property(type=str)
    def row_css(self) -> str:
        for tag in self.tags:
            if tag.color:
                color = Gdk.RGBA()
                color.parse(tag.color)
                color.alpha = 0.1
                return '* { background:' + color.to_string() + '; }'


    @GObject.Property(type=str)
    def tag_colors(self) -> str:
        return ','.join(t.color for t in self.tags 
                        if t.color and not t.icon)


    @GObject.Property(type=bool, default=False)
    def show_tag_colors(self) -> str:
        return any(t.color and not t.icon for t in self.tags)


    @property
    def tag_names(self) -> list[str]:
        return [ t.name for t in self.tags ]
    

    def set_attribute(self, att_name, att_value, namespace="") -> None:
        """Set an arbitrary attribute."""

        val = str(att_value)
        self.attributes[(namespace, att_name)] = val


    def get_attribute(self, att_name, namespace="") -> str | None:
        """Get an attribute."""

        return self.attributes.get((namespace, att_name), None)


    def __str__(self) -> str:
        """String representation."""

        return f'Task: {self.title} ({self.id})'


    def __repr__(self) -> str:
        """String representation."""

        tags = ', '.join([t.name for t in self.tags])
        return (f'Task "{self.title}" with id "{self.id}".'
                f'Status: {self.status}, tags: {tags}')


    def __eq__(self, other) -> bool:
        """Equivalence."""

        return self.id == other.id


    def __hash__(self) -> int:
        """Hash (used for dicts and sets)."""

        return hash(self.id)


# ------------------------------------------------------------------------------
# STORE
# ------------------------------------------------------------------------------

class TaskStore(BaseStore):
    """A tree of tasks."""

    __gtype_name__ = 'gtg_TaskStore'

    #: Tag to look for in XML
    XML_TAG = 'task'

    def __init__(self) -> None:
        super().__init__()

        self.model = Gio.ListStore.new(Task)
        self.tree_model = Gtk.TreeListModel.new(self.model, False, False, self.model_expand)


    def model_expand(self, item):
        model = Gio.ListStore.new(Task)

        if type(item) == Gtk.TreeListRow:
            item = item.get_item()

        # open the first one
        if item.children:
            for child in item.children:
                model.append(child)

        return Gtk.TreeListModel.new(model, False, False, self.model_expand)


    def __str__(self) -> str:
        """String representation."""

        return f'Task Store. Holds {len(self.lookup)} task(s)'


    def get(self, tid: UUID) -> Task:
        """Get a task by name."""

        return self.lookup[tid]


    def duplicate_for_recurrent(self, task: Task) -> Task:
        """Duplicate a task for the next ocurrence."""
        
        new_task = self.new(task.title)
        new_task.tags = task.tags
        new_task.content = task.content
        new_task.date_added = task.date_added
        new_task.date_due = task.get_next_occurrence()

        # Only goes through for the first task 
        if task.parent and task.parent.is_active:
            self.parent(new_task.id, task.parent.id)

        for child in task.children:
            new_child = self.duplicate_for_recurrent(child)
            self.parent(new_child.id, new_task.id)

        log.debug("Duplicated task %s as task %s", task.id, new_task.id)
        return new_task
        

    def new(self, title: str = None, parent: UUID = None) -> Task:
        """Create a new task and add it to the store."""

        tid = uuid4()
        title = title or DEFAULT_TITLE
        task = Task(id=tid, title=title)
        task.date_added = Date.now()

        if parent:
            self.add(task, parent)
        else:
            self.add(task)

        self.emit('added', task)
        return task


    def from_xml(self, xml: Element, tag_store: TagStore) -> None:
        """Load up tasks from a lxml object."""

        elements = list(xml.iter(self.XML_TAG))

        for element in elements:
            tid = element.get('id')
            title = element.find('title').text
            status = element.get('status')

            task = Task(id=tid, title=title)

            dates = element.find('dates')

            modified = dates.find('modified').text
            task.date_modified = Date(datetime.datetime.fromisoformat(modified))

            added = dates.find('added').text
            task.date_added = Date(datetime.datetime.fromisoformat(added))

            if status == 'Done':
                task.status = Status.DONE
            elif status == 'Dismissed':
                task.status = Status.DISMISSED

            # Dates
            try:
                closed = Date.parse(dates.find('done').text)
                task.date_closed = closed
            except AttributeError:
                pass

            fuzzy_due_date = Date.parse(dates.findtext('fuzzyDue'))
            due_date = Date.parse(dates.findtext('due'))

            if fuzzy_due_date:
                task.date_due = fuzzy_due_date
            elif due_date:
                task.date_due = due_date

            fuzzy_start = dates.findtext('fuzzyStart')
            start = dates.findtext('start')

            if fuzzy_start:
                task.date_start = Date(fuzzy_start)
            elif start:
                task.date_start = Date(start)

            taglist = element.find('tags')

            if taglist is not None:
                for t in taglist.iter('tag'):
                    try:
                        tag = tag_store.get(t.text)
                        task.add_tag(tag)
                    except KeyError:
                        pass

            # Content
            content = element.find('content').text or ''
            content = content.replace(']]&gt;', ']]>')
            task.content = content

            self.add(task)

            log.debug('Added %s', task)


        # All tasks have been added, now we parent them
        for element in elements:
            parent_tid = element.get('id')
            subtasks = element.find('subtasks')

            for sub in subtasks.findall('sub'):
                self.parent(sub.text, parent_tid)


    def to_xml(self) -> Element:
        """Serialize the taskstore into a lxml element."""

        root = Element('tasklist')

        for task in self.lookup.values():
            element = SubElement(root, self.XML_TAG)
            element.set('id', str(task.id))
            element.set('status', task.status.value)

            title = SubElement(element, 'title')
            title.text = task.title

            tags = SubElement(element, 'tags')

            for t in task.tags:
                tag_tag = SubElement(tags, 'tag')
                tag_tag.text = str(t.id)

            dates = SubElement(element, 'dates')

            added_date = SubElement(dates, 'added')
            added_date.text = str(task.date_added)

            modified_date = SubElement(dates, 'modified')
            modified_date.text = str(task.date_modified)

            if task.status == Status.DONE:
                done_date = SubElement(dates, 'done')
                done_date.text = str(task.date_closed)

            if task.date_due:
                due = SubElement(dates, 'due')
                due.text = str(task.date_due)

            if task.date_start:
                start = SubElement(dates, 'start')
                start.text = str(task.date_start)

            subtasks = SubElement(element, 'subtasks')

            for subtask in task.children:
                sub = SubElement(subtasks, 'sub')
                sub.text = str(subtask.id)

            content = SubElement(element, 'content')
            text = task.content

            # Poor man's encoding.
            # CDATA's only poison is this combination of characters.
            text = text.replace(']]>', ']]&gt;')
            content.text = CDATA(text)

        return root

    def add(self, item: Any, parent_id: UUID = None) -> None:
        """Add a tag to the tagstore."""

        super().add(item, parent_id)

        if not parent_id:
            self.model.append(item)
        
        item.duplicate_cb = self.duplicate_for_recurrent
        self.notify('task_count_all')
        self.notify('task_count_no_tags')

        self.emit('added', item)


    def remove(self, item_id: UUID) -> None:
        """Remove an existing task."""

        # Remove from UI
        item = self.lookup[item_id]
        pos = self.model.find(item)
        self.model.remove(pos[1])

        super().remove(item_id)

        self.notify('task_count_all')
        self.notify('task_count_no_tags')


    def parent(self, item_id: UUID, parent_id: UUID) -> None:

        super().parent(item_id, parent_id)

        # Remove from UI
        item = self.lookup[item_id]
        pos = self.model.find(item)
        self.model.remove(pos[1])


    def unparent(self, item_id: UUID, parent_id: UUID) -> None:

        super().unparent(item_id, parent_id)
        item = self.lookup[item_id]
        self.model.append(item)


    def filter(self, filter_type: Filter, arg = None) -> list:
        """Filter tasks according to a filter type."""

        def filter_tag(tag: str) -> list:
            """Filter tasks that only have a specific tag."""

            output = []

            for t in self.data:
                tags = [_tag for _tag in t.tags]

                # Include the tag's children
                for _tag in t.tags:
                    for child in _tag.children:
                        tags.append(child)

                if tag in tags:
                    output.append(t)

            return output


        if filter_type == Filter.STATUS:
            return [t for t in self.data if t.status == arg]

        elif filter_type == Filter.ACTIVE:
            return [t for t in self.data if t.status == Status.ACTIVE]

        elif filter_type == Filter.CLOSED:
            return [t for t in self.data if t.status != Status.ACTIVE]

        elif filter_type == Filter.ACTIONABLE:
            return [t for t in self.data if t.is_actionable]

        elif filter_type == Filter.PARENT:
            return [t for t in self.lookup.values() if not t.parent]

        elif filter_type == Filter.CHILDREN:
            return [t for t in self.lookup.values() if t.parent]

        elif filter_type == Filter.TAG:
            if type(arg) == list:
                output = []

                for t in arg:
                    if output:
                        output = list(set(output) & set(filter_tag(t)))
                    else:
                        output = filter_tag(t)


                return output

            else:
                return filter_tag(arg)


    def filter_custom(self, key: str, condition: Callable) -> list:
        """Filter tasks according to a function."""

        return [t for t in self.lookup.values() if condition(getattr(t, key))]


    def sort(self, tasks: list = None,
             key: str = None, reverse: bool = False) -> None:
        """Sort a list of tasks in-place."""

        tasks = tasks or self.data
        key = key or 'date_added'

        for t in tasks:
            t.children.sort(key=attrgetter(key), reverse=reverse)

        tasks.sort(key=attrgetter(key), reverse=reverse)


    @GObject.Property(type=str)
    def task_count_all(self) -> str:
        return str(len(self.lookup.keys()))


    @GObject.Property(type=str)
    def task_count_no_tags(self) -> str:
        i = 0
        
        for task in self.lookup.values():
            if not task.tags:
                i += 1

        return str(i)
