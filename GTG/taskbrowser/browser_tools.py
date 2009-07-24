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

from GTG.taskbrowser.CellRendererTags import CellRendererTags
from GTG.core.task_tree_model import TaskTreeModel
from GTG import _

# ACTIVE TASKS MODEL ##########################################################

#TASK_MODEL_OBJ         = 0
#TASK_MODEL_TITLE       = 1
#TASK_MODEL_TITLE_STR   = 2
#TASK_MODEL_DDATE_STR   = 3
#TASK_MODEL_DLEFT_STR   = 4
#TASK_MODEL_TAGS        = 5
#TASK_MODEL_BGCOL       = 6


#def new_task_ts(dnd_func=None):
#    """Returning a tree store to handle the active tasks"""

#    task_ts        = gtk.TreeStore(gobject.TYPE_PYOBJECT, \
#                                   str,                   \
#                                   str,                   \
#                                   str,                   \
#                                   str,                   \
#                                   gobject.TYPE_PYOBJECT, \
#                                   str)
#    #this is our manual drag-n-drop handling
#    if dnd_func:
#        task_ts.connect("row-changed", dnd_func, "insert")
#        task_ts.connect("row-deleted", dnd_func, None, "delete")
#    return task_ts

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

# CLOSED TASKS MODEL ##########################################################

CTASKS_MODEL_OBJ       = 0
CTASKS_MODEL_TITLE     = 2
CTASKS_MODEL_DDATE     = 3
CTASKS_MODEL_DDATE_STR = 4
CTASKS_MODEL_BGCOL     = 5
CTASKS_MODEL_TAGS      = 6


def new_ctask_ts():
    """Returning a tree store to handle the closed tasks"""

    ctask_ts       = gtk.TreeStore(gobject.TYPE_PYOBJECT, \
                                   str,                   \
                                   str,                   \
                                   str,                   \
                                   str,                   \
                                   str,                   \
                                   gobject.TYPE_PYOBJECT)
    return ctask_ts

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

### ACTIVE TASKS TREEVIEW #####################################################

TASKLIST_COL_TAGS  = 0
TASKLIST_COL_TITLE = 1
TASKLIST_COL_DDATE = 2
TASKLIST_COL_DLEFT = 3


def init_task_tview(tv, tv_sort_cb):

    columns = []

    # Tag column
    tag_col     = gtk.TreeViewColumn()
    render_tags = CellRendererTags()
    tag_col.set_title(_("Tags"))
    tag_col.pack_start(render_tags, expand=False)
    tag_col.add_attribute(render_tags, "tag_list", TaskTreeModel.COL_TAGS)
    render_tags.set_property('xalign', 0.0)
    tag_col.set_resizable(False)
    tag_col.add_attribute(render_tags, "cell-background", TaskTreeModel.COL_BGCOL)
    #tag_col.set_clickable         (True)
    #tag_col.connect               ('clicked', tv_sort_cb)
    tv.append_column(tag_col)
    columns.insert(TASKLIST_COL_TAGS, tag_col)

    # Title column
    title_col   = gtk.TreeViewColumn()
    render_text = gtk.CellRendererText()
    title_col.set_title(_("Title"))
    title_col.pack_start(render_text, expand=False)
    title_col.add_attribute(render_text, "markup", TaskTreeModel.COL_TITLE)
    title_col.set_resizable(True)
    title_col.set_expand(True)
    #The following line seems to fix bug #317469
    #I don't understand why !!! It's voodoo !
    #Is there a Rubber Chicken With a Pulley in the Middle ?
    title_col.set_max_width(100)
    title_col.add_attribute(render_text, "cell_background", TaskTreeModel.COL_BGCOL)
    title_col.set_clickable(True)
    title_col.connect('clicked', tv_sort_cb)
    tv.append_column(title_col)
    columns.insert(TASKLIST_COL_TITLE, title_col)

    # Due date column
    ddate_col   = gtk.TreeViewColumn()
    render_text = gtk.CellRendererText()
    ddate_col.set_title(_("Due date"))
    ddate_col.pack_start(render_text, expand=False)
    ddate_col.add_attribute(render_text, "markup", TaskTreeModel.COL_DDATE)
    ddate_col.set_resizable(False)
    ddate_col.add_attribute(render_text, "cell_background", TaskTreeModel.COL_BGCOL)
    ddate_col.set_clickable(True)
    ddate_col.connect('clicked', tv_sort_cb)
    tv.append_column(ddate_col)
    columns.insert(TASKLIST_COL_DDATE, ddate_col)

    # days left
    dleft_col   = gtk.TreeViewColumn()
    render_text = gtk.CellRendererText()
    dleft_col.set_title(_("Days left"))
    dleft_col.pack_start(render_text, expand=False)
    dleft_col.add_attribute(render_text, "markup", TaskTreeModel.COL_DLEFT)
    dleft_col.set_resizable(False)
    dleft_col.add_attribute(render_text, "cell_background", TaskTreeModel.COL_BGCOL)
    dleft_col.set_clickable(True)
    dleft_col.connect('clicked', tv_sort_cb)
    tv.append_column(dleft_col)
    columns.insert(TASKLIST_COL_DLEFT, dleft_col)

    # Global treeview properties
    tv.set_property("expander-column", title_col)
    tv.set_property("enable-tree-lines", False)
    tv.set_rules_hint(False)
    tv.set_reorderable(True)

    return columns

### CLOSED TASKS TREEVIEW #####################################################

CTASKLIST_COL_TAGS  = 0
CTASKLIST_COL_DDATE = 1
CTASKLIST_COL_TITLE = 2


def init_closed_tasks_tview(tv, tv_sort_cb):

    columns = []

    # Tag column
    tag_col     = gtk.TreeViewColumn()
    render_tags = CellRendererTags()
    tag_col.set_title(_("Tags"))
    tag_col.pack_start(render_tags, expand=False)
    tag_col.add_attribute(render_tags, "tag_list", TaskTreeModel.COL_TAGS)
    render_tags.set_property('xalign', 0.0)
    tag_col.set_resizable(False)
    tag_col.add_attribute(render_tags, "cell-background", TaskTreeModel.COL_BGCOL)
    #tag_col.set_clickable         (True)
    #tag_col.connect               ('clicked', self.sort_tasklist_rows)
    tv.append_column(tag_col)
    columns.insert(CTASKLIST_COL_TAGS, tag_col)

    # Done date column
    ddate_col    = gtk.TreeViewColumn()
    render_text  = gtk.CellRendererText()
    ddate_col.set_title(_("Closing date"))
    ddate_col.pack_start(render_text, expand=True)
    ddate_col.set_attributes(render_text, markup=TaskTreeModel.COL_DDATE)
    ddate_col.set_sort_column_id(CTASKS_MODEL_DDATE)
    ddate_col.add_attribute(render_text, "cell_background", TaskTreeModel.COL_BGCOL)
    tv.append_column(ddate_col)
    columns.insert(CTASKLIST_COL_DDATE, ddate_col)

    # Title column
    title_col    = gtk.TreeViewColumn()
    render_text  = gtk.CellRendererText()
    title_col.set_title(_("Title"))
    title_col.pack_start(render_text, expand=True)
    title_col.set_attributes(render_text, markup=TaskTreeModel.COL_TITLE)
    title_col.set_sort_column_id(CTASKS_MODEL_TITLE)
    title_col.set_expand(True)
    title_col.add_attribute(render_text, "cell_background", TaskTreeModel.COL_BGCOL)
    tv.append_column(title_col)
    columns.insert(CTASKLIST_COL_TITLE, title_col)

### NOTES TREEVIEW ############################################################

def init_note_tview(tv):
    # Title column
    title_col    = gtk.TreeViewColumn()
    render_text  = gtk.CellRendererText()
    title_col.set_title(_("Notes"))
    title_col.pack_start(render_text, expand=True)
    title_col.set_attributes(render_text, markup=CTASKS_MODEL_TITLE)
    title_col.set_sort_column_id(CTASKS_MODEL_TITLE)
    title_col.set_expand(True)
    tv.append_column(title_col)
