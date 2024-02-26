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

from GTG.backends import BackendFactory


class BackendsCombo(Gtk.ComboBox):
    """
    A combobox listing all the available backends types
    """

    # unique name for the backend type. It's never displayed,
    # it's used to find which backend has been selected
    COLUMN_NAME = 0
    # human friendly name (which is localized).
    COLUMN_HUMAN_NAME = 1
    COLUMN_ICON = 2

    def __init__(self, backends):
        """
        Constructor, itializes gtk widgets.
        @param backends: reference to the dialog in which this combo is
                                loaded.
        """
        super().__init__()
        self.dialog = backends
        self._liststore_init()
        self._renderers_init()
        self.set_size_request(-1, 30)

    def _liststore_init(self):
        """Setup the Gtk.ListStore"""
        self.liststore = Gtk.ListStore(str, str, str)
        self.set_model(self.liststore)

    def _renderers_init(self):
        """Configure the cell renderers"""
        # Text renderer
        text_cell = Gtk.CellRendererText()
        self.pack_start(text_cell, False)
        self.add_attribute(text_cell, 'text', 1)
        # Icon renderer
        pixbuf_cell = Gtk.CellRendererPixbuf()
        self.pack_start(pixbuf_cell, False)
        self.add_attribute(pixbuf_cell, "icon-name", self.COLUMN_ICON)

    def refresh(self):
        """
        Populates the combo box with the available backends
        """
        self.liststore.clear()
        backend_types = BackendFactory().get_all_backends()
        ordered_backend_types = sorted(
            backend_types.items(),
            key=lambda btype: btype[1].Backend.get_human_default_name())
        for name, module in ordered_backend_types:
            # FIXME: Disable adding another localfile backend.
            # It just produce many warnings, provides no use case
            # See LP bug #940917 (Izidor)
            if name == "backend_localfile":
                continue
            self.liststore.append((name,
                                   module.Backend.get_human_default_name(),
                                   module.Backend.get_icon()))
        if backend_types:
            # triggers a "changed" signal, which is used in the AddPanel to
            # refresh the backend description and icon
            self.set_active(0)

    def get_selected(self):
        """
        Returns the name of the selected backend, or None
        """
        selected_iter = self.get_active_iter()
        if selected_iter:
            column_name = BackendsCombo.COLUMN_NAME
            return self.liststore.get_value(selected_iter, column_name)
        else:
            return None
