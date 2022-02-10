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


# This is the tool package. It contains some useful function and tool
# that could be useful for any part of GTG.

from gettext import gettext as _


class GnomeConfig():
    CANLOAD = _("Everything necessary to run this plugin is available.")
    CANNOTLOAD = _("This plugin can not be loaded.")
    miss1 = _("Some python modules are missing.")
    miss2 = _("Please install the following python modules:")
    MODULEMISSING = f"{miss1} \n{miss2}"
    dmiss1 = _("Some remote D-Bus objects are missing.")
    dmiss2 = _("Please start the following applications:")
    DBUSMISSING = f"{dmiss1} \n{dmiss2}"
    bmiss1 = _("Some modules and remote D-Bus objects are missing.")
    bmiss2 = _("Please install or start the following components:")
    MODULANDDBUS = f"{bmiss1} \n{bmiss2}"
    umiss1 = _("An unknown error occurred while loading the plugin.")
    umiss2 = _("Very helpful message, isn't it? Please report a bug.")
    UNKNOWN = f"{umiss1} \n{umiss2}"
