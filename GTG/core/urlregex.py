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
Detects urls using regex

Based on
https://dev.twitter.com/docs/tco-url-wrapper/how-twitter-wrap-urls
"""

import re

UTF_CHARS = r'a-z0-9_\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u00ff'

SUBST_DICT = {
    "domain": r'([\.-]|[^\s_\!\.\/])+\.[a-z]+(?::[0-9]+)?',
    "path": r'(?:[\.,]?[%s!\*\'\(\);:&=\+\$/%s#\[\]\-_,~@])' % (
        UTF_CHARS, '%'),
    "query": r'[a-z0-9!\*\'\(\);:&=\+\$/%#\[\]\-_\.,~]',
    # Valid end-of-path characters (so /foo. does not gobble the period).
    "path_end": r'[%s\)=#/]' % UTF_CHARS,
    "query_end": '[a-z0-9_&=#]',
}

HTTP_URI = r'(((https?://|www\\.)(%(domain)s)(\/%(path)s*' \
    r'%(path_end)s?)?(\?%(query)s*%(query_end)s)?))' % SUBST_DICT
FILE_URI = f"(file:///({SUBST_DICT['path']}*{SUBST_DICT['path_end']}?)?)"

URL_REGEX = re.compile(f'{HTTP_URI}|{FILE_URI}', re.IGNORECASE)


def match(text):
    return re.match(URL_REGEX, text)


def search(text):
    return re.finditer(URL_REGEX, text)
