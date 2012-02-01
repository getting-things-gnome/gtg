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
from GTG.core.task               import Task
'''
search.py - contains all search related definitions and operations
'''

class Search:
    ''' 
    This class represent a search instance in GTG.
    '''
    
    #usable join keyWords
    andKeyword = _("and +")
    #orKeyword = _("or |")
    notKeyword = _("not -")
    
    #usable task state keyWords
    activeKeywords = _("active")
    dismissedKeyword = _("dismissed")
    doneKeyword = _("done")
    
    #usable temporal keywords
    beforeKeywords = _("before")
    afterKeywords = _("after")
    pastKeywords = _("past")
    futureKeywords = _("future")
    todayKeywords = _("today")
    tomorrowKeywords = _("tomorrow")
    nextmonthKeywords = _("nextmonth")
    nowKeywords = _("now")
    soonKeywords = _("soon")
    laterKeywords = _("later")
    nodateKeywords = _("nodate")
    lateKeywords = _("late")
    
    #keywords for translations
    #translate this to add the original english and an additional language to all keywords
    #usable join keyWords
    andKeywordTranslation = _("")
    #orKeywordTranslation = _("")
    notKeywordTranslation = _("")
    
    #usable task state keyWords
    activeKeywordsTranslation = _("")
    dismissedKeywordTranslation = _("")
    doneKeywordTranslation = _("")
    
    #usable temporal keywords
    beforeKeywordsTranslation = _("")
    afterKeywordsTranslation = _("")
    pastKeywordsTranslation = _("")
    futureKeywordsTranslation = _("")
    todayKeywordsTranslation = _("")
    tomorrowKeywordsTranslation = _("")
    nextmonthKeywordsTranslation = _("")
    nodateKeywordsTranslation = _("")
    nowKeywordsTranslation = _("")
    soonKeywordsTranslation = _("")
    laterKeywordsTranslation = _("")
    lateKeywordsTranslation = _("")
    
    #character notations for different restrictions
    taskNotation = '#'
    tagNotation = '@'
    commandNotation = '!'
    literalNotation = '"'
    
    
    def __init__(self, text, requester, tree):
        '''
        initialize the search object
        parameter:
         - text of the query
         - requester
         - task tree view
         - tag tree view
        '''
        self.req = requester
        
        self.title = ("My new search")
        self.text = text
        #deals with empty searches
        if len(self.text) == 0:
            self.empty = True
            self.valid = True
        else:
            self.empty = False
            self.valid = False
        
        self.error = ''
        #separate keywords in lists
        self.dicKeyword = self._init_keywords()
        self.tree = tree
        self.oldFilters =[]
        self.paramsToFilter = {}
        #get all tags
        self.alltags = self.req.get_all_tags()
        
##################################private#####################################

    def _my_split(self, s, delim=None):
        """
        string split that removes empty strings
        useful for when there are no translations
        """
        return [x for x in s.split(delim) if x]
    
    def _init_keywords(self):
        """
        gets all keywords, including translations and puts it in lists
        """
        dic = {}
        #join Keywords including translations
        dic["and"] = self.andKeyword.split(' ') + self._my_split(self.andKeywordTranslation, ' ')
        dic["not"] = self.notKeyword.split(' ') + self._my_split(self.notKeywordTranslation, ' ')
        #state keywords
        dic["active"] = self.activeKeywords.split(' ') + self._my_split(self.activeKeywordsTranslation, ' ')
        dic["dismissed"] = self.dismissedKeyword.split(' ') + self._my_split(self.dismissedKeywordTranslation, ' ')
        dic["done"] = self.doneKeyword.split(' ') + self._my_split(self.doneKeywordTranslation, ' ')
        #temporal keywords
        dic["before"]    = self.beforeKeywords.split(' ') + self._my_split(self.beforeKeywordsTranslation, ' ')
        dic["after"]     = self.afterKeywords.split(' ') + self._my_split(self.afterKeywordsTranslation, ' ')
        dic["past"]      = self.pastKeywords.split(' ') + self._my_split(self.pastKeywordsTranslation, ' ')
        dic["future"]    = self.futureKeywords.split(' ') + self._my_split(self.futureKeywordsTranslation, ' ')
        dic["today"]     = self.todayKeywords.split(' ') + self._my_split(self.todayKeywordsTranslation, ' ')
        dic["tomorrow"] = self.tomorrowKeywords.split(' ') + self._my_split(self.tomorrowKeywordsTranslation, ' ')
        dic["nextmonth"] = self.nextmonthKeywords.split(' ') + self._my_split(self.nextmonthKeywordsTranslation, ' ')
        dic["nodate"]    = self.nodateKeywords.split(' ') + self._my_split(self.nodateKeywordsTranslation, ' ')
        dic["now"]    = self.nowKeywords.split(' ') + self._my_split(self.nowKeywordsTranslation, ' ')
        dic["soon"]    = self.soonKeywords.split(' ') + self._my_split(self.soonKeywordsTranslation, ' ')
        dic["later"]    = self.laterKeywords.split(' ') + self._my_split(self.laterKeywordsTranslation, ' ')
        dic["late"]    = self.lateKeywords.split(' ') + self._my_split(self.lateKeywordsTranslation, ' ')
        return dic
        
    def build_search_tokens(self):
        '''
        From the text given on the builder, separate the text, check if its a valid syntax,
        prepares the data for filters and sets flag and error message for a valid search or not 
        '''
        value = True
        union = False
        sequence = -1
        # the OR clausule is discarted for now, until i see a purpose
        #clause = False
        errorList=[]
        self.error = ''
        tempTokens = {}
        #if its empty, is valid but returns
        if self.empty:
            return
        #if the number of " is not pair, the search query is considered invalid
        if (self.text.count('"') % 2) != 0:
            self.error = '"'
            self.valid = False
            return
        #MISSING
        # - different date formats"
        # - wildcard searches
        expression = re.compile(r"""
                    (?P<command>(?<=!)\S+(?=\s)?)|                      # commands
                    (?P<tag>@\S+(?=\s)?)                                # tags
                    |(?P<task>\#.+?\#)|                                 # tasks
                    (?P<date>[01][0-2][/\.-]?[0-3][0-9][/\.-]\d{4})|    # dates - needs work
                    (?P<literal>".+?")|                                 # literals
                    (?P<word>(?![!"#@])\S+(?=\s)?)                      # words
                    """, re.VERBOSE)
        match = expression.findall(self.text)
        #analyze the sets
        #sets are given in a list of sub,lists
        #each main list will have a sublist with one of 5 possible positions with text
        for sets in match:
            #ugly hack so i can look in future elements of the cycle
            sequence +=1
            for word in range(len(sets)):
                #if the position is empty, continue
                if sets[word] =='':
                    continue
                #if its a command
                if word == 0:
                    #check if there's a 'and' to retain previous expression value
                    if sets[word].lower() in self.dicKeyword.get('and'):
                        #if the last operation is false, so is the next
                        #you cannot negate !and
                        if not value:
                            self.error = sets[word]
                            self.valid = False
                            return
                        #gets the value from last entry
                        if not self.paramsToFilter.values()[(len(self.paramsToFilter.values())-1)]:
                            value = False
                        continue
                    #not
                    if sets[word].lower() in self.dicKeyword.get('not'):
                        if value:
                            value = False
                            #cannot be 2 negations in a row
                        else:
                            errorList.append(self.commandNotation)
                            errorList.append(sets[word])
                            self.error = ''.join(errorList)
                            self.valid = False
                            return
                        continue
                    #and
                    if sets[word].lower() in self.dicKeyword.get('and'):
                        continue
                    #active
                    if sets[word].lower() in self.dicKeyword.get("active"):
                        if value:
                            self.paramsToFilter["active"]= True
                        else:
                            self.paramsToFilter["active"]= False
                            value = True
                        continue
                    #dismissed
                    if sets[word].lower() in self.dicKeyword.get("dismissed"):
                        if value:
                            self.paramsToFilter["dismissed"]= True
                        else:
                            self.paramsToFilter["dismissed"]= False
                            value = True
                        continue
                    #done
                    if sets[word].lower() in self.dicKeyword.get("done"):
                        if value:
                            self.paramsToFilter["done"]= True
                        else:
                            self.paramsToFilter["done"]= False
                            value = True
                        continue
                    #now
                    if sets[word].lower() in self.dicKeyword.get("now"):
                        if value:
                            self.paramsToFilter["now"]= True
                        else:
                            self.paramsToFilter["now"]= False
                            value = True
                        continue
                    #soon
                    if sets[word].lower() in self.dicKeyword.get("soon"):
                        if value:
                            self.paramsToFilter["soon"]= True
                        else:
                            self.paramsToFilter["soon"]= False
                            value = True
                        continue
                    #later
                    if sets[word].lower() in self.dicKeyword.get("later"):
                        if value:
                            self.paramsToFilter["later"]= True
                        else:
                            self.paramsToFilter["later"]= False
                            value = True
                        continue
                    #no date defined
                    if sets[word].lower() in self.dicKeyword.get("nodate"):
                        if value:
                            self.paramsToFilter["nodate"]= True
                        else:
                            self.paramsToFilter["nodate"]= False
                            value = True
                        continue
                    #late taks ex taks that the due date already passed
                    if sets[word].lower() in self.dicKeyword.get("late"):
                        if value:
                            self.paramsToFilter["late"]= True
                        else:
                            self.paramsToFilter["late"]= False
                            value = True
                        continue
                    #taks that are due today
                    if sets[word].lower() in self.dicKeyword.get("today"):
                        if value:
                            self.paramsToFilter["today"]= True
                        else:
                            self.paramsToFilter["today"]= False
                            value = True
                        continue
                    #tasks that are due tomorrow
                    if sets[word].lower() in self.dicKeyword.get("tomorrow"):
                        if value:
                            self.paramsToFilter["tomorrow"]= True
                        else:
                            self.paramsToFilter["tomorrow"]= False
                            value = True
                        continue
                    #case the command given doens't exist, return error
                    else:
                        errorList.append(self.commandNotation)
                        errorList.append(sets[word])
                        self.error = ''.join(errorList)
                        self.valid = False
                        return
                
                #if its a tag
                if word == 1:
                    #verifies if the tag exists
                    #for some reason, if the @ remains the lambda function fails
                    if(sum(map(lambda x: x.lower() == sets[word].lower(), self.alltags))):
                        if 'tags' not in self.paramsToFilter:
                            self.paramsToFilter['tags'] = []
                        self.paramsToFilter['tags'].append((value, sets[word]))
                        if not value:
                            value = True
                        continue
                    else:
                        self.error = sets[word]
                        self.valid = False
                        return
                #if its a task
                elif word == 2:
                    #verifies if the task exists
                    taskStriped = sets[word].strip('#')
                    if(sum(map(lambda x: x.lower() == taskStriped.lower(), self.req.get_all_titles()))):
                        if 'tasks' not in self.paramsToFilter:
                            self.paramsToFilter['tasks'] = []
                        self.paramsToFilter['tasks'].append((value, taskStriped))
                        if not value:
                            value = True
                        continue
                    else:
                        self.error = sets[word]
                        self.valid = False
                        return
                #if its a date
                elif word == 3:
                    print("not implemented")
                #if its a literal
                elif word == 4:
                    literalStriped = sets[word].strip('"')
                    if 'literals' not in self.paramsToFilter:
                        self.paramsToFilter['literals'] = []
                    self.paramsToFilter['literals'].append((value, literalStriped.lower()))
                    if not value:
                        value = True
                    continue
                #if its a word
                elif word == 5:
                    if 'words' not in self.paramsToFilter:
                        self.paramsToFilter['words'] = []
                    self.paramsToFilter['words'].append((value, sets[word].lower()))
                    if not value:
                        value = True
                    continue
        self.valid = True
        if len (self.paramsToFilter) < 1:
            self.error = 'NONE'
            self.valid = False
            return
        return True
    
    def apply_search(self):
        """
        apply the search to the desired tree
        
        Return false if the search tokens are not build or are invalid
        """
        if not self.valid:
            return False
        else:
            self.tree.reset_filters()
            self.tree.apply_filter('search', self.paramsToFilter)
            return True
    
    def is_valid(self):
        '''
        returns true if the search tokens given are valid
        returns false if the tokens are not yet given or are not compliant with the syntax
        '''
        return self.valid
    
    def is_empty(self):
        '''
        return True if the search string is ''
        '''
        return self.empty
    
    def return_error(self):
        '''
        Return the error message
        '''
        return self.error
    
    def get_commands(self):
        """
        returns the list of commands with the ! at the beginning
        
        except + and - at this time
        """
        dictlist = []
        for item in self.dicKeyword.iteritems():
            for key in item[1]:
                #exceptions
                if key in ['+', '-']:
                    continue
                dictlist.append('!'+ key)
        return sorted(dictlist)
    
    def get_params(self):
        """
        returns the parameters from the search query
        """
        return self.paramsToFilter
   
    def __str__(self):
        '''
        String representation of the search object
        '''
        s = ""
        s = s + "Search Object\n"
        s = s + 'valid = ' + str(self.is_valid()) + '\n'
        s = s + self.text + "\n"
        return s
    
###############################################################################
# Search Filters
###############################################################################

    """
    The filter used for search is on treefactory.py
    
    Its there to be inserted into filterbank when gtg starts and also to be 
    connected to the tagtree element AKA tagsidebar ^^
    
    as such any any additional variables to the search have to go through 
    self.paramsToFilter{} as that is always passed to the filter
    """