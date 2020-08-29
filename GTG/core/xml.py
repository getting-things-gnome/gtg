# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
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

import os
import shutil
from datetime import datetime
from GTG.core.dates import Date

from lxml import etree

log = logging.getLogger(__name__)
# Total amount of backups
BACKUPS = 7

# Information on whether a backup was used
backup_used = {}


def task_from_element(task, element: etree.Element):
    """Populate task from XML element."""

    task.set_title(element.find('title').text)
    task.set_uuid(element.get('id'))

    dates = element.find('dates')

    modified = dates.find('modified').text
    task.set_modified(datetime.fromisoformat(modified))

    added = dates.find('added').text
    task.set_added_date(datetime.fromisoformat(added))

    # Dates
    try:
        done_date = Date.parse(dates.find('done').text)
        task.set_status(element.attrib['status'], donedate=done_date)
    except AttributeError:
        pass

    try:
        due_date = Date.parse(dates.find('due').text)
        task.set_due_date(due_date)
    except AttributeError:
        pass

    try:
        start = dates.find('start').text
        task.set_start_date(start)
    except (AttributeError, TypeError):
        pass

    # Recurring tasks
    recurring = element.find('recurring')
    recurring_enabled = recurring.get('enabled')

    try:
        recurring_term = element.find('term').text
        task.set_recurring(recurring_enabled == 'true',
                           None if recurring_term == 'None'
                           else recurring_term)

    except AttributeError:
        pass

    taglist = element.find('tags')

    if taglist is not None:
        [task.tag_added_by_id(t.text) for t in taglist.iter('tag')]

    # Content
    content = element.find('content').text or ''
    task.set_text(content)

    # Subtasks
    subtasks = element.find('subtasks')

    for sub in subtasks.findall('sub'):
        task.add_child(sub.text)

    return task


def task_to_element(task) -> etree.Element:
    """Serialize task into XML Element."""

    element = etree.Element('task')

    element.set('id', task.get_id())
    element.set('status', task.get_status())
    element.set('uuid', task.get_uuid())
    element.set('recurring', str(task.get_recurring()))

    tags = etree.SubElement(element, 'tags')

    for t in task.get_tags():
        tag_tag = etree.SubElement(tags, 'tag')
        tag_tag.text = str(t.tid)

    title = etree.SubElement(element, 'title')
    title.text = task.get_title()

    dates = etree.SubElement(element, 'dates')

    added_date = etree.SubElement(dates, 'added')
    added_date.text = task.get_added_date().isoformat()

    modified_date = etree.SubElement(dates, 'modified')
    modified_date.text = Date(task.get_modified()).xml_str()

    done_date = etree.SubElement(dates, 'done')
    done_date.text = task.get_closed_date().xml_str()

    due_date = task.get_due_date()
    due_tag = 'fuzzyDue' if due_date.is_fuzzy() else 'due'
    due = etree.SubElement(dates, due_tag)
    due.text = due_date.xml_str()

    start_date = task.get_start_date()
    start_tag = 'fuzzyStart' if start_date.is_fuzzy() else 'start'
    start = etree.SubElement(dates, start_tag)
    start.text = start_date.xml_str()

    recurring = etree.SubElement(element, 'recurring')
    recurring.set('enabled', str(task.recurring).lower())

    recurring_term = etree.SubElement(recurring, 'term')
    recurring_term.text = str(task.get_recurring_term())

    subtasks = etree.SubElement(element, 'subtasks')

    for subtask_id in task.get_children():
        sub = etree.SubElement(subtasks, 'sub')
        sub.text = subtask_id

    content = etree.SubElement(element, 'content')
    content.text = etree.CDATA(task.get_text())

    return element


def get_file_mtime(filepath: str) -> str:
    """Get date from file."""

    timestamp = os.path.getmtime(filepath)
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')


def get_backup_name(filepath: str, i: int) -> str:
    """Get name of backups which are backup/ directory."""

    dirname, filename = os.path.split(filepath)
    backup_file = f"{filename}.bak.{i}" if i else filename

    return os.path.join(dirname, 'backup', backup_file)


def get_xml_tree(filepath: str) -> etree.ElementTree:
    """Parse XML file at filepath and get tree."""

    parser = etree.XMLParser(remove_blank_text=True, strip_cdata=False)

    with open(filepath, 'rb') as stream:
        tree = etree.parse(stream, parser=parser)

    return tree


def open_file(xml_path: str, root_tag: str) -> etree.ElementTree:
    """Open an XML file in a robust way

    If file could not be opened, try:
        - file__
        - file.bak.0
        - file.bak.1
        - .... until BACKUP_NBR

    If file doesn't exist, create a new file."""

    global backup_used

    files = [
        xml_path,            # Main file
        xml_path + '__',     # Temp file
    ]

    # Add backup files
    files += [get_backup_name(xml_path, i) for i in range(BACKUPS)]

    root = None
    backup_used = None

    for index, filepath in enumerate(files):
        try:
            log.debug('Opening file %s', filepath)
            root = get_xml_tree(filepath)

            # This was a backup. We should inform the user
            if index > 0:
                backup_used = {
                    'name': filepath,
                    'time': get_file_mtime(filepath)
                }

            # We could open a file, let's stop this loop
            break

        except FileNotFoundError:
            log.debug('File not found: %r. Trying next.', filepath)
            continue

        except PermissionError:
            log.debug('Not allowed to open: %r. Trying next.', filepath)
            continue

        except etree.XMLSyntaxError as error:
            log.debug('Syntax error in %r. %r. Trying next.', filepath, error)
            continue

    if root:
        return root

    # We couldn't open any file :(
    else:
        # Try making a new empty file and open it
        try:

            write_empty_file(xml_path, root_tag)
            return open_file(xml_path, root_tag)

        except IOError:
            raise SystemError(f'Could not write a file at {xml_path}')


def write_backups(filepath: str) -> None:
    """Make backups for the file at filepath."""

    current_back = BACKUPS
    backup_name = get_backup_name(filepath, None)
    backup_dir = os.path.dirname(backup_name)

    # Make sure backup dir exists
    try:
        os.makedirs(backup_dir, exist_ok=True)

    except IOError:
        log.error('Backup dir %r cannot be created!', backup_dir)
        return

    # Cycle backups
    while current_back > 0:
        older = f"{backup_name}.bak.{current_back}"
        newer = f"{backup_name}.bak.{current_back - 1}"

        if os.path.exists(newer):
            shutil.move(newer, older)

        current_back -= 1

    # bak.0 is always a fresh copy of the closed file
    # so that it's not touched in case of not opening next time
    bak_0 = f"{backup_name}.bak.0"
    shutil.copy(filepath, bak_0)

    # Add daily backup
    today = datetime.today().strftime('%Y-%m-%d')
    daily_backup = f'{backup_name}.{today}.bak'

    if not os.path.exists(daily_backup):
        shutil.copy(filepath, daily_backup)


def write_xml(filepath: str, tree: etree.ElementTree) -> None:
    """Write an XML file."""

    with open(filepath, 'wb') as stream:
        tree.write(stream, xml_declaration=True,
                   pretty_print=True,
                   encoding='UTF-8')


def create_dirs(filepath: str) -> None:
    """Create directory tree for filepath."""

    base_dir = os.path.dirname(filepath)
    try:
        os.makedirs(base_dir, exist_ok=True)
    except IOError as error:
        log.error("Error while creating directories: %r", error)


def save_file(filepath: str, root: etree.ElementTree) -> None:
    """Save an XML file."""

    temp_file = filepath + '__'

    if os.path.exists(filepath):
        os.rename(filepath, temp_file)

    try:
        write_xml(filepath, root)

        if os.path.exists(temp_file):
            os.remove(temp_file)

    except (IOError, FileNotFoundError):
        log.error('Could not write XML file at %r', filepath)
        create_dirs(filepath)


def write_empty_file(filepath: str, root_tag: str) -> None:
    """Write an empty tasks file."""

    root = etree.Element(root_tag)
    save_file(filepath, etree.ElementTree(root))


def skeleton() -> etree.Element:
    """Generate root XML tag and basic subtags."""

    root = etree.Element('gtgData')
    root.set('appVersion', '0.5')
    root.set('xmlVersion', '2')

    etree.SubElement(root, 'taglist')
    etree.SubElement(root, 'tasklist')

    return root
