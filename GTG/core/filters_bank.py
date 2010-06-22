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
# 

"""
filters_bank stores all of GTG's filters in centralized place
"""

from datetime import datetime

from GTG.core.task import Task
from GTG.tools.dates  import date_today, no_date, Date


class Filter:
    def __init__(self,func,req):
        self.func = func
        self.dic = {}
        self.req = req

    def set_parameters(self,dic):
        self.dic = dic

    def get_function(self):
        '''Returns the filtering function'''
        return self.func
    
    def is_displayed(self,tid):
        task = self.req.get_task(tid)
        value = True
        if not task:
            value = False
        elif self.dic:
            value = self.func(task,parameters=self.dic)
        else:
            value = self.func(task)
        if 'negate' in self.dic and self.dic['negate']:
            value = not value
        return value
        
    def get_parameters(self,param):
        if self.dic.has_key(param):
            return self.dic[param]
        else:
            return None

    #return True is the filter is a flat list only
    def is_flat(self):
        if self.dic.has_key('flat'):
            return self.dic['flat']
        else:
            return False
            
class SimpleTagFilter:
    def __init__(self,tagname,req):
        self.req = req
        self.tname = tagname
        self.dic = {}
        
    def set_parameters(self,dic):
        self.dic = dic
        
    def get_parameters(self,param):
        if self.dic.has_key(param):
            return self.dic[param]
        else:
            return None
        
    def set_parameters(self,dic):
        self.dic = dic
    
    def is_displayed(self,tid):
        task = self.req.get_task(tid)
        value = True
        if not task:
            value = False
        else:
            tags = [self.tname]
            tt = self.req.get_tag(self.tname)
            if tt:
                tags += tt.get_children()
            value = task.has_tags(tags)
        if 'negate' in self.dic and self.dic['negate']:
            value = not value
        return value
            
    def is_flat(self):
        return False
    
class FiltersBank:
    """
    Stores filter objects in a centralized place.
    """

    def __init__(self,req,tree=None):
        """
        Create several stock filters:

        workview - Tasks that are active, workable, and started
        active - Tasks of status Active
        closed - Tasks of status closed or dismissed
        notag - Tasks with no tags
        """
        self.tree = tree
        self.req = req
        self.available_filters = {}
        self.custom_filters = {}
        #Workview
        filt_obj = Filter(self.workview,self.req)
        self.available_filters['workview'] = filt_obj
        #Active
        filt_obj = Filter(self.active,self.req)
        self.available_filters['active'] = filt_obj
        #closed
        filt_obj = Filter(self.closed,self.req)
        param = {}
        param['flat'] = True
        filt_obj.set_parameters(param)
        self.available_filters['closed'] = filt_obj
        #notag
        filt_obj = Filter(self.notag,self.req)
        param = {}
        param['ignore_when_counting'] = True
        filt_obj.set_parameters(param)
        self.available_filters['notag'] = filt_obj
        #workable
        filt_obj = Filter(self.is_workable,self.req)
        self.available_filters['workable'] = filt_obj
        #workable
        filt_obj = Filter(self.is_started,self.req)
        self.available_filters['started'] = filt_obj
        #workdue
        filt_obj = Filter(self.workdue,self.req)
        self.available_filters['workdue'] = filt_obj
        #workstarted
        filt_obj = Filter(self.workstarted,self.req)
        self.available_filters['workstarted'] = filt_obj
        #worktostart
        filt_obj = Filter(self.worktostart,self.req)
        self.available_filters['worktostart'] = filt_obj
        #worklate
        filt_obj = Filter(self.worklate,self.req)
        self.available_filters['worklate'] = filt_obj
        #backend filter
        filt_obj = Filter(self.backend_filter, self.req)
        self.available_filters['backend_filter'] = filt_obj
        #no_disabled_tag
        filt_obj = Filter(self.no_disabled_tag,self.req)
        param = {}
        param['ignore_when_counting'] = True
        filt_obj.set_parameters(param)
        self.available_filters['no_disabled_tag'] = filt_obj

    ######### hardcoded filters #############
    def notag(self,task,parameters=None):
        """ Filter of tasks without tags """
        return task.has_tags(notag_only=True)
        
    def is_leaf(self,task,parameters=None):
        """ Filter of tasks which have no children """
        return not task.has_child()
    
    def is_workable(self,task,parameters=None):
        """ Filter of tasks that can be worked """
        workable = True
        for c in task.get_subtasks():
            if c and c.get_status() == Task.STA_ACTIVE:
                workable = False
        return workable
        
    def is_started(self,task,parameters=None):
        '''Filter for tasks that are already started'''
        start_date = task.get_start_date()
        if start_date :
            #Seems like pylint falsely assumes that subtraction always results
            #in an object of the same type. The subtraction of dates 
            #results in a datetime.timedelta object 
            #that does have a 'days' member.
            difference = date_today() - start_date
            if difference.days == 0:
                # Don't count today's tasks started until morning
                return datetime.now().hour > 4
            else:
                return difference.days > 0 #pylint: disable-msg=E1101
        else:
            return True
            
    def workview(self,task,parameters=None):
        wv = self.active(task) and\
             self.is_started(task) and\
             self.is_workable(task)
        return wv
        
    def workdue(self,task):
        ''' Filter for tasks due within the next day '''
        wv = self.workview(task) and \
             task.get_due_date() != no_date and \
             task.get_days_left() < 2
        return wv

    def worklate(self,task):
        ''' Filter for tasks due within the next day '''
        wv = self.workview(task) and \
             task.get_due_date() != no_date and \
             task.get_days_late() > 0
        return wv

    def workstarted(self,task):
        ''' Filter for workable tasks with a start date specified '''
        wv = self.workview(task) and \
             task.start_date
        return wv
        
    def worktostart(self,task):
        ''' Filter for workable tasks without a start date specified '''
        wv = self.workview(task) and \
             not task.start_date
        return wv
        
    def active(self,task,parameters=None):
        """ Filter of tasks which are active """
        #FIXME: we should also handle unactive tags
        return task.get_status() == Task.STA_ACTIVE
        
    def closed(self,task,parameters=None):
        """ Filter of tasks which are closed """
        ret = task.get_status() in [Task.STA_DISMISSED, Task.STA_DONE]
        return ret

    def backend_filter(self, task, tags_to_match_set):
        '''
        Filter that checks if two tags sets intersect. It is used to check if a
        task should be stored inside a backend
        @param task: a task object
        @oaram tags_to_match_set: a *set* of tag names
        '''
        all_tasks_tag = self.req.get_alltag_tag().get_name()
        if all_tasks_tag in tags_to_match_set:
            return True
        task_tags = set(task.get_tags_name())
        return task_tags.intersection(tags_to_match_set)
        
    def no_disabled_tag(self,task,parameters=None):
        """Filter of task that don't have any disabled/nonworkview tag"""
        toreturn = True
        for t in task.get_tags():
            if t.get_attribute("nonworkview") == "True":
                toreturn = False
        return toreturn
        
    ##########################################
        
    def get_filter(self,filter_name):
        """ Get the filter object for a given name """
        if self.available_filters.has_key(filter_name):
            return self.available_filters[filter_name]
        elif self.custom_filters.has_key(filter_name):
            return self.custom_filters[filter_name]
        else:
            return None
    
    def list_filters(self):
        """ List, by name, all available filters """
        liste = self.available_filters.keys()
        liste += self.custom_filters.keys()
        return liste
    
    def add_filter(self,filter_name,filter_func):
        """
        Adds a filter to the filter bank 
        Return True if the filter was added
        Return False if the filter_name was already in the bank
        """
        if filter_name not in self.list_filters():
            negate = False
            if filter_name.startswith('!'):
                negate = True
                filter_name = filter_name[1:]
            if filter_name.startswith('@'):
                filter_obj = SimpleTagFilter(filter_name,self.req)
                param = {}
                param['ignore_when_counting'] = True
                filter_obj.set_parameters(param)
            else:
                filter_obj = Filter(filter_func,self.req)
            self.custom_filters[filter_name] = filter_obj
            return True
        else:
            return False
        
    def remove_filter(self,filter_name):
        """
        Remove a filter from the bank.
        Only custom filters that were added here can be removed
        Return False if the filter was not removed
        """
        if not self.available_filters.has_key(filter_name):
            if self.custom_filters.has_key(filter_name):
                self.unapply_filter(filter_name)
                self.custom_filters.pop(filter_name)
                return True
            else:
                return False
        else:
            return False
