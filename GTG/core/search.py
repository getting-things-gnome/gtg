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
    This class should be saved later for search history
    '''
    
    #text for errors
    ERROR_GENERIC = _("Error in search: ")
    ERROR_QUOTATIONMARK = _("Bad use of quotation marks")
    ERROR_COMMAND = _("Invalid use of commands")
    ERROR_NOTACOMMAND = _(" is not a command word.")
    ERROR_TAG = _("No tag named ")
    ERROR_TASK = _("No task named ")
    ERROR_CONSECUTIVENOT = _("cannot be used in succession")
    ERROR_ISNOTVALIDSEARCH = _(" is not a valid search")
    
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
    
    #caracter notations for diferent restrictions
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
        self.dicKeyword = self.initKeywords()
        self.tree = tree
        self.oldFilters =[]
        self.paramsToFilter = {}
        #get all tags
        self.alltags = self.req.get_all_tags()
        #gets the titles of tasks
        self.allTaskTitles = self.req.get_all_titles();
        #add the filter to the filteer bank
        #FIXME: this should be added when the app starts
        self.req.add_filter('search', self.search)
        
    def initKeywords(self):
        """
        gets all keywords, including translations and puts it in lists
        """
        dic = {}
        #join Keywords including translations
        dic["and"] = self.andKeyword.split(' ') + self.mysplit(self.andKeywordTranslation, ' ')
        #dic["or"] = self.orKeyword.split(' ') + self.mysplit(self.orKeywordTranslation, ' ')
        dic["not"] = self.notKeyword.split(' ') + self.mysplit(self.notKeywordTranslation, ' ')
        #dic["join"] = dic.get("and")+dic.get("not")#+dic.get("or")
        #state keywords
        dic["active"] = self.activeKeywords.split(' ') + self.mysplit(self.activeKeywordsTranslation, ' ')
        dic["dismissed"] = self.dismissedKeyword.split(' ') + self.mysplit(self.dismissedKeywordTranslation, ' ')
        dic["done"] = self.doneKeyword.split(' ') + self.mysplit(self.doneKeywordTranslation, ' ')
        #dic["state"] = dic.get("active") + dic.get("dismissed") + dic.get("done")
        #temporal keywords
        dic["before"]    = self.beforeKeywords.split(' ') + self.mysplit(self.beforeKeywordsTranslation, ' ')
        dic["after"]     = self.afterKeywords.split(' ') + self.mysplit(self.afterKeywordsTranslation, ' ')
        dic["past"]      = self.pastKeywords.split(' ') + self.mysplit(self.pastKeywordsTranslation, ' ')
        dic["future"]    = self.futureKeywords.split(' ') + self.mysplit(self.futureKeywordsTranslation, ' ')
        dic["today"]     = self.todayKeywords.split(' ') + self.mysplit(self.todayKeywordsTranslation, ' ')
        dic["tomorrow"] = self.tomorrowKeywords.split(' ') + self.mysplit(self.tomorrowKeywordsTranslation, ' ')
        dic["nextmonth"] = self.nextmonthKeywords.split(' ') + self.mysplit(self.nextmonthKeywordsTranslation, ' ')
        dic["nodate"]    = self.nodateKeywords.split(' ') + self.mysplit(self.nodateKeywordsTranslation, ' ')
        dic["now"]    = self.nowKeywords.split(' ') + self.mysplit(self.nowKeywordsTranslation, ' ')
        dic["soon"]    = self.soonKeywords.split(' ') + self.mysplit(self.soonKeywordsTranslation, ' ')
        dic["later"]    = self.laterKeywords.split(' ') + self.mysplit(self.laterKeywordsTranslation, ' ')
        dic["late"]    = self.lateKeywords.split(' ') + self.mysplit(self.lateKeywordsTranslation, ' ')
        #dic["temporal"] = dic.get("before") + dic.get("after") + dic.get("past") + \
        #    dic.get("future") + dic.get("today") + dic.get("tomorrow") + dic.get("nodate") + \
        #    dic.get("nextmonth") + dic.get("now") + dic.get("soon") + dic.get("later") + dic.get("late")
        return dic
        
    def buildSearchTokens(self):
        '''
        From the text given on the builder, separate the text, check if its a valid syntax,
        prepares the data for filters and sets flag and error message for a valid search or not 
        '''
        value = True
        union = False
        sequence = -1
        # the OR clausule is discarted for now, until i see a purpose
        #clause = False
        #list for error strings
        errorlist = []
        #reset error message
        self.error = ""
        tempTokens = {}
        #if its empty, is valid but returns
        if self.empty:
            return
        #if the number of " is not pair, the search query is considered invalid
        if (self.text.count('"') % 2) != 0:
            errorlist.append(self.ERROR_QUOTATIONMARK)
            self.error = ''.join(errorlist)
            self.valid = False
            return
        #MISSING
        # - different date formats"
        # - wildcard searches
        match = re.findall(r'(?P<command>(?<=!)\S+(?=\s)?)|(?P<tag>@\S+(?=\s)?)|(?P<task>#.+?#)|(?P<date>[01][0-2][/\.-]?[0-3][0-9][/\.-]\d{4})|(?P<literal>".+?")|(?P<word>(?![!"#@])\S+(?=\s)?)', self.text)
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
                            errorlist.append(self.text)
                            errorlist.append(self.ERROR_ISNOTVALIDSEARCH)
                            self.error = ''.join(errorlist)
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
                            errorlist.append(self.commandNotation)
                            errorlist.append(sets[word])
                            errorlist.append(' ')
                            errorlist.append(self.ERROR_CONSECUTIVENOT)
                            self.error = ''.join(errorlist)
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
                        errorlist.append(self.commandNotation)
                        errorlist.append(sets[word])
                        errorlist.append(self.ERROR_NOTACOMMAND)
                        self.error = ''.join(errorlist)
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
                        errorlist.append(self.ERROR_TAG)
                        errorlist.append(sets[word])
                        self.error = ''.join(errorlist)
                        self.valid = False
                        return
                #if its a task
                elif word == 2:
                    #verifies if the task exists
                    taskStriped = sets[word].strip('#')
                    if(sum(map(lambda x: x.lower() == taskStriped.lower(), self.allTaskTitles))):
                        if 'tasks' not in self.paramsToFilter:
                            self.paramsToFilter['tasks'] = []
                        self.paramsToFilter['tasks'].append((value, taskStriped))
                        if not value:
                            value = True
                        continue
                    else:
                        errorlist.append(self.ERROR_TASK)
                        errorlist.append(sets[word])
                        self.error = ''.join(errorlist)
                        self.valid = False
                        return
                #if its a date
                elif word == 3:
                    print("date: "+str(sets[word]))
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
            errorlist.append(self.text)
            errorlist.append(self.ERROR_ISNOTVALIDSEARCH)
            self.error = ''.join(errorlist)
            self.valid = False
            return
        return True
    
    def applySearch(self):
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
    
    def isValid(self):
        '''
        returns true if the search tokens given are valid
        returns false if the tokens are not yet given or are not compilant with the syntax
        '''
        return self.valid
    
    def isEmpty(self):
        '''
        return True if the search string is ''
        '''
        return self.empty
    
    def returnError(self):
        '''
        Return the error message
        '''
        return self.error
    
    def removeFilters(self):
        """
        Removes all the filters from the tree
        """
        self.oldFilters = self.tree.list_applied_filters()
        self.tree.reset_filters()
        #self.req.add_filter('leaf',self.is_leaf)
        #self.tree.apply_filter('leaf')
    
    def resetToOriginalTree(self):
        """
        re-aplyes the original filters
        """
        for x in self.oldFilters:
            self.tree.apply_filter(x)
            
    def mysplit(self, s, delim=None):
    	"""
    	string split that removes empty strings
    	useful for when there are no translations
    	"""
        return [x for x in s.split(delim) if x]
    
    def getCommands(self):
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
    
    def getParams(self):
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
        s = s + 'valid = ' + str(self.isValid()) + '\n'
        s = s + self.text + "\n"
        return s
    
###############################################################################
# Search Filters
###############################################################################

    def search(self,task,parameters=None):
        """
        Single filter that has all the search parameters
        Should be more efficient than to have multiple filters
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
                if str(task.get_due_date()) not in self.dicKeyword["now"]:
                    return False
            else:
                if str(task.get_due_date()) in self.dicKeyword["now"]:
                    return False
        #check the due date for a soon
        if 'soon' in parameters:
            #if no state is defined, it shows only active tasks
            if 'active' not in parameters and 'done' not in parameters and 'dismissed' not in parameters:
                if task.get_status() != Task.STA_ACTIVE:
                    return False
            if parameters.get('soon'):
                if str(task.get_due_date()) not in self.dicKeyword["soon"]:
                    return False
            else:
                if str(task.get_due_date()) in self.dicKeyword["soon"]:
                    return False
        #check the due date for a later
        if 'later' in parameters:
            #if no state is defined, it shows only active tasks
            if 'active' not in parameters and 'done' not in parameters and 'dismissed' not in parameters:
                if task.get_status() != Task.STA_ACTIVE:
                    return False
            if parameters.get('later'):
                if str(task.get_due_date()) not in self.dicKeyword["later"]:
                    return False
            else:
                if str(task.get_due_date()) in self.dicKeyword["later"]:
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
    
    def active(self,task,parameters=None):
        """ Filter of tasks which are active """
        #FIXME: we should also handle unactive tags
        return task.get_status() == Task.STA_ACTIVE

    def dismissed(self,task,parameters=None):
        """ Filter of tasks which are active """
        #FIXME: we should also handle unactive tags
        return task.get_status() == Task.STA_DISMISSED

    def done(self,task,parameters=None):
        """ Filter of tasks which are active """
        #FIXME: we should also handle unactive tags
        return task.get_status() == Task.STA_DONE

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