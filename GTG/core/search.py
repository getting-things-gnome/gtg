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
#_ = lambda s: s

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
    possible_words = key.lower().split() + KEYWORDS[key].lower().split()
    possible_words = [word for word in possible_words if word != ""]
    possible_words = list(set(possible_words))
    KEYWORDS[key] = possible_words

# FIXME
search_commands = []
for keyword in KEYWORDS:
    for command in KEYWORDS[keyword]:
        command = '!' + command
        if command not in search_commands:
            search_commands.append(command)

print "commands", search_commands

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

#FIXME rename => parse_search_query()
def parse_query(query):
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

if __name__ == "__main__":
    for query in ["my simple @not query"]:
        print parse_query(query)
