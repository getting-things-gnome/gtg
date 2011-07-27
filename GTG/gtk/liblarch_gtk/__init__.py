# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2011 - Lionel Dricot & Bertrand Rousseau
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

from GTG.gtk.liblarch_gtk.treemodel import TreeModel

class TreeView(gtk.TreeView):
    """ The interface for liblarch_gtk """
    # FIXME Docstring => comment to the whole class

    __string_signal__ = (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (str, ))
    __gsignals__ = {'node-expanded' : __string_signal__, \
                    'node-collapsed': __string_signal__, \
                    }

    # FIXME __emit METHOD

    def __init__(self, tree, description):
        gtk.TreeView.__init__(self)
        self.columns = {}
        self.bg_color_func = None
        self.bg_color_column = None

        self.dnd_internal_target = ''
        self.dnd_external_targets = {}

        # Sort columns
        self.order_of_column = []
        last = 9999
        for col_name in description:
            desc = description[col_name]
            order = desc.get('order', last)
            last += 1
            self.order_of_column.append((order, col_name))

        types = []
        # Build columns according to the order
        for col_num, (order_num, col_name) in enumerate(sorted(self.order_of_column), 1):
            desc = description[col_name]
            types.append(desc['value'])

            expand = desc.get('expandable', False)
            resizable = desc.get('resizable', True)
            visible = desc.get('visible', True)

            if desc.has_key('renderer'):
                renderer = desc["renderer"][1]
                rend_attribute = desc["renderer"][0]
            else:
                raise ValueError("The treeview description should have a renderer")

            col = gtk.TreeViewColumn()
            col.set_visible(visible)

            if desc.has_key('title'):
                col.set_title(desc['title'])

            col.pack_start(renderer, expand=expand)
            col.add_attribute(renderer, rend_attribute, col_num)
            col.set_resizable(resizable)
            col.set_expand(expand)

            # Allow to set background color
            col.set_cell_data_func(renderer, self._celldatafunction)

            self.append_column(col)
            self.columns[col_name] = (col_num, col)

        self.basetree = tree
        self.basetreemodel = TreeModel(tree, types)
        self.treemodel = self.basetreemodel

        self.set_model(self.treemodel)
        # FIXME? Should it be there?

        self.expand_all()
        self.show()

        self.treemodel.connect('row-has-child-toggled', self.on_child_toggled)

    def on_child_toggled(self, treemodel, path, iter, param=None):
        if not self.row_expanded(path):
            self.expand_row(path, False)

    def show(self):
        """ Shows the TreeView and connect basetreemodel to LibLarch """
        gtk.TreeView.show(self)
        self.basetreemodel.connect_model()

    def set_main_search_column(self, col_name):
        """ Set search column for GTK integrate search
        This is just wrapper to use internal representation of columns"""
        col_num, col = self.columns[col_name]
        self.set_search_column(col_num)

    def set_expander_column(self, col_name):
        """ Set expander column (that which expands through free space)
        This is just wrapper to use internal representation of columns"""
        col_num, col = self.columns[col_name]
        self.set_property("expander-column", col)

    def set_sort_column(self, colname):
        # FIXME not implemented yet
        print "FIXME: implement set_sort_column()"

    def set_col_visible(self, col_name,visible):
        """ Set visiblity of column.
        Allow to hide/show certain column """
        col_num, col = self.columns[col_name]
        col.set_visible(visible)

    def set_bg_color(self, color_func, color_column):
        if self.columns.has_key(color_column):
            self.bg_color_column = self.columns[color_column][0]
            self.bg_color_func = color_func
        else:
            raise ValueError("There is no colum %s to use to set color" % color_column)

    def _celldatafunction(self, column, cell, model, iter):
        """ Determine background color for cell
        
        Requirements: self.bg_color_func and self.bg_color_column must be set
        (see self.set_bg_color())
        
        We need:
            * the standard color for a cell (it depends on GTK theme).
            * value of column which the background is generated from
              (e.g. list of tags)

        Then the function for calculating background color is called.
        Result is set as background of cell.
        """
        color = None
        if self.bg_color_func and self.bg_color_column:
            bgcolor = column.get_tree_view().get_style().base[gtk.STATE_NORMAL]
            if iter and model.iter_is_valid(iter):
                value = model.get_value(iter, self.bg_color_column)
                if value:
                    color = self.bg_color_func(value, bgcolor)
        cell.set_property("cell-background", color)

    ######### DRAG-N-DROP functions #####################################

    def set_dnd_name(self, dndname):
        """ Sets Drag'n'Drop name and initialize Drag'n'Drop support"""
        self.dnd_internal_target = dndname
        self.__init_dnd()
        self.connect('drag_drop', self.on_drag_drop)
        self.connect('drag_data_get', self.on_drag_data_get)
        self.connect('drag_data_received', self.on_drag_data_received)

    def set_dnd_external(self, sourcename, func):
        """ Add a new external target and initialize Drag'n'Drop support"""
        i = 1
        while self.dnd_external_targets.has_key(i):
            i += 1
        self.dnd_external_targets[i] = [sourcename, func]
        self.__init_dnd()

    def __init_dnd(self):
        """ Initialize Drag'n'Drop support
        
        Firstly build list of DND targets:
            * name
            * scope - just the same widget / same application
            * id
        
        Do calls: enable_model_drag_dest(), drag_source_set(), drag_dest_set()

        It looks like enable_model-drag_source() is not needed. 
        Worst: it crashes GTG!
        """

        if self.dnd_internal_target == '':
            error = 'Cannot initialize DND without a valid name\n'
            error += 'Use set_dnd_name() first'
            raise Exception(error)
            
        dnd_targets = [(self.dnd_internal_target, gtk.TARGET_SAME_WIDGET, 0)]
        for target in self.dnd_external_targets:
            name = self.dnd_external_targets[target][0]
            dnd_targets.append((name, gtk.TARGET_SAME_APP, target))
    
        self.enable_model_drag_dest(\
            dnd_targets, gtk.gdk.ACTION_DEFAULT)

        self.drag_source_set(\
            gtk.gdk.BUTTON1_MASK, dnd_targets,
            gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_MOVE)

        self.drag_dest_set(\
            gtk.DEST_DEFAULT_ALL, dnd_targets,
            gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_MOVE)
    
    def on_drag_drop(self, treeview, context, selection, info, timestamp):
        """ Stop propagating drag_drop signal to other widgets """
        self.emit_stop_by_name('drag_drop')

    def on_drag_data_get(self, treeview, context, selection, info, timestamp):
        """ Extract data from the source of the DnD operation.
        
        Serialize iterators of selected tasks in format 
        <iter>,<iter>,...,<iter> and set it as parameter of DND """

        treeselection = treeview.get_selection()
        model, paths = treeselection.get_selected_rows()
        iters = [model.get_iter(path) for path in paths]
        iter_str = ','.join([model.get_string_from_iter(iter) for iter in iters])
        selection.set(self.dnd_internal_target, 0, iter_str)

    def on_drag_data_received(self, treeview, context, x, y, selection, info,\
                              timestamp):
        """ Handle a drop situation.

        First of all, we need to get id of node which should accept
        all draged nodes as their new children. If there is no node,
        drop to root node.

        Deserialize iterators of dragged nodes (see self.on_drag_data_get())
        Info parameter determines which target was used:
            * info == 0 => internal DND within this TreeView
            * info > 0 => external DND
        
        In case of internal DND we just use Tree.move_node().
        In case of external DND we call function associated with that DND
        set by self.set_dnd_external()
        
        In the end forbid the next propagation of this signal.
        """
        #TODO: it should be configurable for each TreeView if you want:
        # 0 : no drag-n-drop at all
        # 1 : drag-n-drop move the node
        # 2 : drag-n-drop copy the node 

        model = treeview.get_model()
        drop_info = treeview.get_dest_row_at_pos(x, y)
        if drop_info:
            path, position = drop_info
            iter = model.get_iter(path)
            # Must add the task to the parent of the task situated
            # before/after 
            if position == gtk.TREE_VIEW_DROP_BEFORE or\
               position == gtk.TREE_VIEW_DROP_AFTER:
                # Get sibling parent
                destination_iter = model.iter_parent(iter)
            else:
                # Must add task as a child of the dropped-on iter
                # Get parent
                destination_iter = iter

            if destination_iter:
                destination_tid = model.get_value(destination_iter, 0)
            else:
                #it means we have drag-n-dropped above the first task
                # we should consider the destination as a root then.
                destination_tid = None
        else:
            # Must add the task to the root
            # Parent = root => iter=None
            destination_tid = None

        tree = self.basetree.get_basetree()

        # Get dragged iter as a TaskTreeModel iter
        # If there is no selected task (empty selection.data), 
        # explictly skip handling it (set to empty list)
        if selection.data == '':
            iters = []
        else:
            iters = selection.data.split(',')

        for iter in iters:
            if info == 0:
                try:
                    dragged_iter = model.get_iter_from_string(iter)
                except ValueError:
                    #I hate to silently fail but we have no choice.
                    #It means that the iter is not good.
                    #Thanks shitty gtk API for not allowing us to test the string
                    dragged_iter = None

                if dragged_iter and model.iter_is_valid(dragged_iter):
                    dragged_tid = model.get_value(dragged_iter, 0)
                    tree.move_node(dragged_tid, new_parent_id=destination_tid)

            elif info in self.dnd_external_targets and destination_tid:
                f = self.dnd_external_targets[info][1]

                src_model = context.get_source_widget().get_model()
                i = src_model.get_iter_from_string(iter)
                source = src_model.get_value(i,0)

                f(source, destination_tid)

        self.emit_stop_by_name('drag_data_received')

    def get_selected_nodes(self):
        """ Return list of node ids from liblarch for selected nodes """

        # FIXME this code is copy'n'paste from old code
        ''' Return the selected nodes ID'''
        # Get the selection in the gtk.TreeView
        selection = self.get_selection()
        # Get the selection iter
        if selection.count_selected_rows() <= 0:
            ids = []
        else:
            model, paths = selection.get_selected_rows()
            iters = [model.get_iter(path) for path in paths]
            ts  = self.get_model()
            #0 is the column of the tid
            ids = [ts.get_value(iter, 0) for iter in iters]

        return ids

    def set_multiple_selection(self,bol):
        # FIXME implementation, copy'n'paste
        if bol:
            self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        #    self.connect('button_press_event', self.on_button_press)
        #    self.connect('button_release_event', self.on_button_release)
        else:
            self.get_selection().set_mode(gtk.SELECTION_SINGLE)
            #FIXME : we have to disconnect the two signals !

