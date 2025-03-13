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

from functools import reduce

from gi.repository import Gtk

from GTG.gtk.backends.backendscombo import BackendsCombo
from GTG.backends import BackendFactory
from gettext import gettext as _, ngettext

from GTG.backends import inactive_modules


class AddPanel(Gtk.Box):
    """
    A vertical Box filled with gtk widgets to let the user choose a new
    backend.
    """

    def __init__(self, backends):
        """
        Constructor, just initializes the gtk widgets

        @param backends: a reference to the dialog in which this is
        loaded
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_spacing(24)
        self.dialog = backends
        self._create_widgets()

    def _create_widgets(self):
        """
        gtk widgets initialization
        """
        # Division of the available space in three segments:
        # top, middle and bottom.
        top = Gtk.Box()
        top.set_spacing(6)
        middle = Gtk.Box()
        middle.set_valign(Gtk.Align.CENTER)
        middle.set_vexpand(True)
        bottom = Gtk.Box()
        bottom.set_valign(Gtk.Align.END)
        bottom.set_vexpand(True)
        self._fill_top_box(top)
        self._fill_middle_box(middle)
        self._fill_bottom_box(bottom)
        self.append(top)
        self.append(middle)
        self.append(bottom)

    def _fill_top_box(self, box):
        """
        Helper function to fill and box with a combobox that lists the
        available backends and a Gtk.Label.

        @param box: the Gtk.Box to fill
        """
        label = Gtk.Label(label=_("Select synchronization service:"))
        label.set_xalign(0)
        label.set_yalign(0.5)
        self.combo_types = BackendsCombo(self.dialog)
        # FIXME
        # self.combo_types.get_child().connect(
        #     'changed', self.on_combo_changed)
        self.combo_types.connect('changed', self.on_combo_changed)
        box.append(label)
        box.append(self.combo_types)

    def _fill_middle_box(self, box):
        """
        Helper function to fill an box with a label describing the backend
        and a Gtk.Image (that loads the backend image)

        @param box: the Gtk.Box to fill
        """
        self.label_name = Gtk.Label()
        self.label_description = Gtk.Label()
        self.label_description.set_xalign(0)
        self.label_description.set_wrap(True)
        self.label_author = Gtk.Label()
        self.label_modules = Gtk.Label()
        self.image_icon = Gtk.Image()
        self.image_icon.set_hexpand(True)
        self.image_icon.set_halign(Gtk.Align.END)
        self.image_icon.set_pixel_size(128)
        labels_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        labels_vbox.set_spacing(6)
        labels_vbox.append(self.label_description)
        labels_vbox.append(self.label_author)
        labels_vbox.append(self.label_modules)
        low_box = Gtk.Box()
        low_box.set_vexpand(True)
        low_box.append(labels_vbox)
        low_box.append(self.image_icon)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(12)
        vbox.append(self.label_name)
        vbox.append(low_box)
        box.append(vbox)

    def _fill_bottom_box(self, box):
        """
        Helper function to fill and box with a buttonbox, featuring
        and ok and cancel buttons.

        @param box: the Gtk.Box to fill
        """
        cancel_button = Gtk.Button()
        cancel_button.set_label(_("Cancel"))
        cancel_button.connect('clicked', self.on_cancel)
        self.ok_button = Gtk.Button()
        self.ok_button.set_label(_("OK"))
        self.ok_button.set_hexpand(True)
        self.ok_button.set_halign(Gtk.Align.END)
        self.ok_button.connect('clicked', self.on_confirm)
        box.append(cancel_button)
        box.append(self.ok_button)

    def refresh_backends(self):
        """Populates the combo box containing the available backends"""
        self.combo_types.refresh()

    def on_confirm(self, widget=None):
        """
        Notifies the dialog holding this Box that a backend has been
        chosen

        @param widget: just to make this function usable as a signal callback.
                       Not used.
        """
        backend_name = self.combo_types.get_selected()
        self.dialog.on_backend_added(backend_name)

    def on_cancel(self, widget=None):
        """
        Aborts the addition of a new backend. Shows the configuration panel
        previously loaded.

        @param widget: just to make this function usable as a signal callback.
                       Not used.
        """
        self.dialog.show_config_for_backend(None)

    def on_combo_changed(self, widget=None):
        """
        Updates the backend description and icon.

        @param widget: just to make this function usable as a signal callback.
                       Not used.
        """
        backend_name = self.combo_types.get_selected()
        if backend_name is None:
            if 'backend_caldav' in inactive_modules:
                markup = '<big>Error: Python package \'caldev\' not installed.</big>'
                self.label_name.set_markup(markup)
                return


            markup = '<big>Error: An unknown backend could not be loaded.</big>'
            self.label_name.set_markup(markup)
            return

        backend = BackendFactory().get_backend(backend_name)
        self.label_description.set_markup(backend.Backend.get_description())

        markup = '<big><big><big><b>%s</b></big></big></big>' % \
            backend.Backend.get_human_default_name()
        self.label_name.set_markup(markup)
        authors = backend.Backend.get_authors()
        author_txt = '<b>%s</b>:\n   - %s' % \
            (ngettext("Author", "Authors", len(authors)),
             reduce(lambda a, b: a + "\n" + "   - " + b, authors))
        self.label_author.set_markup(author_txt)
        self.image_icon.set_from_icon_name(backend.Backend.get_icon())
