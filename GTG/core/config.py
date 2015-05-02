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

from re import findall
import configparser
import os

from GTG.core.dirs import CONFIG_DIR
from GTG.tools.borg import Borg
from GTG.tools.logger import Log

DEFAULTS = {
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
    }
}


# Instead of accessing directly the ConfigParser, each module will have
# one SubConfig object. (one SubConfig object always match one first level
# element of the ConfigParser directory)
#
# The goal of the SubConfig object is to handle default value and converting
# String to Bool and Int when needed.
#
# Each GTG component using config should be ported to SubConfig and, for each
# setting, a default value should be written in the DEFAULTS above.
#
# Currently done : browser
# Todo : editor, plugins

class SubConfig():

    def __init__(self, section, conf, conf_path):
        self._section = section
        self._conf = conf
        self._conf_path = conf_path

    # This return the value of the setting (or the default one)
    #
    # If a default value exists and is a Int or a Bool, the returned
    # value is converted to that type.
    def get(self, option):
        if self._conf.has_option(self._section, option):
            toreturn = self._conf.get(self._section, option)
            # Converting to the good type
            if option in DEFAULTS[self._section]:
                ntype = type(DEFAULTS[self._section][option])
                if ntype == int:
                    toreturn = int(toreturn)
                elif ntype == list:
                    # All list config should be saved in ','.join(list) pattern
                    # This is just for backward compatibility
                    if toreturn and toreturn[0] == '[' and toreturn[-1] == ']':
                        toreturn = toreturn[1:-1]

                    # Splitting by ',' caused bugs #1218093 and #1216807.
                    # Parsing the below way
                    # does not split "('string1', 'string2', ... )" further
                    toreturn_backup_str = toreturn
                    toreturn = findall(r'\(.*?\)', toreturn)
                    if not toreturn:
                        toreturn = toreturn_backup_str.split(',')
                    while toreturn and toreturn[-1] == '':
                        toreturn = toreturn[:-1]
                elif ntype == bool and type(toreturn) == str:
                    toreturn = toreturn.lower() == "true"
        elif option in DEFAULTS[self._section]:
            toreturn = DEFAULTS[self._section][option]
            self.set(option, toreturn)
        else:
            print("Warning : no default conf value for %s in %s" % (
                option, self._section))
            toreturn = None
        return toreturn

    def clear(self):
        for option in self._conf.options(self._section):
            self._conf.remove_option(self._section, option)

    def save(self):
        self._conf.write(open(self._conf_path, 'w'))

    def set(self, option, value):
        if type(value) == list:
            value = ','.join(value)
        self._conf.set(self._section, option, str(value))
        # Save immediately
        self.save()


class TaskConfig():
    """ TaskConfig is used to save the position and size of each task, both of
    value are one tuple with two numbers, so set and get will use join and
    split"""

    def __init__(self, conf, conf_path):
        self._conf = conf
        self._conf_path = conf_path

    def has_section(self, section):
        return self._conf.has_section(section)

    def has_option(self, section, option):
        return self._conf.has_option(section, option)

    def add_section(self, section):
        self._conf.add_section(section)

    def get(self, tid, option):
        value = self._conf.get(tid, option)
        # Check single quote for backward compatibility
        if value[0] == '(' and value[-1] == ')':
            value = value[1:-1]
        # Remove all whitespaces, tabs, newlines and then split by ','
        value_without_spaces = ''.join(value.split())
        return value_without_spaces.split(',')

    def set(self, tid, option, value):
        value = ','.join(str(x) for x in value)
        self._conf.set(tid, option, value)
        self.save()

    def save(self):
        self._conf.write(open(self._conf_path, 'w'))


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


class CoreConfig(Borg):

    def __init__(self):
        if hasattr(self, '_conf'):
            # Borg has already been initialized
            return

        self.conf_path = os.path.join(CONFIG_DIR, 'gtg.conf')
        self._conf = open_config_file(self.conf_path)

        self.task_conf_path = os.path.join(CONFIG_DIR, 'tasks.conf')
        self._task_conf = open_config_file(self.task_conf_path)

    def save(self):
        ''' Saves the configuration of CoreConfig '''
        self._conf.write(open(self.conf_path, 'w'))
        self._task_conf.write(open(self.task_conf_path, 'w'))

    def get_subconfig(self, section):
        if not self._conf.has_section(section):
            self._conf.add_section(section)
        return SubConfig(section, self._conf, self.conf_path)

    def get_taskconfig(self):
        return TaskConfig(self._task_conf, self.task_conf_path)
