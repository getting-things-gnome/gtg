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
        self.dnd_internal_target = ''
        self.bg_color_func = None
        self.bg_color_column = None

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

    def set_dnd_name(self, dndname):
        """ Sets Drag'n'Drop name and initialize Drag'n'Drop support"""
        self.dnd_internal_target = dndname
        # FIXME add support of DND
        #self.__init_dnd()
        #self.connect('drag_drop', self.on_drag_drop)
        #self.connect('drag_data_get', self.on_drag_data_get)
        #self.connect('drag_data_received', self.on_drag_data_received)

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

