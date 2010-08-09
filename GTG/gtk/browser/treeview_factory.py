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
import locale

from GTG     import _
from GTG.core.task import Task
from GTG.gtk.browser.CellRendererTags import CellRendererTags
from GTG.gtk.liblarch_gtk import TreeView
from GTG.gtk import colors
from GTG.tools.dates             import no_date,\
                                        FuzzyDate, \
                                        get_canonical_date

class TreeviewFactory():

    def __init__(self,requester,config):
        self.req = requester
        self.config = config
        
        #Initial unactive color
        #This is a crude hack. As we don't have a reference to the 
        #treeview to retrieve the style, we save that color when we 
        #build the treeview.
        self.unactive_color = "#888a85"
        
        
    #############################
    #Functions for tasks columns
    ################################
    def _count_active_subtasks_rec(self, task):
        count = 0
        if task.has_child():
            for tid in task.get_children():
                task = self.req.get_task(tid)
                if task and task.get_status() == Task.STA_ACTIVE:
                    count = count + 1 + self._count_active_subtasks_rec(task)
        return count
    
    def task_bg_color(self,tags,bg):
        if self.config['browser'].get('bg_color_enable',False):
            return colors.background_color(tags,bg)
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
        title = saxutils.escape(node.get_title())
        #FIXME
#        color = self.treeview.style.text[gtk.STATE_INSENSITIVE].to_string()
        color = "red"
        if node.get_status() == Task.STA_ACTIVE:
            count = self._count_active_subtasks_rec(node)
            if count != 0:
                title += " (%s)" % count
            
            if self.config['browser'].get("contents_preview_enable",False):
            	excerpt = saxutils.escape(node.get_excerpt(lines=1, \
            		strip_tags=True, strip_subtasks=True))
            	title += " <span size='small' color='%s'>%s</span>" \
            		%(self.unactive_color, excerpt) 
        elif node.get_status() == Task.STA_DISMISSED:
            title = "<span color='%s'>%s</span>"%(self.unactive_color, title)
        return title
        
    #task start date
    def task_sdate_column(self,node):
        return node.get_start_date().to_readable_string()
        
    def task_duedate_column(self,node):
        return node.get_due_date().to_readable_string()
        
    def task_cdate_column(self,node):
        return node.get_closed_date().to_readable_string()
        
    def start_date_sorting(self,task1,task2,order):
        sort = self.__date_comp(task1,task2,'start',order)
        return sort
        
    def due_date_sorting(self,task1,task2,order):
        sort = self.__date_comp(task1,task2,'due',order)
        return sort
    
    def closed_date_sorting(self,task1,task2,order):
        sort = self.__date_comp(task1,task2,'closed',order)
        return sort
        
    def title_sorting(self,task1,task2,order):
        return cmp(task1.get_title(),task2.get_title())
        
    def __date_comp(self,task1,task2,para,order):
        '''This is a quite complex method to sort tasks by date,
        handling fuzzy date and complex situation.
        Return -1 if nid1 is before nid2, return 1 otherwise
        '''
        if task1 and task2:
            if para == 'start':
                t1 = task1.get_start_date()
                t2 = task2.get_start_date()
            elif para == 'due':
                t1 = task1.get_due_date()
                t2 = task2.get_due_date()
            elif para == 'closed':
                t1 = task1.get_closed_date()
                t2 = task2.get_closed_date()
            else:
                raise ValueError('invalid date comparison parameter: %s')%para
            sort = cmp(t2,t1)
        else:
            sort = 0
        
        #local function
        def reverse_if_descending(s):
            """Make a cmp() result relative to the top instead of following 
               user-specified sort direction"""
            if order == gtk.SORT_ASCENDING:
                return s
            else:
                return -1*s

        if sort == 0:
            # Put fuzzy dates below real dates
            if isinstance(t1, FuzzyDate) and not isinstance(t2, FuzzyDate):
                sort = reverse_if_descending(1)
            elif isinstance(t2, FuzzyDate) and not isinstance(t1, FuzzyDate):
                sort = reverse_if_descending(-1)
        
        if sort == 0: # Group tasks with the same tag together for visual cleanness 
            t1_tags = task1.get_tags_name()
            t1_tags.sort()
            t2_tags = task2.get_tags_name()
            t2_tags.sort()
            sort = reverse_if_descending(cmp(t1_tags, t2_tags))
            
        if sort == 0:  # Break ties by sorting by title
            t1_title = task1.get_title()
            t2_title = task2.get_title()
            t1_title = locale.strxfrm(t1_title)
            t2_title = locale.strxfrm(t2_title)
            sort = reverse_if_descending(cmp(t1_title, t2_title))
        
        return sort
        
    #############################
    #Functions for tags columns
    #############################
    def tag_list(self,node):
        #FIXME: we should really use the name instead of the object
        tname = node.get_id()
        return [node]
    
    def tag_name(self,node):
        return node.get_attribute('label')
        
    def get_tag_count(self,node):
        toreturn = node.get_active_tasks_count()
        return "<span color='%s'>%s</span>" %(self.unactive_color,toreturn)
        
    def is_tag_separator_filter(self,tag):
        return tag.get_attribute('special') == 'sep'
        
    def tag_sorting(self,t1,t2,order):
        t1_sp = t1.get_attribute("special")
        t2_sp = t2.get_attribute("special")
        t1_name = locale.strxfrm(t1.get_name())
        t2_name = locale.strxfrm(t2.get_name())
        if not t1_sp and not t2_sp:
            return cmp(t1_name, t2_name)
        elif not t1_sp and t2_sp:
            return 1
        elif t1_sp and not t2_sp:
            return -1
        else:
            t1_order = t1.get_attribute("order")
            t2_order = t2.get_attribute("order")
            return cmp(t1_order, t2_order)

    ############################################
    ######## The Factory #######################
    ############################################
    def tags_treeview(self,tree):
        desc = {}
        
        #Tags color
        col_name = 'color'
        col = {}
        render_tags = CellRendererTags()
        render_tags.set_property('ypad', 3)
        col['title'] = _("Tags")
        col['renderer'] = ['tag_list',render_tags]
        col['value'] = [gobject.TYPE_PYOBJECT,self.tag_list]
        col['expandable'] = False
        col['resizable'] = False
        col['order'] = 1
        desc[col_name] = col
        
        #Tag names
        col_name = 'tagname'
        col = {}
        render_text = gtk.CellRendererText()
        render_text.set_property('editable', True) 
        render_text.set_property('ypad', 3)
        #FIXME : renaming tag feature
#        render_text.connect("edited", self.req.rename_tag)
        col['renderer'] = ['markup',render_text]
        col['value'] = [str,self.tag_name]
        col['expandable'] = True
        col['new_column'] = False
        col['order'] = 2
        col['sorting_func'] = self.tag_sorting
        desc[col_name] = col
        
        #Tag count
        col_name = 'tagcount'
        col = {}
        render_text = gtk.CellRendererText()
        render_text.set_property('xpad', 3)
        render_text.set_property('ypad', 3)
        render_text.set_property('xalign', 1.0)
        col['renderer'] = ['markup',render_text]
        col['value'] = [str,self.get_tag_count]
        col['expandable'] = False
        col['new_column'] = False
        col['order'] = 3
        desc[col_name] = col
        
        return self.build_tag_treeview(tree,desc)
    
    def active_tasks_treeview(self,tree):
        #Build the title/label/tags columns
        desc = self.common_desc_for_tasks(tree)
        
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
        col['sorting_func'] = self.start_date_sorting
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
        col['sorting_func'] = self.due_date_sorting
        desc[col_name] = col

        #Returning the treeview
        treeview = self.build_task_treeview(tree,desc)
        treeview.set_sort_column('duedate')
        return treeview
        
    def closed_tasks_treeview(self,tree):
        #Build the title/label/tags columns
        desc = self.common_desc_for_tasks(tree)
        
        # "startdate" column
        col_name = 'closeddate'
        col = {}
        col['title'] = _("Closed date")
        render_text = gtk.CellRendererText()
        col['expandable'] = False
        col['renderer'] = ['markup',render_text]
        col['resizable'] = False
        col['value'] = [str,self.task_cdate_column]
        col['order'] = 3
        col['sorting_func'] = self.closed_date_sorting
        desc[col_name] = col

        #Returning the treeview
        treeview = self.build_task_treeview(tree,desc)
        treeview.set_sort_column('closeddate')
        return treeview
        
    
    #This build the first tag/title columns, common
    #to both active and closed tasks treeview
    def common_desc_for_tasks(self,tree):
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
        col['sorting_func'] = self.title_sorting
        desc[col_name] = col
        
        # "tags" column (no title)
        col_name = 'tags'
        col = {}
        render_tags = CellRendererTags()
        render_tags.set_property('xalign', 0.0)
        col['renderer'] = ['tag_list',render_tags]
        col['value'] = [gobject.TYPE_PYOBJECT,self.task_tags_column]
        col['expandable'] = False
        col['resizable'] = False
        col['order'] = 1
        desc[col_name] = col

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
        return desc
        
    def build_task_treeview(self,tree,desc):
        treeview = TreeView(tree,desc)
        #Now that the treeview is done, we can polish
        treeview.set_main_search_column('label')
        treeview.set_expander_column('label')
        #Background colors
        treeview.set_bg_color(self.task_bg_color,'tags')
         # Global treeview properties
        treeview.set_property("enable-tree-lines", False)
        treeview.set_rules_hint(False)
        #Updating the unactive color (same for everyone)
        self.unactive_color = \
                        treeview.style.text[gtk.STATE_INSENSITIVE].to_string()
        return treeview
        
    def build_tag_treeview(self,tree,desc):
        treeview = TreeView(tree,desc)
        # Global treeview properties
        treeview.set_property("enable-tree-lines", False)
        treeview.set_rules_hint(False)
        treeview.set_row_separator_func(self.is_tag_separator_filter)
        treeview.set_headers_visible(False)
        #Updating the unactive color (same for everyone)
        self.unactive_color = \
                        treeview.style.text[gtk.STATE_INSENSITIVE].to_string()
        treeview.set_sort_column('tagname')
        return treeview
        
