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
Information where various resources like config, icons, etc. are stored
"""
import os

from gi.repository import GLib

# Folder where core GTG data is stored like services information, tags, etc
DATA_DIR = os.path.join(GLib.get_user_data_dir(), 'gtg')
# Folder where configuration like opened tasks is stored
CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), 'gtg')

# File defining used tags
TAGS_XMLFILE = os.path.join(DATA_DIR, 'tags.xml')

# Root is 2 folders up of this file (as it is in GTG/core)
local_rootdir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..'))

# Icons from local folder
ICONS_DIR = os.path.join(local_rootdir, 'data', 'icons')
CSS_DIR = os.path.join(local_rootdir, 'GTG', 'gtk', 'data')

# Where data & cache for synchronization services is stored
SYNC_DATA_DIR = os.path.join(DATA_DIR, 'backends')
SYNC_CACHE_DIR = os.path.join(GLib.get_user_cache_dir(), 'gtg')

# Folders where to look for plugins
PLUGIN_DIRS = [os.path.join(local_rootdir, 'GTG', 'plugins')]

# Place for user's plugins installed locally
USER_PLUGINS_DIR = os.path.join(CONFIG_DIR, 'plugins')
if os.path.exists(USER_PLUGINS_DIR):
    PLUGIN_DIRS.append(USER_PLUGINS_DIR)

UI_DIR = os.path.join(local_rootdir, 'GTG', 'gtk', 'data')


def plugin_configuration_dir(plugin_name):
    """ Returns the directory for plugin configuration. """
    return os.path.join(USER_PLUGINS_DIR, plugin_name)
