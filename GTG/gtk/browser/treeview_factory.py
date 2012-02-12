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

from GTG                              import _
from GTG.core                         import CoreConfig
from GTG.core.task                    import Task
from GTG.gtk.browser.CellRendererTags import CellRendererTags
from liblarch_gtk                     import TreeView
from GTG.gtk                          import colors
from GTG.tools                        import dates


class AutoExpandTreeView(TreeView):
    """TreeView which hide the expander column when not needed"""

    def __init__(self, tree, desc):
        TreeView.__init__(self, tree, desc)
        self.show_expander = False
        self.treemodel.connect("row-has-child-toggled", self.__show_expander_col)
        self.__show_expander_col(self.treemodel, None, None)

    def __has_child(self, model, path, iter):
        if model.iter_has_child(iter):
            self.show_expander = True
            return True

    def __show_expander_col(self, treemodel, path, iter):
        self.show_expander = False
        treemodel.foreach(self.__has_child)
        self.set_show_expanders(self.show_expander)

class TreeviewFactory():

    def __init__(self,requester,config):
        self.req = requester
        self.mainview = self.req.get_tasks_tree()
        self.config = config
        
        #Initial unactive color
        #This is a crude hack. As we don't have a reference to the 
        #treeview to retrieve the style, we save that color when we 
        #build the treeview.
        self.unactive_color = "#888a85"

        # List of keys for connecting/disconnecting Tag tree
        self.tag_cllbcks = []

        # Cache tags treeview for on_rename_tag callback
        self.tags_view = None
        
    #############################
    #Functions for tasks columns
    ################################
        
    def _has_hidden_subtask(self,task):
        #not recursive
        display_count = self.mainview.node_n_children(task.get_id())
        real_count = 0
        if task.has_child():
            for tid in task.get_children():
                sub_task = self.req.get_task(tid)
                if sub_task and sub_task.get_status() == Task.STA_ACTIVE:
                    real_count = real_count + 1
        return display_count < real_count
    
    def task_bg_color(self,tags,bg):
        if self.config.get('bg_color_enable'):
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
        str_format = "%s"
        #we mark in bold tasks which are due now and those marked as Now (fuzzy
        # date)
        due = node.get_due_date()
        if (due.days_left == 0 or due == dates.NOW):
            str_format = "<b>%s</b>"
        if self._has_hidden_subtask(node):
            str_format = "<span color='%s'>%s</span>"\
                                            %(self.unactive_color,str_format)
        title = str_format % saxutils.escape(node.get_title())
        #FIXME
#        color = self.treeview.style.text[gtk.STATE_INSENSITIVE].to_string()
        color = "red"
        if node.get_status() == Task.STA_ACTIVE:
            count = self.mainview.node_n_children(node.get_id(),recursive=True)
            if count != 0:
                title += " (%s)" % count
            
            if self.config.get("contents_preview_enable"):
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
            if isinstance(t1, dates.FuzzyDate) \
               and not isinstance(t2, dates.FuzzyDate):
                sort = reverse_if_descending(1)
            elif isinstance(t2, dates.FuzzyDate) \
                    and not isinstance(t1, dates.FuzzyDate):
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
    def tag_name(self,node):
        label = node.get_attribute("label")
        if label.startswith('@'):
            label = label[1:]

        if node.get_attribute("nonworkview") == "True":
            return "<span color='%s'>%s</span>" %(self.unactive_color, label)
        else:
            return label
        
    def get_tag_count(self,node):
# FIXME: is this good idea?
        if node.get_id() == 'search':
            return ""
        else:
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
            
    def ontag_task_dnd(self,source,target):
        if target.startswith('@'):
            task = self.req.get_task(source)
            task.add_tag(target)
        elif target == 'gtg-tags-none':
            task = self.req.get_task(source)
            for t in task.get_tags_name():
                task.remove_tag(t)

    ############################################
    ######## The Factory #######################
    ############################################
    def tags_completion_treeview(self, tree):
        desc = {}
        desc['tagname'] = {'value': [str, self.tag_name]}

        return TreeView(tree, desc)

    def tags_treeview(self,tree):
        desc = {}

        #Tag id
        col_name = 'tag_id'
        col = {}
        col['renderer'] = ['markup', gtk.CellRendererText()]
        col['value'] = [str, lambda node: node.get_id()]
        col['visible'] = False
        col['order'] = 0
        col['sorting_func'] = self.tag_sorting
        desc[col_name] = col
        
        #Tags color
        col_name = 'color'
        col = {}
        render_tags = CellRendererTags()
        render_tags.set_property('ypad', 3)
        col['title'] = _("Tags")
        col['renderer'] = ['tag',render_tags]
        col['value'] = [gobject.TYPE_PYOBJECT,lambda node: node]
        col['expandable'] = False
        col['resizable'] = False
        col['order'] = 1
        desc[col_name] = col
        
        #Tag names
        col_name = 'tagname'
        col = {}
        render_text = gtk.CellRendererText()
        render_text.set_property('ypad', 3)
        # Allow renaming
        # FIXME Is there any way how to disable renaming for certain tags?
        render_text.set_property('editable', True) 
        render_text.connect("edited", self.on_rename_tag)
        col['renderer'] = ['markup',render_text]
        col['value'] = [str,self.tag_name]
        col['expandable'] = True
        col['new_column'] = False
        col['order'] = 2
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

        self.enable_update_tags()

        return self.build_tag_treeview(tree,desc)

    def on_rename_tag(self, renderer, path, new_name):
        model = self.tags_view.get_model()
        my_iter = model.get_iter(path)
        tag_id = model.get_value(my_iter, 0)
        tag = self.req.get_tag(tag_id)

        if tag.is_search_tag():
            self.req.rename_tag(tag_id, new_name)
        else:
            print "FIXME: renaming tags is not implemented"

    def enable_update_tags(self):
        self.tag_cllbcks = []

        tasks = self.req.get_tasks_tree()
        for event in 'node-added-inview', 'node-modified-inview', 'node-deleted-inview':
            handle = tasks.register_cllbck(event, self._update_tags)
            self.tag_cllbcks.append((event, handle))

    def disable_update_tags(self):
        tasks = self.req.get_tasks_tree()
        for event, handle in self.tag_cllbcks:
            tasks.deregister_cllbck(event, handle)
        self.tag_cllbcks = []

    def _update_tags(self, node_id, path):
        tree = self.req.get_tag_tree().get_basetree()
        tree.refresh_node('gtg-tags-all')
        tree.refresh_node('gtg-tags-none')

        search_parent = self.req.get_tag(CoreConfig.SEARCH_TAG)
        for search_tag in search_parent.get_children():
            tree.refresh_node(search_tag)

        task = self.req.get_task(node_id)
        if task:
            for t in self.req.get_task(node_id).get_tags():
                tree.refresh_node(t.get_name())
    
    def active_tasks_treeview(self,tree):
        #Build the title/label/tags columns
        desc = self.common_desc_for_tasks(tree)
        
        # "startdate" column
        col_name = 'startdate'
        col = {}
        col['title'] = _("Start date")
        col['expandable'] = False
        col['resizable'] = False
        col['value'] = [str,self.task_sdate_column]
        col['order'] = 3
        col['sorting_func'] = self.start_date_sorting
        desc[col_name] = col

        # 'duedate' column
        col_name = 'duedate'
        col = {}
        col['title'] = _("Due")
        col['expandable'] = False
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
        col['expandable'] = False
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
        treeview = AutoExpandTreeView(tree,desc)
        #Now that the treeview is done, we can polish
        treeview.set_main_search_column('label')
        treeview.set_expander_column('label')
        treeview.set_dnd_name('gtg/task-iter-str')
        #Background colors
        treeview.set_bg_color(self.task_bg_color,'tags')
         # Global treeview properties
        treeview.set_property("enable-tree-lines", False)
        treeview.set_rules_hint(False)
        treeview.set_multiple_selection(True)
        #Updating the unactive color (same for everyone)
        self.unactive_color = \
                        treeview.style.text[gtk.STATE_INSENSITIVE].to_string()
        return treeview
        
    def build_tag_treeview(self,tree,desc):
        treeview = AutoExpandTreeView(tree,desc)
        # Global treeview properties
        treeview.set_property("enable-tree-lines", False)
        treeview.set_rules_hint(False)
        treeview.set_row_separator_func(self.is_tag_separator_filter)
        treeview.set_headers_visible(False)
        treeview.set_dnd_name('gtg/tag-iter-str')
        treeview.set_dnd_external('gtg/task-iter-str',self.ontag_task_dnd)
        #Updating the unactive color (same for everyone)
        self.unactive_color = \
                        treeview.style.text[gtk.STATE_INSENSITIVE].to_string()
        treeview.set_sort_column('tag_id')
        self.tags_view = treeview
        return treeview 
