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

"""
Search feature for GTG

The first implementation by João Ascenso during GSoC 2011

FIXME: there should go the overal help/short documentation of this feature

FIXME parameters of query => how it should looks like
"""

import re

from GTG import _

# Generate keywords and their possible translations
# They must be listed because of gettext
KEYWORDS = {
  "and": _("and"),
  "not": _("not"),
  "active": _("active"),
  "dismissed": _("dismissed"),
  "done": _("done"),
  "before": _("before"),
  "after": _("after"),
  "past": _("past"),
  "future": _("future"),
  "today": _("today"),
  "tomorrow": _("tomorrow"),
  "nextmonth": _("nextmonth"),
  "nodate": _("nodate"),
  "now": _("now"),
  "soon": _("soon"),
  "later": _("later"),
  "late": _("late"),
}

# transform keywords and their translations into a list of possible commands
for key in KEYWORDS:
    if " " not in KEYWORDS[key] and KEYWORDS[key].lower() != key.lower():
        possible_words = [key.lower(), KEYWORDS[key].lower()]
    else:
        possible_words = [key.lower()]
    KEYWORDS[key] = possible_words

# Generate list of possible commands
search_commands = []
for keyword in KEYWORDS:
    for command in KEYWORDS[keyword]:
        command = '!' + command
        if command not in search_commands:
            search_commands.append(command)

class InvalidQuery(Exception):
    pass

# FIXME MISSING
# - different date formats"
# - wildcard searches
# - parsing list of all tasks? -> why?
TOKENS_RE = re.compile(r"""
            (?P<command>!\S+(?=\s)?) |
            (?P<tag>@\S+(?=\s)?) |
            (?P<task>\#.+?\#) |
            (?P<date>[01][0-2][/\.-]?[0-3][0-9][/\.-]\d{4}) |
            (?P<literal>".+?") | 
            (?P<word>(?![!"#@])\S+(?=\s)?) |
            (?P<space>(\s+))
            """, re.VERBOSE)

def _tokenize_query(query):
    """ Split query into a sequence of tokens (type, value)

    This is inspired by following tokenizer:
    http://stackoverflow.com/a/2359619/99944
    by Matt Anderson
    (it is licensed under CC atribution required)
    """
    pos = 0
    while True:
        m = TOKENS_RE.match(query, pos)
        if not m: 
            break
        pos = m.end()
        token_type = m.lastgroup
        token_value = m.group(token_type)
        if token_type != 'space':
            yield token_type, token_value
    if pos != len(query):
        raise InvalidQuery('tokenizer stopped at pos %r of %r left of "%s"' % (
            pos, len(query), query[pos:pos+10]))

def parse_search_query(query):
    """ Parse query into parameters for search filter

    If query is not correct, exception InvalidQuery is raised.
    """

    if len(query.strip()) == 0:
        raise InvalidQuery("Query is empty")

    if query.count('"') % 2 != 0:
        raise InvalidQuery("Query has odd number of quotes")

# FIXME: value from Joao's code?????
#FIXME why are literals and words differently handled?
    parameters = {
        'tags': [],
        'literals': [],
        'words': []
    }

    for token, value in _tokenize_query(query):
        if token == 'command':
            value = value.lower()[1:]
            found = False
            for keyword in KEYWORDS:
                if value.lower() in KEYWORDS[keyword]:
                    parameters[keyword] = True
                    found = True
                    break
            if not found:
                raise InvalidQuery("Unknown command !%s" % value)

#FIXME MAYBE it would make sense merge 'tags' with 'tag', etc
            #FIXME handle and, not, or: it might be cool!
#FIXME merge those classes!
        elif token == 'tag':
#FIXME (want/dontwant, value)
            parameters['tags'].append((True, value))
        elif token == 'task':
            print "not implemented"
            #FIXME remove tasks
        elif token == 'literal':
#FIXME why lower()? 
            parameters['literals'].append((True, value.strip('"').lower()))
        elif token == 'word':
            parameters['words'].append((True, value.lower()))

    return parameters

# FIXME maybe put filter also there!

# FIXME write down unit test for this
# FIXME +, - keywords? probably not!
    
#FIXME => make it nicer!!!! FIXME
def search_filter(task,parameters=None):
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
