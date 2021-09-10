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
import datetime

from GTG.core.tasks2 import Task2, Status, TaskStore, Filter
from GTG.core.tags2 import Tag2, TagStore
from GTG.core.dates import Date

from lxml.etree import Element, SubElement, XML


class TestTask2(TestCase):

    def test_title(self):
        task = Task2(id=uuid4(), title='\tMy Title\n')

        self.assertEqual(task.title, 'My Title')

    def test_excerpt(self):
        task = Task2(id=uuid4(), title='A Task')

        self.assertEqual(task.excerpt, '')

        task.content = ('This is a sample content with some @tags, and some '
                        'extra text for padding. I could go on and on and on '
                        'and on and on.')


        expected = ('This is a sample content with some @tags, and some '
                    'extra text for padding. I cou…')

        self.assertEqual(task.excerpt, expected)


    def test_status(self):
        task = Task2(id=uuid4(), title='A Task')

        self.assertEqual(task.status, Status.ACTIVE)

        task.toggle_status()
        self.assertEqual(task.status, Status.DONE)
        self.assertEqual(task.date_closed, Date.today())

        task.dismiss()
        self.assertEqual(task.status, Status.DISMISSED)
        self.assertEqual(task.date_closed, Date.today())

        task.toggle_status()
        self.assertEqual(task.status, Status.ACTIVE)
        self.assertEqual(task.date_closed, Date.no_date())

        task.dismiss()
        self.assertEqual(task.status, Status.DISMISSED)
        self.assertEqual(task.date_closed, Date.no_date())

        task.toggle_status()

        task2 = Task2(id=uuid4(), title='A Child Task')
        task.children.append(task2)
        task2.parent = task

        task.toggle_status()
        self.assertEqual(task.status, Status.DONE)
        self.assertEqual(task.date_closed, Date.today())
        self.assertEqual(task2.status, Status.DONE)
        self.assertEqual(task2.date_closed, Date.today())

        task.toggle_status()
        self.assertEqual(task.status, Status.ACTIVE)
        self.assertEqual(task.date_closed, Date.no_date())
        self.assertEqual(task2.status, Status.ACTIVE)
        self.assertEqual(task2.date_closed, Date.no_date())

        task.dismiss()
        self.assertEqual(task.status, Status.DISMISSED)
        self.assertEqual(task.date_closed, Date.no_date())
        self.assertEqual(task2.status, Status.DISMISSED)
        self.assertEqual(task2.date_closed, Date.no_date())

        task2.toggle_status()
        self.assertEqual(task.status, Status.ACTIVE)
        self.assertEqual(task.date_closed, Date.no_date())
        self.assertEqual(task2.status, Status.ACTIVE)
        self.assertEqual(task2.date_closed, Date.no_date())


    def test_tags(self):
        task = Task2(id=uuid4(), title='A Task')
        tag = Tag2(id=uuid4(), name='A Tag')

        task.add_tag(tag)
        self.assertEqual(len(task.tags), 1)

        with self.assertRaises(ValueError):
            task.add_tag('my super tag')

        self.assertEqual(len(task.tags), 1)

        task.add_tag(tag)
        self.assertEqual(len(task.tags), 1)

        task.remove_tag('A Tag')
        self.assertEqual(len(task.tags), 0)


    def test_tags_children(self):
        task1 = Task2(id=uuid4(), title='A Parent Task')
        task2 = Task2(id=uuid4(), title='A Child Task')

        tag1 = Tag2(id=uuid4(), name='A Tag')
        tag2 = Tag2(id=uuid4(), name='Another Tag')

        task1.children.append(task2)
        task1.add_tag(tag1)

        self.assertEqual(len(task1.tags), 1)
        self.assertEqual(len(task2.tags), 0)

        task2.add_tag(tag2)
        self.assertEqual(len(task1.tags), 1)
        self.assertEqual(len(task2.tags), 1)
        self.assertEqual(task2.tags[0].name, 'Another Tag')


    def test_due_date(self):
        task1 = Task2(id=uuid4(), title='A Parent Task')
        task2 = Task2(id=uuid4(), title='A Child Task')
        task3 = Task2(id=uuid4(), title='Another Child Task')
        task4 = Task2(id=uuid4(), title='Yet Another Child Task')
        task5 = Task2(id=uuid4(), title='So many Child Tasks')
        task6 = Task2(id=uuid4(), title='More childs')

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
        task1.date_due = None
        self.assertEqual(task2.date_due, random_date)


    def test_new_simple(self):
        store = TaskStore()
        task = store.new('My Task')

        self.assertIsInstance(task, Task2)
        self.assertEqual(store.get(task.id), task)
        self.assertEqual(task.title, 'My Task')
        self.assertEqual(store.count(), 1)


    def test_new_tree(self):
        store = TaskStore()

        root_task = store.new('My Root Task')
        child_task = store.new('My Child Task', root_task.id)

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

        store.unparent(child_task.id, root_task.id)

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

        store.unparent(inner_child_task.id, inner_child_task.parent.id)
        self.assertEqual(inner_child_task.parent, None)
        self.assertEqual(len(child_task.children), 0)


    def test_xml_load_simple(self):
        task_store = TaskStore()
        tag_store = TagStore()

        TAG_ID = '6f1ba7b3-a797-44b9-accd-303adaf04073'
        TASK_ID = '1d34df07-4185-43ad-adbd-698a86193411'

        tag = Tag2(id=TAG_ID, name='My Tag')
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
        self.assertEqual(len(task_store.get(str(TASK_ID_1)).children), 2)


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
                    <sub>lol</sub>
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

        task1.toggle_status()
        task2.dismiss()
        task3.toggle_status()

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
        task4 = task_store.new('My Other Other Other Task')

        tag1 = Tag2(id=uuid4(), name='A Tag')
        tag2 = Tag2(id=uuid4(), name='Another Tag')

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

        task1 = task_store.new('My Task')
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
        task3 = task_store.new('3. My Other Other Task')
        task4 = task_store.new('4. My Other Other Other Task')

        tasks = [task2, task4, task1]

        task_store.sort(tasks, key='title')
        expected = [task1, task2, task4]
        self.assertEqual(tasks, expected)


