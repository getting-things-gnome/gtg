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

""" Configuration for browser, it contains path to .glade files """

import os


class ViewConfig:
    current_rep = os.path.dirname(os.path.abspath(__file__))
    DELETE_GLADE_FILE = os.path.join(current_rep, "deletion.glade")
    PREFERENCES_GLADE_FILE = os.path.join(current_rep, "preferences.glade")
    PLUGINS_GLADE_FILE = os.path.join(current_rep, "plugins.glade")
    BACKENDS_GLADE_FILE = os.path.join(current_rep, "backends_dialog.glade")
