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

import re

import GTG
from GTG.core.datastore import DataStore
from GTG                import _, info, ngettext
'''
search.py - contains all search related definitions and operations
'''

class Search:
    ''' 
    This class represent a search instance in GTG.
    This class should be saved later for search history
    '''
    
    #text for errors
    ERROR_GENERIC = _("Error in search: ")
    ERROR_QUOTATIONMARK = _("Bad use of quotation marks")
    ERROR_COMMAND = _("Invalid use of commands")
    ERROR_NOTACOMMAND = _("is not a command word.")
    ERROR_TAG = _("No tag named ")
    ERROR_TASK = _("No task named named")
    
    
    #usable join keyWords
    joinKeywords = _("and AND + " +
                      "or OR | " +
                      "not NOT -")
    
    #usable task state keyWords
    stateKeywords = _("active ACTIVE " +
                      "dismissed DISMISSED " +
                      "done DONE")
    
    #usable temporal keywords
    temporalKeywords = _("before BEFORE " +
                        "after AFTER " +
                        "past PAST " +
                        "future FUTURE " +
                        "today TODAY " +
                        "tomorrow TOMORROW " +
                        "nextmonth NEXTMONTH " +
                        "nodate NODATE ")
    
    #caracter notations for diferent restrictions
    taskNotation = '#'
    tagNotation = '@'
    commandNotation = '!'
    literalNotation = '"'
    
    
    def __init__(self, text, requester, tree, tags):
        '''
        initialize the search object
        parameter:
         - text of the query
         - requester
         - task tree view
         - tag tree view
        '''
        self.title = ("My new search")
        self.text = text
        self.error = ""
        self.valid = False
        self.req = requester
        #separate keywords in lists
        self.joinTokens = self.joinKeywords.split(' ')
        self.stateTokens = self.stateKeywords.split(' ')
        self.temporalTokens = self.temporalKeywords.split(' ')
        self.tree = tree
        self.oldFilters =[]
        self.alltags = tags
        
    def buildSearchTokens(self):
        '''
        From the text given on the builder, separate the text, check if its a valid syntax,
        prepares the data for filters and sets flag and error message for a valid search or not 
        '''
        #reset error message
        self.error = ""
        tempTokens = {}
        #if the number of " is not pair, the search query is considered invalid
        if (self.text.count('"') % 2) != 0:
            self.valid = False
            self.error += self.ERROR_QUOTATIONMARK
            return
        #separate in groups with diferent meanings
        #MISSING
        # - diferente date formats"
        match = re.findall(r'(?P<command>(?<=!)\S+\s?)|(?P<tag>@\S+\s?)|(?P<task>(?<=#)\S+\s?)|(?P<date>[01][0-2][/\.-]?[0-3][0-9][/\.-]\d{4})|(?P<literal>".+?")|(?P<word>(?![!"#@])\S+\s?)', self.text)
        #self.printMatches(match)
        #analise the sets
        #sets are given in a list of sub,lists
        #each main list will have a sublist with one of 5 possible positions with text
        for sets in match:
            for word in range(len(sets)):
                #if the position is empty, continue
                if sets[word] =='':
                    continue
                #if its a command
                elif word == 0:
                    #if its not a valid command word, set error and return
                    if (sets[word] not in self.joinKeywords and
                        sets[word] not in self.stateKeywords and 
                        sets[word] not in self.temporalKeywords):
                        self.error = self.commandNotation + sets[word] + self.ERROR_NOTACOMMAND
                        self.valid = False
                        return
                #if its a tag
                elif word == 1:
                    #if (x in sets[word] for x in self.alltags):
                    if(sum(map(lambda x: x in sets[word], self.alltags))):
                        continue
                    else:
                        self.error = self.ERROR_TAG + sets[word]
                        self.valid = False
                        return
                #if its a task
                elif word == 2:
                    print("task: "+str(sets[word]))
                #if its a date
                elif word == 3:
                    print("date: "+str(sets[word]))
                #if its a literal
                elif word == 4:
                    print("literal: "+str(sets[word]))
                #if its a word
                elif word == 5:
                    print("word: "+str(sets[word]))
        self.valid = True
        return
    
    def isValid(self):
        '''
        See if a search query is valid or not
        '''
        return self.valid
    
    def returnError(self):
        '''
        Return the error message
        '''
        return self.error
    
    def removeFilters(self):
        """
        Removes all the filters from the tree
        """
        print(self.get_all_tasks_title())
        self.oldFilters = self.tree.list_applied_filters()
        #print(self.tree.list_applied_filters())
        self.tree.reset_filters()
        print(self.get_all_tasks_title())
        #print(self.tree.list_applied_filters())
    
    def get_all_tasks_title(self):
        """
        Gets the titles from all tasks
        """
        titles = []
        nodes = self.tree.get_all_nodes()
        for x in nodes:
            titles.append(self.tree.get_node(x).get_title())
        return titles
    
    def resetToActiveTree(self):
        """
        re-aplyes the original filters
        """
        for x in self.oldFilters:
            self.tree.apply_filter(x)

    def __str__(self):
        '''
        String representation of the search object
        '''
        s = ""
        s = s + "Search Object\n"
        s = s + self.text + "\n"
        return s
###############################################################################
# DEGUB STUFF
###############################################################################
    def test(self):
        print (self.req.list_filters())

    def printMatches(self, match):
        """
        prints the result of the the regular expression
        
        Keyword arguments:
        match -- list of values returned from the .findall() of the regular expression
        """
        print(match)
        for sets in match:
            for word in range(len(sets)):
                print("sets. " + sets[word])
                if sets[word] =='':
                    continue
                elif word == 0:
                    print("command: "+str(sets[word]))
                elif word == 1:
                    print("tag: "+str(sets[word]))
                elif word == 2:
                    print("task: "+str(sets[word]))
                elif word == 3:
                    print("literal: "+str(sets[word]))
                elif word == 4:
                    print("word: "+str(sets[word]))