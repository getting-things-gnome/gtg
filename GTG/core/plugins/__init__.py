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


# This is the tool package. It contains some useful function and tool
# that could be useful for any part of GTG.

import os

from GTG import _


class GnomeConfig:
    current_rep = os.path.dirname(os.path.abspath(__file__))
    GLADE_FILE = os.path.join(current_rep, "pluginmanager.glade")

    CANLOAD = _("Everything necessary to run this plugin is available.")
    CANNOTLOAD = _("The plugin can not be loaded")
    miss1 = _("Some python modules are missing")
    miss2 = _("Please install the following python modules:")
    MODULEMISSING = "%s \n%s" % (miss1, miss2)
    dmiss1 = _("Some remote dbus objects are missing.")
    dmiss2 = _("Please start the following applications:")
    DBUSMISSING = "%s \n%s" % (dmiss1, dmiss2)
    bmiss1 = _("Some modules and remote dbus objects are missing.")
    bmiss2 = _("Please install or start the following components:")
    MODULANDDBUS = "%s \n%s" % (bmiss1, bmiss2)
    umiss1 = _("Unknown error while loading the plugin.")
    umiss2 = _("Very helpful message, isn't it? Please report a bug.")
    UNKNOWN = "%s \n%s" % (umiss1, umiss2)
