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

"""
Search feature for GTG

Created by:
  - João Ascenso, GSoC 2011
  - Izidor Matušov, Jan/Feb 2012

You can search by entring a query in a simple language. Function
parse_search_query() parse the query and return internal representation which
is used for filtering in search_filter() function. If the query is malformed,
the exception InvalidQuery is raised.

The query language consists of several elements:
  - commands
    - !not <elem> -- the next element will be negated
    - <elem> !or <elem> -- return True if at least on of elements is true
    - !after <date> -- show tasks which could be done after this date
    - !before <date> -- show tasks which must be done before this date
    - !today -- show tasks with due_date == today
    - !tomorrow -- show tasks with due_date == tomorrow
    - !nodate -- show tasks without due_date
    - !now -- show tasks with due_date == now
    - !soon -- show tasks with due_date == soon
    - !someday -- show tasks with due_date == someday
    - !notag -- show tasks without tags
  - tags -- show tasks with this tag
  - word -- show tasks which contains this word
  - "literal" -- basically the same as word but allows the space and special
        characters inside. Literal must be inside "quotes".
  - date -- date which could be parsed with Date.parse()

Elements are supposed to be in conjuction, i.e. they are interpreted as::
  E1 AND E2 AND E3 AND E4 AND ( E5 OR E6 OR E7 ) AND E8 ...

Examples of queries:
'!tomorrow !or !today' => show tasks which are today or tomorrow
'@gtg @writing' => show tasks with both of the tags @gtg, @writing
'@gtg !before 2012-03-01' => show GTG tasks with due_date before March 1
'buy @errands' => show errands where I have to buy something
'!not buy @errands' => show errands without keyword buy
'!after "next month"' => show tasks after this month


search_filter() expect parameter 'q' which is a list of commands in the form
(name_of_command, should_be_positive, arguments). If::
  should_be_positive == True => task has to satisfy this command
  should_be_positive == False => task must not satisfy this command

A special command is "or" which contains subcommands and returns Ture if
at least one subcommand returns True.

search_filter() could be easily plugged in Liblarch and filter only suitable
tasks.

For more information see unittests:
  - GTG/tests/test_search_query.py -- parsing query
  - GTG/tests/test_search_filter.py -- filtering a task
"""

import re

from GTG import _
from GTG.tools.dates import Date

# Generate keywords and their possible translations
# They must be listed because of gettext
KEYWORDS = {
    "not": _("not"),
    "or": _("or"),
    "after": _("after"),
    "before": _("before"),
    "today": _("today"),
    "tomorrow": _("tomorrow"),
    "nodate": _("nodate"),
    "now": _("now"),
    "soon": _("soon"),
    "someday": _("someday"),
    "notag": _("notag"),
}

# transform keywords and their translations into a list of possible commands
for key in KEYWORDS:
    if " " not in KEYWORDS[key] and KEYWORDS[key].lower() != key.lower():
        possible_words = [key.lower(), KEYWORDS[key].lower()]
    else:
        possible_words = [key.lower()]
    KEYWORDS[key] = possible_words

# Generate list of possible commands
SEARCH_COMMANDS = []
for key in KEYWORDS:
    for key_command in KEYWORDS[key]:
        key_command = '!' + key_command
        if key_command not in SEARCH_COMMANDS:
            SEARCH_COMMANDS.append(key_command)


class InvalidQuery(Exception):
    """ Exception which is raised during parsing of
    search query if it is invalid """
    pass

TOKENS_RE = re.compile(r"""
            (?P<command>!\S+(?=\s)?) |
            (?P<tag>@\S+(?=\s)?) |
            (?P<date>\d{4}-\d{2}-\d{2}|\d{8}|\d{4}) |
            (?P<literal>".+?") |
            (?P<word>(?![!"@])\S+(?=\s)?) |
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
        match = TOKENS_RE.match(query, pos)
        if not match:
            break
        pos = match.end()
        token_type = match.lastgroup
        token_value = match.group(token_type)
        if token_type != 'space':
            yield token_type, token_value
    if pos != len(query):
        raise InvalidQuery('tokenizer stopped at pos %r of %r left of "%s"' % (
            pos, len(query), query[pos:pos + 10]))


def parse_search_query(query):
    """ Parse query into parameters for search filter

    If query is not correct, exception InvalidQuery is raised.
    """

    if len(query.strip()) == 0:
        raise InvalidQuery("Query is empty")

    if query.count('"') % 2 != 0:
        raise InvalidQuery("Query has odd number of quotes")

    commands = []

    not_count, after_or = 0, False
    require_date = None
    for token, value in _tokenize_query(query):
        cmd = None

        if require_date:
            if token not in ['date', 'word', 'literal']:
                raise InvalidQuery("Unexpected token '%s' after '%s'" % (
                    token, require_date))

            value = value.strip('"')
            try:
                date = Date.parse(value)
            except ValueError:
                raise InvalidQuery("Date '%s' in wrong format" % (value))

            cmd = (require_date, not_count % 2 == 0, date)
            require_date = None

        elif token == 'command':
            value = value.lower()[1:]

            found = False
            for keyword in KEYWORDS:
                if value not in KEYWORDS[keyword]:
                    continue

                if keyword == 'not':
                    not_count += 1
                elif keyword == 'or':
                    if not_count > 0:
                        raise InvalidQuery("!or cann't follow !not")

                    if commands == []:
                        raise InvalidQuery(
                            "Or is not allowed at the beginning of query")

                    if commands[-1][0] != "or":
                        commands.append(("or", True, [commands.pop()]))

                    after_or = True
                elif keyword in ['after', 'before']:
                    require_date = keyword
                else:
                    cmd = (keyword, not_count % 2 == 0)
                found = True
                break
            if not found:
                raise InvalidQuery("Unknown command !%s" % value)

        elif token == 'tag':
            cmd = (token, not_count % 2 == 0, value)
        elif token in ['literal', 'word']:
            cmd = ('word', not_count % 2 == 0, value.strip('"').lower())

        if cmd is not None:
            if after_or:
                commands[-1][2].append(cmd)
            else:
                commands.append(cmd)

            not_count, after_or = 0, False

    if not_count > 0:
        raise InvalidQuery("Query cannot end with !not (Forgot something?)")

    if after_or:
        raise InvalidQuery("Or is not allowed at the end of query")

    if require_date:
        raise InvalidQuery("Required date after '%s'" % require_date)

    return {'q': commands}


def search_filter(task, parameters=None):
    """ Check if task satisfies all search parameters """

    if parameters is None or 'q' not in parameters:
        return False

    def check_commands(commands_list):
        """ Execute search commands

        This method is recursive for !or and !and """

        def fulltext_search(task, word):
            """ check if task contains the word """
            word = word.lower()
            text = task.get_excerpt(strip_tags=False).lower()
            title = task.get_title().lower()

            return word in text or word in title

        value_checks = {
            'after': lambda t, v: task.get_due_date() > v,
            'before': lambda t, v: task.get_due_date() < v,
            'tag': lambda t, v: v in task.get_tags_name(),
            'word': fulltext_search,
            'today': lambda task, v: task.get_due_date() == Date.today(),
            'tomorrow': lambda task, v: task.get_due_date() == Date.tomorrow(),
            'nodate': lambda task, v: task.get_due_date() == Date.no_date(),
            'now': lambda task, v: task.get_due_date() == Date.now(),
            'soon': lambda task, v: task.get_due_date() == Date.soon(),
            'someday': lambda task, v: task.get_due_date() == Date.someday(),
            'notag': lambda task, v: task.get_tags() == [],
        }

        for command in commands_list:
            cmd, positive, args = command[0], command[1], command[2:]
            result = False

            if cmd == 'or':
                for sub_cmd in args[0]:
                    if check_commands([sub_cmd]):
                        result = True
                        break
            elif value_checks.get(cmd, None):
                if len(args) > 0:
                    args = args[0]
                result = value_checks[cmd](task, args)

            if (positive and not result) or (not positive and result):
                return False

        return True

    return check_commands(parameters['q'])
