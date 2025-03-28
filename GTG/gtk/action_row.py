# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2025 - The GTG Team
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

from gi.repository import GObject, Gtk
from typing import Any

from GTG.gtk.browser import GnomeConfig


@Gtk.Template(filename=GnomeConfig.ACTION_ROW)
class ActionRow(Gtk.ListBoxRow, Gtk.Buildable):

    __gtype_name__ = 'ActionRow'

    box = Gtk.Template.Child()
    subtitle_label = Gtk.Template.Child()

    title = GObject.Property(type=str)

    handler_id = None

    @GObject.Property(type=str, default="")
    def subtitle(self) -> str:
        return self._subtitle

    @subtitle.setter
    def subtitle(self, subtitle: str) -> None:
        self._subtitle = subtitle

        self.subtitle_label.set_visible(bool(subtitle))

    @GObject.Property(type=Gtk.Widget, default=None)
    def activatable_widget(self) -> Gtk.Widget | None:
        return self._activatable_widget

    @activatable_widget.setter
    def activatable_widget(self, activatable_widget: Gtk.Widget | None) -> None:
        self._activatable_widget = activatable_widget

        self.set_activatable(bool(activatable_widget))

        parent = self.get_parent()
        if not isinstance(parent, Gtk.ListBox):
            raise TypeError(f"Parent must be a {Gtk.ListBox}.")

        if activatable_widget:
            self.handler_id = parent.connect("row-activated", lambda _, row: row.activatable_widget.activate())
        else:
            if self.handler_id:
                parent.disconnect(handler_id)

    def do_add_child(self, builder: Gtk.Builder, child: GObject.Object, type: str | None) -> None:
        match type:
            case "suffix" | None:
                self.box.append(child)
            case "prefix":
                self.box.prepend(child)
            case _:
                raise TypeError("Invalid type")
