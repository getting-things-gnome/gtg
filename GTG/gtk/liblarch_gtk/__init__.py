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

from GTG.gtk.liblarch_gtk.treemodel import TreeModel

class TreeView(gtk.TreeView):

    def __init__(self, tree, description):
        gtk.TreeView.__init__(self)
        self.columns = {}
        self.bg_color_func = None
        self.bg_color_column = None
        
        #We build the model
        self.treemodel = TreeModel(tree)
        
        
        for col_name in description:
            desc = description[col_name]
            col_nbr = self.treemodel.add_col(desc['value'])
            col = gtk.TreeViewColumn()
            self.columns[col_name] = [col_nbr,col]
            renderer = desc["renderer"][1]
            rend_attribute = desc["renderer"][0]
            #Those are default value that can be changed later
            if desc.has_key['expandable']:
                expand = desc['expandable']
            else:
                expand = True
            if desc.has_key['resizable']:
                resizable = desc['resizable']
            else:
                resizable = True
            if desc.has_key['visible']:
                visible = desc['visible']
            else:
                visible = True
            col.set_visible(visible)
            #title is not mandatory
            if desc.has_key('title'):
                col.set_title(desc['title'])
            col.pack_start(renderer, expand=expand)
            col.add_attribute(renderer, rend_attribute, col_nbr)
            #By default, resizable
            col.set_resizable(resizable)
            col.set_cell_data_func(renderer, self._celldatafunction)
            self.append_column(col)
        
        
        #We apply a treemodelsort on top of it
        self.modelsort = gtk.TreeModelSort(self.treemodel)
        self.set_model(self.modelsort)
        self.show()
        
        
    def set_col_resizable(self,col_name,resizable):
        self.columns[col_name][1].set_resizable(resizable)
    
    def set_col_visible(self,col_name,visible):
        self.columns[col_name][1].set_visible(visible)
        
    def set_bg_color(self,color_func,color_column):
        if self.columns.has_key(color_column):
            self.bg_color_column = self.columns[color_column][0]
            self.bg_color_func = color_func
        else:
            raise ValueError("There is no colum %s to use to set color"%color_column)


    def _celldatafunction(self, column, cell, model, iter):
        col = None
        if self.bg_color_func and self.bg_color_column:
            bgcolor = column.get_tree_view().get_style().base[gtk.STATE_NORMAL]
            if iter and model.iter_is_valid(iter):
                value = model.get_value(iter, self.bg_color_column)
                if value:
                    col = self.bg_color_func(value, bgcolor)
        cell.set_property("cell-background", col)
        
#        #TODO
#        self.task_modelsort.set_sort_func(\
#            tasktree.COL_DDATE, self.date_sort_func)
#        self.task_modelsort.set_sort_func(\
#            tasktree.COL_DLEFT, self.date_sort_func)
#        self.task_modelsort.connect("row-has-child-toggled",\
#                                    self.on_task_child_toggled)
#        self.task_modelsort.set_sort_column_id(\
#            tasktree.COL_DLEFT, gtk.SORT_ASCENDING)
