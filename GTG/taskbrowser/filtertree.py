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
    def on_get_iter(self, path):
        #print "get_iter for path %s" %str(path)
        #We should convert the path to the base.path
        base_path = path
        return TaskTreeModel.on_get_iter(self,base_path)

    def on_get_path(self, node):
        #print "get_path for node %s" %node
        #For that node, we should convert the base_path to path
        base_path = TaskTreeModel.on_get_path(self,node)
        path = base_path
        return path

#    def on_get_value(self, node, column):
#        print "on_get_value for node %s - column %s" %(node,column)
#        return TaskTreeModel.on_get_value(self,node,column)

    def on_iter_next(self, node):
        #print "on_iter_next for node %s" %node
        #We should take the next good node, not the next base node
        next_node = TaskTreeModel.on_iter_next(self,node)
        return next_node

    def on_iter_children(self, parent):
        #print "on_iter_children for parent %s" %parent
        #here, we should return only good childrens
        return TaskTreeModel.on_iter_children(self,parent)

    def on_iter_has_child(self, node):
        #print "on_iter_has_child for node %s" %node
        #we should say "has_good_child"
        return TaskTreeModel.on_iter_has_child(self,node)

    def on_iter_n_children(self, node):
        #print "on_iter_n_children for node %s" %node
        #we should return the number of "good" children
        return TaskTreeModel.on_iter_n_children(self,node)

    def on_iter_nth_child(self, parent, n):
        #print "on_iter_nth_child for parent %s - n %s" %(parent,n)
        #we return the nth good children !
        return TaskTreeModel.on_iter_nth_child(self,parent,n)

    def on_iter_parent(self, child):
        #print "on_iter_parent %s" %child
        #return None if we are at a Virtual root
        return TaskTreeModel.on_iter_parent(self,child)


    #### Filtering methods ##########
        
    def refilter(self):
        print "refiltering"
