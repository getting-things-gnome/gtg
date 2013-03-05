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

list_prefix = "gsettings list-keys "
CHECK_VERSION = list_prefix + "org.gnome.settings-daemon.plugins.media-keys"
NEW_TASK_ACTION = "gtg_new_task"
NEW_TASK_NAME = "GTG New Task"
get_temp = "gsettings get "
path = "org.gnome.settings-daemon.plugins.media-keys "
GSETTINGS_GET_LIST = get_temp + path + "custom-keybindings"
set_temp = "gsettings set "
GSETTINGS_SET_LIST = set_temp + path + "custom-keybindings"
key_path1 = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:"
path2 = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/"
GSETTINGS_GET = get_temp + key_path1 + path2 + "custom"
GSETTINGS_SET = set_temp + key_path1 + path2 + "custom"
GCONF_GET = "gconftool-2 --get /desktop/gnome/keybindings/custom"
GCONF_SET = "gconftool-2 --type string --set /desktop/gnome/keybindings/custom"


def get_saved_binding():
    """ Get the current shortcut if the task exists """
    list_keys = call_subprocess(cmd = CHECK_VERSION)
    list_keys = list_keys.splitlines()
    if "custom-keybindings" in list_keys:
        binding = get_shortcut_from_dconf()
    else:
        binding = get_shortcut_from_gconf()
    return binding


def get_shortcut_from_dconf():
    """ If system uses dconf, then get the shortcut via gsettings """
    dconf_out = call_subprocess(cmd = GSETTINGS_GET_LIST)
    custom_shortcuts_list = re.findall(r'custom[0-9]+', dconf_out)

    for entry in custom_shortcuts_list:
        to_access = entry[-1]
        get_cmd = call_subprocess(cmd = GSETTINGS_GET, i = str(to_access),
                                  key = "/ command")

        if NEW_TASK_ACTION in get_cmd:
            get_bind = call_subprocess(cmd = GSETTINGS_GET, i = str(to_access),
                                       key = "/ binding")
            return get_bind.strip("\'\n")
    return None


def get_shortcut_from_gconf():
    """ If system uses gconf, then get the shortcut via gconftool-2 """
    item=0
    while(1):
        get_action = call_subprocess(cmd = GCONF_GET, i = str(item),
                                     key = "/action")

        if NEW_TASK_ACTION in get_action:
            get_bind = call_subprocess(cmd = GCONF_GET, i = str(item),
                                       key = "/binding")
            return get_bind.rstrip("\n")

        elif get_action == "":
            get_name = call_subprocess(cmd = GCONF_GET, i = str(item),
                                       key = "/name")
            if get_name == "":
                return None
    item += 1


def on_shortcut_change(binding, button_state):
    """ When user has entered a new shortcut """
    if button_state == True:
        list_keys = call_subprocess(cmd = CHECK_VERSION)
        list_keys = list_keys.splitlines()
        if "custom-keybindings" in list_keys:
            add_shortcut_to_dconf(binding)
        else:
            add_shortcut_to_gconf(binding)


def add_shortcut_to_dconf(binding):
    """ If system uses dconf, then set the new shortcut via gsettings """
    dconf_out = call_subprocess(cmd = GSETTINGS_GET_LIST)
    custom_keys = re.findall(r'custom[0-9]+', dconf_out)

    for entry in custom_keys:
        to_access = entry[-1]
        get_cmd = call_subprocess(cmd = GSETTINGS_GET, i = str(to_access),
                                  key = "/ command")

        if NEW_TASK_ACTION in get_cmd:
            call_subprocess(cmd = GSETTINGS_SET, to_append = binding,
                            i = str(to_access), key = "/ binding")
            return

    a=[]
    for item in custom_keys:
        a.append(int(re.findall(r'[0-9]+', item)[0]))
    if a == []:
        index = 0
    else:
        a.sort()
        index = a[-1] + 1
    prefix = "['/org/gnome/settings-daemon/plugins/media-keys/"
    prefix = prefix + "custom-keybindings/custom"
    append_this = prefix + str(index) + "/']"
    call_subprocess(cmd = GSETTINGS_SET, to_append = NEW_TASK_ACTION,
                    i = str(index), key = "/ command")
    call_subprocess(cmd = GSETTINGS_SET, to_append = binding,
                    i = str(index), key = "/ binding")
    call_subprocess(cmd = GSETTINGS_SET, to_append = NEW_TASK_NAME,
                    i = str(index), key = "/ name")

    if index == 0:
        call_subprocess(cmd = GSETTINGS_SET_LIST, key = ' ' + append_this)

    else:
        result_list = dconf_out[:-2] + ", "
        result_list = result_list + append_this[1:-1] + "]"
        call_subprocess(cmd = GSETTINGS_SET_LIST,
                        to_append = result_list)


def add_shortcut_to_gconf(binding):
    """ If system uses gconf, then set the new shortcut via gconftool-2 """
    item=0
    while(1):
        get_action = call_subprocess(cmd = GCONF_GET, i = str(item),
                                     key = "/action")

        if NEW_TASK_ACTION in get_action:
            binding_ans = call_subprocess(cmd = GCONF_SET,
                                          to_append = binding, i = str(item),
                                          key = "/binding")
            break

        if get_action == "":
            call_subprocess(cmd = GCONF_SET, to_append = NEW_TASK_ACTION,
                            i = str(item), key = "/action")
            call_subprocess(cmd = GCONF_SET, to_append = binding,
                            i = str(item), key = "/binding")
            call_subprocess(cmd = GCONF_SET, to_append = NEW_TASK_NAME,
                            i = str(item), key = "/name")
            break
    item += 1


def call_subprocess(cmd, i = "", key = "", to_append = None):
    """ Sets the values in either dconf or gconf.
        'cmd' holds the command to access the configuration database,
        'i' accesses a custom shortcut,
        'key' accesses values inside the shortcut,
        'to_append' contains the new value to replace if any """
    cmd = cmd + i + key
    cmd = cmd.split(" ")
    if to_append != None:
        cmd.append(to_append)
    out = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
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
