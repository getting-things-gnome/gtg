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


class Filter:
    def __init__(self,func,req):
        self.func = func
        self.dic = {}
        self.tree = req

    def set_parameters(self,dic):
        if dic:
            self.dic = dic
    
    def is_displayed(self,tid):
        if self.tree.has_node(tid):
            task = self.tree.get_node(tid)
            value = True
        else:
            return False
        if self.dic:
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
            
    
class FiltersBank:
    """
    Stores filter objects in a centralized place.
    """

    def __init__(self,tree):
        """
        Create several stock filters:

        workview - Tasks that are active, workable, and started
        active - Tasks of status Active
        closed - Tasks of status closed or dismissed
        notag - Tasks with no tags
        """
        self.tree = tree
        self.available_filters = {}
        self.custom_filters = {}

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
    
    def add_filter(self,filter_name,filter_func,parameters=None):
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
            else:
                filter_obj = Filter(filter_func,self.tree)
                filter_obj.set_parameters(parameters)
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
                #self.unapply_filter(filter_name)
                self.custom_filters.pop(filter_name)
                return True
            else:
                return False
        else:
            return False