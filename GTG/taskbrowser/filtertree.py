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

#from gtk import GenericTreeModel
from GTG.taskbrowser.tasktree         import TaskTreeModel

class FilterTreeModel(TaskTreeModel):

    def __init__(self,req):
        TaskTreeModel.__init__(self,req)
#        self.tree = tasktree
#        self.tree.connect('row-changed',self.fil_row_changed)
#        self.tree.connect('row-deleted',self.fil_row_deleted)
#        self.tree.connect('row-has-child-toggled',self.row_has_child_toggled)
#        self.tree.connect('row-inserted',self.row_inserted)
#        self.tree.connect('rows-reordered',self.rows_reordered)
        
#    def get_model(self):
#        return self.tree.get_model()
#    
#    #### Signals #############
#    def fil_row_changed(self,model,node_path, node_iter):
#        #print "row %s changed" %str(node_path)
#        self.row_changed(node_path, node_iter)
#        
#    def fil_row_deleted(self,model,node_iter):
#        #print "row %s deleted" %str(node_iter)
#        self.row_deleted(node_iter)
#        
#    def update_task(self,tid):
#        self.tree.update_task(tid)
#        
#    def add_task(self, tid):
#        print "dummy add_task %s" %tid
#        
#    def remove_task(self, tid):
#        return self.tree.remove_task(tid)
#        
#    def move_task(self, parent, child):
#        print "dummy Moving %s below %s (tasktree)" % (child, parent)
#        
#    ##############################
#    # GenericTreeModel methods
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
#        print "get_iter for path %s" %str(path)
#        return self.tree.on_get_iter(path)
#        
    def on_get_path(self, rowref):
        print "get_path for rowref %s" %rowref
        return TaskTreeModel.on_get_path(self,rowref)
#        
    def on_get_value(self, rowref, column):
#        print "on_get_value for rowref %s - column %s" %(rowref,column)
        return TaskTreeModel.on_get_value(self,rowref,column)
#        
#    def on_iter_next(self, rowref):
#        print "on_iter_next for rowref %s" %rowref
#        return self.tree.on_iter_next(rowref)
#        
#    def on_iter_children(self, parent):
#        print "on_iter_children for parent %s" %parent
#        return self.tree.on_iter_children(parent)
#        
#    def on_iter_has_child(self, rowref):
#        print "on_iter_has_child for rowref %s" %rowref
#        return self.tree.on_iter_has_child(rowref)
#        
#    def on_iter_n_children(self, rowref):
#        print "on_iter_n_children for rowref %s" %rowref
#        return self.tree.on_iter_n_children(rowref)
#        
#    def on_iter_nth_child(self, parent, n):
#        print "on_iter_nth_child for parent %s - n %s" %(parent,n)
#        return self.tree.on_iter_nth_child(parent,n)
#        
#    def on_iter_parent(self, child):
#        print "on_iter_parent %s" %child
#        return self.tree.on_iter_parent(child)
#        
#        
#    #### Filtering methods ##########
#        
#    def refilter(self):
#        print "refiltering"
