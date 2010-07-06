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
        
        #We build the model
        self.treemodel = TreeModel(tree)
        
        
        for col_name in description:
            desc = description[col_name]
            col_nbr = self.treemodel.add_col(desc['value'])
            col = gtk.TreeViewColumn()
            self.columns[col_name] = [col_nbr,col]
            renderer = desc["renderer"][1]
            rend_attribute = desc["renderer"][0]
            #TODO : handle those variables
            expand = True
            resizable = True
            visible = True
            #title is not mandatory
            if desc.has_key('title'):
                col.set_title(desc['title'])
            col.pack_start(renderer, expand=expand)
            col.add_attribute(renderer, rend_attribute, col_nbr)
            col.set_resizable(resizable)
            self.append_column(col)
        
        
        #We apply a treemodelsort on top of it
        self.modelsort = gtk.TreeModelSort(self.treemodel)
        self.set_model(self.modelsort)
        
        
        
        
#        #TODO
#        self.task_modelsort.set_sort_func(\
#            tasktree.COL_DDATE, self.date_sort_func)
#        self.task_modelsort.set_sort_func(\
#            tasktree.COL_DLEFT, self.date_sort_func)
#        self.task_modelsort.connect("row-has-child-toggled",\
#                                    self.on_task_child_toggled)
#        self.task_modelsort.set_sort_column_id(\
#            tasktree.COL_DLEFT, gtk.SORT_ASCENDING)
