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

import re


def extract_tags_from_text(text):
    """ Given a string, returns a list of the @tags contained in that """
    return re.findall(r'(?:^|[\s])(@[\w\/\.\-\:]*\w)', text)


def parse_tag_list(text):
    """ Parse a line of a list of tasks. User can specify if the tag is
    positive or not by prepending '!'.

    @param  text:  string entry from user
    @return: list of tupples (tag, is_positive)
    """
    result = []
    for tag in text.split():
        if tag.startswith('!'):
            tag = tag[1:]
            is_positive = False
        else:
            is_positive = True

        if not tag.startswith('@'):
            tag = "@" + tag

        result.append((tag, is_positive))
    return result
