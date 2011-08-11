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


# Useful for debugging purpose.
# Disabling that will disable the TreeModelSort on top of our TreeModel
ENABLE_SORTING = True
USE_TREEMODELFILTER = False
#FIXME Drag and Drop does not work with ENABLE_SORTING = True :-(
#Problem: on-child-row_expanded is really slow with ENABLE_SORTING = True :-(
#Answer: this is not our fault but a known bug in gtk.treemodelsort.
# see test delete_child_randomly

class TreeView(gtk.TreeView):
    """ Widget which display LibLarch FilteredTree.

    This widget extends gtk.TreeView by several features:
      * Drag'n'Drop support
      * Sorting support
      * separator rows
      * background color of a row
      * selection of multiple rows
    """

    __string_signal__ = (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (str, ))
    __gsignals__ = {'node-expanded' : __string_signal__, \
                    'node-collapsed': __string_signal__, \
                    }

    def __init__(self, tree, description):
        """ Build the widget

        @param  tree - LibLarch FilteredTree
        @param  description - definition of columns.

        Parameters of description dictionary for a column:
          * value => (type of values, function for generating value from a node)
          * renderer => (renderer_attribute, renderer object)

          Optional:
          * order => specify order of column otherwise use natural oreder
          * expandable => is the column expandable?
          * resizable => is the column resizable?
          * visible => is the column visible?
          * title => title of column
          * new_colum => do not create a separate column, just continue with the previous one
                (this can be used to create columns without borders)
          * sorting => allow default sorting on this column
          * sorting_func => use special function for sorting on this func

        Example of columns descriptions:
        description = { 'title': {
                'value': [str, self.task_title_column],
                'renderer': ['markup', gtk.CellRendererText()],
                'order': 0
            }}
        """
        gtk.TreeView.__init__(self)
        self.columns = {}
        self.bg_color_func = None
        self.bg_color_column = None
        self.separator_func = None

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
        sorting_func = []
        # Build the first coulumn if user starts with new_colum=False
        col = gtk.TreeViewColumn()

        # Build columns according to the order
        for col_num, (order_num, col_name) in enumerate(sorted(self.order_of_column), 1):
            desc = description[col_name]
            types.append(desc['value'])

            expand = desc.get('expandable', False)
            resizable = desc.get('resizable', True)
            visible = desc.get('visible', True)

            if 'renderer' in desc:
                rend_attribute, renderer = desc['renderer']
            else:
                rend_attribute = 'markup'
                renderer = gtk.CellRendererText()

            # If new_colum=False, do not create new column, use the previous one
            # It will create columns without borders
            if desc.get('new_column',True):
                col = gtk.TreeViewColumn()
                newcol = True
            else:
                newcol = False
            col.set_visible(visible)

            if 'title' in desc:
                col.set_title(desc['title'])

            col.pack_start(renderer, expand=expand)
            col.add_attribute(renderer, rend_attribute, col_num)
            col.set_resizable(resizable)
            col.set_expand(expand)

            # Allow to set background color
            col.set_cell_data_func(renderer, self._celldatafunction)
            
            if newcol:
                self.append_column(col)
            self.columns[col_name] = (col_num, col)

            if ENABLE_SORTING:
                if 'sorting' in desc:
                    # Just allow sorting and use default comparing
                    sort_num, sort_col = self.columns[desc['sorting']]
                    col.set_sort_column_id(sort_num)

                if 'sorting_func' in desc:
                    # Use special funcion for comparing, e.g. dates
                    sorting_func.append((col_num, col, desc['sorting_func']))

        self.basetree = tree
        # Build the model around LibLarch tree
        self.basetreemodel = TreeModel(tree, types)
        #Applying an intermediate treemodelfilter, for debugging purpose
        if USE_TREEMODELFILTER:
            treemodelfilter = self.basetreemodel.filter_new()
        else:
            treemodelfilter = self.basetreemodel
        # Apply TreeModelSort to be able to sort
        if ENABLE_SORTING:
#            self.treemodel = gtk.TreeModelSort(treemodelfilter)
            self.treemodel = self.basetreemodel
            for col_num, col, sort_func in sorting_func:
                self.treemodel.set_sort_func(col_num,
                    self._sort_func, sort_func)
                col.set_sort_column_id(col_num)
        else:
            self.treemodel = treemodelfilter

        self.set_model(self.treemodel)

        self.expand_all()
        self.show()

        self.connect('row-expanded', self.__emit, 'expanded')
        self.connect('row-collapsed', self.__emit, 'collapsed')
        #FIXME: this one is crazingly slow, but it is a gtk bug in TreeModelSort
        self.treemodel.connect('row-has-child-toggled', self.on_child_toggled)

    def __emit(self, sender, iter, path, data):
        """ Emitt expanded/collapsed signal """
        node_id = self.treemodel.get_value(iter, 0)
        if data == 'expanded':
            self.emit('node-expanded', node_id)
        elif data == 'collapsed':
            self.emit('node-collapsed', node_id)

    def on_child_toggled(self, treemodel, path, iter, param=None):
        """ Expand row """
        if not self.row_expanded(path):
            self.expand_row(path, True)

    def collapse_node(self, node_id):
        """ Hide children of a node
        
        This method is needed for "rember collapsed nodes" feature of GTG.
        Transform node_id into paths and those paths collapse. By default all
        children are expanded (see self.expand_all())"""

        paths = self.basetree.get_paths_for_node(node_id)
        for path in paths:
            try:
                self.collapse_row(path)
            except TypeError, e:
                # FIXME why this is so?
                # FIXME what to do, if task is not in FilteredTree yet?
                print "FIXME: problem with TreeView.collapse_node():", e

                # FIXME this is just a workaround, discuss it with ploum
                gobject.idle_add(self.collapse_node, node_id)

    def show(self):
        """ Shows the TreeView and connect basetreemodel to LibLarch """
        gtk.TreeView.show(self)
        self.basetreemodel.connect_model()

    def get_columns(self):
        """ Return the list of columns name """
        return self.columns.keys()

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

    def set_sort_column(self, col_name):
        """ Select column to sort by it by default """
        if ENABLE_SORTING:
            col_num, col = self.columns[col_name]
            self.treemodel.set_sort_column_id(col_num, gtk.SORT_ASCENDING)

    def set_col_visible(self, col_name,visible):
        """ Set visiblity of column.
        Allow to hide/show certain column """
        col_num, col = self.columns[col_name]
        col.set_visible(visible)

    def set_col_resizable(self, col_name, resizable):
        """ Allow/forbid column to be resizable """
        col_num, col = self.columns[col_name]
        col.set_resizable(resizable)

    def set_bg_color(self, color_func, color_column):
        """ Set which column and function for generating background color """
        if self.columns.has_key(color_column):
            self.bg_color_column = self.columns[color_column][0]
            self.bg_color_func = color_func
        else:
            raise ValueError("There is no colum %s to use to set color" % color_column)

    def _sort_func(self, model, iter1, iter2, func=None):
        """ Sort two iterators by function which gets node objects.

        This is a simple wrapper which prepares node objects and then
        call comparing function. In other case return default value -1
        """
        if model.iter_is_valid(iter1) and model.iter_is_valid(iter2):
            node_id_a = model.get_value(iter1, 0)
            node_id_b = model.get_value(iter2, 0)
            if node_id_a and node_id_b and func:
                id, order = self.treemodel.get_sort_column_id()
                node_a = self.basetree.get_node(node_id_a)
                node_b = self.basetree.get_node(node_id_b)
                sort = func(node_a, node_b, order)
            else:
                sort = -1
        else:
            print "some of the iter given for sorting are invalid. WTF?"
            sort = -1
        return sort

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
        """ Sets Drag'n'Drop name and initialize Drag'n'Drop support
        
        If ENABLE_SORTING, drag_drop signal must be handled by this widget."""
        self.dnd_internal_target = dndname
        self.__init_dnd()
        self.connect('drag_data_get', self.on_drag_data_get)
        self.connect('drag_data_received', self.on_drag_data_received)

#        if ENABLE_SORTING:
#            self.connect('drag_drop', self.on_drag_drop)
#            self.connect('button_press_event', self.on_button_press)
#            self.connect('button_release_event', self.on_button_release)
            

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

        Enable DND by calling enable_model_drag_dest(), 
        enable_model-drag_source()

        It didnt use support from gtk.Widget(drag_source_set(),
        drag_dest_set()). To know difference, look in PyGTK FAQ:
        http://faq.pygtk.org/index.py?file=faq13.033.htp&req=show
        """
        self.defer_select = False
        
        if self.dnd_internal_target == '':
            error = 'Cannot initialize DND without a valid name\n'
            error += 'Use set_dnd_name() first'
            raise Exception(error)
            
        dnd_targets = [(self.dnd_internal_target, gtk.TARGET_SAME_WIDGET, 0)]
        for target in self.dnd_external_targets:
            name = self.dnd_external_targets[target][0]
            dnd_targets.append((name, gtk.TARGET_SAME_APP, target))
    
        self.enable_model_drag_source( gtk.gdk.BUTTON1_MASK,
            dnd_targets, gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_MOVE)

        self.enable_model_drag_dest(\
            dnd_targets, gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_MOVE)
            
#        self.drag_source_set(\
#            gtk.gdk.BUTTON1_MASK,
#            [('gtg/task-iter-str', gtk.TARGET_SAME_WIDGET, 0)],
#            gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_MOVE)

#        self.drag_dest_set(\
#            gtk.DEST_DEFAULT_ALL,
#            [('gtg/task-iter-str', gtk.TARGET_SAME_WIDGET, 0)],
#            gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_MOVE)
            
#    def on_button_press(self, widget, event):
#        # Here we intercept mouse clicks on selected items so that we can
#        # drag multiple items without the click selecting only one
#        target = self.get_path_at_pos(int(event.x), int(event.y))
#        if (target 
#           and event.type == gtk.gdk.BUTTON_PRESS
#           and not (event.state & (gtk.gdk.CONTROL_MASK|gtk.gdk.SHIFT_MASK))
#           and self.get_selection().path_is_selected(target[0])):
#               # disable selection
#               self.get_selection().set_select_function(lambda *ignore: False)
#               self.defer_select = target[0]
#            
#    def on_button_release(self, widget, event):
#        # re-enable selection
#        self.get_selection().set_select_function(lambda *ignore: True)
#        
#        target = self.get_path_at_pos(int(event.x), int(event.y))    
#        if (self.defer_select and target 
#           and self.defer_select == target[0]
#           and not (event.x==0 and event.y==0)): # certain drag and drop 
#                                                 # operations still have path
#               # if user didn't drag, simulate the click previously ignored
#               self.set_cursor(target[0], target[1], False)
#            
#        self.defer_select=False

#    def on_drag_drop(self, treeview, context, selection, info, timestamp):
#        """ When using TreeModelSort, drag_drop signal must be handled to
#        prevent GTK warning in console.

#        Do nothing, just prevent default callback.
#        """
#        self.emit_stop_by_name('drag_drop')
    
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

        dragged_iters = []
        for iter in iters:
            if info == 0:
                try:
                    dragged_iters.append(model.get_iter_from_string(iter))
                except ValueError:
                    #I hate to silently fail but we have no choice.
                    #It means that the iter is not good.
                    #Thanks shitty gtk API for not allowing us to test the string
                    print "cannot get an iter from %s" %iter
                    dragged_iter = None

            elif info in self.dnd_external_targets and destination_tid:
                f = self.dnd_external_targets[info][1]

                src_model = context.get_source_widget().get_model()
                dragged_iters.append(src_model.get_iter_from_string(iter))
                
                
        for dragged_iter in dragged_iters:
            if info == 0:
                if dragged_iter and model.iter_is_valid(dragged_iter):
                    dragged_tid = model.get_value(dragged_iter, 0)
                    try:
                        tree.move_node(dragged_tid, new_parent_id=destination_tid)
                    except Exception, e:
                        print 'Problem with dragging: %s' % e
            elif info in self.dnd_external_targets and destination_tid:    
                source = src_model.get_value(dragged_iter,0)
                # Handle external Drag'n'Drop
                f(source, destination_tid)


    ######### Separators support ##############################################
    def _separator_func(self, model, itera, user_data=None):
        """ Call user function to determine if this node is separator """
        if itera and model.iter_is_valid(itera):
            node_id = model.get_value(itera, 0)
            node = self.basetree.get_node(node_id)
            if self.separator_func:
                return self.separator_func(node)
            else:
                return False
        else:
            return False

    def set_row_separator_func(self, func):
        """ Enable support for row separators.

        @param func - function which determines if a node is separator,
            None will disable support for row separators.
        """
        self.separator_func = func
        gtk.TreeView.set_row_separator_func(self,self._separator_func)

    ######### Multiple selection ####################################################
    def get_selected_nodes(self):
        """ Return list of node_id from liblarch for selected nodes """
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

    def set_multiple_selection(self, multiple_selection):
        """ Allow/forbid multiple selection in TreeView """
        # TODO support for dragging multiple rows at the same time
        # See LP #817433

        if multiple_selection:
            selection_type = gtk.SELECTION_MULTIPLE
        else:
            selection_type = gtk.SELECTION_SINGLE

        self.get_selection().set_mode(selection_type)
