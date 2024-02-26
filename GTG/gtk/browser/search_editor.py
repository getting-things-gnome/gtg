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
This module contains the SearchEditor class which is a window that allows the
user to edit a saved search properties.
"""
from gi.repository import GObject, Gtk, Gdk, GdkPixbuf, GLib

import logging
import random
from gettext import gettext as _
from GTG.gtk.browser import GnomeConfig

log = logging.getLogger(__name__)


@Gtk.Template(filename=GnomeConfig.SEARCH_EDITOR_UI_FILE)
class SearchEditor(Gtk.Dialog):
    """
    A window to edit certain properties of a saved search.
    """

    __gtype_name__ = 'GTG_SearchEditor'
    _emoji_chooser = Gtk.Template.Child('emoji-chooser')
    _icon_button = Gtk.Template.Child('icon-button')
    _name_entry = Gtk.Template.Child('name-entry')

    def __init__(self, app, search=None):
        super().__init__(use_header_bar=1)

        set_icon_shortcut = Gtk.Shortcut.new(
            Gtk.ShortcutTrigger.parse_string("<Control>I"),
            Gtk.CallbackAction.new(self._set_icon))

        self.add_shortcut(set_icon_shortcut)

        self.app = app
        self.search = search

        self.set_transient_for(app.browser)
        self._title_format = self.get_title()
        self._emoji_chooser.set_parent(self._icon_button)

        self.is_valid = True
        self._emoji = None
        self.use_icon = False
        self._search_name = ''

        self.set_search(search)
        self.show()


    @GObject.Property(type=str, default='')
    def search_name(self):
        """The (new) name of the search."""

        return self._search_name

    @search_name.setter
    def search_name(self, value: str):
        self._search_name = value
        self._validate()

    @GObject.Property(type=str, default='')
    def search_query(self):
        """The (new) name of the search."""

        return self._search_query

    @search_query.setter
    def search_query(self, value: str):
        self._search_query = value
        self._validate()

    @GObject.Property(type=bool, default=True)
    def is_valid(self):
        """
        Whenever it is valid to apply the changes (like malformed search name).
        """

        return self._is_valid

    @is_valid.setter
    def is_valid(self, value: bool):
        self._is_valid = value

    @GObject.Property(type=bool, default=False)
    def has_icon(self):
        """
        Whenever the search will have an icon.
        """

        return bool(self._emoji)

    def _validate(self):
        """
        Validates the current search preferences.
        Returns true whenever it passes validation, False otherwise,
        and modifies the is_valid property appropriately.
        On failure, the widgets are modified accordingly to show the user
        why it doesn't accept it.
        """

        valid = True
        valid &= self._validate_search_name()
        self.is_valid = valid
        return valid

    def _validate_search_name(self):
        """
        Validates the current search name.
        Returns true whenever it passes validation, False otherwise.
        On failure, the widgets are modified accordingly to show the user
        why it doesn't accept it.
        """

        if self.search_name == '':
            self._name_entry.add_css_class("error")
            self._name_entry.props.tooltip_text = \
                _("search name can not be empty")
            return False
        else:
            self._name_entry.remove_css_class("error")
            self._name_entry.props.tooltip_text = ""
            return True

    def set_search(self, search):
        """
        Set the search to edit.
        Widgets are updated with the information of the search,
        the previous information/state is lost.
        """
        self.search = search
        if search is None:
            return

        icon = search.icon
        self._set_emoji(self._emoji_chooser, text=icon if icon else '')

        self.search_name = search.name
        self.search_query = search.query
        self.set_title(self._title_format % self.search_name)


    def do_destroy(self):

        self.app.close_search_editor()
        super().destroy()

    def _cancel(self):
        """
        Cancel button has been clicked, closing the editor window without
        applying changes.
        """

        self.destroy()

    def _apply(self):
        """
        Apply button has been clicked, applying the settings and closing the
        editor window.
        """
        if self.search is None:
            log.warning("Trying to apply but no search set, shouldn't happen")
            self._cancel()
            return

        if self.has_icon and self._emoji:
            self.search.icon = self._emoji
        elif self.has_icon:  # Should never happen, but just in case
            log.warning("Tried to set icon for %r but no icon given",
                        self.search.name)
            self.search.icon = None
        else:
            self.search.icon = None

        if self.search_name != self.search.name:
            log.debug("Renaming %r → %r", self.search.name, self.search_name)
            self.search.name = self.search_name

        self.app.ds.saved_searches.model.emit('items-changed', 0, 0, 0)
        self.destroy()

    # CALLBACKS #####
    @Gtk.Template.Callback('response')
    def _response(self, widget: GObject.Object, response: Gtk.ResponseType):
        if response == Gtk.ResponseType.APPLY:
            self._apply()
        else:
            self._cancel()


    @Gtk.Template.Callback('set_icon')
    def _set_icon(self, widget: GObject.Object, shargs: GLib.Variant = None):
        """
        Button to set the icon/emoji has been clicked.
        """
        self._emoji_chooser.popup()

    @Gtk.Template.Callback('emoji_set')
    def _set_emoji(self, widget: GObject.Object, text: str = None):
        """
        Callback when an emoji has been inserted.
        """
        self._emoji = text if text else None

        if text:
            self._emoji = text
            self._icon_button.set_label(text)
            if label := self._icon_button.get_child():
                label.set_opacity(1)
        else:
            self._emoji = None
            self._icon_button.set_label('🏷️')
            if label := self._icon_button.get_child():
                label.set_opacity(0.4)

        self.notify('has-icon')

    @Gtk.Template.Callback('remove_icon')
    def _remove_icon(self, widget: GObject.Object):
        """
        Callback to remove the icon.
        """

        self._set_emoji(self._emoji_chooser, text='')
