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

from GTG.taskbrowser.tasktree         import TaskTreeModel

class FilterTreeModel(TaskTreeModel):

    def __init__(self,requester):
        TaskTreeModel.__init__(self,requester)
#        self.tree = tasktree
#        self.tree.connect('row-changed',self.row_changed)
#        self.tree.connect('row-deleted',self.row_deleted)
#        self.tree.connect('row-has-child-toggled',self.row_has_child_toggled)
#        self.tree.connect('row-inserted',self.row_inserted)
#        self.tree.connect('rows-reordered',self.rows_reordered)
#        
#    def get_model(self):
#        return self.tree
#    
#    #### Signals #############
#    def row_changed(self,model,node_path, node_iter):
#        print "row %s changed" %str(node_path)
#        gtk.GenericTreeModel.row_changed(self,node_path, node_iter)
#        
#    def row_deleted(self,model,node_iter):
#        print "row %s deleted" %str(node_iter)
#        gtk.GenericTreeModel.row_deleted(self, node_iter)
#        
#    ##############################
#    def on_get_flags(self):
#        return self.tree.on_get_flags()
#        
#    def on_get_n_columns(self):
#        return self.tree.on_get_n_columns()
#        
#    def on_get_column_type(self, index):
#        return self.tree.on_get_column_type(index)
#        
#    def on_get_iter(self, path):
#        return self.tree.on_get_iter(path)
#        
#    def on_get_path(self, rowref):
#        return self.tree.on_get_path(rowref)
#        
#    def on_get_value(self, rowref, column):
#        return self.tree.on_get_value(rowref,column)
#        
#    def on_iter_next(self, rowref):
#        return self.tree.on_iter_next(rowref)
#        
#    def on_iter_children(self, parent):
#        return self.tree.on_iter_children(parent)
#        
#    def on_iter_has_child(self, rowref):
#        return self.tree.on_iter_has_child(rowref)
#        
#    def on_iter_n_children(self, rowref):
#        return self.tree.on_iter_n_children(rowref)
#        
#    def on_iter_nth_child(self, parent, n):
#        return self.tree.on_iter_nth_child(parent,n)
#        
#    def on_iter_parent(self, child):
#        return self.tree.on_iter_parent(child)
#        
#    def refilter(self):
#        print "refiltering"
