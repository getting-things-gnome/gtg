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
from bzrlib.urlutils import join
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
    ERROR_NOTACOMMAND = _(" is not a command word.")
    ERROR_TAG = _("No tag named ")
    ERROR_TASK = _("No task named ")
    
    #usable join keyWords
    andKeyword = _("and +")
    orKeyword = _("or |")
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
    tommorrowKeywords = _("tomorrow")
    nextmonthKeywords = _("nextmonth")
    nodateKeywords = _("nodate")
    
    #keywords for translations
    #translate this to add the original english and an additional language to all keywords
    #usable join keyWords
    andKeywordTranslation = _("")
    orKeywordTranslation = _("")
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
    tommorrowKeywordsTranslation = _("")
    nextmonthKeywordsTranslation = _("")
    nodateKeywordsTranslation = _("")
    
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
        self.dicKeyword = self.initKeywords()
        self.tree = tree
        self.oldFilters =[]
        #get all tags
        self.alltags = tags
        #gets the titles of tasks
        self.allTaskTitles = self.get_all_tasks_title();
        
    def initKeywords(self):
        """
        gets all keywords, including translations and puts it in lists
        """
        dic = {}
        #join Keywords including translations
        dic["and"] = self.andKeyword.split(' ') + self.mysplit(self.andKeywordTranslation, ' ')
        dic["or"] = self.orKeyword.split(' ') + self.mysplit(self.orKeywordTranslation, ' ')
        dic["not"] = self.notKeyword.split(' ') + self.mysplit(self.notKeywordTranslation, ' ')
        dic["join"] = dic.get("and")+dic.get("or")+dic.get("not")
        #state keywords
        dic["active"] = self.activeKeywords.split(' ') + self.mysplit(self.activeKeywordsTranslation, ' ')
        dic["dismissed"] = self.dismissedKeyword.split(' ') + self.mysplit(self.dismissedKeywordTranslation, ' ')
        dic["done"] = self.doneKeyword.split(' ') + self.mysplit(self.doneKeywordTranslation, ' ')
        dic["state"] = dic.get("active") + dic.get("dismissed") + dic.get("done")
        #temporal keywords
        dic["before"]    = self.beforeKeywords.split(' ') + self.mysplit(self.beforeKeywordsTranslation, ' ')
        dic["after"]     = self.afterKeywords.split(' ') + self.mysplit(self.afterKeywordsTranslation, ' ')
        dic["past"]      = self.pastKeywords.split(' ') + self.mysplit(self.pastKeywordsTranslation, ' ')
        dic["future"]    = self.futureKeywords.split(' ') + self.mysplit(self.futureKeywordsTranslation, ' ')
        dic["today"]     = self.todayKeywords.split(' ') + self.mysplit(self.todayKeywordsTranslation, ' ')
        dic["tommorrow"] = self.tommorrowKeywords.split(' ') + self.mysplit(self.tommorrowKeywordsTranslation, ' ')
        dic["nextmonth"] = self.nextmonthKeywords.split(' ') + self.mysplit(self.nextmonthKeywordsTranslation, ' ')
        dic["nodate"]    = self.nodateKeywords.split(' ') + self.mysplit(self.nodateKeywordsTranslation, ' ')
        dic["temporal"] = dic.get("before") + dic.get("after") + dic.get("past") + \
            dic.get("future") + dic.get("today") + dic.get("tommorrow") + \
            dic.get("nextmonth") + dic.get("nodate")
        return dic
        
    def buildSearchTokens(self):
        '''
        From the text given on the builder, separate the text, check if its a valid syntax,
        prepares the data for filters and sets flag and error message for a valid search or not 
        '''
        #reset error message
        self.error = ""
        tempTokens = {}
        commands = self.dicKeyword["join"]+self.dicKeyword["temporal"] + self.dicKeyword["state"]
        #if the number of " is not pair, the search query is considered invalid
        if (self.text.count('"') % 2) != 0:
            self.valid = False
            self.error += self.ERROR_QUOTATIONMARK
            return
        #separate in groups with diferent meanings
        #MISSING
        # - diferente date formats"
        match = re.findall(r'(?P<command>(?<=!)\S+\s?)|(?P<tag>@\S+\s?)|(?P<task>(?<=#)\S+\s?)|(?P<date>[01][0-2][/\.-]?[0-3][0-9][/\.-]\d{4})|(?P<literal>".+?")|(?P<word>(?![!"#@])\S+\s?)', self.text)
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
                    if(sum(map(lambda x: x.lower() in sets[word].lower(), commands))):
                        continue
                    else:
                        self.error = self.commandNotation + sets[word] + self.ERROR_NOTACOMMAND
                        self.valid = False
                        return
                #if its a tag
                elif word == 1:
                    #Ignore case of words
                    if(sum(map(lambda x: x.lower() in sets[word].lower(), self.alltags))):
                        continue
                    else:
                        self.error = self.ERROR_TAG + sets[word]
                        self.valid = False
                        return
                #if its a task
                elif word == 2:
                    #Ignore case of words
                    if(sum(map(lambda x: x.lower() in sets[word].lower(), self.allTaskTitles))):
                        continue
                    else:
                        self.error = self.ERROR_TAG + sets[word]
                        self.valid = False
                        return
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
            
    def mysplit(self, s, delim=None):
        return [x for x in s.split(delim) if x]
       
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