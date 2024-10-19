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

"""Code to read older versions of the XML file."""

import os
import html
from uuid import uuid4

from lxml import etree as et
from GTG.core.dates import Date
from GTG.core.dirs import DATA_DIR

from datetime import date
from typing import Optional, Tuple


#: A dicionary of tags and IDs to add in tasks
tags_cache = {}

#: A dictionary of old style task IDs to UUIDs
tid_cache = {}


def convert(path: str) -> et._ElementTree:
    """Convert old XML into the new format."""

    old_tree = xml.open_file(path, 'project')

    new_root = et.Element('gtgData')
    # Bump this on each new GTG release, no matter what:
    new_root.set('appVersion', '0.6')
    # Bump this when there are known file format changes:
    new_root.set('xmlVersion', '2')

    taglist, searches = convert_tags(old_tree)
    new_root.append(taglist)
    new_root.append(searches)

    tasklist = et.SubElement(new_root, 'tasklist')

    for task in old_tree.iter('task'):

        # Keep a map of old style IDs to UUIDs for later
        tid = task.attrib['id']

        try:
            new_tid = task.attrib['uuid']
        except KeyError:
            new_tid = str(uuid4())

        tid_cache[tid] = new_tid

    for task in old_tree.iter('task'):
        new_task = convert_task(task)

        if new_task is not None:
            tasklist.append(new_task)

    return et.ElementTree(new_root)


def convert_tags(old_tree: et._Element) -> Tuple[et._Element, et._Element]:
    """Convert old tags for the new format."""

    old_file = os.path.join(DATA_DIR, 'tags.xml')
    tree = xml.open_file(old_file, 'tagstore')

    taglist = et.Element('taglist')
    searchlist = et.Element('searchlist')

    for tag in tree.iter('tag'):
        name = tag.get('name')
        parent = tag.get('parent')
        nonactionable = tag.get('nonworkview')
        color = tag.get('color')
        tid = str(uuid4())

        if tag.get('query'):
            new_tag = et.SubElement(searchlist, 'savedSearch')
            new_tag.set('name', name)

            query = tag.get('query')
            new_tag.set('query', query)

        else:
            new_tag = et.SubElement(taglist, 'tag')

            # Remove @ in name
            new_tag.set('name', name[1:])
            tags_cache[name] = tid

            if parent:
                new_tag.set('parent', parent[1:])

            if nonactionable:
                new_tag.set('nonactionable', nonactionable)

        new_tag.set('id', tid)

        # Remove # in color hex
        if color:
            new_tag.set('color', color[1:].upper())


    # In older versions not all tags were saved in the tag file
    # Some were just saved in the tasks, so we need to loop
    # through the tasks to make sure we get *all* tags and have
    # their IDs ready for task conversion.
    for task in old_tree.iter('task'):
        tags_str = task.get('tags')
        assert tags_str is not None, "Missing tags property in old task."
        for tag_name in tags_str.split(','):
            if tag_name and tag_name not in tags_cache:
                new_tag = et.SubElement(taglist, 'tag')
                tid = str(uuid4())
                new_tag.set('id', tid)
                new_tag.set('name', tag_name[1:])

                tags_cache[tag_name] = tid

    return taglist, searchlist


def convert_task(task: et._Element) -> Optional[et._Element]:
    """Convert old task XML into the new format."""

    if task is None:
        return

    tid = task.attrib['id']

    # Get the old task properties
    # TIDs were stored as UUID, but sometimes they were not present
    tid = task.get('uuid') or str(uuid4())
    status = task.get('status')
    assert status is not None, 'Missing status property in old task.'
    title_element = task.find('title')
    assert title_element is not None, 'Missing title element in old task.'
    title = title_element.text
    content = task.find('content')

    donedate_element = task.find('donedate')
    if donedate_element is not None:
        done_date = donedate_element.text
    else:
        done_date = None

    duedate_element = task.find('duedate')
    if duedate_element is not None:
        due_date = duedate_element.text
    else:
        due_date = None

    modified_element = task.find('modified')
    if modified_element is not None:
        modified = modified_element.text
    else:
        modified = None

    added_element = task.find('added')
    if added_element is not None:
        added = added_element.text
    else:
        added = None

    startdate_element = task.find('startdate')
    if startdate_element is not None:
        start = startdate_element.text
    else:
        start = None


    # Build the new task
    new_task = et.Element('task')

    new_task.set('status', status)
    new_task.set('id', tid)

    new_title = et.SubElement(new_task, 'title')
    new_title.text = title

    tags = et.SubElement(new_task, 'tags')

    tags_str = task.get('tags')
    assert tags_str is not None, 'Missing tags property in old task.'
    for tag_name in tags_str.split(','):
        if tag_name:
            tag_id = tags_cache[tag_name]
            task_tag = et.SubElement(tags, 'tag')
            task_tag.text = tag_id

    dates = et.SubElement(new_task, 'dates')
    new_added = et.SubElement(dates, 'added')
    new_modified = et.SubElement(dates, 'modified')

    if added:
        added = str(Date(added))
    else:
        added = date.today().isoformat()

    new_added.text = added

    if modified:
        modified = modified[:10]
        modified = str(Date(modified))
    else:
        modified = date.today().isoformat()

    new_modified.text = modified

    if done_date:
        new_done = et.SubElement(dates, 'done')
        new_done.text = str(Date(done_date))

    if start:
        tmp_start = Date(start)

        if tmp_start.is_fuzzy():
            new_start = et.SubElement(dates, 'fuzzyStart')
        else:
            new_start = et.SubElement(dates, 'start')

        new_start.text = str(tmp_start)

    if due_date:
        tmp_due_date = Date(due_date)

        if tmp_due_date.is_fuzzy():
            new_due = et.SubElement(dates, 'fuzzyDue')
        else:
            new_due = et.SubElement(dates, 'due')

        new_due.text = str(tmp_due_date)

    recurring = et.SubElement(new_task, 'recurring')
    recurring.set('enabled', 'false')

    subtasks = et.SubElement(new_task, 'subtasks')

    for sub in task.findall('subtask'):
        new_sub = et.SubElement(subtasks, 'sub')
        new_sub.text = tid_cache[sub.text]

    new_content = et.SubElement(new_task, 'content')

    if content is not None:
        content_text = content.text or ''
        new_content.text = et.CDATA(convert_content(content_text))
    else:
        new_content.text = et.CDATA('')


    return new_task


def convert_content(content: str) -> str:
    """Convert a task contents to new format."""

    if not content:
        return ''

    # Unescape &quot;a and friends
    text = html.unescape(content)

    # Get rid of the content tag if it slip all the way there
    text = text.replace('</content>', '')
    text = text.replace('<content>', '')

    # Tag tags arent' needed anymore
    text = text.replace('</tag>', '')
    text = text.replace('<tag>', '')

    # New subtask style
    text = text.replace('</subtask>', ' !}')
    text = text.replace('<subtask>', '{! ')

    # Get rid of the arrow and indent
    text = text.replace('→', '')

    return text
