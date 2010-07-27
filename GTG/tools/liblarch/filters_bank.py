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
# TODO: GTG-specific filters should be outside liblarch
from datetime import datetime

from GTG.core.task import Task
from GTG.tools.dates import date_today, no_date, Date


class Filter:
    """Base class for filters."""
    def __init__(self, func, params={}):
        """Initialize the filter.
        
        *func* is a callback accepts two arguments:
        
        """
        self.function = func
        # call dict() to make sure the params are in the right format
        self.parameters = dict(params)

    def set_parameters(self, dic):
        """Set the parameters to be passed to the filter callback.
        
        *dic* should be a dictionary.
        
        """
        self.parameters.update(dic)

    def is_displayed(self, node):
        """Filter a node.
        
        A liblarch TreeNode (or an instance of a subclass) is with the ID
        *node_id* is retrieved from the Filter's associated tree.
        
        """
        if len(self.parameters) > 0:
            displayed = self.function(node, parameters=self.parameters)
        else:
            displayed = self.function(node)
        if self.parameters.get('negate', False):
            displayed = not displayed
        return displayed

    # alias for is_displayed
    filter = is_displayed

    def get_parameter(self, name):
        """Get a filter parameter named *name*.
        
        If the parameter does not exist, None is returned.
        
        """
        return self.parameters.get(name, None)

    def is_flat(self):
        """Return True if the filter is a flat list only."""
        return self.parameters.get('flat', False)


class TagFilter(Filter):
    def __init__(self, tag):
        self._tag = tag
        Filter.__init__(self, self._filter)

    def _filter(self, node):
        pass


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
        return True
#        task = self.tree.get_node(tid)
#        value = True
#        if not task:
#            value = False
#        else:
#            tags = [self.tname]
#            tt = self.req.get_tag(self.tname)
#            if tt:
#                tags += tt.get_children()
#            value = task.has_tags(tags)
#        if 'negate' in self.dic and self.dic['negate']:
#            value = not value
#        return value
            
    def is_flat(self):
        return False


class FiltersBank:
    """
    Stores filter objects in a centralized place.
    """
    def __init__(self):
        """
        Create several stock filters:

        workview - Tasks that are active, workable, and started
        active - Tasks of status Active
        closed - Tasks of status closed or dismissed
        notag - Tasks with no tags
        """
        self.available_filters = {}
        self.custom_filters = {}
        f = {
          'workview': Filter(self.workview),
          'active': Filter(self.active),
          'closed': Filter(self.closed, {'flat': True}),
          'notag': Filter(self.notag, {'transparent': True}),
          'workable': Filter(self.is_workable),
          'started': Filter(self.is_started),
          'workdue': Filter(self.workdue),
          'workstarted': Filter(self.workstarted),
          'worktostart': Filter(self.worktostart),
          'worklate': Filter(self.worklate),
          'no_disabled_tag': Filter(self.no_disabled_tag,
            {'transparent': True}),
          }
        self.available_filters.update(f)

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
        
    def no_disabled_tag(self,task,parameters=None):
        """Filter of task that don't have any disabled/nonworkview tag"""
        toreturn = True
        for t in task.get_tags():
            if t.get_attribute("nonworkview") == "True":
                toreturn = False
        return toreturn
        
    ##########################################
    def get_filter(self, filter_name):
        """ Get the filter object for a given *filter_name*."""
        if self.available_filters.has_key(filter_name):
            return self.available_filters[filter_name]
        elif self.custom_filters.has_key(filter_name):
            return self.custom_filters[filter_name]
        else:
            raise KeyError("FiltersBank contains no filter '%s'" %
              filter_name)

    def list_filters(self):
        """List, by name, all available filters."""
        liste = self.available_filters.keys()
        liste += self.custom_filters.keys()
        return liste

    def add_filter(self, filter_name, filter_func, parameters={}):
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
                filter_obj = SimpleTagFilter(filter_name)
                param = {}
                param['transparent'] = True
                filter_obj.set_parameters(param)
            else:
                filter_obj = Filter(filter_func, parameters)
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

