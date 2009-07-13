# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personnal organizer for the GNOME desktop
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


from GTG.tools.listes import *


class Requester :
    """A view on a GTG datastore.

    `Requester` is a stateless object that simply provides a nice API for user
    interfaces to use for datastore operations.

    Multiple `Requester`s can exist on the same datastore, so they should
    never have state of their own.
    """
    
    def __init__(self,datastore) :
        self.ds = datastore
        
    def connect(self,signal,func) :
        self.ds.connect(signal,func)
        
    ############## Tasks ##########################
    ###############################################


    #Return True if the task exists
    def has_task(self,tid) :
        return self.ds.has_task(tid)
            
    #Get the task with the given pid
    #If the task doesn't exist, we create it and force the pid
    def get_task(self,tid) :
        task = self.ds.get_task(tid)
        return task
        
    #Pid is the project in which the new task will be created
    #MODIFICATION class (the data will be modified)
    def new_task(self,pid=None,tags=None,newtask=True) :
        task = self.ds.new_task(pid=pid,newtask=newtask)
        if tags :
            for t in tags :
                task.add_tag(t.get_name())
        return task
        
        
    #MODIFICATION class (the data will be modified)
    def delete_task(self,tid) :
        self.ds.delete_task(tid)
        
    #Return a list of active tasks tid
    #
    # tags = []. All tasks will have at least one of those tags.
    # If None, all tasks are eligible
    #
    # Status = [] : a list of status to choose from
    # available status are : Active - Done - Dismiss - Deleted
    # If none, all tasks are eligible
    #
    # notag_only : if True, only tasks without tags are selected
    #
    # started_only : if True, only tasks with an already passed started date are selected
    # (task with no startdate are considered as started)
    #
    # is_root : if True, only tasks that have no parent in the current selection
    # are eligible. If False, all tasks are eligible
    def get_tasks_list(self,tags=None, status=["Active"],notag_only=False,\
                                started_only=True,is_root=False) :
        l_tasks = []
        for tid in self.ds.all_tasks() :
            task = self.get_task(tid)
            if task and not task.is_loaded() :
                task = None
            #This is status filtering
            if task and not task.get_status() in status :
                task = None
            #This is tag filtering
            #If we still have a task and we need to filter tags
            #(if tags is None, this test is skipped)
            if task and tags :
                if not task.has_tags(tags) :
                    task = None
                #Checking here the is_root because it has sense only with tags
                elif is_root and task.has_parents(tag=tags) :
                    task = None
            #If tags = [], we still check the is_root
            elif task and is_root :
                if task.has_parents() :
                    #We accept children of a note
                    for p in task.get_parents() :
                        pp = self.get_task(p)
                        if pp.get_status() != "Note" :
                            task = None
            #Now checking if it has no tag
            if task and notag_only :
                if not task.has_tags(notag_only=notag_only) :
                    task = None
            #This is started filtering
            if task and started_only :
                if not task.is_started() :
                    task = None
                    
            #If we still have a task, we return it
            if task :
                l_tasks.append(tid)
        return l_tasks
        
    #Workable means that the task have no pending subtasks and can be done directly
    #It also means that all tags are to be "workview" tags (which is the default for tags)
    #Except if the tag is explicitely selected
    def get_active_tasks_list(self,tags=None,notag_only=False,\
                            started_only=True,is_root=False,workable=False) :
        l_tasks = []
        if workable :
            nonwork_tag = self.ds.get_tagstore().get_all_tags(\
                                                    attname="nonworkview",\
                                                    attvalue="True")
            #nonwork_tag = []
            #We build the list of tags we will skip
            for nwtag in nonwork_tag :
                #If the tag is explicitely selected, it doesn't go in the
                #nonwork_tag
                if tags and nwtag in tags :
                    nonwork_tag.remove(nwtag)
            #We build the task list
            temp_tasks = self.get_active_tasks_list(tags=tags, notag_only=notag_only,\
                                started_only=True,is_root=False,workable=False)
            #Now we verify that the tasks are workable and doesn't have
            #a nonwork_tag.
            for tid in temp_tasks :
                t = self.get_task(tid)
                if t and t.is_workable() :
                    if len(nonwork_tag) == 0 :
                        l_tasks.append(tid)
                    elif not t.has_tags(nonwork_tag) :
                        l_tasks.append(tid)
            return l_tasks
        else :
            active = ["Active"]
            temp_tasks = self.get_tasks_list(tags=tags,status=active,\
                 notag_only=notag_only,started_only=started_only,is_root=is_root)
            for t in temp_tasks :
                l_tasks.append(t)
            return l_tasks
        
    def get_closed_tasks_list(self,tags=None,notag_only=False,\
                            started_only=False,is_root=False) :
        closed = ["Done","Dismiss","Deleted"]
        return self.get_tasks_list(tags=tags,status=closed,\
                 notag_only=notag_only,started_only=started_only,is_root=is_root)
                 
    def get_notes_list(self,tags=None,notag_only=False) :
        note = ["Note"]
        return self.get_tasks_list(tags=tags,status=note,\
                 notag_only=notag_only,started_only=False,is_root=False)
       
       
                 
    ############### Tags ##########################
    ###############################################    
    
    #MODIFICATION
    def new_tag(self,tagname) :
        return self.ds.get_tagstore().new_tag(tagname)
        
    def get_tag(self,tagname) :
        return self.ds.get_tagstore().get_tag(tagname)
    
    #Not used currently because it returns every tag that was ever used
    def get_all_tags(self):
        return returnlist(self.ds.get_tagstore().get_all_tags())
        
    def get_notag_tag(self) :
        return self.ds.get_tagstore().get_notag_tag()
    def get_alltag_tag(self) :
        return self.ds.get_tagstore().get_alltag_tag()
        
        
    #return only tags that are currently used in a task
    #FIXME it should be only active and visible tasks
    def get_used_tags(self) :
        l = []
        for tid in self.ds.all_tasks():
            t = self.get_task(tid)
            if t :
                for tag in t.get_tags() :
                    if tag not in l: l.append(tag)
        return l
        
