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

#Different tools used by the TaskBrowser
import gtk
import gobject

from GTG import _
from GTG.taskbrowser.CellRendererTags import CellRendererTags

# TAGS MODEL ##################################################################

TAGS_MODEL_OBJ         = 0
TAGS_MODEL_COLOR       = 1
TAGS_MODEL_NAME        = 2
TAGS_MODEL_COUNT       = 3
TAGS_MODEL_SEP         = 4

def new_tag_ts():
    """Returning a tree store to handle the tags"""

    tag_ts         = gtk.ListStore(gobject.TYPE_PYOBJECT, \
                                   str,                   \
                                   str,                   \
                                   str,                   \
                                   bool)
    return tag_ts

### TAGS TREEVIEW #############################################################

def tag_separator_filter(model, itera, user_data=None):
    return model.get_value(itera, TAGS_MODEL_SEP)

def init_tags_tview(tv):

    # Tag column
    tag_col      = gtk.TreeViewColumn()
    render_text  = gtk.CellRendererText()
    render_count = gtk.CellRendererText()
    render_tags  = CellRendererTags()
    tag_col.set_title(_("Tags"))
    tag_col.set_clickable(False)
    tag_col.pack_start(render_tags, expand=False)
    tag_col.set_attributes(render_tags, tag=TAGS_MODEL_OBJ)
    tag_col.pack_start(render_text, expand=True)
    tag_col.set_attributes(render_text, markup=TAGS_MODEL_NAME)
    tag_col.pack_end(render_count, expand=False)
    tag_col.set_attributes(render_count, markup=TAGS_MODEL_COUNT)
    render_count.set_property("foreground", "#888a85")
    render_count.set_property('xalign', 1.0)
    render_tags.set_property('ypad', 3)
    render_text.set_property('ypad', 3)
    render_count.set_property('xpad', 3)
    render_count.set_property('ypad', 3)
    tag_col.set_sort_column_id(-1)
    tag_col.set_expand(True)
    tv.append_column(tag_col)
    # Global treeview properties
    tv.set_row_separator_func(tag_separator_filter)
    tv.set_headers_visible(False)

### NOTES TREEVIEW ############################################################

#def init_note_tview(tv):
#    # Title column
#    title_col    = gtk.TreeViewColumn()
#    render_text  = gtk.CellRendererText()
#    title_col.set_title(_("Notes"))
#    title_col.pack_start(render_text, expand=True)
#    title_col.set_attributes(render_text, markup=tasktree.COL_TITLE)
#    title_col.set_sort_column_id(tasktree.COL_TITLE)
#    title_col.set_expand(True)
#    tv.append_column(title_col)
