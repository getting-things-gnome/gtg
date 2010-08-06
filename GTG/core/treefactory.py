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

from GTG.tools.liblarch          import Tree
from GTG.core.task               import Task

class TreeFactory:

    def get_tasks_tree(self):
        '''This create a liblarch tree suitable for tasks, 
        including default filters
        For tags, filter are dynamically created at Tag insertion.
        '''
        tasktree = Tree()
        f_dic = {
          'workview': [self.workview],
          'active': [self.active],
          'closed': [self.closed, {'flat': True}],
          'notag': [self.notag, {'transparent': True}],
          'workable': [self.is_workable],
          'started': [self.is_started],
          'workdue': [self.workdue],
          'workstarted': [self.workstarted],
          'worktostart': [self.worktostart],
          'worklate': [self.worklate],
          'no_disabled_tag': [self.no_disabled_tag,{'transparent': True}],
          }
          
        for f in f_dic:
            filt = f_dic[f]
            if len(filt) > 1:
                param = filt[1]
            else:
                param = None
            tasktree.add_filter(f,filt[0],param)
        
        
        return tasktree
    
    
    def get_tags_tree(self):
        '''This create a liblarch tree suitable for tags,
        including the all_tags_tag and notag_tag.
        '''
        tagtree = Tree()
        return tagtree
    
    ################# Tag Filters ##########################################
    
    def tag_filter(self,node,parameters):
        #FIXME: we should take tag children into account
        tname = parameters['tag']
        return node.has_tags([tname])
        
        
    ################# Task Filters #########################################
    
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
