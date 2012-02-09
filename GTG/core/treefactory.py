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

from datetime import datetime

from GTG.tools.dates  import date_today, no_date, Date

from GTG                         import _
from liblarch                    import Tree
from GTG.core.task               import Task
from GTG.core.tagstore           import Tag
from GTG.core         import CoreConfig


class TreeFactory:

    def __init__(self):
        #Keep the tree in memory jus in case we have to use it for filters.
        self.tasktree = None
        self.tagtree = None

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
          'no_disabled_tag': [self.no_disabled_tag, {'transparent': True}],
          }

        for f in f_dic:
            filt = f_dic[f]
            if len(filt) > 1:
                param = filt[1]
            else:
                param = None
            tasktree.add_filter(f, filt[0], param)
        self.tasktree = tasktree
        return tasktree

    def get_tags_tree(self, req):
        '''This create a liblarch tree suitable for tags,
        including the all_tags_tag and notag_tag.
        '''
        tagtree = Tree()

        ### building the initial tags
        # Build the "all tasks tag"
        alltag = Tag(CoreConfig.ALLTASKS_TAG, req=req)
        alltag.set_attribute("special", "all")
        alltag.set_attribute("label", "<span weight='bold'>%s</span>"\
                                             % _("All tasks"))
        alltag.set_attribute("icon", "gtg-tags-all")
        alltag.set_attribute("order", 0)
        tagtree.add_node(alltag)
        p = {'transparent': True}
        self.tasktree.add_filter(CoreConfig.ALLTASKS_TAG,\
                                    self.alltag, parameters=p)
        # Build the "without tag tag"
        notag_tag = Tag(CoreConfig.NOTAG_TAG, req=req)
        notag_tag.set_attribute("special", "notag")
        notag_tag.set_attribute("label", "<span weight='bold'>%s</span>"\
                                             % _("Tasks with no tags"))
        notag_tag.set_attribute("icon", "gtg-tags-none")
        notag_tag.set_attribute("order", 1)
        tagtree.add_node(notag_tag)
        p = {'transparent': True}
        self.tasktree.add_filter(CoreConfig.NOTAG_TAG,\
                                    self.notag, parameters=p)
        
        # Build the search tag
        search_tag = Tag(CoreConfig.SEARCH_TAG,req=req)
        search_tag.set_attribute("special","search")
        search_tag.set_attribute("label","<span weight='bold'>%s</span>"\
                                             % _("Search"))
        search_tag.set_attribute("icon","search")
        search_tag.set_attribute("order",2)
        tagtree.add_node(search_tag)
        p = {'transparent':True}
        self.tasktree.add_filter('search',\
                                    self.search, parameters=None)
        
        # Build the separator
        sep_tag = Tag(CoreConfig.SEP_TAG, req=req)
        sep_tag.set_attribute("special", "sep")
        sep_tag.set_attribute("order",3)
        tagtree.add_node(sep_tag)

        #### Filters
        tagtree.add_filter('activetag', self.actively_used_tag)
        tagtree.add_filter('usedtag', self.used_tag)
        tagtree.add_filter('search', self.search)

        activeview = tagtree.get_viewtree(name='activetags', refresh=False)
        activeview.apply_filter('activetag')
        
        #This view doesn't seem to be used. So it's not useful to build it now
#        usedview = tagtree.get_viewtree(name='usedtags',refresh=False)
#        usedview.apply_filter('usedtag')

        self.tagtree = tagtree
        self.tagtree_loaded = True
        return tagtree

    ################# Tag Filters ##########################################

    #filter to display only tags with active tasks
    def actively_used_tag(self, node, parameters=None):
        toreturn = node.is_actively_used()
        return toreturn

    def used_tag(self, node, parameters=None):
        return node.is_used()

    ################# Task Filters #########################################
    #That one is used to filters tag. Is it built dynamically each times
    #a tag is added to the tagstore
    def tag_filter(self, node, parameters=None):
        #FIXME: we should take tag children into account
        #Bryce : use self.tagtree to find children/parents of tags
        tname = parameters['tag']
        toreturn = node.has_tags([tname])
        return toreturn

    def alltag(self, task, parameters=None):
        return True

    def notag(self, task, parameters=None):
        """ Filter of tasks without tags """
        return task.has_tags(notag_only=True)

    def is_leaf(self, task, parameters=None):
        """ Filter of tasks which have no children """
        return not task.has_child()

    def is_workable(self, task, parameters=None):
        """ Filter of tasks that can be worked """
        tree = task.get_tree()
        for child_id in task.get_children():
            if not tree.has_node(child_id):
                continue

            child = tree.get_node(child_id)
            if child.get_status() == Task.STA_ACTIVE:
                return False

        return True

    def is_started(self, task, parameters=None):
        '''Filter for tasks that are already started'''
        start_date = task.get_start_date()
        if start_date:
            #Seems like pylint falsely assumes that subtraction always results
            #in an object of the same type. The subtraction of dates
            #results in a datetime.timedelta objec
            #that does have a 'days' member.
            difference = date_today() - start_date
            if difference.days == 0:
                # Don't count today's tasks started until morning
                return datetime.now().hour > 4
            else:
                return difference.days > 0 #pylint: disable-msg=E1101
        else:
            return True

    def workview(self, task, parameters=None):
        wv = self.active(task) and\
             self.is_started(task) and\
             self.is_workable(task) and\
             self.no_disabled_tag(task)
        return wv

    def workdue(self, task):
        ''' Filter for tasks due within the next day '''
        wv = self.workview(task) and \
             task.get_due_date() != no_date and \
             task.get_days_left() < 2
        return wv

    def worklate(self, task):
        ''' Filter for tasks due within the next day '''
        wv = self.workview(task) and \
             task.get_due_date() != no_date and \
             task.get_days_late() > 0
        return wv

    def workstarted(self, task):
        ''' Filter for workable tasks with a start date specified '''
        wv = self.workview(task) and \
             task.start_date
        return wv

    def worktostart(self, task):
        ''' Filter for workable tasks without a start date specified '''
        wv = self.workview(task) and \
             not task.start_date
        return wv

    def active(self, task, parameters=None):
        """ Filter of tasks which are active """
        #FIXME: we should also handle unactive tags
        return task.get_status() == Task.STA_ACTIVE

    def closed(self, task, parameters=None):
        """ Filter of tasks which are closed """
        ret = task.get_status() in [Task.STA_DISMISSED, Task.STA_DONE]
        return ret

    def no_disabled_tag(self, task, parameters=None):
        """Filter of task that don't have any disabled/nonworkview tag"""
        toreturn = True
        for t in task.get_tags():
            if t.get_attribute("nonworkview") == "True":
                toreturn = False
        return toreturn
    
    def search(self,task,parameters=None):
        """
        Single filter that has all the search parameters
        
        parameters will have a dictionary in which keys will be a kind of filter to apply
        the search will check for the existence of parameters, check it's negated or not 
        """
        #escape case
        if parameters == None:
            return False
        #if a task is active
        if 'active' in parameters:
            if parameters.get('active'):
                if task.get_status() != Task.STA_ACTIVE:
                    return False
            else:
                if task.get_status() == Task.STA_ACTIVE:
                    return False
        #if a task is Dismissed
        if 'dismissed' in parameters:
            if parameters.get('dismissed'):
                if task.get_status() != Task.STA_DISMISSED:
                    return False
            else:
                if task.get_status() == Task.STA_DISMISSED:
                    return False
        #if a task is Done
        if 'done' in parameters:
            if parameters.get('done'):
                if task.get_status() != Task.STA_DONE:
                    return False
            else:
                if task.get_status() == Task.STA_DONE:
                    return False
        #check the due date for a now
        if 'now' in parameters:
            #if no state is defined, it shows only active tasks
            if 'active' not in parameters and 'done' not in parameters and 'dismissed' not in parameters:
                if task.get_status() != Task.STA_ACTIVE:
                    return False
            if parameters.get('now'):
                if str(task.get_due_date()) != 'now':
                    return False
            else:
                if str(task.get_due_date()) == 'now':
                    return False
        #check the due date for a soon
        if 'soon' in parameters:
            #if no state is defined, it shows only active tasks
            if 'active' not in parameters and 'done' not in parameters and 'dismissed' not in parameters:
                if task.get_status() != Task.STA_ACTIVE:
                    return False
            if parameters.get('soon'):
                if str(task.get_due_date()) != 'soon':
                    return False
            else:
                if str(task.get_due_date()) == 'soon':
                    return False
        #check the due date for a later
        if 'later' in parameters:
            #if no state is defined, it shows only active tasks
            if 'active' not in parameters and 'done' not in parameters and 'dismissed' not in parameters:
                if task.get_status() != Task.STA_ACTIVE:
                    return False
            if parameters.get('later'):
                if str(task.get_due_date()) != 'later':
                    return False
            else:
                if str(task.get_due_date()) == 'later':
                    return False
        #check the due date for a later
        if 'late' in parameters:
            #if no state is defined, it shows only active tasks
            if 'active' not in parameters and 'done' not in parameters and 'dismissed' not in parameters:
                if task.get_status() != Task.STA_ACTIVE:
                    return False
            if parameters.get('late'):
                if task.get_days_left() > -1 or task.get_days_left() == None:
                    return False
            else:
                if task.get_days_left() < 0 and task.get_days_left() != None:
                    return False
        #check for tasks that have no date defined
        if 'nodate' in parameters:
            #if no state is defined, it shows only active tasks
            if 'active' not in parameters and 'done' not in parameters and 'dismissed' not in parameters:
                if task.get_status() != Task.STA_ACTIVE:
                    return False
            if parameters.get('nodate'):
                if str(task.get_due_date()) != '':
                    return False
            else:
                if str(task.get_due_date()) == '':
                    return False
        #check for tasks that are due tomorrow
        if 'tomorrow' in parameters:
            #if no state is defined, it shows only active tasks
            if 'active' not in parameters and 'done' not in parameters and 'dismissed' not in parameters:
                if task.get_status() != Task.STA_ACTIVE:
                    return False
            if parameters.get('tomorrow'):
                if task.get_days_left() != 1:
                    return False
            else:
                if task.get_days_left() == 1:
                    return False
        #check for tasks that are due today
        if 'today' in parameters:
            #if no state is defined, it shows only active tasks
            if 'active' not in parameters and 'done' not in parameters and 'dismissed' not in parameters:
                if task.get_status() != Task.STA_ACTIVE:
                    return False
            if parameters.get('today'):
                if task.get_days_left() != 0:
                    return False
            else:
                if task.get_days_left() == 0:
                    return False
        #task titles
        if 'tasks' in parameters:
            for tasks in parameters.get('tasks'):
                if tasks[0]:
                    if task.get_title().lower() != tasks[1]:
                        return False
                else:
                    if task.get_title().lower() == tasks[1]:
                        return False
        #tags
        if 'tags' in parameters:
            for tags in parameters.get('tags'):
                if tags[1] not in task.get_tags_name():
                    if tags[0]:
                        return False
                else:
                    if not tags[0]:
                        return False
        #words
        if 'words' in parameters:
            #tags are also included in the search
            #maybe latter i'll add the option to chose
            for words in parameters.get('words'):
                text = task.get_excerpt(strip_tags=False).lower()
                title = task.get_title().lower()
                #search for the word
                if text.find(words[1]) > -1 or words[1] in title:
                    if not words[0]:
                        return False
                else:
                    if words[0]:
                        return False
        #literas ex. "abc"
        if 'literals' in parameters:
            #tthis one is the same thing as the word search
            #only the literal includes spaces, special chars, etc
            #should define latter one more specific stuff about literals
            for literals in parameters.get('literals'):
                #search for the word
                text = task.get_excerpt(strip_tags=False).lower()
                title = task.get_title().lower()
                if text.find(literals[1]) > -1 or literals[1] in title:
                    if not literals[0]:
                        return False
                else:
                    if literals[0]:
                        return False
        #if it gets here, the task is in the search params
        return True
