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
The GTK frontend for browsing collections of tasks.

This is the gnome_frontend package. It's a GTK interface that wants to be
simple, HIG compliant and well integrated with Gnome.
"""
import os


class GnomeConfig():
    current_rep = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(current_rep, '..', 'data')
    ACTION_ROW = os.path.join(data, "action_row.ui")
    BROWSER_UI_FILE = os.path.join(data, "main_window.ui")
    HELP_OVERLAY_UI_FILE = os.path.join(data, "help_overlay.ui")
    MENUS_UI_FILE = os.path.join(data, "context_menus.ui")
    MODIFYTAGS_UI_FILE = os.path.join(data, "modify_tags.ui")
    TAG_EDITOR_UI_FILE = os.path.join(data, "tag_editor.ui")
    SEARCH_EDITOR_UI_FILE = os.path.join(data, "search_editor.ui")
