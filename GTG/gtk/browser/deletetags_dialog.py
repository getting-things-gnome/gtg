# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2014-2015 - Sagar Ghuge
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

from GTG.core.translations import _, ngettext
from GTG.gtk.browser import GnomeConfig


class DeleteTagsDialog():

    MAXIMUM_TAGS_TO_SHOW = 5

    def __init__(self, req, browser):
        self.req = req
        self.browser = browser
        self.tags_todelete = []
        self.builder = Gtk.Builder()
        self.builder.add_from_file(GnomeConfig.DELETETAGS_UI_FILE)
        signals = {
            "on_delete_confirm": self.browser.on_delete_tag,
            "on_delete_cancel": lambda x: x.hide, }
        self.builder.connect_signals(signals)

    def delete_tags(self, tags=None):
        if tags:
            self.tags_todelete = tags
        # We must at least have something to delete !
        if len(self.tags_todelete) > 0:

            # We fill the text and the buttons' labels according to the number
            # of tags to delete
            label = self.builder.get_object("label1")
            label_text = label.get_text()
            cdlabel2 = self.builder.get_object("cd-label2")
            cdlabel3 = self.builder.get_object("cd-label3")
            cdlabel4 = self.builder.get_object("cd-label4")
            singular = len(self.tags_todelete)
            label_text = ngettext("Deleting a tag cannot be undone, "
                                  "and will delete the following tag: ",
                                  "Deleting a tag cannot be undone, "
                                  "and will delete the following tag: ",
                                  singular)
            cdlabel2.set_label(ngettext("Are you sure you want to delete this"
                                        " tag?",
                                        "Are you sure you want to delete "
                                        "these tags?",
                                        singular))

            cdlabel3.set_label(ngettext("Keep selected tag",
                                        "Keep selected tags",
                                        singular))
            cdlabel4.set_label(ngettext("Permanently remove tag",
                                        "Permanently remove tags",
                                        singular))
            label_text = label_text[0:label_text.find(":") + 1]

            # we don't want to end with just one task that doesn't fit the
            # screen and a line saying "And one more task", so we go a
            # little over our limit
            tags_count = len(self.tags_todelete)
            missing_tags_count = tags_count - self.MAXIMUM_TAGS_TO_SHOW
            if missing_tags_count >= 2:
                tagslist = self.tags_todelete[:self.MAXIMUM_TAGS_TO_SHOW]
                titles_suffix = _("\nAnd %d more tags") % missing_tags_count
            else:
                tagslist = self.tags_todelete
                titles_suffix = ""

            titles = "".join("\n - " + tag for tag in tagslist)
            label.set_text(label_text + titles + titles_suffix)
            delete_dialog = self.builder.get_object("confirm_delete_tag")
            delete_dialog.resize(1, 1)
            cancel_button = self.builder.get_object("cancel")
            cancel_button.grab_focus()
            if delete_dialog.run() != 1:
                self.tags_todelete = []
            delete_dialog.hide()
            return tagslist
        else:
            return []
