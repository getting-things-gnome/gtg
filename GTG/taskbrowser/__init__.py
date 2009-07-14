# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personnal organizer for the GNOME desktop
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


#This is the gnome_frontend package. It's a GTK interface that want to be
#simple, HIG compliant and well integrated with Gnome.
import os

from GTG import _

class GnomeConfig :
    current_rep = os.path.dirname(os.path.abspath(__file__))
    GLADE_FILE    = os.path.join(current_rep,"taskbrowser.glade")
    
    MARK_DONE      = _("Mark as done")
    MARK_DONE_TOOLTIP = _("Mark the selected task as done")
    MARK_UNDONE    = _("Mark as not done")
    MARK_UNDONE_TOOLTIP = _("Mark the selected task as to be done")
    MARK_DISMISS   = _("Dismiss")
    MARK_DISMISS_TOOLTIP = _("Mark the task as not to be done anymore")
    MARK_UNDISMISS = _("Undismiss")
    MARK_UNDISMISS_TOOLTIP = _("Mark the selected task as to be done")
    DELETE_TOOLTIP = _("Permanently remove the selected task")
