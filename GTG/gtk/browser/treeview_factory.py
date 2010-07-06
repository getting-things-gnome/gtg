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

    def __init__(self,requester,config):
        self.req = requester
        self.config = config

    #Functions for tasks columns
    def _count_active_subtasks_rec(self, task):
        count = 0
        if task.has_child():
            for tid in task.get_children():
                task = self.req.get_task(tid)
                if task and task.get_status() == Task.STA_ACTIVE:
                    count = count + 1 + self._count_active_subtasks_rec(task)
        return count
    
    def task_bg_color(tags,bg):
        if self.config['bg-color-enabled']:
            return color.background_color(tags,bg)
        else:
            return None
    
    #return an ordered list of tags of a task
    def task_tags_column(self,node):
        tags = node.get_tags()
        tags.sort(key = lambda x: x.get_name())
        return tags
        
    #task title
    def task_title_column(self, node):
        return saxutils.escape(node.get_title())
        
    #task title/label
    def task_label_column(self, node):
        title = saxutils.escape(task.get_title())
        print "we need the style here"
        color = self.style.text[gtk.STATE_INSENSITIVE].to_string()
        if task.get_status() == Task.STA_ACTIVE:
            count = self._count_active_subtasks_rec(task)
            if count != 0:
                title += " (%s)" % count
            
            if self.config["contents_preview_enable"]:
            	excerpt = saxutils.escape(task.get_excerpt(lines=1, \
            		strip_tags=True, strip_subtasks=True))
            	title += " <span size='small' color='%s'>%s</span>" \
            		%(color, excerpt) 
        elif task.get_status() == Task.STA_DISMISSED:
            title = "<span color='%s'>%s</span>"%(color, title)
        return title


    ######## The Factory #######################
    def active_tasks_treeview(self,tree):
        desc = {}
        
        #invisible 'title' column
        col = {}
        render_text = gtk.CellRendererText()
        render_text.set_property("ellipsize", pango.ELLIPSIZE_END)
        col['renderer'] = ['markup',render_text]
        col['value'] = [str,task_title_column]
        desc['visible'] = False
        desc['title'] = col
        
        # "tags" column (no title)
        col = {}
        render_tags = CellRendererTags()
        render_tags.set_property('xalign', 0.0)
        col['renderer'] = ['tag_list',render_tags]
        col['value'] = [str,self.task_tags_column]
        col['expandable'] = False
        col['resizable'] = False
        col.set_bg_color(task_bg_color,'tags')
        desc['tags'] = col


        # "label" column
        col = {}
        col['title'] = _("Title")
        render_text = gtk.CellRendererText()
        render_text.set_property("ellipsize", pango.ELLIPSIZE_END)
        col['renderer'] = ['markup',render_text]
        col['value'] = [str,task_label_column]
        col['expandable'] = True
        col['resizable'] = True
        col.set_bg_color(task_bg_color,'tags')
        col.set_sort_column
        desc['label'] = col
        


        

        # Start date column
        sdate_col   = gtk.TreeViewColumn()
        render_text = gtk.CellRendererText()
        sdate_col.set_title(_("Start date"))
        sdate_col.pack_start(render_text, expand=False)
        sdate_col.add_attribute(render_text, "markup", COL_SDATE)
        sdate_col.set_resizable(False)
        sdate_col.set_sort_column_id(COL_SDATE)
        sdate_col.set_cell_data_func(render_text, self._celldatafunction)


        # Due column
        ddate_col   = gtk.TreeViewColumn()
        render_text = gtk.CellRendererText()
        ddate_col.set_title(_("Due"))
        ddate_col.pack_start(render_text, expand=False)
        ddate_col.add_attribute(render_text, "markup", COL_DUE)
        ddate_col.set_resizable(False)
        ddate_col.set_sort_column_id(COL_DDATE)
        ddate_col.set_cell_data_func(render_text, self._celldatafunction)


        
        #Returning the treeview
        treeview = TreeView(tree,desc)
        
        #Now that the treeview is done, we can polish
        #TODO : those two functions are not implemented
        treeview.change_sort_column_id('label','title')
        treeview.set_main_search_column(COL_TITLE)
        
         # Global treeview properties
        self.set_property("expander-column", title_col)
        self.set_property("enable-tree-lines", False)
        self.set_rules_hint(False)
        
        return treeview
