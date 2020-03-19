# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
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

"""
Contains TwoKeyDict, a Dictionary which also has a secondary key
"""

from functools import reduce


class BiDict():
    """
    Bidirectional dictionary: the pairs stored can be accessed using either the
    first or the second element as key (named key1 and key2).
    You don't need this if there is no clash between the domains of the first
    and second element of the pairs.
    """

    def __init__(self, *pairs):
        """
        Initialization of the bidirectional dictionary

        @param pairs: optional. A list of pairs to add to the dictionary
        """
        super().__init__()
        self._first_to_second = {}
        self._second_to_first = {}
        for pair in pairs:
            self.add(pair)

    def add(self, pair):
        """
        Adds a pair (key1, key2) to the dictionary

        @param pair: the pair formatted as (key1, key2)
        """
        self._first_to_second[pair[0]] = pair[1]
        self._second_to_first[pair[1]] = pair[0]

    def _get_by_first(self, key):
        """
        Gets the key2 given key1

        @param key: the first key
        """
        return self._first_to_second[key]

    def _get_by_second(self, key):
        """
        Gets the key1 given key2

        @param key: the second key
        """
        return self._second_to_first[key]

    def _remove_by_first(self, first):
        """
        Removes a pair given the first key

        @param key: the first key
        """
        second = self._first_to_second[first]
        del self._second_to_first[second]
        del self._first_to_second[first]

    def _remove_by_second(self, second):
        """
        Removes a pair given the second key

        @param key: the second key
        """
        first = self._second_to_first[second]
        del self._first_to_second[first]
        del self._second_to_first[second]

    def _get_all_first(self):
        """
        Returns the list of all first keys

        @returns: list
        """
        return list(self._first_to_second)

    def _get_all_second(self):
        """
        Returns the list of all second keys

        @returns: list
        """
        return list(self._second_to_first)

    def __str__(self):
        """
        returns a string representing the content of this BiDict

        @returns: string
        """
        return reduce(lambda text, keys:
                      str(text) + str(keys),
                      iter(self._first_to_second.items()))



class TwoKeyDict():
    """
    It's a standard Dictionary with a secondary key.
    For example, you can add an element ('2', 'II', two'), where the
    first two arguments are keys and the third is the stored object, and access
    it as::
        twokey['2'] ==> 'two'
        twokey['II'] ==> 'two'
    You can also request the other key, given one.
    Function calls start with _ because you'll probably want to rename them
     when you use this dictionary, for the sake of clarity.
    """

    def __init__(self, *triplets):
        """
        Creates the TwoKeyDict and optionally populates it with some data

        @param triplets: tuples for populating the TwoKeyDict. Format:
                         ((key1, key2, data_to_store), ...)
        """
        super().__init__()
        self._key_to_key_bidict = BiDict()
        self._primary_to_value = {}
        for triplet in triplets:
            self.add(triplet)

    def add(self, triplet):
        """
        Adds a new triplet to the TwoKeyDict

        @param triplet: a tuple formatted like this:
                        (key1, key2, data_to_store)
        """
        self._key_to_key_bidict.add((triplet[0], triplet[1]))
        self._primary_to_value[triplet[0]] = triplet[2]

    def _get_by_primary(self, primary):
        """
        Gets the stored data given the primary key

        @param primary: the primary key
        @returns object: the stored object
        """
        return self._primary_to_value[primary]

    def _get_by_secondary(self, secondary):
        """
        Gets the stored data given the secondary key

        @param secondary: the primary key
        @returns object: the stored object
        """
        primary = self._key_to_key_bidict._get_by_second(secondary)
        return self._get_by_primary(primary)

    def _remove_by_primary(self, primary):
        """
        Removes a triplet given the rpimary key.

        @param primary: the primary key
        """
        del self._primary_to_value[primary]
        self._key_to_key_bidict._remove_by_first(primary)

    def _remove_by_secondary(self, secondary):
        """
        Removes a triplet given the rpimary key.

        @param secondary: the primary key
        """
        primary = self._key_to_key_bidict._get_by_second(secondary)
        self._remove_by_primary(primary)

    def _get_secondary_key(self, primary):
        """
        Gets the secondary key given the primary

        @param primary: the primary key
        @returns object: the secondary key
        """
        return self._key_to_key_bidict._get_by_first(primary)

    def _get_primary_key(self, secondary):
        """
        Gets the primary key given the secondary

        @param secondary: the secondary key
        @returns object: the primary key
        """
        return self._key_to_key_bidict._get_by_second(secondary)

    def _get_all_primary_keys(self):
        """
        Returns all primary keys

        @returns list: list of all primary keys
        """
        return self._key_to_key_bidict._get_all_first()

    def _get_all_secondary_keys(self):
        """
        Returns all secondary keys

        @returns list: list of all secondary keys
        """
        return self._key_to_key_bidict._get_all_second()
