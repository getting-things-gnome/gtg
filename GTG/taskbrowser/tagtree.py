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
import xml.sax.saxutils as saxutils

from GTG import _
from GTG.taskbrowser.CellRendererTags import CellRendererTags
from GTG.taskbrowser.tasktree import COL_OBJ as TASKTREE_COL_OBJ
    
COL_ID    = 0
COL_NAME  = 1
COL_LABEL = 2
COL_OBJ   = 3
COL_COLOR = 4
COL_COUNT = 5
COL_SEP   = 6


class TagTreeModel(gtk.GenericTreeModel):

    column_types = (str,\
                    str,\
                    str,\
                    gobject.TYPE_PYOBJECT,\
                    str,\
                    str,\
                    bool)

    def __init__(self, requester):
        gtk.GenericTreeModel.__init__(self)
        self.req  = requester
        self.tree = self.req.get_tag_tree()
        self.workview = False
        
        self.req.connect('tag-added',self.add_tag)
        self.req.connect('tag-modified',self.update_tag)

        self.displayed = {}
        for n in self.tree.get_all_nodes():
            path = self.tree.get_path_for_node(n)
            self.displayed[n.get_id()] = path

### MODEL METHODS ############################################################
    def update_tags_for_task(self, tid):
        task = self.req.get_task(tid)
        if task:
            for t in task.get_tags():
                path = self.tree.get_path_for_node(t)
                iter = self.get_iter(path)
                self.row_changed(path, iter)

    def set_workview(self, val):
        self.workview = val

### TREEMODEL INTERFACE ######################################################
#
    def on_get_flags(self):
        return gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
        return len(self.column_types)

    def on_get_column_type(self, n):
        return self.column_types[n]

    def on_get_iter(self, path):
#        print "on_get_iter: %s" % str(path)
        return self.tree.get_node_for_path(path)

    def on_get_path(self, node):
#        print "on_get_path: %s" % str(node)
        return self.tree.get_path_for_node(node)

    def on_get_value(self, node, column):
        tag = node
        if   column == COL_ID:
            return saxutils.escape(tag.get_name())
        if   column == COL_NAME:
            return saxutils.escape(tag.get_name())[1:]
        if   column == COL_LABEL:
            if tag.get_attribute("label"):
                return tag.get_attribute("label")
            else:
                if tag.get_attribute("nonworkview"):
                    nwv = eval(tag.get_attribute("nonworkview"))
                else:
                    nwv = False
                if nwv:
                    return "<span color='#AAAAAA'>%s</span>"\
                         % saxutils.escape(tag.get_name())[1:]
                else:
                    return saxutils.escape(tag.get_name())[1:]
        if   column == COL_OBJ:
            return tag
        elif column == COL_COLOR:
            return tag.get_attribute("color")
        elif column == COL_COUNT:
            sp_id = tag.get_attribute("special")
            if not sp_id:
                #This call is critical because called thousand of times
                count = tag.get_tasks_nbr(workview=self.workview)
                return  count
            else:
                ft = self.req.get_custom_tasks_tree()
                if sp_id == "all":
                    ft.apply_filter("active")
                elif sp_id == "notag":
                    ft.apply_filter("notag")
                else:
                    return 0
                return ft.get_nodes_count()
        elif column == COL_SEP:
            sp_id = tag.get_attribute("special")
            if not sp_id:
                return False
            else:
                if sp_id == "sep":
                    return True

    def on_iter_next(self, node):
#        print "on_iter_next: %s" % str(node)
        if node:
            tid = node.get_id()
            parent_id = node.get_parent()
            parent_node = self.tree.get_node(parent_id)
            if not parent_node:
                parent_node = self.tree.get_root()
            try:
                idx = parent_node.get_child_index(tid) + 1
                nextnode = parent_node.get_nth_child(idx)
            except ValueError:
                nextnode = None
        else:
            nextnode = root
        return nextnode

    def on_iter_children(self, node):
#        print "on_iter_children: %s" % str(node)
        if node:
            if node.has_child():
                return node.get_nth_child(0)
            else:
                return None
        else:
            node = self.root.get_nth_child(0)
            return node

    def on_iter_has_child(self, node):
#        print "on_iter_has_child: %s : %s" % (str(node), node.has_child() )
        return node.has_child()

    def on_iter_n_children(self, node):
#        print "on_iter_n_children: %s" % str(node)
        if not node:
            node = self.tree.get_root()
        return node.get_n_children()

    def on_iter_nth_child(self, node, n):
#        print "on_iter_nth_child: %s" % str(node)
        if not node:
            node = self.tree.get_root()
        nth_child = node.get_nth_child(n)
        return nth_child

    def on_iter_parent(self, node):
#        print "on_iter_parent: %s" % str(node)
        if node.has_parent():
            parent_id = node.get_parent()
            parent_node = self.tree.get_node(parent_id)
            return parent_node
        else:
            return None

    def add_tag(self, sender, tname):
#        print "add tag %s" % (tname)
#        self.tree.add_node(tag)
        tag = self.tree.get_node(tname)
        tag_path  = self.tree.get_path_for_node(tag)
        tag_iter  = self.get_iter(tag_path)
        #print "path is %s " %tag_path
        if tag_path != None:
#            print "### tag %s added to path %s" %(tname,tag_path)
            if not self.displayed.get(tname):
                self.row_inserted(tag_path, tag_iter)
                self.displayed[tname] = tag_path
            if tag.has_child():
                self.row_has_child_toggled(tag_path, tag_iter)

    def update_tag(self, sender, tname):
#        print "update tag %s" % (tname)
        if self.displayed.get(tname):
            self.row_deleted(self.displayed[tname])
            self.displayed.pop(tname)
            tag = self.tree.get_node(tname)
            tag_path  = self.tree.get_path_for_node(tag)
            tag_iter  = self.get_iter(tag_path)
            self.row_inserted(tag_path, tag_iter)
            self.displayed[tname] = tag_path
            if tag.has_child():
                self.row_has_child_toggled(tag_path, tag_iter)

    def move_tag(self, parent, child):
        #print "Moving %s below %s" % (child, parent)
        # Get child
        child_tag  = self.get_value(child, COL_OBJ)
        child_path = self.get_path(child)
        # Get old parent
        old_par = self.iter_parent(child)
        if old_par:
            old_par_tag  = self.get_value(old_par, COL_OBJ)
            old_par_n_children = self.iter_n_children(old_par)
        else:
            old_par_tag = None
        # Get new parent
        if parent:
            new_par_tag  = self.get_value(parent, COL_OBJ)
            new_par_n_children = self.iter_n_children(parent)
        else:
            new_par_tag = self.tree.root

        # prevent illegal moves
        c = new_par_tag
        while c is not self.tree.root:
            if c is child_tag:
                return
            c = c.get_parent()

        if new_par_tag is not self.tree.root:
            if new_par_tag.get_name()[0]!='@':
                return
        if child_tag.get_name()[0]!='@':
            return

        child_tag.reparent(new_par_tag)

        # Warn tree about deleted row
        self.row_deleted(child_path)
        # Warn tree about inserted row
        new_child_path=self.tree.get_path_for_node(child_tag)
        new_child_iter = self.get_iter(new_child_path)
        self.row_inserted(new_child_path, new_child_iter)
        
    def rename_tag(self,oldname,newname):
        newname = newname.replace(" ", "_")
        tag = self.req.get_tag(oldname)
        # delete old row
        old_path=self.tree.get_path_for_node(tag)
        #self.row_deleted(old_path)
        # perform rename
        self.req.rename_tag(oldname,newname)
        # insert new row
        tag = self.req.get_tag(newname)
        new_path=self.tree.get_path_for_node(tag)
        new_iter = self.get_iter(new_path)
        #self.row_inserted(new_path, new_iter)

class TagTreeView(gtk.TreeView):
    """TreeView for display of a list of task. Handles DnD primitives too."""
    DND_ID_TAG = 0
    DND_ID_TASK = 1
    DND_TARGETS = [
        ('gtg/tag-iter-str', gtk.TARGET_SAME_WIDGET, DND_ID_TAG),
        ('gtg/task-iter-str', gtk.TARGET_SAME_APP, DND_ID_TASK)
    ]

    def __init__(self):
        self.tv = gtk.TreeView.__init__(self)
        self.show_expander = False
        self.show()
        self._init_tree_view()

        # Drag and drop
        self.enable_model_drag_source(\
            gtk.gdk.BUTTON1_MASK,
            self.DND_TARGETS,
            gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_MOVE)
        self.enable_model_drag_dest(\
            self.DND_TARGETS,
            gtk.gdk.ACTION_DEFAULT)

        self.drag_source_set(\
            gtk.gdk.BUTTON1_MASK,
            self.DND_TARGETS,
            gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_MOVE)

        self.drag_dest_set(\
            gtk.DEST_DEFAULT_ALL,
            self.DND_TARGETS,
           gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_MOVE)
            

        self.connect('drag_drop', self.on_drag_drop)
        self.connect('drag_data_get', self.on_drag_data_get)
        self.connect('drag_data_received', self.on_drag_data_received)

    def __has_child(self, model, path, iter):
        if model.iter_has_child(iter):
            self.show_expander = True
            return True

    def __show_expander_col(self, treemodel, path, iter):
        self.show_expander = False
        treemodel.foreach(self.__has_child)
        if self.show_expander:
            self.set_show_expanders(True)
        else:
            self.set_show_expanders(False)

    def set_model(self, model):
        model.connect("row-has-child-toggled", self.__show_expander_col)
        gtk.TreeView.set_model(self, model)

    def refresh(self):
        model = self.get_model()
        if model:
            model.foreach(self._refresh_func)

    def _refresh_func(self, model, path, iter, user_data=None):
        model.row_changed(path, iter)

    def _tag_separator_filter(self, model, itera, user_data=None):
        return self.get_model().get_value(itera, COL_SEP)

    def _init_tree_view(self):
         # Tag column
        tag_col      = gtk.TreeViewColumn()
        render_text  = gtk.CellRendererText()
        render_count = gtk.CellRendererText()
        render_tags  = CellRendererTags()
        tag_col.set_title(_("Tags"))
        tag_col.set_clickable(False)
        tag_col.pack_start(render_tags, expand=False)
        tag_col.set_attributes(render_tags, tag=COL_OBJ)
        tag_col.pack_start(render_text, expand=True)
        tag_col.set_attributes(render_text, markup=COL_LABEL)
        tag_col.pack_end(render_count, expand=False)
        tag_col.set_attributes(render_count, markup=COL_COUNT)
        render_count.set_property("foreground", "#888a85")
        render_count.set_property('xalign', 1.0)
        render_tags.set_property('ypad', 3)
        render_text.set_property('ypad', 3)
        # Disable edit feature for 0.2.1
        #render_text.set_property('editable', True) 
        render_text.connect("edited", self.rename_tag)
        render_count.set_property('xpad', 3)
        render_count.set_property('ypad', 3)
        tag_col.set_sort_column_id(-1)
        tag_col.set_expand(True)
        self.append_column(tag_col)
        self.set_show_expanders(self.show_expander)

        # Global treeview properties
        self.set_row_separator_func(self._tag_separator_filter)
        self.set_headers_visible(False)
        
    def rename_tag(self,renderer,path,newname):
        #This is a bit ugly ! We have to get the TreeModel from
        #the treemodelfilter that we get from the treemodelsort
        model = self.get_model()
        itera = model.get_iter(path)
        oldname = saxutils.unescape(model.get_value(itera,COL_ID))
        basemodel = model.get_model().get_model()
        basemodel.rename_tag(oldname,newname)

    ### DRAG AND DROP ########################################################
    def on_drag_drop(self, treeview, context, selection, info, timestamp):
        self.emit_stop_by_name('drag_drop')

    def on_drag_data_get(self, treeview, context, selection, info, timestamp):
        """Extract data from the source of the DnD operation. Here the id of
        the parent task and the id of the selected task is passed to the
        destination"""
        treeselection = treeview.get_selection()
        model, iter = treeselection.get_selected()
        iter_str = model.get_string_from_iter(iter)
        selection.set('gtg/tag-iter-str', 0, iter_str)

    def on_drag_data_received(self, treeview, context, x, y, selection, info,\
                              timestamp):                     
        model          = treeview.get_model()
        model_filter   = model.get_model()
        tagtree_model = model_filter.get_model()

        drop_info = treeview.get_dest_row_at_pos(x, y)

        if drop_info:
            path, position = drop_info
            iter = model.get_iter(path)
            if position == gtk.TREE_VIEW_DROP_BEFORE or\
               position == gtk.TREE_VIEW_DROP_AFTER:
                # Must add the tag to the parent of the tag situated\
                # before/after
                # Get sibling parent
                par_iter = model.iter_parent(iter)
            else:
                # Must add tag as a child of the dropped-on iter
                # Get parent
                par_iter = iter
        else:
            # Must add the tag to the root
            # Parent = root => iter=None
            par_iter = None

        # Get parent iter as a TagTreeModel iter
        if par_iter:
            par_iter_filter   =\
                model.convert_iter_to_child_iter(None, par_iter)
            par_iter_tagtree =\
                model_filter.convert_iter_to_child_iter(par_iter_filter)
        else:
            par_iter_tagtree = None
            
            
        if info == self.DND_ID_TAG:
            # Get dragged iter as a TagTreeModel iter
            drag_iter = model.get_iter_from_string(selection.data)
            drag_iter_filter   =\
                model.convert_iter_to_child_iter(None, drag_iter)
            drag_iter_tagtree =\
                model_filter.convert_iter_to_child_iter(drag_iter_filter)
            tagtree_model.move_tag(par_iter_tagtree, drag_iter_tagtree)
        elif info == self.DND_ID_TASK:
            if drop_info: #can't drop task onto root
                tag = model.get_value(iter, COL_OBJ)
            
                src_model = context.get_source_widget().get_model()
                src_str_iters = selection.data.split(',')
                src_iters = [src_model.get_iter_from_string(i) for i in src_str_iters]
                tasks = [src_model.get_value(i, TASKTREE_COL_OBJ) for i in src_iters]
            
                if tag.get_name()[0]=='@':  #can't drop onto special pseudo-tags
                    for task in tasks:
                        task.add_tag(tag.get_name())
                        task.sync()
                elif tag.get_name() == 'gtg-tags-none':
                    for task in tasks:
                        for t in task.get_tags_name():
                            task.remove_tag(t)
                        task.sync()

        self.emit_stop_by_name('drag_data_received')
