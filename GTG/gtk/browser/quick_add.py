# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c)  - The GTG Team
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

"""Functionality for the Quick Add entry."""

import re
from typing import Dict

from gettext import gettext as _

from GTG.core.dates import Date
from GTG.gtk.editor.taskview import TAG_REGEX


TAGS_TOKEN = (
    "tags",
    "tag",
    # Translators: Used in parsing, no spaces, lowercased in code
    _("tags").lower(),
    # Translators: Used in parsing, no spaces, lowercased in code
    _("tag").lower(),
)

START_TOKEN = (
    "defer",
    "start",
    "starts",
    # Translators: Used in parsing, no spaces, lowercased in code
    _("defer").lower(),
    # Translators: Used in parsing, no spaces, lowercased in code
    _("start").lower(),
)

DUE_TOKEN = ("due", _("due").lower())
REPEAT_TOKEN = ("every", _("every").lower())

# Match a word ending in :, followed by a space and some text.
# Examples: "start: monday", "due: friday", "tags: home,pet"
TOKEN_REGEX = re.compile(r'([\s]*)([\w-]+):\s*([^\s]+)')


def parse(text: str) -> Dict:
    """Parse contents of the quick add input."""

    result = {
        'title': '',
        'tags': set(),
        'start': None,
        'due': Date.no_date(),
        'recurring': None
    }

    for match in re.finditer(TAG_REGEX, text):
        data = match.group(0)
        result['tags'].add(data[1:])

    for match in re.finditer(TOKEN_REGEX, text):
        token = match.group(2)
        data = match.group(3)
        matched = False

        if token in TAGS_TOKEN:
            for tag in data.split(','):
                if tag:
                    # Strip @
                    if tag.startswith('@'):
                        tag = tag[1:]

                    result['tags'].add(tag)

            matched = True

        elif token in START_TOKEN:
            try:
                result['start'] = Date.parse(data)
                matched = True
            except ValueError:
                pass

        elif token in DUE_TOKEN:
            try:
                result['due'] = Date.parse(data)
                matched = True
            except ValueError:
                pass

        elif token in REPEAT_TOKEN:
            try:
                Date.today().parse_from_date(data)
                result['recurring'] = data
                matched = True
            except ValueError:
                pass

        # Remove this part from the title
        if matched:
            text = text.replace(match[0], '')

    result['title'] = text
    return result
