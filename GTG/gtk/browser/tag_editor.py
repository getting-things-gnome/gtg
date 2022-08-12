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
This module contains the TagEditor class which is a window that allows the
user to edit a tag properties.
"""
from gi.repository import GObject, Gtk, Gdk, GdkPixbuf, GLib

import logging
import random
from gettext import gettext as _
from GTG.gtk.colors import color_add, color_remove, RGBA, rgb_to_hex, random_color
from GTG.gtk.browser import GnomeConfig

log = logging.getLogger(__name__)


@Gtk.Template(filename=GnomeConfig.TAG_EDITOR_UI_FILE)
class TagEditor(Gtk.Dialog):
    """
    A window to edit certain properties of an tag.
    """

    __gtype_name__ = 'GTG_TagEditor'
    _emoji_chooser = Gtk.Template.Child('emoji-chooser')
    _icon_button = Gtk.Template.Child('icon-button')
    _name_entry = Gtk.Template.Child('name-entry')

    def __init__(self, req, app, tag=None):
        super().__init__(use_header_bar=1)

        set_icon_shortcut = Gtk.Shortcut.new(
            Gtk.ShortcutTrigger.parse_string("<Control>I"),
            Gtk.CallbackAction.new(self._set_icon))

        self.add_shortcut(set_icon_shortcut)

        self.req = req
        self.app = app
        self.tag = tag

        self.set_transient_for(app.browser)
        self._title_format = self.get_title()
        self._emoji_chooser.set_parent(self._icon_button)

        self.tag_rgba = Gdk.RGBA()
        (self.tag_rgba.red, self.tag_rgba.green,
         self.tag_rgba.blue, self.tag_rgba.alpha) = 1.0, 1.0, 1.0, 1.0
        self.tag_name = ''
        self.tag_is_actionable = True
        self.is_valid = True
        self._emoji = None
        self.use_icon = False

        self.set_tag(tag)
        self.show()

    @GObject.Property(type=bool, default=False)
    def has_color(self):
        """Whenever the tag has a color."""

        return self._has_color

    @has_color.setter
    def has_color(self, value: bool):

        self._has_color = value

    @GObject.Property(type=Gdk.RGBA)
    def tag_rgba(self):
        """The color of the tag. Alpha is ignored."""

        return self._tag_rgba

    @tag_rgba.setter
    def tag_rgba(self, value: Gdk.RGBA):

        self._tag_rgba = value

    @GObject.Property(type=str, default='')
    def tag_name(self):
        """The (new) name of the tag."""

        return self._tag_name

    @tag_name.setter
    def tag_name(self, value: str):
        self._tag_name = value.strip().replace(' ', '')
        self._validate()

    @GObject.Property(type=bool, default=False)
    def tag_is_actionable(self):
        """
        Whenever the tag should show up in the actionable tab.
        """

        return self._tag_is_actionable

    @tag_is_actionable.setter
    def tag_is_actionable(self, value: bool):
        self._tag_is_actionable = value

    @GObject.Property(type=bool, default=True)
    def is_valid(self):
        """
        Whenever it is valid to apply the changes (like malformed tag name).
        """

        return self._is_valid

    @is_valid.setter
    def is_valid(self, value: bool):
        self._is_valid = value

    @GObject.Property(type=bool, default=False)
    def has_icon(self):
        """
        Whenever the tag will have an icon.
        """

        return bool(self._emoji)

    def _validate(self):
        """
        Validates the current tag preferences.
        Returns true whenever it passes validation, False otherwise,
        and modifies the is_valid property appropriately.
        On failure, the widgets are modified accordingly to show the user
        why it doesn't accept it.
        """

        valid = True
        valid &= self._validate_tag_name()
        self.is_valid = valid
        return valid

    def _validate_tag_name(self):
        """
        Validates the current tag name.
        Returns true whenever it passes validation, False otherwise.
        On failure, the widgets are modified accordingly to show the user
        why it doesn't accept it.
        """

        if self.tag_name == '':
            self._name_entry.add_css_class("error")
            self._name_entry.props.tooltip_text = \
                _("Tag name can not be empty")
            return False
        else:
            self._name_entry.remove_css_class("error")
            self._name_entry.props.tooltip_text = ""
            return True

    def set_tag(self, tag):
        """
        Set the tag to edit.
        Widgets are updated with the information of the tag,
        the previous information/state is lost.
        """
        self.tag = tag
        if tag is None:
            return

        icon = tag.icon
        self._set_emoji(self._emoji_chooser, text=icon if icon else '')

        self.tag_name = tag.name
        self.set_title(self._title_format % ('@' + self.tag_name,))

        rgba = Gdk.RGBA()
        rgba.red, rgba.green, rgba.blue, rgba.alpha = 1.0, 1.0, 1.0, 1.0

        if color := tag.color:
            if not rgba.parse(color):
                log.warning("Failed to parse tag color for %r: %r",
                            tag.name, color)

        self.has_color = bool(color)
        self.tag_rgba = rgba
        self.tag_is_actionable = self.tag.actionable

    def do_destroy(self):

        self.app.close_tag_editor()
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
        if self.tag is None:
            log.warning("Trying to apply but no tag set, shouldn't happen")
            self._cancel()
            return

        if self.has_icon and self._emoji:
            self.tag.icon = self._emoji
        elif self.has_icon:  # Should never happen, but just in case
            log.warning("Tried to set icon for %r but no icon given",
                        self.tag.name)
            self.tag.icon = None
        else:
            self.tag.icon = None

        if self.has_color:
            color = rgb_to_hex(self.tag_rgba)
            color_add(color)
            self.tag.color = color
        else:
            if tag_color := self.tag.color:
                color_remove(tag_color)

            self.tag.color = None

        self.tag.actionable = self.tag_is_actionable

        if self.tag_name != self.tag.name:
            log.debug("Renaming %r → %r", self.tag.name, self.tag_name)

            for t in self.app.ds.tasks.lookup.values():
                t.rename_tag(self.tag.name, self.tag_name)
                
            self.tag.name = self.tag_name

        self.app.ds.notify_tag_change(self.tag)
        self.destroy()

    # CALLBACKS #####
    @Gtk.Template.Callback('response')
    def _response(self, widget: GObject.Object, response: Gtk.ResponseType):
        if response == Gtk.ResponseType.APPLY:
            self._apply()
        else:
            self._cancel()

    @Gtk.Template.Callback('random_color')
    def _random_color(self, widget: GObject.Object):
        """
        The random color button has been clicked, overriding the color
        with an random color.
        """
        self.has_color = True
        color = self.app.ds.tags.generate_color()
        c = Gdk.RGBA()
        c.red, c.green, c.blue, c.alpha = 1.0, 1.0, 1.0, 1.0
        c.parse('#' + color)
        self.tag_rgba = c
        
    @Gtk.Template.Callback('activate_color')
    def _activate_color(self, widget: GObject.Object):
        """
        Enable using the selected color because a color has been selected.
        """

        self.has_color = True

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

    @Gtk.Template.Callback('remove_color')
    def _remove_color(self, widget: GObject.Object):
        """
        Callback to remove the color.
        """

        c = Gdk.RGBA()
        c.red, c.green, c.blue, c.alpha = 1.0, 1.0, 1.0, 1.0
        self.tag_rgba = c
        self.has_color = False
