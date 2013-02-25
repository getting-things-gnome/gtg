# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 - Lionel Dricot & Bertrand Rousseau
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


class BiDict(object):
    '''
    Bidirectional dictionary: the pairs stored can be accessed using either the
    first or the second element as key (named key1 and key2).
    You don't need this if there is no clash between the domains of the first
    and second element of the pairs.
    '''

    def __init__(self, *pairs):
        '''
        Initialization of the bidirectional dictionary

        @param pairs: optional. A list of pairs to add to the dictionary
        '''
        super(BiDict, self).__init__()
        self._first_to_second = {}
        self._second_to_first = {}
        for pair in pairs:
            self.add(pair)

    def add(self, pair):
        '''
        Adds a pair (key1, key2) to the dictionary

        @param pair: the pair formatted as (key1, key2)
        '''
        self._first_to_second[pair[0]] = pair[1]
        self._second_to_first[pair[1]] = pair[0]

    def _get_by_first(self, key):
        '''
        Gets the key2 given key1

        @param key: the first key
        '''
        return self._first_to_second[key]

    def _get_by_second(self, key):
        '''
        Gets the key1 given key2

        @param key: the second key
        '''
        return self._second_to_first[key]

    def _remove_by_first(self, first):
        '''
        Removes a pair given the first key

        @param key: the first key
        '''
        second = self._first_to_second[first]
        del self._second_to_first[second]
        del self._first_to_second[first]

    def _remove_by_second(self, second):
        '''
        Removes a pair given the second key

        @param key: the second key
        '''
        first = self._second_to_first[second]
        del self._first_to_second[first]
        del self._second_to_first[second]

    def _get_all_first(self):
        '''
        Returns the list of all first keys

        @returns: list
        '''
        return list(self._first_to_second)

    def _get_all_second(self):
        '''
        Returns the list of all second keys

        @returns: list
        '''
        return list(self._second_to_first)

    def __str__(self):
        '''
        returns a string representing the content of this BiDict

        @returns: string
        '''
        return reduce(lambda text, keys:
                      str(text) + str(keys),
                      self._first_to_second.iteritems())
