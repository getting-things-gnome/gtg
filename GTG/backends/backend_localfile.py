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

"""
Localfile is a read/write backend that will store your tasks in an XML file
This file will be in your $XDG_DATA_DIR/gtg folder.

This backend contains comments that are meant as a reference, in case someone
wants to write a backend.
"""

import os

from GTG.backends.backend_signals import BackendSignals
from GTG.backends.generic_backend import GenericBackend
from GTG.core.dirs import DATA_DIR
from gettext import gettext as _
from GTG.core import xml
from GTG.core import firstrun_tasks
from GTG.core import versioning
from GTG.core.logger import log

from typing import Dict
from lxml import etree as et


class Backend(GenericBackend):
    """
    Localfile backend, which stores your tasks in a XML file in the standard
    XDG_DATA_DIR/gtg folder (the path is configurable).
    An instance of this class is used as the default backend for GTG.
    This backend loads all the tasks stored in the localfile after it's enabled
    and from that point on just writes the changes to the file: it does not
    listen for eventual file changes
    """

    # General description of the backend: these are used to show a description
    # of the backend to the user when s/he is considering adding it.
    # BACKEND_NAME is the name of the backend used internally (it must be
    # unique).
    # Please note that BACKEND_NAME and BACKEND_ICON_NAME should *not* be
    # translated.
    _general_description = {
        GenericBackend.BACKEND_NAME: 'backend_localfile',
        GenericBackend.BACKEND_HUMAN_NAME: _('Local File'),
        GenericBackend.BACKEND_AUTHORS: ['Lionel Dricot',
                                         'Luca Invernizzi'],
        GenericBackend.BACKEND_TYPE: GenericBackend.TYPE_READWRITE,
        GenericBackend.BACKEND_DESCRIPTION:
        _(('Your tasks are saved in a text file (XML format). '
           ' This is the most basic and the default way '
           'for GTG to save your tasks.')),
    }

    # These are the parameters to configure a new backend of this type. A
    # parameter has a name, a type and a default value.
    # Here, we define a parameter "path", which is a string, and has a default
    # value as a random file in the default path
    _static_parameters = {
        "path": {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_STRING,
            GenericBackend.PARAM_DEFAULT_VALUE:
            'gtg_data.xml'}}

    def __init__(self, parameters: Dict):
        """
        Instantiates a new backend.

        @param parameters: A dictionary of parameters, generated from
        _static_parameters. A few parameters are added to those, the list of
        these is in the "DefaultBackend" class, look for the KEY_* constants.

        The backend should take care if one expected value is None or
        does not exist in the dictionary.
        """
        super().__init__(parameters)

        if self.KEY_DEFAULT_BACKEND not in parameters:
            parameters[self.KEY_DEFAULT_BACKEND] = True

    def get_path(self) -> str:
        """Return the current path to XML

        Path can be relative to projects.xml
        """
        path = self._parameters['path']

        # This is local path, convert it to absolute path
        if os.sep not in path:
            path = os.path.join(DATA_DIR, path)

        return os.path.abspath(path)

    def initialize(self):
        """ This is called when a backend is enabled """

        super(Backend, self).initialize()
        filepath = self.get_path()

        if versioning.is_required(filepath):
            log.warning('Found old file. Running versioning code.')
            old_path = os.path.join(DATA_DIR, 'gtg_tasks.xml')
            tree = versioning.convert(old_path, self.datastore)

            xml.save_file(filepath, tree)

        self.data_tree = xml.open_file(filepath, 'gtgData')
        self.task_tree = self.data_tree.find('tasklist')
        self.tag_tree = self.data_tree.find('taglist')
        self.search_tree = self.data_tree.find('searchlist')

        self.datastore.load_tag_tree(self.tag_tree)
        self.datastore.load_search_tree(self.search_tree)

        # Make safety daily backup after loading
        xml.save_file(self.get_path(), self.data_tree)
        xml.write_backups(self.get_path())

    def this_is_the_first_run(self, _) -> None:
        """ Called upon the very first GTG startup.

        This function is needed only in this backend, because it can be used
        as default one. The xml parameter is an object containing GTG default
        tasks. It will be saved to a file, and the backend will be set as
        default.

        @param xml: an xml object containing the default tasks.
        """

        self._parameters[self.KEY_DEFAULT_BACKEND] = True

        root = firstrun_tasks.generate()
        xml.create_dirs(self.get_path())
        xml.save_file(self.get_path(), root)

        # Load the newly created file
        self.data_tree = xml.open_file(self.get_path(), 'gtgData')
        self.task_tree = self.data_tree.find('tasklist')
        self.tag_tree = self.data_tree.find('taglist')
        xml.backup_used = None

    def start_get_tasks(self) -> None:
        """ This function starts submitting the tasks from the XML file into
        GTG core. It's run as a separate thread.

        @return: start_get_tasks() might not return or finish
        """

        for element in self.task_tree.iter('task'):
            tid = element.get('id')
            task = self.datastore.task_factory(tid)

            if task:
                task = xml.task_from_element(task, element)
                self.datastore.push_task(task)


    def set_task(self, task) -> None:
        """
        This function is called from GTG core whenever a task should be
        saved, either because it's a new one or it has been modified.
        This function will look into the loaded XML object if the task is
        present, and if it's not, it will create it. Then, it will save the
        task data in the XML object.

        @param task: the task object to save
        """

        tid = task.get_id()
        element = xml.task_to_element(task)
        existing = self.task_tree.findall(f"task[@id='{tid}']")

        if existing and element != existing[0]:
            existing[0].getparent().replace(existing[0], element)

        else:
            self.task_tree.append(element)

        # Write the xml
        xml.save_file(self.get_path(), self.data_tree)

    def remove_task(self, tid: str) -> None:
        """ This function is called from GTG core whenever a task must be
        removed from the backend. Note that the task could be not present here.

        @param tid: the id of the task to delete
        """

        element = self.task_tree.findall(f'task[@id="{tid}"]')

        if element:
            element[0].getparent().remove(element[0])
            xml.save_file(self.get_path(), self.data_tree)

    def save_tags(self, tagnames, tagstore) -> None:
        """Save changes to tags and saved searches."""

        already_saved = []

        for tagname in tagnames:
            if tagname in already_saved:
                continue

            tag = tagstore.get_node(tagname)

            attributes = tag.get_all_attributes(butname=True, withparent=True)
            if "special" in attributes:
                continue

            if tag.is_search_tag():
                root = self.search_tree
                tag_type = 'savedSearch'
            else:
                root = self.tag_tree
                tag_type = 'tag'

            tid = str(tag.tid)
            element = root.findall(f'{tag_type}[@id="{tid}"]')

            if len(element) == 0:
                element = et.SubElement(self.task_tree, tag_type)
                root.append(element)
            else:
                element = element[0]

            # Don't save the @ in the name
            element.set('id', tid)
            element.set('name', tagname)

            for attr in attributes:
                # skip labels for search tags
                if tag.is_search_tag() and attr == 'label':
                    continue

                value = tag.get_attribute(attr)

                if value:
                    element.set(attr, value)

            already_saved.append(tagname)

        xml.save_file(self.get_path(), self.data_tree)

    def used_backup(self):
        """ This functions return a boolean value telling if backup files
        were used when instantiating Backend class.
        """
        return xml.backup_used is not None

    def backup_file_info(self):
        """This functions returns status of the attempt to recover
        gtg_tasks.xml
        """

        back = xml.backup_used

        if not back:
            return

        elif back['filepath']:
            return f"Recovered from backup made on: {back['time']}"

        else:
            return 'No backups found. Created a new file'


    def notify_user_about_backup(self) -> None:
        """ This function causes the inforbar to show up with the message
        about file recovery.
        """
        message = _(
            'Oops, something unexpected happened! '
            'GTG tried to recover your tasks from backups. \n'
        ) + self.backup_file_info()

        BackendSignals().interaction_requested(
            self.get_id(), message,
            BackendSignals().INTERACTION_INFORM, 'on_continue_clicked')

    def on_continue_clicked(self, *args) -> None:
        """ Callback when the user clicks continue in the infobar."""
        pass
