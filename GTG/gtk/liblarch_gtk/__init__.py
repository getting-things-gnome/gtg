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

    def __init__(self, tree, description):
        gtk.TreeView.__init__(self)

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

            #col.set_cell_data_func(renderer, self._celldatafunction)
            self.append_column(col)

        self.basetree = tree
        self.basetreemodel = TreeModel(tree, types)
        self.treemodel = self.basetreemodel

        self.set_model(self.treemodel)
        # FIXME? Should it be there?

        #FIXME?
        self.expand_all()
        self.show()

#FIXME this code is taken from older liblarch 
        self.treemodel.connect('row-has-child-toggled',self.child_toggled_cllb)

    def child_toggled_cllb(self,treemodel,path,iter,param=None):
        if not self.row_expanded(path):
            self.expand_row(path,False)
#FIXME end


    def show(self):
        """ Shows the TreeView and at the same time connect basetreemodel to
        liblarch tree
        
        FIXME: fetch the stable state of tree at this moment """
        gtk.TreeView.show(self)
        self.basetreemodel.connect_model()

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

