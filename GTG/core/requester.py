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

import gobject

from GTG.core.filteredtree import FilteredTree
from GTG.core.filters_bank import FiltersBank


class Requester(gobject.GObject):
    """A view on a GTG datastore.

    L{Requester} is a stateless object that simply provides a nice API for
    user interfaces to use for datastore operations.

    Multiple L{Requester}s can exist on the same datastore, so they should
    never have state of their own.
    """
    __gsignals__ = {'task-added': (gobject.SIGNAL_RUN_FIRST, \
                                    gobject.TYPE_NONE, (str, )),
                    'task-deleted': (gobject.SIGNAL_RUN_FIRST, \
                                    gobject.TYPE_NONE, (str, )),
                    'task-modified': (gobject.SIGNAL_RUN_FIRST, \
                                    gobject.TYPE_NONE, (str, )),
                    'tag-added': (gobject.SIGNAL_RUN_FIRST, \
                                    gobject.TYPE_NONE, (str, )),
                    'tag-deleted': (gobject.SIGNAL_RUN_FIRST, \
                                    gobject.TYPE_NONE, (str, )),
                    'tag-modified': (gobject.SIGNAL_RUN_FIRST, \
                                    gobject.TYPE_NONE, (str, ))}

    def __init__(self, datastore):
        """Construct a L{Requester}."""
        gobject.GObject.__init__(self)
        self.ds = datastore
        self.basetree = self.ds.get_tasks_tree()
        self.main_tree = FilteredTree(self,self.basetree,maintree=True)
        
        self.filters = FiltersBank(self,tree=self.main_tree)
        self.counter_call = 0

    ############# Signals #########################
    #Used by the tasks to emit the task added/modified signal
    #Should NOT be used by anyone else
    def _task_loaded(self, tid):
        gobject.idle_add(self.emit, "task-added", tid)

    def _task_modified(self, tid):
        self.counter_call += 1
        #print "signal task_modified %s (%s modifications)" %(tid,self.counter_call)
        gobject.idle_add(self.emit, "task-modified", tid)
        
    def _tag_added(self,tagname):
        gobject.idle_add(self.emit, "tag-added", tagname)
        
    ############ Tasks Tree ######################
    # This is the main FilteredTree. You cannot apply filters
    # directly to it, you have to pass them through the requester.
    # This is the tree as it is displayed in the main window
    def get_main_tasks_tree(self):
        return self.main_tree
        
    # This is a FilteredTree that you have to handle yourself.
    # You can apply/unapply filters on it as you wich.
    def get_custom_tasks_tree(self):
        return FilteredTree(self,self.basetree,maintree=False)
        
    def get_main_tasks_list(self):
        return self.main_tree.get_all_keys()
        
    def get_main_n_tasks(self):
        return self.main_tree.get_n_nodes()
    
    def get_all_tasks_list(self):
        return self.basetree.get_all_keys()
        
    # Apply a given filter to the main FilteredTree
    def apply_filter(self,filter_name,parameters=None):
        r = self.main_tree.apply_filter(filter_name,parameters=parameters,imtherequester=True)
        return r
            
    
    # Unapply a filter from the main FilteredTree.
    # Does nothing if the filter was not previously applied.
    def unapply_filter(self,filter_name):
        r = self.main_tree.unapply_filter(filter_name,imtherequester=True)
        return r
    
    def reset_filters(self):
        self.main_tree.reset_filters(imtherequester=True)
        
    def reset_tag_filters(self,refilter=True):
        self.main_tree.reset_tag_filters(refilter=refilter,imtherequester=True)
        
    def is_displayed(self,task):
        return self.main_tree.is_displayed(task)
    
    
    ######### Filters bank #######################
    # Get the filter object for a given name
    def get_filter(self,filter_name):
        return self.filters.get_filter(filter_name)
    
    # List, by name, all available filters
    def list_filters(self):
        return self.filters.list_filters()
    
    # Add a filter to the filter bank
    # Return True if the filter was added
    # Return False if the filter_name was already in the bank
    def add_filter(self,filter_name,filter_func):
        return self.filters.add_filter(filter_name,filter_func)
        
    # Remove a filter from the bank.
    # Only custom filters that were added here can be removed
    # Return False if the filter was not removed
    def remove_filter(self,filter_name):
        return self.filters.remove_filter(filter_name)

    ############## Tasks ##########################
    ###############################################
    def has_task(self, tid):
        """Does the task 'tid' exist?"""
        return self.ds.has_task(tid)

    def get_task(self, tid):
        """Get the task with the given C{tid}.

        If no such task exists, create it and force the tid to be C{tid}.

        @param tid: The task id.
        @return: A task.
        """
        task = self.ds.get_task(tid)
        return task

    def new_task(self, pid=None, tags=None, newtask=True):
        """Create a new task.

        Note: this modifies the datastore.

        @param pid: The project where the new task will be created.
        @param tags: The tags for the new task. If not provided, then the
            task will have no tags.
        @param newtask: C{True} if this is creating a new task that never
            existed, C{False} if importing an existing task from a backend.
        @return: A task.
        """
        task = self.ds.new_task(pid=pid)
        if tags:
            for t in tags:
                task.tag_added(t.get_name())
        return task

    def delete_task(self, tid):
        """Delete the task 'tid'.

        Note: this modifies the datastore.

        @param tid: The id of the task to be deleted.
        """
        #send the signal before actually deleting the task !
        self.emit('task-deleted', tid)
        return self.ds.delete_task(tid)

    ############### Tags ##########################
    ###############################################
    def get_tag_tree(self):
        return self.ds.get_tagstore()

    def new_tag(self, tagname):
        """Create a new tag called 'tagname'.

        Note: this modifies the datastore.

        @param tagname: The name of the new tag.
        @return: The newly-created tag.
        """
        return self.ds.get_tagstore().new_tag(tagname)

    def rename_tag(self, oldname, newname):
        self.ds.get_tagstore().rename_tag(oldname, newname)

    def get_tag(self, tagname):
        return self.ds.get_tagstore().get_tag(tagname)

    def get_all_tags(self):
        """Return a list of every tag that was used.
        We don't return tag that were used only on permanently deleted tasks.

        @return: A list of tags used by a open or closed task.
        """
        l = []
        for t in self.ds.get_tagstore().get_all_tags():
            if t.is_used() and t not in l:
                l.append(t)
        l.sort(cmp=lambda x, y: cmp(x.get_name().lower(),\
            y.get_name().lower()))
        return l

    def get_notag_tag(self):
        return self.ds.get_tagstore().get_notag_tag()

    def get_alltag_tag(self):
        return self.ds.get_tagstore().get_alltag_tag()

    def get_used_tags(self):
        """Return tags currently used by a task.

        @return: A list of tag names used by a task.
        """
        l = []
        for t in self.ds.get_tagstore().get_all_tags():
            if t.is_actively_used() and t not in l:
                l.append(t.get_name())
        l.sort(cmp=lambda x, y: cmp(x.lower(),y.lower()))
        return l
