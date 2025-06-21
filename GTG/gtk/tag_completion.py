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

from gi.repository import Gtk
import unicodedata

FILTER_NAME = '@@TagCompletion'


def tag_filter(tag, parameters=None):
    """ Show only regular tags which has some active tasks or the user has
    changed an attribute (e.g. color, workview) => only important tags """

    has_attributes = len(tag.get_all_attributes(butname=True)) > 0
    return has_attributes or tag.get_active_tasks_count() > 0


def normalize_unicode(string):
    """ Unicode characters with diacritic could have more than just one
    representation. We force them to be in just one of them."""
    return unicodedata.normalize('NFC', str(string))


def tag_match(completion, key, iterator, column):
    """ Does key match an item in the list?

    Don't match any item if only artefacts (!, @) are inserted
    (don't show all tags) """

    key = key.lower().lstrip()
    if key in ['', '!', '@', '!@']:
        return False

    text = completion.get_model().get_value(iterator, column)
    text = normalize_unicode(text.lower())

    return text.startswith(key)


class TagCompletion(Gtk.EntryCompletion):
    """ Tag completion which allows to enter 4 representation of a '@tag':
       ['@tag', '!@tag', 'tag', '!tag']

       The user can choose wheter write tag with or without '@',
       with or without '!' which is used for negation."""

    def __init__(self, tagstore):
        """ Initialize entry completion"""
        super().__init__()

        self.tagstore = tagstore
        self.tags = Gtk.ListStore(str)

        self.set_model(self.tags)
        self.set_text_column(0)
        self.set_match_func(tag_match, 0)
        self.set_inline_completion(True)
        self.set_inline_selection(True)
        self.set_popup_single_match(False)

        for opt in sorted(self._get_all_completion_options()):
            self.tags.append((opt,))


    def _get_all_completion_options(self) -> list[str]:
        options = []
        for tag in self.tagstore.lookup.values():
            tname = normalize_unicode(tag.name)
            options.append('@'+tname)
            options.append('!@'+tname)
            options.append(tname)
            options.append('!'+tname)
        return options


    def _try_insert(self, name):
        """ Insert an item into ListStore if it is not already there.
        It keeps the list sorted. """

        position = 0
        for position, row in enumerate(self.tags, 1):
            if row[0] == name:
                # already there
                return
            elif row[0] > name:
                position -= 1
                break

        self.tags.insert(position, (name, ))


    def _on_tag_added(self, tag):
        """ Add all variants of tag """

        tag = normalize_unicode(tag)
        self._try_insert(tag)
        self._try_insert('!' + tag)
        self._try_insert(tag[1:])
        self._try_insert('!' + tag[1:])


    def _try_delete(self, name):
        """ Delete an item if it is in the list """

        for row in self.tags:
            if row[0] == name:
                self.tags.remove(row.iter)
                break


    def _on_tag_deleted(self, tag, path):
        """ Delete all variants of tag """

        tag = normalize_unicode(tag)
        self._try_delete(tag)
        self._try_delete('!' + tag)
        self._try_delete(tag[1:])
        self._try_delete('!' + tag[1:])
