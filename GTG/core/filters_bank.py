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

class Filter:
    def __init__(self,func):
        self.func = func
        self.dic = None
        
    def set_parameters(self,dic):
        self.dic = dic
    
    def is_displayed(self,task):
        if self.dic:
            return self.func(task,parameters=self.dic)
        else:
            return self.func(task)
    

class FiltersBank:

    #FIXME : put those 3 constants and those in Task.py in one place
    STA_ACTIVE    = "Active"
    STA_DISMISSED = "Dismiss"
    STA_DONE      = "Done"

    def __init__(self,req,tree=None):
        self.tree = tree
        self.req = req
        self.applied_filters = []
        self.available_filters = {}
        self.custom_filters = {}
        #Workview
        filt_obj = Filter(self.workview)
        self.available_filters['workview'] = filt_obj
        #Active
        filt_obj = Filter(self.active)
        self.available_filters['active'] = filt_obj
        #closed
        filt_obj = Filter(self.closed)
        self.available_filters['closed'] = filt_obj
        
    def is_displayed(self,task):
        result = True
        for f in self.applied_filters:
            filt = self.get_filter(f)
            result = result and filt.is_displayed(task)
        return result
        
        
    ######### hardcoded filters #############
    def is_leaf(self,task):
        return not task.has_child()
    
    def is_workable(self,task):
        return task.is_workable()
            
    def workview(self,task):
        wv = self.is_workable(task) 
        wv = wv and self.active(task)
        wv = wv and task.is_started()
        return wv
        
    def active(self,task):
        #FIXME: we should also handle unactive tags
        return task.get_status() == self.STA_ACTIVE
        
    def closed(self,task):
        return task.get_status() in [self.STA_DISMISSED,self.STA_DONE]
        
    ##########################################
        
    #FIXME : it seems that this function is called twice
    # when setting the workview. Shouldn't be the case
    def apply_filter(self,filter_name,parameters=None):
        filt = None
        if filter_name in self.available_filters:
            filt = self.available_filters[filter_name]
        elif filter_name in self.custom_filters:
            filt = self.custom_filters[filter_name]
        if filt:
            if parameters:
                filt.set_parameters(parameters)
            if filter_name not in self.applied_filters:
                self.applied_filters.append(filter_name)
                self.tree.refilter()
            return True
        else:
            return False
    
    def unapply_filter(self,filter_name):
        if filter_name in self.applied_filters:
            self.applied_filters.remove(filter_name)
            self.tree.refilter()
            return True
        else:
            return False
    
    
    def reset_filters(self):
        self.applied_filters = []
        self.tree.refilter()
        
        
    # Get the filter object for a given name
    def get_filter(self,filter_name):
        if self.available_filters.has_key(filter_name):
            return self.available_filters[filter_name]
        elif self.custom_filters.has_key(filter_name):
            return self.custom_filters[filter_name]
        else:
            return None
    
    # List, by name, all available filters
    def list_filters(self):
        liste = self.available_filters.keys()
        liste += self.custom_filters.keys()
        return liste
    
    # Add a filter to the filter bank
    # Return True if the filter was added
    # Return False if the filter_name was already in the bank
    def add_filter(self,filter_name,filter_func):
        if filter_name not in self.list_filters:
            filter_obj = Filter(filter_func)
            self.custom_filters[filter_name] = filter_obj
            return True
        else:
            return False
        
    # Remove a filter from the bank.
    # Only custom filters that were added here can be removed
    # Return False if the filter was not removed
    def remove_filter(self,filter_name):
        if not self.available_filters.has_key(filter_name):
            if self.custom_filters.has_key(filter_name):
                self.unapply_filter(filter_name)
                self.custom_filters.pop(filter_name)
            else:
                return False
        else:
            return False
