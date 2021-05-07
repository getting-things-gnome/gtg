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
from gi.repository import GObject, Gtk, Gdk, GdkPixbuf

import logging
import random
from gettext import gettext as _
from GTG.gtk.colors import color_add, color_remove
from GTG.gtk.browser import GnomeConfig

log = logging.getLogger(__name__)

class TagEditor(Gtk.Window):
    """
    A window to edit certain properties of an tag.
    """

    def __init__(self, req, app, tag=None):
        super().__init__()

        self.req = req
        self.app = app
        self.tag = tag

        self._builder = Gtk.Builder.new_from_file(GnomeConfig.TAG_EDITOR_UI_FILE)
        self.set_titlebar(self._builder.get_object('headerbar'))
        self.add(self._builder.get_object('main'))
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_position(Gtk.WindowPosition.CENTER)
        # self.set_border_width(10)
        self.set_resizable(True)
        self.set_default(self._builder.get_object('apply'))
        self._title_format = self.get_title()

        self._emoji_entry = self._builder.get_object('emoji-entry')
        self._icon_button = self._builder.get_object('icon-button')
        self._name_entry = self._builder.get_object('name-entry')
        self.bind_property('use_color',
                           self._builder.get_object('color-switch'),
                           'active',
                           GObject.BindingFlags.BIDIRECTIONAL)
        self.bind_property('tag_rgba',
                           self._builder.get_object('color-button'),
                           'rgba',
                           GObject.BindingFlags.BIDIRECTIONAL)
        self.bind_property('tag_is_actionable',
                           self._builder.get_object('actionable-switch'),
                           'active',
                           GObject.BindingFlags.BIDIRECTIONAL)
        self.bind_property('is_valid',
                           self._builder.get_object('apply'),
                           'sensitive',
                           0)
        self.bind_property('has_icon',
                           self._builder.get_object('remove-icon'),
                           'sensitive',
                           0)
        self.bind_property('tag_name', self._name_entry, 'text',
                           GObject.BindingFlags.BIDIRECTIONAL)

        self.tag_rgba = Gdk.RGBA(1.0, 1.0, 1.0, 1.0)
        self.use_color = False
        self.tag_name = ''
        self.tag_is_actionable = True
        self.is_valid = True

        self._builder.connect_signals({
            'cancel': self._cancel,
            'apply': self._apply,
            'activate_color': self._activate_color,
            'random_color': self._random_color,
            'set_icon': self._set_icon,
            'remove_icon': self._remove_icon,
        })
        self._emoji_entry_changed_id = self._emoji_entry.connect(
            'changed', self._set_emoji)

        accelGroup = Gtk.AccelGroup()
        self.add_accel_group(accelGroup)
        accelGroup.connect(*Gtk.accelerator_parse('Escape'),
                           Gtk.AccelFlags.VISIBLE, self._on_escape)

        self.set_tag(tag)
        self.show_all()

    @GObject.Property(type=bool, default=False)
    def use_color(self):
        """Whenever it should use and save the specified color."""
        return self._use_color

    @use_color.setter
    def use_color(self, value: bool):
        self._use_color = value

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
        self._validate_tag_name()

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

    def _reset_emoji_entry(self):
        """
        The emoji entry should stay clear in order to function properly.
        When something is being inserted, then it should be cleared after
        either starting editing a new tag, selected one, or otherwise changed.
        """
        with GObject.signal_handler_block(self._emoji_entry,
                                          self._emoji_entry_changed_id):
            self._emoji_entry.set_text('')

    def _validate_tag_name(self):
        """
        Validates the current tag name.
        Returns true whenever it passes validation, False otherwise.
        On failure, the widgets are modified accordingly to show the user
        why it doesn't accept it.
        """
        # TODO: Possibly add more restrictions.
        if self.tag_name == '':
            self._name_entry.set_icon_from_icon_name(
                Gtk.EntryIconPosition.SECONDARY, Gtk.STOCK_DIALOG_ERROR)
            self._name_entry.props.secondary_icon_tooltip_text = \
                _("Tag name can not be empty")
            self.is_valid = False
            return False
        else:
            self._name_entry.set_icon_from_icon_name(
                Gtk.EntryIconPosition.SECONDARY, None)
            self.is_valid = True
            return True

    # PUBLIC API #####
    def set_tag(self, tag):
        """
        Set the tag to edit.
        Widgets are updated with the information of the tag,
        the previous information/state is lost.
        """
        self.tag = tag
        if tag is None:
            return

        icon = tag.get_attribute('icon')
        self._set_emoji(self._emoji_entry, text=icon if icon else '')

        self.tag_name = tag.get_name()
        self.set_title(self._title_format % ('@' + tag.get_name(),))

        rgba = Gdk.RGBA(1.0, 1.0, 1.0, 1.0)
        if color := tag.get_attribute('color'):
            if not rgba.parse(color):
                log.warning("Failed to parse tag color for %r: %r",
                            (tag.get_name(), color))
        self.use_color = bool(color)
        self.tag_rgba = rgba
        self.tag_name = tag.get_name()
        self.tag_is_actionable = \
            self.tag.get_attribute("nonactionable") != "True"

    def do_destroy(self):
        self.app.close_tag_editor()
        super().destroy()

    # CALLBACKS #####
    def _cancel(self, widget: GObject.Object):
        """
        Cancel button has been clicked, closing the editor window without
        applying changes.
        """
        self.destroy()

    def _apply(self, widget: GObject.Object):
        """
        Apply button has been clicked, applying the settings and closing the
        editor window.
        """
        if self.tag is None:
            log.warning("Trying to apply but no tag set, shouldn't happen")
            self._cancel(widget)
            return

        if self._emoji:
            self.tag.set_attribute('icon', self._emoji)
        else:
            self.tag.del_attribute('icon')

        if self.use_color:
            rgba = self.tag_rgba
            color = "#%02x%02x%02x" % (int(max(0, min(rgba.red, 1)) * 255),
                                       int(max(0, min(rgba.green, 1)) * 255),
                                       int(max(0, min(rgba.blue, 1)) * 255))
            color_add(color)
            self.tag.set_attribute('color', color)
        else:
            if tag_color := self.tag.get_attribute('color'):
                color_remove(tag_color)
            self.tag.del_attribute('color')

        self.tag.set_attribute('nonactionable', str(not self.tag_is_actionable))

        if self.tag_name != self.tag.get_name():
            log.debug("Renaming %r → %r", self.tag.get_name(), self.tag_name)
            self.req.rename_tag(self.tag.get_name(), self.tag_name)
            self.tag = self.req.get_tag(self.tag_name)

        self.destroy()

    def _random_color(self, widget: GObject.Object):
        """
        The random color button has been clicked, overriding the color
        with an random color.
        """
        self.use_color = True
        self.tag_rgba = Gdk.RGBA(random.uniform(0.0, 1.0),
                                 random.uniform(0.0, 1.0),
                                 random.uniform(0.0, 1.0),
                                 1.0)

    def _activate_color(self, widget: GObject.Object):
        """
        Enable using the selected color because a color has been selected.
        """
        self.use_color = True

    def _set_icon(self, widget: GObject.Object):
        """
        Button to set the icon/emoji has been clicked.
        """
        self._reset_emoji_entry()
        self._emoji_entry.do_insert_emoji(self._emoji_entry)

    def _set_emoji(self, widget: GObject.Object, text: str = None):
        """
        Callback when an emoji has been inserted.
        This is part of the emoji insertion hack.
        The text parameter can be used to override the emoji to use, used
        for initialization.
        """
        if text is None:
            text = self._emoji_entry.get_text()

        if text:
            self._emoji = text
            self._icon_button.set_label(text)
            self._icon_button.set_opacity(1)
        else:
            self._emoji = None
            self._icon_button.set_label('🏷️')
            self._icon_button.set_opacity(0.4)
        self.notify('has-icon')

        self._reset_emoji_entry()

    def _remove_icon(self, widget: GObject.Object):
        """
        Callback to remove the icon.
        """
        self._set_emoji(self._emoji_entry, text='')

    def _on_escape(self, accel_group: Gtk.AccelGroup,
                   acceleratable: GObject.Object, keyval: int,
                   modifier: Gdk.ModifierType) -> bool:
        """
        Callback to close the window when ESC (Escape) is being pressed.
        """
        self.destroy()
        return True
