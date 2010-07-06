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
import gtk

class TreeviewFactory():

    def active_tasks_treeview(self,tree):
        # Tag column
        tag_col     = gtk.TreeViewColumn()
        render_tags = CellRendererTags()
#        tag_col.set_title(_("Tags"))
        tag_col.pack_start(render_tags, expand=False)
        tag_col.add_attribute(render_tags, "tag_list", COL_TAGS)
        render_tags.set_property('xalign', 0.0)
        tag_col.set_resizable(False)
        tag_col.set_cell_data_func(render_tags, self._celldatafunction)
        #tag_col.set_clickable         (True)
        #tag_col.connect               ('clicked', tv_sort_cb)
        self.append_column(tag_col)
        self.set_column(COL_TAGS, tag_col)

        # Title column
        title_col   = gtk.TreeViewColumn()
        render_text = gtk.CellRendererText()
        render_text.set_property("ellipsize", pango.ELLIPSIZE_END)
        title_col.set_title(_("Title"))
        title_col.pack_start(render_text, expand=True)
        title_col.add_attribute(render_text, "markup", COL_LABEL)
        title_col.set_resizable(True)
        title_col.set_expand(True)
        title_col.set_sort_column_id(COL_TITLE)
        title_col.set_cell_data_func(render_text, self._celldatafunction)
        self.append_column(title_col)
        self.set_column(COL_TITLE, title_col)
        self.set_search_column(COL_TITLE)

        # Start date column
        sdate_col   = gtk.TreeViewColumn()
        render_text = gtk.CellRendererText()
        sdate_col.set_title(_("Start date"))
        sdate_col.pack_start(render_text, expand=False)
        sdate_col.add_attribute(render_text, "markup", COL_SDATE)
        sdate_col.set_resizable(False)
        sdate_col.set_sort_column_id(COL_SDATE)
        sdate_col.set_cell_data_func(render_text, self._celldatafunction)
        self.append_column(sdate_col)
        self.set_column(COL_SDATE, sdate_col)

        # Due column
        ddate_col   = gtk.TreeViewColumn()
        render_text = gtk.CellRendererText()
        ddate_col.set_title(_("Due"))
        ddate_col.pack_start(render_text, expand=False)
        ddate_col.add_attribute(render_text, "markup", COL_DUE)
        ddate_col.set_resizable(False)
        ddate_col.set_sort_column_id(COL_DDATE)
        ddate_col.set_cell_data_func(render_text, self._celldatafunction)
        self.append_column(ddate_col)
        self.set_column(COL_DUE, ddate_col)

        # days left
#        dleft_col   = gtk.TreeViewColumn()
#        render_text = gtk.CellRendererText()
#        dleft_col.set_title(_("Days left"))
#        dleft_col.pack_start(render_text, expand=False)
#        dleft_col.add_attribute(render_text, "markup", COL_DLEFT)
#        dleft_col.set_resizable(False)
#        dleft_col.set_sort_column_id(COL_DLEFT)
#        dleft_col.set_cell_data_func(render_text, self._celldatafunction)
#        self.append_column(dleft_col)
#        self.set_column(COL_DLEFT, dleft_col)

        # Global treeview properties
        self.set_property("expander-column", title_col)
        self.set_property("enable-tree-lines", False)
        self.set_rules_hint(False)
