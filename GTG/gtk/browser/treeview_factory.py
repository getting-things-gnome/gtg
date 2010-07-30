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
import gobject
import pango
import xml.sax.saxutils as saxutils

from GTG     import _
from GTG.core.task import Task
from GTG.gtk.browser.CellRendererTags import CellRendererTags
from GTG.gtk.liblarch_gtk import TreeView

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
        print "tast_title_column"
        return saxutils.escape(node.get_title())
        
    #task title/label
    def task_label_column(self, node):
        title = saxutils.escape(node.get_title())
        print "we need the style here"
#        color = self.treeview.style.text[gtk.STATE_INSENSITIVE].to_string()
        color = "#F00"
        if node.get_status() == Task.STA_ACTIVE:
            count = self._count_active_subtasks_rec(node)
            if count != 0:
                title += " (%s)" % count
            
            if self.config.has_key("contents_preview_enable"):
            	excerpt = saxutils.escape(node.get_excerpt(lines=1, \
            		strip_tags=True, strip_subtasks=True))
            	title += " <span size='small' color='%s'>%s</span>" \
            		%(color, excerpt) 
        elif node.get_status() == Task.STA_DISMISSED:
            title = "<span color='%s'>%s</span>"%(color, title)
        print "task_label_column"
        return title
        
    #task start date
    def task_sdate_column(self,node):
        print "task_sdate_column"
        return node.get_start_date().to_readable_string()
        
    def task_duedate_column(self,node):
        print "task_duetade_column"
        return node.get_due_date().to_readable_string()


    ######## The Factory #######################
    def active_tasks_treeview(self,tree):
        desc = {}
        
        #invisible 'title' column
        col_name = 'title'
        col = {}
        render_text = gtk.CellRendererText()
        render_text.set_property("ellipsize", pango.ELLIPSIZE_END)
        col['renderer'] = ['markup',render_text]
        col['value'] = [str,self.task_title_column]
        col['visible'] = False
        col['order'] = 0
        desc[col_name] = col
        
#        # "tags" column (no title)
#        col_name = 'tags'
#        col = {}
#        render_tags = CellRendererTags()
#        render_tags.set_property('xalign', 0.0)
#        col['renderer'] = ['tag_list',render_tags]
#        col['value'] = [gobject.TYPE_PYOBJECT,self.task_tags_column]
#        col['expandable'] = False
#        col['resizable'] = False
#        col['order'] = 1
#        desc[col_name] = col

        # "label" column
        col_name = 'label'
        col = {}
        col['title'] = _("Title")
        render_text = gtk.CellRendererText()
        render_text.set_property("ellipsize", pango.ELLIPSIZE_END)
        col['renderer'] = ['markup',render_text]
        col['value'] = [str,self.task_label_column]
        col['expandable'] = True
        col['resizable'] = True
        col['sorting'] = 'title'
        col['order'] = 2
        desc[col_name] = col
        
        # "startdate" column
        col_name = 'startdate'
        col = {}
        col['title'] = _("Start date")
        render_text = gtk.CellRendererText()
        col['expandable'] = False
        col['renderer'] = ['markup',render_text]
        col['resizable'] = False
        col['value'] = [str,self.task_sdate_column]
        col['order'] = 3
        desc[col_name] = col

        # 'duedate' column
        col_name = 'duedate'
        col = {}
        col['title'] = _("Due")
        render_text = gtk.CellRendererText()
        col['expandable'] = False
        col['renderer'] = ['markup',render_text]
        col['resizable'] = False
        col['value'] = [str,self.task_duedate_column]
        col['order'] = 4
        desc[col_name] = col

        #Returning the treeview
        treeview = TreeView(tree,desc)
        
        #Now that the treeview is done, we can polish
        treeview.set_main_search_column('label')
        treeview.set_expander_column('label')
        #Background colors
#        treeview.set_bg_color(self.task_bg_color,'tags')
         # Global treeview properties
        treeview.set_property("enable-tree-lines", False)
        treeview.set_rules_hint(False)
        
        
        #TODO
#        self.task_modelsort.set_sort_func(\
#            tasktree.COL_DDATE, self.date_sort_func)
#        self.task_modelsort.set_sort_func(\
#            tasktree.COL_DLEFT, self.date_sort_func)
# Connect signals from models
#        self.task_modelsort.connect("row-has-child-toggled",\
#                                    self.on_task_child_toggled)
# Set sorting order
#        self.task_modelsort.set_sort_column_id(\
#            tasktree.COL_DLEFT, gtk.SORT_ASCENDING)
        return treeview
        
        
        return treeview
