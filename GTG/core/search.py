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

def search_filter(task, parameters=None):
    """ Check if task satisfies all search parameters """

    if parameters is None:
        return False

    # Check boolean properties
    properties = {
        'now': str(task.get_due_date()) != 'now',
        'soon': str(task.get_due_date()) != 'soon',
        'later': str(task.get_due_date()) != 'later',
        'late': task.get_days_left() > -1 or task.get_days_left() == None,
        'nodate': str(task.get_due_date()) != '',
        'tomorrow': task.get_days_left() != 1,
        'today': task.get_days_left() != 0,
    }

    for name, value in properties.iteritems():
        if name in parameters:
            if parameters[name] == True:
                if not value:
                    return False
            else:
                if value:
                    return False

    # Check if contian values
    def fulltext_search(task, word):
        text = task.get_excerpt(strip_tags=False).lower()
        title = task.get_title().lower()
        return text.find(word) > -1 or word[1] in title

    value_checks = {
        'tasks': lambda t, v: t.get_title().lower() == v,
        'tags': lambda t, v: v in task.get_tags_name(),
        'words': fulltext_search,
        'literals', fulltext_search
    }
    for name, func in value_checks.iteritems():
        neg, value = parameters[name]
        is_ok = func(task, value)
        if neg:
            if is_ok:
                return False
        else:
            if not is_ok:
                return False

    # passing all cirteria
    return True
