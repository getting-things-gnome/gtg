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
tag_context_menu:
Implements a context (pop-up) menu for the tag item in the sidebar.
Right now it is just a void shell It is supposed to become a more generic
sidebar context for all kind of item displayed there.
Also, it is supposed to handle more complex menus (with non-std widgets,
like a color picker)
"""

from gi.repository import Gtk, Gio

from gettext import gettext as _
from GTG.gtk.colors import generate_tag_color, color_add, color_remove
from GTG.gtk.browser import GnomeConfig


class TagContextMenu(Gtk.PopoverMenu):
    """Context menu fo the tag i the sidebar"""

    def __init__(self, ds, app, tag):
        super().__init__(has_arrow=False)
        self.tag = tag
        self.app = app
        self.ds = ds

        actions = [
            ("edit_tag", self.on_mi_cc_activate),
            ("generate_tag_color", self.on_mi_ctag_activate),
            ("delete_tag", lambda w, a, p : self.app.browser.on_delete_tag_activate([self.tag]))
        ]

        for action_disc in actions:
            self.install_action(
                ".".join(["tags_popup", action_disc[0]]), None, action_disc[1])

        # Build up the menu
        self.build_menu()


    def build_menu(self):
        """Build up the widget"""
        if self.tag:
            menu_builder = Gtk.Builder()
            menu_builder.add_from_file(GnomeConfig.MENUS_UI_FILE)
            menu_model = menu_builder.get_object("tag_context_menu")
            self.mi_del_tag = Gio.MenuItem.new(_("Delete"), "tags_popup.delete_tag")
            menu_model.append_item(self.mi_del_tag)

            self.set_menu_model(menu_model)


    # CALLBACKS ###############################################################
    def on_mi_cc_activate(self, widget, action_name, param):
        """Callback: show the tag editor upon request"""

        self.app.open_tag_editor(self.tag)


    def on_mi_ctag_activate(self, widget, action_name, param):

        self.tag.color = self.ds.tags.generate_color()
        self.ds.notify_tag_change(self.tag)


class SearchesContextMenu(Gtk.PopoverMenu):
    """Context menu fo the tag i the sidebar"""

    def __init__(self, ds, app, search):
        super().__init__(has_arrow=False)
        self.search = search
        self.app = app
        self.ds = ds

        actions = [
            ("edit_search", lambda w, a, p: app.open_search_editor(search)),
            ("delete_search", lambda w, a, p : ds.saved_searches.remove(self.search.id))
        ]

        for action_disc in actions:
            self.install_action(
                ".".join(["search_popup", action_disc[0]]), None, action_disc[1])

        # Build up the menu
        self.build_menu()


    def build_menu(self):
        """Build up the widget"""

        menu_builder = Gtk.Builder()
        menu_builder.add_from_file(GnomeConfig.MENUS_UI_FILE)
        menu_model = menu_builder.get_object("search_context_menu")

        self.set_menu_model(menu_model)


    # CALLBACKS ###############################################################
    def on_mi_cc_activate(self, widget, action_name, param):
        """Callback: show the tag editor upon request"""

        # self.app.open_tag_editor(self.tag)