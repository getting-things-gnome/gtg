# -*- coding: utf-8 -*-
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
GTG's core functionality.

In order to not interact directly with the datastore, we provide
"requesters".  The requester is only an interface and there can be as
many requesters as you want as long as they are all from the same
datastore.  Requester also provides an interface for the tagstore.

If you want to display only a subset of tasks, you can either:

 - have access to the main FilteredTree (the one displayed in the main
   window) and apply filters on it.  (You can create your own)

 - get your own personal FilteredTree and apply on it the filters you
   want without interfering with the main view. (This is how the closed
   tasks pane is built currently)
"""

from re import findall
import configparser

from xdg.BaseDirectory import xdg_data_home, xdg_config_home, xdg_data_dirs
import os

from GTG.tools.borg import Borg
import GTG

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
# Each GTG component using config should be ported to SubConfig and, for each
# setting, a default value should be written in the DEFAULTS above.
#
# Currently done : browser
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


class CoreConfig(Borg):
    # The projects and tasks are of course DATA !
    # We then use XDG_DATA for them
    # Don't forget the "/" at the end.
    DATA_FILE = "projects.xml"
    CONF_FILE = "gtg.conf"
    TASK_CONF_FILE = "tasks.conf"
    conf_dict = None
    # DBus
    BUSNAME = "org.gnome.GTG"
    BUSINTERFACE = "/org/gnome/GTG"
    # TAGS
    ALLTASKS_TAG = "gtg-tags-all"
    NOTAG_TAG = "gtg-tags-none"
    SEP_TAG = "gtg-tags-sep"
    SEARCH_TAG = "search"

    def check_config_file(self, path):
        """ This function bypasses the errors of config file and allows GTG
        to open smoothly"""
        config = configparser.ConfigParser()
        try:
            config.read(path)
        except configparser.Error:
            open(path, "w").close()
        return config

    def __init__(self):
        if hasattr(self, 'data_dir'):
            # Borg has already been initialized
            return
        self.data_dir = os.path.join(xdg_data_home, 'gtg/')
        self.conf_dir = os.path.join(xdg_config_home, 'gtg/')
        if not os.path.exists(self.conf_dir):
            os.makedirs(self.conf_dir)
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        self.conf_path = os.path.join(self.conf_dir, self.CONF_FILE)
        self.task_conf_path = os.path.join(self.conf_dir, self.TASK_CONF_FILE)
        if not os.path.exists(self.conf_path):
            open(self.conf_path, "w").close()
        if not os.path.exists(self.task_conf_path):
            open(self.task_conf_path, "w").close()
        for conf_file in [self.conf_path, self.task_conf_path]:
            if not os.access(conf_file, os.R_OK | os.W_OK):
                raise Exception("File " + file +
                                " is a configuration file for gtg, but it "
                                "cannot be read or written. Please check it")
        self._conf = self.check_config_file(self.conf_path)
        self._task_conf = self.check_config_file(self.task_conf_path)

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

    def get_icons_directories(self):
        """ Returns the directories containing the icons """
        icons_dirs = [os.path.join(dir, 'gtg/icons') for dir in xdg_data_dirs]
        icons_dirs.append(os.path.join(GTG.DATA_DIR, "icons"))
        icons_dirs.append(GTG.DATA_DIR)
        return icons_dirs

    def get_data_dir(self):
        return self.data_dir

    def set_data_dir(self, path):
        self.data_dir = path

    def get_conf_dir(self):
        return self.conf_dir

    def set_conf_dir(self, path):
        self.conf_dir = path
        self.conf_path = os.path.join(self.conf_dir, self.CONF_FILE)
        self.task_conf_path = os.path.join(self.conf_dir, self.TASK_CONF_FILE)
