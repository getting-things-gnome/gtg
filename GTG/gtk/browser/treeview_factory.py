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

import locale
from datetime import datetime
import xml.sax.saxutils as saxutils

from gi.repository import GObject, Gtk, Pango

from GTG.core.search import parse_search_query, search_filter
from GTG.core.tag import SEARCH_TAG
from GTG.core.task import Task
from gettext import gettext as _
from GTG.gtk import colors
from GTG.gtk.browser.cell_renderer_tags import CellRendererTags
from GTG.core.dates import Date
from liblarch_gtk import TreeView


class TreeviewFactory():

    def __init__(self, requester, config):
        self.req = requester
        self.mainview = self.req.get_tasks_tree()
        self.config = config

        # Initial unactive color
        # This is a crude hack. As we don't have a reference to the
        # treeview to retrieve the style, we save that color when we
        # build the treeview.
        self.unactive_color = "#888a85"

        # List of keys for connecting/disconnecting Tag tree
        self.tag_cllbcks = []

        # Cache tags treeview for on_rename_tag callback
        self.tags_view = None

    #############################
    # Functions for tasks columns
    ################################
    def _has_hidden_subtask(self, task):
        # not recursive
        display_count = self.mainview.node_n_children(task.get_id())
        real_count = 0
        if task.has_child():
            for tid in task.get_children():
                sub_task = self.req.get_task(tid)
                if sub_task and sub_task.get_status() == Task.STA_ACTIVE:
                    real_count = real_count + 1
        return display_count < real_count

    def get_task_bg_color(self, node, default_color):
        if self.config.get('bg_color_enable'):
            return colors.background_color(node.get_tags(), default_color)
        else:
            return None

    def get_task_tags_column_contents(self, node):
        """Returns an ordered list of tags of a task"""
        tags = node.get_tags()

        search_parent = self.req.get_tag(SEARCH_TAG)
        for search_tag in search_parent.get_children():
            tag = self.req.get_tag(search_tag)
            match = search_filter(
                node,
                parse_search_query(tag.get_attribute('query')),
            )
            if match and search_tag not in tags:
                tags.append(tag)

        tags.sort(key=lambda x: x.get_name())
        return tags

    def get_task_title_column_string(self, node):
        return saxutils.escape(node.get_title())

    def get_task_label_column_string(self, node):
        str_format = "%s"

        # We add the indicator when task is repeating
        INDICATOR = "\u21BB "
        if node.get_recurring():
            str_format = INDICATOR + str_format

        if node.get_status() == Task.STA_ACTIVE:
            # we mark in bold tasks which are due today or as Now
            days_left = node.get_days_left()
            if days_left is not None and days_left <= 0:
                str_format = f"<b>{str_format}</b>"
            if self._has_hidden_subtask(node):
                str_format = f"<span color='{self.unactive_color}'>{str_format}</span>"

        title = str_format % saxutils.escape(node.get_title())
        if node.get_status() == Task.STA_ACTIVE:
            count = self.mainview.node_n_children(node.get_id(), recursive=True)
            if count != 0:
                title += f" ({count})"
        elif node.get_status() == Task.STA_DISMISSED:
            title = f"<span color='{self.unactive_color}'>{title}</span>"

        if self.config.get("contents_preview_enable"):
            excerpt = saxutils.escape(node.get_excerpt(lines=1,
                                                       strip_tags=True,
                                                       strip_subtasks=True))
            title += " <span size='small' color='%s'>%s</span>" \
                % (self.unactive_color, excerpt)
        return title

    def get_task_startdate_column_string(self, node):
        start_date = node.get_start_date()
        if start_date:
            return _(start_date.to_readable_string())
        else:
            # Do not parse with gettext then, or you'll get undefined behavior.
            return ""

    def get_task_duedate_column_string(self, node):
        # For tasks with no due dates, we use the most constraining due date.
        if node.get_due_date() == Date.no_date():
            # This particular call must NOT use the gettext "_" function,
            # as you will get some very weird erratic behavior:
            # strings showing up and changing on the fly when the mouse hovers,
            # whereas no strings should even be shown at all.
            return node.get_due_date_constraint().to_readable_string()
        else:
            # Other tasks show their due date (which *can* be fuzzy)
            return _(node.get_due_date().to_readable_string())

    def get_task_closeddate_column_string(self, node):
        closed_date = node.get_closed_date()
        if closed_date:
            return _(closed_date.to_readable_string())
        else:
            # Do not parse with gettext then, or you'll get undefined behavior.
            return ""

    def sort_by_startdate(self, task1, task2, order):
        t1 = task1.get_start_date()
        t2 = task2.get_start_date()
        return self.__date_comp_continue(task1, task2, order, t1, t2)

    def sort_by_duedate(self, task1, task2, order):
        t1 = task1.get_urgent_date()
        t2 = task2.get_urgent_date()
        if t1 == Date.no_date():
            t1 = task1.get_due_date_constraint()
        if t2 == Date.no_date():
            t2 = task2.get_due_date_constraint()
        return self.__date_comp_continue(task1, task2, order, t1, t2)

    def sort_by_closeddate(self, task1, task2, order):
        t1 = task1.get_closed_date()
        t2 = task2.get_closed_date()

        # Convert both times to datetimes (accurate comparison)
        if isinstance(t1, Date):
            d = t1.date()
            t1 = datetime(year=d.year, month=d.month, day=d.day)
        if isinstance(t2, Date):
            d = t2.date()
            t2 = datetime(year=d.year, month=d.month, day=d.day)
        return self.__date_comp_continue(task1, task2, order, t1, t2)

    def sort_by_title(self, task1, task2, order):
        # Strip "@" and convert everything to lowercase to allow fair comparisons;
        # otherwise, Capitalized Tasks get sorted after their lowercase equivalents,
        # and tasks starting with a tag would get sorted before everything else.
        t1 = task1.get_title().replace("@", "").lower()
        t2 = task2.get_title().replace("@", "").lower()
        return (t1 > t2) - (t1 < t2)

    def __date_comp_continue(self, task1, task2, order, t1, t2):
        sort = (t2 > t1) - (t2 < t1)
        if sort != 0: # Ingore order, since this will be done automatically
            return sort

        # Dates are equal
        # Group tasks with the same tag together for visual cleanness
        t1_tags = task1.get_tags_name()
        t1_tags.sort()
        t2_tags = task2.get_tags_name()
        t2_tags.sort()
        sort = (t1_tags > t2_tags) - (t1_tags < t2_tags)

        if sort == 0: # Even tags are equal
            # Break ties by sorting by title
            sort = locale.strcoll(task1.get_title(), task2.get_title())

        if order != Gtk.SortType.ASCENDING:
            return -sort
        return sort

    #############################
    # Functions for tags columns
    #############################
    def get_tag_name(self, node):
        label = node.get_attribute("label")
        if label.startswith('@'):
            label = label[1:]

        if node.get_attribute("nonworkview") == "True":
            return f"<span color='{self.unactive_color}'>{label}</span>"
        elif node.get_id() == 'search' and not node.get_children():
            return f"<span color='{self.unactive_color}'>{label}</span>"
        else:
            return label

    def get_tag_count(self, node):
        if node.get_id() == 'search':
            return ""
        else:
            toreturn = node.get_active_tasks_count()
            return f"<span color='{self.unactive_color}'>{toreturn}</span>"

    def is_tag_separator_filter(self, tag):
        return tag.get_attribute('special') == 'sep'

    def tag_sorting(self, t1, t2, order):
        t1_sp = t1.get_attribute("special")
        t2_sp = t2.get_attribute("special")
        t1_name = locale.strxfrm(t1.get_name())
        t2_name = locale.strxfrm(t2.get_name())
        if not t1_sp and not t2_sp:
            return (t1_name > t2_name) - (t1_name < t2_name)
        elif not t1_sp and t2_sp:
            return 1
        elif t1_sp and not t2_sp:
            return -1
        else:
            t1_order = t1.get_attribute("order")
            t2_order = t2.get_attribute("order")
            return (t1_order > t2_order) - (t1_order < t2_order)

    def on_tag_task_dnd(self, source, target):
        task = self.req.get_task(source)
        if target.startswith('@'):
            task.add_tag(target)
        elif target == 'gtg-tags-none':
            for t in task.get_tags_name():
                task.remove_tag(t)
        task.modified()

    ############################################
    # The Factory ##############################
    ############################################
    def tags_treeview(self, tree):
        desc = {}

        # Tag id
        col_name = 'tag_id'
        col = {}
        col['renderer'] = ['markup', Gtk.CellRendererText()]
        col['value'] = [str, lambda node: node.get_id()]
        col['visible'] = False
        col['order'] = 0
        col['sorting_func'] = self.tag_sorting
        desc[col_name] = col

        # Tags color
        col_name = 'color'
        col = {}
        render_tags = CellRendererTags(self.config)
        render_tags.set_property('ypad', 5)
        col['title'] = _("Tags")
        col['renderer'] = ['tag', render_tags]
        col['value'] = [GObject.TYPE_PYOBJECT, lambda node: node]
        col['expandable'] = False
        col['resizable'] = False
        col['order'] = 1
        desc[col_name] = col

        # Tag names
        col_name = 'tagname'
        col = {}
        render_text = Gtk.CellRendererText()
        render_text.set_property('ypad', 5)
        col['renderer'] = ['markup', render_text]
        col['value'] = [str, self.get_tag_name]
        col['expandable'] = True
        col['new_column'] = False
        col['order'] = 2
        desc[col_name] = col

        # Tag count
        col_name = 'tagcount'
        col = {}
        render_text = Gtk.CellRendererText()
        render_text.set_property('xpad', 17)
        render_text.set_property('ypad', 5)
        render_text.set_property('xalign', 1)
        col['renderer'] = ['markup', render_text]
        col['value'] = [str, self.get_tag_count]
        col['expandable'] = False
        col['new_column'] = False
        col['order'] = 3
        desc[col_name] = col

        return self.build_tag_treeview(tree, desc)

    def active_tasks_treeview(self, tree):
        # Build the title/label/tags columns
        # Translators: Column name, containing the task titles
        desc = self.common_desc_for_tasks(tree, _("Tasks"))

        # "startdate" column
        col_name = 'startdate'
        col = {}
        # Translators: Column name, containing the start date
        col['title'] = _("Start Date")
        col['expandable'] = False
        col['resizable'] = False
        col['value'] = [str, self.get_task_startdate_column_string]
        col['order'] = 3
        col['sorting_func'] = self.sort_by_startdate
        desc[col_name] = col

        # 'duedate' column
        col_name = 'duedate'
        col = {}
        # Translators: Column name, containing the due date
        col['title'] = _("Due")
        col['expandable'] = False
        col['resizable'] = False
        col['value'] = [str, self.get_task_duedate_column_string]
        col['order'] = 4
        col['sorting_func'] = self.sort_by_duedate
        desc[col_name] = col

        # Returning the treeview
        treeview = self.build_task_treeview(tree, desc)
        treeview.set_sort_column('duedate')
        return treeview

    def closed_tasks_treeview(self, tree):
        # Build the title/label/tags columns
        # Translators: Column name, containing the task titles
        desc = self.common_desc_for_tasks(tree, _("Closed Tasks"))

        # "startdate" column
        col_name = 'closeddate'
        col = {}
        # Translators: Column name, containing the closed date
        col['title'] = _("Closed Date")
        col['expandable'] = False
        col['resizable'] = False
        col['value'] = [str, self.get_task_closeddate_column_string]
        col['order'] = 3
        col['sorting_func'] = self.sort_by_closeddate
        desc[col_name] = col

        # Returning the treeview
        treeview = self.build_task_treeview(tree, desc)
        treeview.set_sort_column('closeddate')
        return treeview

    # This build the first tag/title columns, common
    # to both active and closed tasks treeview
    def common_desc_for_tasks(self, tree, title_label):
        desc = {}

        # invisible 'task_id' column
        col_name = 'task_id'
        col = {}
        col['renderer'] = ['markup', Gtk.CellRendererText()]
        col['value'] = [str, lambda node: node.get_id()]
        col['visible'] = False
        col['order'] = 0
        desc[col_name] = col

        # invisible 'bg_color' column
        col_name = 'bg_color'
        col = {}
        col['value'] = [str, lambda node: None]
        col['visible'] = False
        desc[col_name] = col

        # invisible 'title' column
        col_name = 'title'
        col = {}
        render_text = Gtk.CellRendererText()
        render_text.set_property("ellipsize", Pango.EllipsizeMode.END)
        col['renderer'] = ['markup', render_text]
        col['value'] = [str, self.get_task_title_column_string]
        col['visible'] = False
        col['order'] = 0
        col['sorting_func'] = self.sort_by_title
        desc[col_name] = col

        # "tags" column (no title)
        col_name = 'tags'
        col = {}
        render_tags = CellRendererTags(self.config)
        render_tags.set_property('xalign', 0.0)
        col['renderer'] = ['tag_list', render_tags]
        col['value'] = [GObject.TYPE_PYOBJECT, self.get_task_tags_column_contents]
        col['expandable'] = False
        col['resizable'] = False
        col['order'] = 1
        desc[col_name] = col

        # "label" column
        col_name = 'label'
        col = {}
        col['title'] = title_label
        render_text = Gtk.CellRendererText()
        render_text.set_property("ellipsize", Pango.EllipsizeMode.END)
        col['renderer'] = ['markup', render_text]
        col['value'] = [str, self.get_task_label_column_string]
        col['expandable'] = True
        col['resizable'] = True
        col['sorting'] = 'title'
        col['order'] = 2
        desc[col_name] = col
        return desc

    def build_task_treeview(self, tree, desc):
        treeview = TreeView(tree, desc)
        # Now that the treeview is done, we can polish
        treeview.set_main_search_column('label')
        treeview.set_expander_column('label')
        treeview.set_dnd_name('gtg/task-iter-str')
        # Background colors
        treeview.set_bg_color(self.get_task_bg_color, 'bg_color')
        # Global treeview properties
        treeview.set_property("enable-tree-lines", False)
        treeview.set_rules_hint(False)
        treeview.set_multiple_selection(True)
        # Updating the unactive color (same for everyone)
        color = treeview.get_style_context().get_color(Gtk.StateFlags.INSENSITIVE)
        # Convert color into #RRRGGGBBB
        self.unactive_color = color.to_color().to_string()
        return treeview

    def build_tag_treeview(self, tree, desc):
        treeview = TreeView(tree, desc)
        # Global treeview properties
        treeview.set_property("enable-tree-lines", False)
        treeview.set_rules_hint(False)
        treeview.set_row_separator_func(self.is_tag_separator_filter)
        treeview.set_headers_visible(False)
        treeview.set_dnd_name('gtg/tag-iter-str')
        treeview.set_dnd_external('gtg/task-iter-str', self.on_tag_task_dnd)
        # Updating the unactive color (same for everyone)
        color = treeview.get_style_context().get_color(Gtk.StateFlags.INSENSITIVE)
        # Convert color into #RRRGGGBBB
        self.unactive_color = color.to_color().to_string()

        treeview.set_sort_column('tag_id')
        self.tags_view = treeview
        return treeview
