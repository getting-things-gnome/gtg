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
Detects urls using regex
"""

import re

# 
UTF_CHARS = ur'a-z0-9_\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u00ff'
# URLs
PRE_CHARS = ur'(?:[^/"\':!=]|^|\:)'
DOMAIN_CHARS = ur'([\.-]|[^\s_\!\.\/])+\.[a-z]{2,}(?::[0-9]+)?'
PATH_CHARS = ur'(?:[\.,]?[%s!\*\'\(\);:=\+\$/%s#\[\]\-_,~@])' % (UTF_CHARS, '%')
QUERY_CHARS = ur'[a-z0-9!\*\'\(\);:&=\+\$/%#\[\]\-_\.,~]'

# Valid end-of-path characters (so /foo. does not gobble the period).
PATH_ENDING_CHARS = r'[%s\)=#/]' % UTF_CHARS
QUERY_ENDING_CHARS = '[a-z0-9_&=#]'

URL_REGEX = re.compile('((%s)((https?://|www\\.)(%s)(\/%s*%s?)?(\?%s*%s)?))'
                       % (PRE_CHARS, DOMAIN_CHARS, PATH_CHARS,
                         PATH_ENDING_CHARS, QUERY_CHARS, QUERY_ENDING_CHARS),
                         re.IGNORECASE)

def match(text):
    return re.match(URL_REGEX,text)
