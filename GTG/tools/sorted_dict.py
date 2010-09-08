# -*- coding: utf-8 -*-
# pylint: disable-msg=W0201
# -----------------------------------------------------------------------------
# Getting Things Gnome! - a personal organizer for the GNOME desktop
# Copyright (c) 2010 - Luca Invernizzi
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

import  bisect



class SortedDict(dict):
    '''
    Keeps a list of tuples sorted in the first tuple element.
    It's possible to delete a tuple just by giving an element and its position.
    The sorted element must be a Unicode string (lexicographical sorting)
    '''


    def __init__(self, key_position, sort_position, *initial_values):
        super(SortedDict, self).__init__()
        self.__key_position = key_position
        self.__sort_position = sort_position
        self.__sorted_list = []
        for value in  initial_values:
            self.sorted_insert(value)

    def sorted_insert(self, a_tuple):
        sort_elem = a_tuple[self.__sort_position].lower()
        position = bisect.bisect(self.__sorted_list, sort_elem)
        self.__sorted_list.insert(position, sort_elem)
        self[a_tuple[self.__key_position]]= a_tuple
        return position

    def pop_by_key(self, key):
        a_tuple = self[key]
        sort_elem = a_tuple[self.__sort_position].lower()
        self.__sorted_list.remove(sort_elem)
        return a_tuple

    def get_index(self, a_tuple):
        sort_elem = a_tuple[self.__sort_position]
        position = bisect.bisect(self.__sorted_list, sort_elem)
        if self.__sorted_list[position] == sort_elem:
            return position
        else:
            return None



