# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2009 - Lionel Dricot & Bertrand Rousseau
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
Getting Things Gnome!  A personal organizer for the GNOME desktop
"""

import os
import locale
#Fallback to LANG C if unsupported locale
try:
    locale.setlocale(locale.LC_ALL, '')
except:
    locale.setlocale(locale.LC_ALL, 'C')

import gettext
try:
    from gtk import glade
    loaded_glade = glade
except:
    #that's not pretty but it looks functional.
    loaded_glade = None
from os.path import pardir, abspath, dirname, join

try:
    from xdg.BaseDirectory import xdg_config_home
    config_home = xdg_config_home
except ImportError:
    config_home = os.path.dirname(__file__)

LOCAL_ROOTDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DIST_ROOTDIR_LOCAL = "/usr/local/share/gtg"
DIST_ROOTDIR = "/usr/share/gtg"

#Translation setup (from pyroom)
GETTEXT_DOMAIN = 'gtg'
LOCALE_PATH = gettext.bindtextdomain(GETTEXT_DOMAIN)

for module in gettext, loaded_glade:
    #check if glade is well loaded to avoid error in Fedora build farm
    if module:
        module.bindtextdomain(GETTEXT_DOMAIN, LOCALE_PATH)
        module.textdomain(GETTEXT_DOMAIN)

translation = gettext.translation(GETTEXT_DOMAIN, LOCALE_PATH, fallback=True)

_ = translation.gettext
ngettext = translation.ngettext

#GTG directories setup
if os.path.isdir(os.path.join(LOCAL_ROOTDIR, 'data')):
    DATA_DIR = os.path.join(LOCAL_ROOTDIR, 'data')
elif os.path.isdir(DIST_ROOTDIR_LOCAL):
    DATA_DIR = DIST_ROOTDIR_LOCAL
else:
    DATA_DIR = DIST_ROOTDIR

#GTG plugin dir setup
if not os.path.isdir(os.path.join(LOCAL_ROOTDIR, 'GTG/plugins/')):
    PLUGIN_DIR = [DIST_ROOTDIR]
else:
    PLUGIN_DIR = [os.path.join(LOCAL_ROOTDIR, 'GTG/plugins/')]

if os.path.isdir(os.path.join(config_home, 'gtg/plugins')):
    PLUGIN_DIR.append(os.path.join(config_home, 'gtg/plugins'))

#Register GTG URI (temporary, it should be created by a schema upon installing)
# FIXME Discuss it with Luca
# FIXME it was commented out because of automatic build
"""
try:
    import gconf
    domain = "/desktop/gnome/url-handlers/gtg/"
    client = gconf.client_get_default()
    #this should work both in debugging mode and in deployed mode
    client.set_string(os.path.join(domain, "command"), "gtg %s")
    client.set_bool(os.path.join(domain, "enabled"), True)
    client.set_bool(os.path.join(domain, "needs_terminal"), False)
except ImportError:
    # Ignore it on systems which do not have GConf
    pass
"""
