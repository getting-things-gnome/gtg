# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2015 - Lionel Dricot & Bertrand Rousseau
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
Classes responsible for handling user configuration
"""

import configparser
import os
import re

from GTG.core.dirs import CONFIG_DIR
from GTG.tools.logger import Log

DEFAULTS = {
    # TODO: Remove toolbar and quick_add options from configuration
    # They won't be used in GTG 0.4
    'browser': {
        "bg_color_enable": True,
        "contents_preview_enable": False,
        'tag_pane': False,
        "sidebar_width": 120,
        "closed_task_pane": False,
        'bottom_pane_position': 300,
        'toolbar': True,
        'quick_add': True,
        'collapsed_tasks': [],
        'expanded_tags': [],
        'view': 'default',
        "opened_tasks": [],
        'width': 400,
        'height': 400,
        'max': False,
        'x_pos': 10,
        'y_pos': 10,
        'tasklist_sort_column': 5,
        'tasklist_sort_order': 1,
        "font_name": "",
        'hour': "00",
        'min': "00",
    },
    'tag_editor': {
        "custom_colors": [],
    },
    'plugins': {
        "enabled": [],
        "disabled": [],
    },
    'task': {
        'position': [],
        'size': [],
    },
}


def open_config_file(config_file):
    """ Opens config file and makes additional checks

    Creates config file if it doesn't exist and makes sure it is readable and
    writable by user. That prevents surprise when user is not able to save
    configuration when exiting the app.
    """
    dirname = os.path.dirname(config_file)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    if not os.path.exists(config_file):
        open(config_file, "w").close()
    if not os.access(config_file, os.R_OK | os.W_OK):
        raise Exception("File " + config_file + " is a configuration file "
                        "for gtg, but it cannot be read or written. "
                        "Please check it")
    config = configparser.ConfigParser()
    try:
        config.read(config_file)
    except configparser.Error as e:
        Log.warning("Problem with opening file %s: %s", config_file, e)
    return config


class SectionConfig(object):
    """ Configuration only for a section (system or a task) """

    def __init__(self, section_name, section, defaults, save_function):
        """ Initiatizes section config:

         - section_name: name for writing error logs
         - section: section of the config handled by this object
         - defaults: dictionary of default values
         - save_function: function to be called to save changes (this function
                          needs to save the whole config)
        """
        self._section_name = section_name
        self._section = section
        self._defaults = defaults
        self._save_function = save_function

    def _getlist(self, option):
        """ Parses string representation of list from configuration

        List can't contain an empty value as those are skipped over,
        e.g. "a, ,b" is parsed as ['a', 'b'].

        Accepted formats:
         - "('a', 'b'),('c','d','e')" => ["('a', 'b')", "('c','d','e')"]
         - "a, b" => ['a', 'b']
        """
        raw = self._section.get(option)
        if not raw:
            return None

        # Match tuples in format "('string1', 'string2', ...)"
        values = re.findall(r'\(.*?\)', raw)
        if not values:
            # It only normal list
            values = raw.split(',')

        return [item.strip() for item in values if item]

    def _type_function(self, default_value):
        """ Returns function that returns correct type of value """
        default_type = type(default_value)
        if default_type in (list, tuple):
            return self._getlist
        elif default_type == int:
            return self._section.getint
        elif default_type == bool:
            return self._section.getboolean
        else:
            return self._section.get

    def get(self, option):
        """ Get option from configuration.

        If the option is not specified in the configuration or is of invalid
        type, return default value. If there is no default value,
        None is returned
        """
        default_value = self._defaults.get(option)
        if default_value is None:
            Log.warning(
                'No default value for %s in %s', option, self._section_name)

        get_function = self._type_function(default_value)

        try:
            value = get_function(option)
        except ValueError as e:
            value = None
            Log.warning(
                'Invalid configuration value "%s" for %s in %s: %s',
                self._section.get(option), option, self._section_name, e)

        if value is None and default_value is None:
            raise ValueError(
                'No valid configuration value or default value was '
                'found for %s in %s'.format(option, self._section_name))
        elif value is None:
            return default_value
        else:
            return value

    def set(self, option, value):
        if type(value) in (list, tuple):
            value = ','.join(str(item) for item in value)
        else:
            value = str(value)
        self._section[option] = value
        # Immediately save the configuration
        self.save()

    def save(self):
        self._save_function()


class CoreConfig(object):
    """ Class holding configuration to all systems and tasks """

    def __init__(self):
        self._conf_path = os.path.join(CONFIG_DIR, 'gtg.conf')
        self._conf = open_config_file(self._conf_path)

        self._task_conf_path = os.path.join(CONFIG_DIR, 'tasks.conf')
        self._task_conf = open_config_file(self._task_conf_path)

    def save_gtg_config(self):
        self._conf.write(open(self._conf_path, 'w'))

    def save_task_config(self):
        self._task_conf.write(open(self._task_conf_path, 'w'))

    def get_subconfig(self, name):
        """ Returns configuration object for special section of config """
        if name not in self._conf:
            self._conf.add_section(name)
        defaults = DEFAULTS.get(name, dict())
        return SectionConfig(
            name, self._conf[name], defaults, self.save_gtg_config)

    def get_task_config(self, task_id):
        if task_id not in self._task_conf:
            self._task_conf.add_section(task_id)
        return SectionConfig(
            'Task {}'.format(task_id),
            self._task_conf[task_id],
            DEFAULTS['task'],
            self.save_task_config)
