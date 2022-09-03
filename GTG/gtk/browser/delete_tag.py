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
from GTG.core.tasks2 import Filter

from gettext import gettext as _, ngettext


class DeleteTagsDialog:

    MAXIMUM_TAGS_TO_SHOW = 5

    def __init__(self, browser):
        self.browser = browser
        self.tags_todelete = []

    def on_delete_confirm(self):
        """if we pass a tid as a parameter, we delete directly
        otherwise, we will look which tid is selected"""

        for tag in self.tags_todelete:
            tasks = self.browser.app.ds.tasks.filter(Filter.TAG, tag)

            for t in tasks:
                t.remove_tag(tag.name)

            self.browser.app.ds.tags.remove(tag.id)

        self.browser.app.ds.tasks.notify('task_count_no_tags')
        self.tags_todelete = []

    def on_response(self, dialog, response, tagslist, callback):
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            self.on_delete_confirm()
        elif response == Gtk.ResponseType.REJECT:
            tagslist = []

        if callback:
            callback(tagslist)

    def show(self, tags=None, callback=None):
        self.tags_todelete = tags or self.tags_todelete

        if not self.tags_todelete:
            # We must at least have something to delete !
            return []

        # Prepare labels
        singular = len(self.tags_todelete)

        cancel_text = ngettext("Keep selected tag", "Keep selected tags", singular)

        delete_text = ngettext("Permanently remove tag", "Permanently remove tags", singular)

        label_text = ngettext("Deleting a tag cannot be undone, "
                              "and will delete the tag shown below. Tasks containing this tag will not be deleted: ",
                              "Deleting a tag cannot be undone, "
                              "and will delete the tag shown below. Tasks containing this tag will not be deleted:",
                              singular)

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

        if len(tagslist) == 1:
            # Don't show a bulleted list if there's only one item
            titles = "".join(tag.name for tag in tagslist)
        else:
            titles = "".join("\n• " + tag.name for tag in tagslist)

        # Build and run dialog
        dialog = Gtk.MessageDialog(transient_for=self.browser, modal=True)
        dialog.add_button(cancel_text, Gtk.ResponseType.CANCEL)

        delete_btn = dialog.add_button(delete_text, Gtk.ResponseType.YES)
        delete_btn.add_css_class("destructive-action")

        dialog.props.use_markup = True
        # Decrease size of title to workaround not being able to put two texts in GTK4
        dialog.props.text = "<span size=\"small\" weight=\"bold\">" + label_text + "</span>"

        dialog.props.secondary_text = titles + titles_suffix

        dialog.connect("response", self.on_response, tagslist, callback)
        dialog.present()
