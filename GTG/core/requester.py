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

class Requester(gobject.GObject):
    """A view on a GTG datastore.

    L{Requester} is a stateless object that simply provides a nice API for
    user interfaces to use for datastore operations.

    Multiple L{Requester}s can exist on the same datastore, so they should
    never have state of their own.
    """
    __gsignals__ = {'task-added': (gobject.SIGNAL_RUN_FIRST, \
                                    gobject.TYPE_NONE, (str,)),
                    'task-deleted': (gobject.SIGNAL_RUN_FIRST, \
                                    gobject.TYPE_NONE, (str,)),
                    'task-modified': (gobject.SIGNAL_RUN_FIRST, \
                                    gobject.TYPE_NONE, (str,)) }

    def __init__(self, datastore):
        """Construct a L{Requester}."""
        self.ds = datastore
        
        #filter
        self.filter = {}
        self.filter["tasks"] = []
        self.filter["tags"] = []
        
        gobject.GObject.__init__(self)

    ############# Signals #########################   
    #Used by the tasks to emit the task added/modified signal
    #Should NOT be used by anyone else
    def _task_loaded(self,tid) :
        gobject.idle_add(self.emit,"task-added",tid)
    def _task_modified(self,tid) :
        gobject.idle_add(self.emit,"task-modified",tid)

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
        """
        task = self.ds.new_task(pid=pid, newtask=newtask)
        if tags:
            for t in tags:
                task.add_tag(t.get_name())
        return task

    def delete_task(self, tid):
        """Delete the task 'tid'.

        Note: this modifies the datastore.

        @param tid: The id of the task to be deleted.
        """
        self.ds.delete_task(tid)
        gobject.idle_add(self.emit,"task-deleted",tid)

    def get_tasks_list(self, tags=None, status=["Active"], notag_only=False,
                       started_only=True, is_root=False):
        """Return a list of tids of tasks.

        By default, returns a list of all the tids of all active tasks.

        @param tags: A list of tags. If provided, restricts the list of
            returned tasks to those that have one or more of these tags.
        @param status: A list of statuses. If provided, restricts the list of
            returned tasks to those that are in one of these states.
        @param notag_only: If True, only include tasks without tags. Defaults
            to C{False}.
        @param started_only: If True, only include tasks that have been
            started. That is, tasks that have an already-passed start date or
            tasks with no startdate. Defaults to C{True}.
        @param is_root: If True, only include tasks that have no parent in the
            current selection. Defaults to False.

        @return: A list of task ids (tids).
        """
        l_tasks = []
        for tid in self.ds.all_tasks():
            task = self.get_task(tid)
            if task and not task.is_loaded():
                task = None
            # This is status filtering.
            if task and not task.get_status() in status:
                task = None
            # This is tag filtering.
            # If we still have a task and we need to filter tags
            # (if tags is None, this test is skipped)
            if task and tags:
                if not task.has_tags(tags):
                    task = None
                # Checking here the is_root because it has sense only with
                # tags.
                elif is_root and task.has_parents(tag=tags):
                    task = None
            #If tags = [], we still check the is_root.
            elif task and is_root:
                if task.has_parents():
                    # We accept children of a note.
                    for p in task.get_parents():
                        pp = self.get_task(p)
                        if pp.get_status() != "Note":
                            task = None
            # Now checking if it has no tag.
            if task and notag_only:
                if not task.has_tags(notag_only=notag_only):
                    task = None
            # This is started filtering.
            if task and started_only:
                if not task.is_started():
                    task = None

            # If we still have a task, we return it.
            if task:
                l_tasks.append(tid)  
        return l_tasks
    
    ############# Filters #########################
    def set_filter(self, filter):
        """Set a filter for the tasks.
        
        @param filter: A dictionary with two keys, 'tags' and 'tasks'.
            The 'tags' key corresponds to a list of tag names and the 'tasks'
            corresponds to a list of tids.
        """
        self.filter = filter
        
    def get_filter(self):
        """Return the current task filter.

        @return: The filter object.
        """
        return self.filter
        
    def add_task_to_filter(self, tid):
        """Adds (appends) a task to the filter (task list).
        
        @param tid: A task id.
        """
        if tid not in self.filter["tasks"]:
            self.filter["tasks"].append(tid)
        
    def remove_task_from_filter(self, tid):
        """Removes a task from the filter (task list).
        
        @param tid: A task id.
        """
        if tid in self.filter["tasks"]:
            self.filter["tasks"].remove(tid)
            
    def add_tag_to_filter(self, tag):
        """Adds (appends) a tag to the filter (tag list).
        
        @param tag: A tag name.
        """
        if tag not in self.filter["tags"]:
            self.filter["tags"].append(tag)
        
    def remove_tag_from_filter(self, tag):
        """Removes a tag from the filter (tag list).
        
        @param tag: A tag name.
        """
        if tag in self.filter["tags"]:
            self.filter["tags"].remove(tag)
    ############# Filters #########################

    def get_active_tasks_list(self, tags=None, notag_only=False,
                              started_only=True, is_root=False,
                              workable=False):
        """Return a list of task ids for all active tasks.

        See L{get_tasks_list} for more information about the parameters.

        @param workable: If C{True}, then only include tasks with no pending
            subtasks and that can be done directly and exclude any tasks that
            have a C{nonworkview} tag which is not explicitly provided in the
            C{tags} parameter. Defaults to C{False}.
        """
        l_tasks = []
        if workable:
            nonwork_tag = self.ds.get_tagstore().get_all_tags(
                attname="nonworkview", attvalue="True")
            # We build the list of tags we will skip.
            #for nwtag in nonwork_tag:
                # If the tag is explicitly selected, it doesn't go in the
                # nonwork_tag.
                #if tags and nwtag in tags:
                #    nonwork_tag.remove(nwtag)
            # We build the task list.
            temp_tasks = self.get_active_tasks_list(
                tags=tags, notag_only=notag_only, started_only=True,
                is_root=False, workable=False)
            
            #remove from temp_tasks the filtered out tasks
            #for tid in temp_tasks:
            #    if tid in self.filter["tasks"]:
            #        temp_tasks.remove(tid)
            #    else:
            #        for filter_tag in self.get_task(tid).get_tags():
            #            if filter_tag.get_attribute("name") in self.filter["tags"]:
            #                print self.get_task(tid).get_title()
            #                temp_tasks.remove(tid)
            #                break
            
            # Now we verify that the tasks are workable and don't have a
            # nonwork_tag.
            for tid in temp_tasks:
                filtered_tag = False
                t = self.get_task(tid)
                if t and t.is_workable() and (tid not in self.filter["tasks"]):
                    for filter_tag in t.get_tags():
                        if filter_tag.get_attribute("name") in self.filter["tags"]:
                            #print t.get_title()
                            temp_tasks.remove(tid)
                            filtered_tag = True
                            
                    if not filtered_tag:
                        if len(nonwork_tag) == 0:
                            #print t.get_title()
                            l_tasks.append(tid)
                        elif not t.has_tags(nonwork_tag):
                            #print t.get_title()
                            l_tasks.append(tid)
            return l_tasks
        else:
            active = ["Active"]
            temp_tasks = self.get_tasks_list(
                tags=tags, status=active, notag_only=notag_only,
                started_only=started_only, is_root=is_root)
            for t in temp_tasks:
                l_tasks.append(t)
            return l_tasks

    def get_closed_tasks_list(self, tags=None, notag_only=False,
                              started_only=False, is_root=False):
        """Return a list of task ids for closed tasks.

        "Closed" means either "done", "dismissed" or "deleted".

        See L{get_tasks_list} for more information about the parameters.
        """
        closed = ["Done", "Dismiss", "Deleted"]
        return self.get_tasks_list(
            tags=tags, status=closed, notag_only=notag_only,
            started_only=started_only, is_root=is_root)

    def get_notes_list(self, tags=None, notag_only=False):
        """Return a list of task ids for notes.

        See `get_tasks_list` for more information about the parameters.
        """
        note = ["Note"]
        return self.get_tasks_list(
            tags=tags, status=note, notag_only=notag_only, started_only=False,
            is_root=False)

    ############### Tags ##########################
    ###############################################

    def get_tag_tree(self):
        return self.ds.get_tagstore().get_tree()

    def new_tag(self, tagname):
        """Create a new tag called 'tagname'.

        Note: this modifies the datastore.

        @param tagname: The name of the new tag.
        @return: The newly-created tag.
        """
        return self.ds.get_tagstore().new_tag(tagname)

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
#        l = []
#        for tid in self.ds.all_tasks():
#            t = self.get_task(tid)
#            if t:
#                for tag in t.get_tags():
#                    if tag not in l:
#                        l.append(tag)
        l.sort(cmp=lambda x, y: cmp(x.get_name().lower(),\
            y.get_name().lower()))
        return l

    def get_notag_tag(self):
        return self.ds.get_tagstore().get_notag_tag()

    def get_alltag_tag(self):
        return self.ds.get_tagstore().get_alltag_tag()

    def get_used_tags(self):
        """Return tags currently used by a task.

        @return: A list of tags used by a task.
        """
        l = []
        for t in self.ds.get_tagstore().get_all_tags():
            if t.is_actively_used() and t not in l:
                l.append(t) 
#        for tid in self.get_tasks_list(started_only=False):
#            t = self.get_task(tid)
#            if t:
#                for tag in t.get_tags():
#                    if tag not in l:
#                        l.append(tag)
        l.sort(cmp=lambda x, y: cmp(x.get_name().lower(),\
            y.get_name().lower()))
        return l
