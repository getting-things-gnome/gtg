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

from unittest import TestCase
from uuid import uuid4

from GTG.core.tasks import Task, Status, TaskStore, Filter
from GTG.core.tags import Tag, TagStore
from GTG.core.dates import Date

from lxml.etree import XML


class TestTask(TestCase):

    def test_default_task_from_store_is_new(self):
        task = TaskStore().new()

        self.assertTrue(task.is_new())

    def test_task_with_content_is_not_new(self):
        task = TaskStore().new()
        task.content = 'foobar'

        self.assertFalse(task.is_new())

    def test_task_with_title_is_not_new(self):
        task = TaskStore().new(title='My new task')

        self.assertFalse(task.is_new())

    def test_title(self):
        task = Task(id=uuid4(), title='\tMy Title\n')

        self.assertEqual(task.title, 'My Title')


    def test_excerpt_normal(self):
        task = Task(id=uuid4(), title='A Task')

        self.assertEqual(task.excerpt, '')

        task.content = ('This is a sample content with some @tags, and some '
                        'extra text for padding. I could go on and on and on '
                        'and on and on.')


        expected = ('This is a sample content with some @tags, and some '
                    'extra text for padding. I cou…')

        self.assertEqual(task.excerpt, expected)


    def test_excerpt_empty_task(self):
        task = Task(id=uuid4(), title='A Task')

        self.assertEqual(task.excerpt, '')

        task.content = ''

        self.assertEqual(task.excerpt, '')


    def test_excerpt_only_tags(self):
        task = Task(id=uuid4(), title='A Task')

        self.assertEqual(task.excerpt, '')

        task.content = '@sometag, @someother'

        self.assertEqual(task.excerpt, '')


    def test_excerpt_only_whitespace(self):
        task = Task(id=uuid4(), title='A Task')

        self.assertEqual(task.excerpt, '')

        task.content = ('     '
                        ''
                        '   ')

        self.assertEqual(task.excerpt, '')


    def test_toggle_active_single(self):
        task = Task(id=uuid4(), title='A Task')

        self.assertEqual(task.status, Status.ACTIVE)

        task.toggle_active()
        self.assertEqual(task.status, Status.DONE)
        self.assertEqual(task.date_closed, Date.today())

        task.toggle_active()
        self.assertEqual(task.status, Status.ACTIVE)
        self.assertEqual(task.date_closed, Date.no_date())

    def test_toggle_active_children(self):
        task = Task(id=uuid4(), title='A Task')
        task2 = Task(id=uuid4(), title='A Child Task')
        task.children.append(task2)
        task2.parent = task

        task.toggle_active()
        self.assertEqual(task.status, Status.DONE)
        self.assertEqual(task.date_closed, Date.today())
        self.assertEqual(task2.status, Status.DONE)
        self.assertEqual(task2.date_closed, Date.today())

        task.toggle_active()
        self.assertEqual(task.status, Status.ACTIVE)
        self.assertEqual(task.date_closed, Date.no_date())
        self.assertEqual(task2.status, Status.ACTIVE)
        self.assertEqual(task2.date_closed, Date.no_date())


    def test_toggle_dismiss_single(self):
        task = Task(id=uuid4(), title='A Task')

        task.toggle_dismiss()
        self.assertEqual(task.status, Status.DISMISSED)
        self.assertEqual(task.date_closed, Date.today())

        task.toggle_dismiss()
        self.assertEqual(task.status, Status.ACTIVE)
        self.assertEqual(task.date_closed, Date.no_date())


    def test_toggle_dismiss_children(self):
        task = Task(id=uuid4(), title='A Task')
        task2 = Task(id=uuid4(), title='A Child Task')
        task.children.append(task2)
        task2.parent = task

        task.toggle_dismiss()
        self.assertEqual(task.status, Status.DISMISSED)
        self.assertEqual(task.date_closed, Date.today())
        self.assertEqual(task2.status, Status.DISMISSED)
        self.assertEqual(task2.date_closed, Date.today())

        task.toggle_dismiss()
        self.assertEqual(task.status, Status.ACTIVE)
        self.assertEqual(task.date_closed, Date.no_date())
        self.assertEqual(task2.status, Status.ACTIVE)
        self.assertEqual(task2.date_closed, Date.no_date())


    def test_tags(self):
        task = Task(id=uuid4(), title='A Task')
        tag = Tag(id=uuid4(), name='A Tag')

        task.add_tag(tag)
        self.assertEqual(len(task.tags), 1)

        with self.assertRaises(ValueError):
            task.add_tag('my super tag')

        self.assertEqual(len(task.tags), 1)

        task.add_tag(tag)
        self.assertEqual(len(task.tags), 1)

        task.remove_tag('A Tag')
        self.assertEqual(len(task.tags), 0)


    def test_remove_tag_with_regex_metacharacters(self):
        """Tag names are injected into the content regexes verbatim.

        A name carrying regex metacharacters either changes the
        pattern's meaning (parentheses become a group, so the tag is
        never removed) or makes it invalid ('a[b' opens a character
        set that is never closed, which raises re.error). GTG's editor
        already accepts those characters in a tag, and since #1305
        CalDAV categories reach the store verbatim too, so a remote
        name can now crash the removal.
        """
        for name in ('x(y)', 'a[b', '50%', 'a+b', 'v1.2', 'fin*',
                     'Deck:_Server', "7-N'importe_ou"):
            task = Task(id=uuid4(), title='A Task')
            task.content = f'start @{name} end'
            task.add_tag(Tag(id=uuid4(), name=name))

            task.remove_tag(name)

            self.assertEqual(0, len(task.tags), name)
            self.assertNotIn('@', task.content,
                             f'{name!r} was left behind in the content')

    def test_remove_tag_leaves_longer_tags_alone(self):
        task = Task(id=uuid4(), title='A Task')
        task.content = 'start @work, @workshop, @work-item end'
        task.add_tag(Tag(id=uuid4(), name='work'))

        task.remove_tag('work')

        self.assertIn('@workshop', task.content)
        self.assertIn('@work-item', task.content)

    def test_rename_tag_with_regex_metacharacters(self):
        task = Task(id=uuid4(), title='A Task')
        task.content = 'start @x(y) end'

        task.rename_tag('x(y)', 'z')

        self.assertIn('@z', task.content)
        self.assertNotIn('@x(y)', task.content)


    def test_tags_children(self):
        task1 = Task(id=uuid4(), title='A Parent Task')
        task2 = Task(id=uuid4(), title='A Child Task')

        tag1 = Tag(id=uuid4(), name='A Tag')
        tag2 = Tag(id=uuid4(), name='Another Tag')

        task1.children.append(task2)
        task1.add_tag(tag1)

        self.assertEqual(len(task1.tags), 1)
        self.assertEqual(len(task2.tags), 0)

        task2.add_tag(tag2)
        self.assertEqual(len(task1.tags), 1)
        self.assertEqual(len(task2.tags), 1)
        self.assertIn(tag2, task2.tags)


    def test_due_date(self):
        task1 = Task(id=uuid4(), title='A Parent Task')
        task2 = Task(id=uuid4(), title='A Child Task')
        task3 = Task(id=uuid4(), title='Another Child Task')
        task4 = Task(id=uuid4(), title='Yet Another Child Task')
        task5 = Task(id=uuid4(), title='So many Child Tasks')
        task6 = Task(id=uuid4(), title='More childs')

        task1.children.append(task2)
        task1.children.append(task3)
        task3.children.append(task4)
        task4.children.append(task5)
        task4.children.append(task6)

        # Test changing parent's due
        random_date = Date('1996-2-3')
        random_date2 = Date('2010-7-10')

        task1.date_due = random_date
        self.assertEqual(task1.date_due, random_date)

        task2.date_due = random_date
        task3.date_due = random_date
        task4.date_due = random_date
        task5.date_due = random_date
        task6.date_due = random_date

        # Test changes in the parent - Fuzzy
        task1.date_due = Date.now()

        self.assertEqual(task1.date_due, Date.now())
        self.assertEqual(task2.date_due, random_date)
        self.assertEqual(task3.date_due, random_date)
        self.assertEqual(task4.date_due, random_date)
        self.assertEqual(task5.date_due, random_date)
        self.assertEqual(task6.date_due, random_date)

        # Test changing child's due (after parent's)
        task3.date_due = random_date2
        self.assertEqual(task3.date_due, random_date2)
        self.assertEqual(task4.date_due, random_date)
        self.assertEqual(task5.date_due, random_date)
        self.assertEqual(task6.date_due, random_date)


        # Test changing child's due (before parent's)
        task4.date_due = random_date2
        task3.date_due = random_date

        self.assertEqual(task4.date_due, random_date)
        self.assertEqual(task5.date_due, random_date)
        self.assertEqual(task6.date_due, random_date)

        # Test changing parent's due (before child's)
        task4.date_due = random_date
        task3.date_due = random_date2

        self.assertEqual(task3.date_due, random_date2)
        self.assertEqual(task4.date_due, random_date)

        # Test changing parent's due (None or nodate)
        task2.date_due = random_date
        task1.date_due = Date.no_date()
        self.assertEqual(task2.date_due, random_date)


    def test_new_simple(self):
        store = TaskStore()
        task = store.new('My Task')

        self.assertIsInstance(task, Task)
        self.assertEqual(store.get(task.id), task)
        self.assertEqual(task.title, 'My Task')
        self.assertEqual(store.count(), 1)


    def test_new_tree(self):
        store = TaskStore()

        root_task = store.new('My Root Task')
        store.new('My Child Task', root_task.id)

        self.assertEqual(store.count(), 2)
        self.assertEqual(store.count(root_only=True), 1)


    def test_parenting(self):
        store = TaskStore()

        root_task = store.new('My Root Task')
        child_task = store.new('My Child task')

        store.parent(child_task.id, root_task.id)

        self.assertEqual(store.count(), 2)
        self.assertEqual(store.count(root_only=True), 1)
        self.assertEqual(child_task.parent, root_task)
        self.assertEqual(root_task.children[0], child_task)

        store.unparent(child_task.id)

        self.assertEqual(store.count(), 2)
        self.assertEqual(store.count(root_only=True), 2)
        self.assertEqual(child_task.parent, None)
        self.assertEqual(len(root_task.children), 0)

        inner_child_task = store.new('Inner Child task')
        store.parent(child_task.id, root_task.id)
        store.parent(inner_child_task.id, child_task.id)

        self.assertEqual(store.count(), 3)
        self.assertEqual(store.count(root_only=True), 1)
        self.assertEqual(child_task.parent, root_task)
        self.assertEqual(root_task.children[0], child_task)
        self.assertEqual(child_task.children[0], inner_child_task)
        self.assertEqual(child_task.parent, root_task)
        self.assertEqual(inner_child_task.parent, child_task)

        store.unparent(inner_child_task.id)
        self.assertEqual(inner_child_task.parent, None)
        self.assertEqual(len(child_task.children), 0)


    def test_xml_load_simple(self):
        task_store = TaskStore()
        tag_store = TagStore()

        TAG_ID = '6f1ba7b3-a797-44b9-accd-303adaf04073'
        TASK_ID = '1d34df07-4185-43ad-adbd-698a86193411'

        tag = Tag(id=TAG_ID, name='My Tag')
        tag_store.add(tag)

        parsed_xml = XML(f'''
        <tasklist>
            <task id="{TASK_ID}" status="Active" recurring="False">
                <tags>
                    <tag>{TAG_ID}</tag>
                </tags>
                <title>My Task</title>
                <dates>
                    <added>2020-10-23T00:00:00</added>
                    <modified>2021-03-20T14:55:46.219761</modified>
                    <done></done>
                    <fuzzyDue></fuzzyDue>
                    <start>2010-07-20</start>
                </dates>
                <recurring enabled="false">
                    <term>None</term>
                </recurring>
                <subtasks/>
                <content><![CDATA[ My Content ]]></content>
            </task>
        </tasklist>
        ''')

        task_store.from_xml(parsed_xml, tag_store)
        self.assertEqual(task_store.count(), 1)


    def test_xml_load_tree(self):
        task_store = TaskStore()

        TASK_ID_1 = uuid4()
        TASK_ID_2 = uuid4()
        TASK_ID_3 = uuid4()
        TASK_ID_4 = uuid4()

        parsed_xml = XML(f'''
        <tasklist>
            <task id="{TASK_ID_1}" status="Active" recurring="False">
                <title>My Task</title>
                <dates>
                    <added>2020-10-23T00:00:00</added>
                    <modified>2021-03-20T14:55:46.219761</modified>
                    <done></done>
                    <fuzzyDue></fuzzyDue>
                    <start>2010-07-20</start>
                </dates>
                <recurring enabled="false">
                    <term>None</term>
                </recurring>
                <subtasks>
                    <sub>{TASK_ID_2}</sub>
                    <sub>{TASK_ID_3}</sub>
                </subtasks>

                <content><![CDATA[ My Content ]]></content>
            </task>

            <task id="{TASK_ID_2}" status="Active" recurring="False">
                <title>My Task</title>
                <dates>
                    <added>2020-10-23T00:00:00</added>
                    <modified>2021-03-20T14:55:46.219761</modified>
                    <done></done>
                    <fuzzyDue></fuzzyDue>
                    <start>2010-07-20</start>
                </dates>
                <recurring enabled="false">
                    <term>None</term>
                </recurring>
                <subtasks/>
                <content><![CDATA[ My Content ]]></content>
            </task>

            <task id="{TASK_ID_3}" status="Active" recurring="False">
                <title>My Task</title>
                <dates>
                    <added>2020-10-23T00:00:00</added>
                    <modified>2021-03-20T14:55:46.219761</modified>
                    <done></done>
                    <fuzzyDue></fuzzyDue>
                    <start>2010-07-20</start>
                </dates>
                <recurring enabled="false">
                    <term>None</term>
                </recurring>
                <subtasks>
                    <sub>{TASK_ID_4}</sub>
                </subtasks>

                <content><![CDATA[ My Content ]]></content>
            </task>

            <task id="{TASK_ID_4}" status="Active" recurring="False">
                <title>My Task</title>
                <dates>
                    <added>2020-10-23T00:00:00</added>
                    <modified>2021-03-20T14:55:46.219761</modified>
                    <done></done>
                    <fuzzyDue></fuzzyDue>
                    <start>2010-07-20</start>
                </dates>
                <recurring enabled="false">
                    <term>None</term>
                </recurring>
                <subtasks/>
                <content><![CDATA[ My Content ]]></content>
            </task>
        </tasklist>
        ''')

        task_store.from_xml(parsed_xml, None)
        self.assertEqual(task_store.count(), 4)
        self.assertEqual(task_store.count(root_only=True), 1)
        self.assertEqual(len(task_store.get(TASK_ID_1).children), 2)


    def test_xml_load_bad(self):
        task_store = TaskStore()

        TASK_ID_1 = uuid4()
        TASK_ID_2 = uuid4()

        parsed_xml = XML(f'''
        <tasklist>
            <task id="{TASK_ID_1}" status="Active" recurring="False">
                <title>My Task</title>
                <dates>
                    <added>2020-10-23T00:00:00</added>
                    <modified>2021-03-20T14:55:46.219761</modified>
                    <done></done>
                    <fuzzyDue></fuzzyDue>
                    <start>2010-07-20</start>
                </dates>
                <recurring enabled="false">
                    <term>None</term>
                </recurring>
                <subtasks>
                    <sub>ghost-subtask-that-matches-no-task</sub>
                </subtasks>

                <content><![CDATA[ My Content ]]></content>
            </task>

            <task id="{TASK_ID_2}" status="Active" recurring="False">
                <title>My Task</title>
                <dates>
                    <added>2020-10-23T00:00:00</added>
                    <modified>2021-03-20T14:55:46.219761</modified>
                    <done></done>
                    <fuzzyDue></fuzzyDue>
                    <start>2010-07-20</start>
                </dates>
                <recurring enabled="false">
                    <term>None</term>
                </recurring>
                <subtasks/>
                <content><![CDATA[ My Content ]]></content>
            </task>
        </tasklist>
        ''')

        # a <sub> pointing at no existing task is still rejected, now as
        # a KeyError from parent() (missing task) rather than a ValueError
        # from casting the id: non-canonical ids no longer crash the cast
        with self.assertRaises(KeyError):
            task_store.from_xml(parsed_xml, None)


    def test_xml_write_simple(self):
        task_store = TaskStore()

        task_store.new('My Task')
        task_store.new('My Other Task')
        task_store.new('My Other Other Task')
        task_store.new('My Other Other Other Task')

        xml_root = task_store.to_xml()
        self.assertEqual(len(xml_root), 4)


    def test_filter_status(self):
        task_store = TaskStore()

        task1 = task_store.new('My Task')
        task2 = task_store.new('My Other Task')
        task3 = task_store.new('My Other Other Task')
        task4 = task_store.new('My Other Other Other Task')

        task1.toggle_active()
        task2.toggle_dismiss()
        task3.toggle_active()

        filtered = task_store.filter(Filter.STATUS, Status.ACTIVE)
        expected = [task4]
        self.assertEqual(filtered, expected)

        filtered = task_store.filter(Filter.STATUS, Status.DISMISSED)
        expected = [task2]
        self.assertEqual(filtered, expected)

        filtered = task_store.filter(Filter.STATUS, Status.DONE)
        expected = [task1, task3]
        self.assertEqual(filtered, expected)


    def test_filter_parent(self):
        task_store = TaskStore()

        task1 = task_store.new('My Task')
        task2 = task_store.new('My Other Task')
        task3 = task_store.new('My Other Other Task')

        task_store.parent(task2.id, task1.id)
        task_store.parent(task3.id, task2.id)

        filtered = task_store.filter(Filter.PARENT)
        expected = [task1]
        self.assertEqual(filtered, expected)


    def test_filter_children(self):
        task_store = TaskStore()

        task1 = task_store.new('My Task')
        task2 = task_store.new('My Other Task')
        task3 = task_store.new('My Other Other Task')

        task_store.parent(task2.id, task1.id)
        task_store.parent(task3.id, task2.id)

        filtered = task_store.filter(Filter.CHILDREN)
        expected = [task2, task3]
        self.assertEqual(filtered, expected)


    def test_filter_tag(self):
        task_store = TaskStore()

        task1 = task_store.new('My Task')
        task2 = task_store.new('My Other Task')
        task3 = task_store.new('My Other Other Task')
        task_store.new('My Other Other Other Task')

        tag1 = Tag(id=uuid4(), name='A Tag')
        tag2 = Tag(id=uuid4(), name='Another Tag')

        task1.add_tag(tag1)
        task2.add_tag(tag2)

        # Test single tags
        filtered = task_store.filter(Filter.TAG, tag1)
        expected = [task1]
        self.assertEqual(filtered, expected)

        filtered = task_store.filter(Filter.TAG, tag2)
        expected = [task2]
        self.assertEqual(filtered, expected)

        # Test tag intersection
        task3.add_tag(tag1)
        task3.add_tag(tag2)

        filtered = task_store.filter(Filter.TAG, [tag1, tag2])
        expected = [task3]
        self.assertEqual(filtered, expected)


    def test_filter_custom(self):
        task_store = TaskStore()

        task_store.new('My Task')
        task2 = task_store.new('My Other Task')

        filtered = task_store.filter_custom('title', lambda t: 'Other' in t)
        expected = [task2]
        self.assertEqual(filtered, expected)


    def test_default_sort(self):
        task_store = TaskStore()

        task1 = task_store.new('My Task')
        task2 = task_store.new('My Other Task')

        # Sort by added date
        task_store.sort()
        expected = [task1, task2]
        self.assertEqual(task_store.data, expected)


    def test_simple_sort(self):
        task_store = TaskStore()

        task1 = task_store.new('1. My Task')
        task2 = task_store.new('2. My Other Task')

        # Simple sort
        task_store.sort(key='title')
        expected = [task1, task2]
        self.assertEqual(task_store.data, expected)


    def test_simple_reverse_sort(self):
        task_store = TaskStore()

        task1 = task_store.new('1. My Task')
        task2 = task_store.new('2. My Other Task')

        # Simple sort
        task_store.sort(key='title',reverse=True)
        expected = [task2, task1]
        self.assertEqual(task_store.data, expected)


    def test_nested_sort(self):
        task_store = TaskStore()

        task1 = task_store.new('2. My Task')
        task2 = task_store.new('3. My Other Task')
        task3 = task_store.new('1. My Other Other Task')
        task4 = task_store.new('5. My Other Other Other Task')

        task_store.parent(task3.id, task2.id)
        task_store.parent(task4.id, task2.id)

        # Tree sort
        task_store.sort(key='title')
        expected = [task1, task2]
        expected_children = [task3, task4]

        self.assertEqual(task_store.data, expected)
        self.assertEqual(task_store.data[1].children, expected_children)


    def test_sort_custom_list(self):
        task_store = TaskStore()

        task1 = task_store.new('1. My Task')
        task2 = task_store.new('2. My Other Task')
        task_store.new('3. My Other Other Task')
        task4 = task_store.new('4. My Other Other Other Task')

        tasks = [task2, task4, task1]

        task_store.sort(tasks, key='title')
        expected = [task1, task2, task4]
        self.assertEqual(tasks, expected)


class LoadStoreWithoutAddedDateTest(TestCase):
    """Regression test for #1033: a gtg_data.xml written while a task
    had no added date (e.g. after importing a CalDAV VTODO without a
    CREATED field, before the fill_task guard) lacks the <added>
    element or leaves it empty. Refusing to load such a file makes
    GTG crash at startup; the store must heal the task instead,
    falling back on the modification date like the import side does."""

    TASK_XML = ('<tasklist>'
                '<task id="0ab33328-4bd0-4d1b-8b06-58bdd8fc4d05"'
                ' status="Active">'
                '<title>Sturm des Wissens</title>'
                '<dates>'
                '<modified>2023-11-08 14:14:27.529767</modified>'
                '{added}'
                '</dates>'
                '<subtasks/>'
                '<content>from a Nextcloud Deck card</content>'
                '</task>'
                '</tasklist>')

    def _load(self, added_fragment):
        task_store = TaskStore()
        xml = XML(self.TASK_XML.format(added=added_fragment))
        task_store.from_xml(xml, TagStore())
        return next(iter(task_store.lookup.values()))

    def test_missing_added_element_falls_back_on_modified(self):
        task = self._load('')
        self.assertTrue(task.date_added)
        self.assertEqual(str(task.date_modified), str(task.date_added))

    def test_empty_added_element_falls_back_on_modified(self):
        task = self._load('<added></added>')
        self.assertTrue(task.date_added)
        self.assertEqual(str(task.date_modified), str(task.date_added))

    def test_valid_added_element_is_still_honored(self):
        task = self._load('<added>2020-01-02 03:04:05</added>')
        self.assertIn('2020-01-02', str(task.date_added))


class LoadStoreWithNonUuidIdsTest(TestCase):
    """Regression test for #1289: a 0.6 data file that ever synced tasks
    created by another CalDAV client can carry task ids that are not
    canonical UUIDs (RFC 5545 makes the iCalendar UID an opaque string;
    the 0.6 CalDAV backend used it verbatim as the local id). from_xml
    cast every id with UUID() and no guard, so a single non-UUID id
    raised ValueError, aborted find_and_load_file, and GTG failed to
    start entirely -- one bad id made all the other tasks unreachable.

    The store must instead map any non-canonical id to a deterministic
    UUID (uuid5), exactly as the CalDAV backend already does on the sync
    side, so the same original string always yields the same task id and
    parent/child references stay intact."""

    NON_UUID_XML = ('<tasklist>'
                    '<task id="deck-card-986" status="Active">'
                    '<title>Sturm des Wissens</title>'
                    '<dates>'
                    '<added>2023-11-08 14:14:27</added>'
                    '<modified>2023-11-08 14:14:27</modified>'
                    '</dates>'
                    '<subtasks>'
                    '<sub>task-1772@someclient</sub>'
                    '</subtasks>'
                    '<content>from a Nextcloud Deck card</content>'
                    '</task>'
                    '<task id="task-1772@someclient" status="Active">'
                    '<title>A child with a mail-style id</title>'
                    '<dates>'
                    '<added>2023-11-08 14:14:27</added>'
                    '<modified>2023-11-08 14:14:27</modified>'
                    '</dates>'
                    '<subtasks/>'
                    '<content>child content</content>'
                    '</task>'
                    '</tasklist>')

    def test_non_uuid_ids_load_instead_of_crashing(self):
        task_store = TaskStore()
        task_store.from_xml(XML(self.NON_UUID_XML), TagStore())
        self.assertEqual(task_store.count(), 2)

    def test_non_uuid_ids_are_mapped_deterministically(self):
        # the same original string must always yield the same task id,
        # otherwise a reload would orphan every subtask
        first = TaskStore()
        first.from_xml(XML(self.NON_UUID_XML), TagStore())
        second = TaskStore()
        second.from_xml(XML(self.NON_UUID_XML), TagStore())
        self.assertEqual(sorted(str(t.id) for t in first.lookup.values()),
                         sorted(str(t.id) for t in second.lookup.values()))

    def test_non_uuid_parent_child_link_survives(self):
        task_store = TaskStore()
        task_store.from_xml(XML(self.NON_UUID_XML), TagStore())
        parents = [t for t in task_store.lookup.values() if t.children]
        self.assertEqual(1, len(parents))
        self.assertEqual(1, len(parents[0].children))

    def test_canonical_uuid_ids_are_left_untouched(self):
        canonical = '1d34df07-4185-43ad-adbd-698a86193411'
        xml = ('<tasklist><task id="' + canonical + '" status="Active">'
               '<title>T</title>'
               '<dates><added>2020-01-01 00:00:00</added>'
               '<modified>2020-01-01 00:00:00</modified></dates>'
               '<subtasks/><content>c</content></task></tasklist>')
        task_store = TaskStore()
        task_store.from_xml(XML(xml), TagStore())
        self.assertIn(canonical, [str(t.id) for t in task_store.lookup.values()])
