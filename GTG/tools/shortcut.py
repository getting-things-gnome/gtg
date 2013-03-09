# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 - Lionel Dricot & Bertrand Rousseau
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

import subprocess
import re


CHECK_VERSION = "gsettings list-keys " \
"org.gnome.settings-daemon.plugins.media-keys"
NEW_TASK_ACTION = "gtg_new_task"
NEW_TASK_NAME = "GTG New Task"
GSETTINGS_GET_LIST = "gsettings get " \
"org.gnome.settings-daemon.plugins.media-keys custom-keybindings"
GSETTINGS_SET_LIST = "gsettings set " \
"org.gnome.settings-daemon.plugins.media-keys custom-keybindings"
GSETTINGS_GET = "gsettings get " \
"org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:" \
"/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom"
GSETTINGS_SET = "gsettings set " \
"org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:" \
"/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom"
GCONF_GET = "gconftool-2 --get /desktop/gnome/keybindings/custom"
GCONF_SET = "gconftool-2 --type string --set /desktop/gnome/keybindings/custom"


def get_saved_binding():
    """ Get the current shortcut if the task exists """
    list_keys = call_subprocess(CHECK_VERSION).splitlines()
    if "custom-keybindings" in list_keys:
        binding = get_shortcut_from_dconf()
    else:
        binding = get_shortcut_from_gconf()
    return binding


def get_shortcut_from_dconf():
    """ If system uses dconf, then get the shortcut via gsettings """
    dconf_out = call_subprocess(GSETTINGS_GET_LIST)
    custom_shortcuts_list = re.findall(r'\d+', dconf_out)

    for entry in custom_shortcuts_list:
        get_cmd = call_subprocess(GSETTINGS_GET, entry, "/ command")

        if NEW_TASK_ACTION in get_cmd:
            get_bind = call_subprocess(GSETTINGS_GET, entry, "/ binding")
            return get_bind.strip("\'\n")
    return None


def get_shortcut_from_gconf():
    """ If system uses gconf, then get the shortcut via gconftool-2 """
    item = 0
    while True:
        get_action = call_subprocess(GCONF_GET, str(item), "/action")

        if NEW_TASK_ACTION in get_action:
            get_bind = call_subprocess(GCONF_GET, str(item), "/binding")
            return get_bind.rstrip("\n")

        elif get_action == "":
            get_name = call_subprocess(GCONF_GET, str(item), "/name")
            if get_name == "":
                return None
        item += 1


def save_new_binding(binding, button_state):
    """ When user has entered a new shortcut """
    if button_state:
        list_keys = call_subprocess(CHECK_VERSION).splitlines()
        if "custom-keybindings" in list_keys:
            add_shortcut_to_dconf(binding)
        else:
            add_shortcut_to_gconf(binding)


def add_shortcut_to_dconf(binding):
    """ If system uses dconf, then set the new shortcut via gsettings """
    dconf_out = call_subprocess(GSETTINGS_GET_LIST)
    custom_keys = re.findall(r'\d+', dconf_out)
    a = []

    for entry in custom_keys:
        get_cmd = call_subprocess(GSETTINGS_GET, entry, "/ command")

        if NEW_TASK_ACTION in get_cmd:
            call_subprocess(GSETTINGS_SET, entry, "/ binding", binding)
            return
        a.append(int(entry))

    if a == []:
        index = 0
    else:
        a.sort()
        index = a[-1] + 1
    append_this = "['/org/gnome/settings-daemon/plugins/media-keys/" \
    "custom-keybindings/custom" + str(index) + "/']"
    call_subprocess(GSETTINGS_SET, str(index), "/ command", NEW_TASK_ACTION)
    call_subprocess(GSETTINGS_SET, str(index), "/ binding", binding)
    call_subprocess(GSETTINGS_SET, str(index), "/ name", NEW_TASK_NAME)

    if index == 0:
        call_subprocess(GSETTINGS_SET_LIST, key=' ' + append_this)

    else:
        result_list = dconf_out[:-2] + ", " + append_this[1:]
        call_subprocess(GSETTINGS_SET_LIST, to_append=result_list)


def add_shortcut_to_gconf(binding):
    """ If system uses gconf, then set the new shortcut via gconftool-2 """
    item = 0
    while True:
        get_action = call_subprocess(GCONF_GET, str(item), "/action")

        if NEW_TASK_ACTION in get_action:
            call_subprocess(GCONF_SET, str(item), "/binding", binding)
            return

        if get_action == "":
            call_subprocess(GCONF_SET, str(item), "/action", NEW_TASK_ACTION)
            call_subprocess(GCONF_SET, str(item), "/binding", binding)
            call_subprocess(GCONF_SET, str(item), "/name", NEW_TASK_NAME)
            return
        item += 1


def call_subprocess(cmd, i="", key="", to_append=None):
    """ Sets the values in either dconf or gconf.
        'cmd' holds the command to access the configuration database,
        'i' accesses a custom shortcut,
        'key' accesses values inside the shortcut,
        'to_append' contains the new value to replace if any """
    cmd += i + key
    cmd = cmd.split(" ")
    if to_append is not None:
        cmd.append(to_append)
    out = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return out.communicate()[0]


def check_invalidity(binding, key, mods):
    """ Checks if the user has entered inappropriate shortcut """
    if mods == 0:
        if (key >= 97 and key <= 122):
            # key is an alphabet
            return 1
        elif (key >= 48 and key <= 57):
            # key is a number
            return 1
        elif (key >= 65361 and key <= 65364):
            # key is one of the arrow keys
            return 1
        elif key == 32:
            # key is 'space'
            return 1
    return 0
