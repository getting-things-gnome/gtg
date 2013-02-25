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
"""
The task editing GUI
"""
import os

from GTG import _


class GnomeConfig:
    current_rep = os.path.dirname(os.path.abspath(__file__))
    GLADE_FILE = os.path.join(current_rep, "taskeditor.glade")

    MARK_DONE = _("Mark as Done")
    MARK_UNDONE = _("Mark as not Done")
    MARK_DISMISS = _("Dismiss")
    MARK_UNDISMISS = _("Undismiss")

    MARK_DONE_TOOLTIP = _("Mark this task as done")
    MARK_UNDONE_TOOLTIP = _("Mark this task as to be done")
    MARK_DISMISS_TOOLTIP = _("Mark this task as not to be done anymore")
    MARK_UNDISMISS_TOOLTIP = _("Mark this task as to be done")
    DELETE_TOOLTIP = _("Permanently remove this task")
    SUBTASK_TOOLTIP = _("Insert a subtask in this task")
    TAG_TOOLTIP = _("Insert a tag in this task")

    # Number of second between to save in the task editor
    SAVETIME = 7
