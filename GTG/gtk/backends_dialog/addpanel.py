# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 - Lionel Dricot & Bertrand Rousseau
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

import gtk

from GTG.gtk.backends_dialog.backendscombo import BackendsCombo
from GTG.backends import BackendFactory
from GTG import _, ngettext


class AddPanel(gtk.VBox):
    '''
    A VBox filled with gtk widgets to let the user choose a new backend.
    '''

    def __init__(self, backends_dialog):
        '''
        Constructor, just initializes the gtk widgets

        @param backends_dialog: a reference to the dialog in which this is
        loaded
        '''
        super(AddPanel, self).__init__()
        self.dialog = backends_dialog
        self._create_widgets()

    def _create_widgets(self):
        '''
        gtk widgets initialization
        '''
        # Division of the available space in three segments:
        # top, middle and bottom.
        top = gtk.HBox()
        top.set_spacing(6)
        middle = gtk.HBox()
        bottom = gtk.HBox()
        self._fill_top_hbox(top)
        self._fill_middle_hbox(middle)
        self._fill_bottom_hbox(bottom)
        self.pack_start(top, False)
        self.pack_start(middle, True)
        self.pack_start(bottom, True)
        self.set_border_width(12)

    def _fill_top_hbox(self, hbox):
        '''
        Helper function to fill and hbox with a combobox that lists the
        available backends and a gtk.Label.

        @param hbox: the gtk.HBox to fill
        '''
        label = gtk.Label(_("Select synchronization service:"))
        label.set_alignment(0, 0.5)
        self.combo_types = BackendsCombo(self.dialog)
        self.combo_types.child.connect('changed', self.on_combo_changed)
        hbox.pack_start(label, False, True)
        hbox.pack_start(self.combo_types, False, True)

    def _fill_middle_hbox(self, hbox):
        '''
        Helper function to fill an hbox with a label describing the backend
        and a gtk.Image (that loads the backend image)

        @param hbox: the gtk.HBox to fill
        '''
        self.label_name = gtk.Label("name")
        self.label_name.set_alignment(xalign=0.5, yalign=1)
        self.label_description = gtk.Label()
        self.label_description.set_justify(gtk.JUSTIFY_FILL)
        self.label_description.set_line_wrap(True)
        self.label_description.set_size_request(300, -1)
        self.label_description.set_alignment(xalign=0, yalign=0.5)
        self.label_author = gtk.Label("")
        self.label_author.set_line_wrap(True)
        self.label_author.set_alignment(xalign=0, yalign=0)
        self.label_modules = gtk.Label("")
        self.label_modules.set_line_wrap(True)
        self.label_modules.set_alignment(xalign=0, yalign=0)
        self.image_icon = gtk.Image()
        self.image_icon.set_size_request(128, 128)
        align_image = gtk.Alignment(xalign=1, yalign=0)
        align_image.add(self.image_icon)
        labels_vbox = gtk.VBox()
        labels_vbox.pack_start(self.label_description, True, True, padding=10)
        labels_vbox.pack_start(self.label_author, True, True)
        labels_vbox.pack_start(self.label_modules, True, True)
        low_hbox = gtk.HBox()
        low_hbox.pack_start(labels_vbox, True, True)
        low_hbox.pack_start(align_image, True, True)
        vbox = gtk.VBox()
        vbox.pack_start(self.label_name, True, True)
        vbox.pack_start(low_hbox, True, True)
        hbox.pack_start(vbox, True, True)

    def _fill_bottom_hbox(self, hbox):
        '''
        Helper function to fill and hbox with a buttonbox, featuring
        and ok and cancel buttons.

        @param hbox: the gtk.HBox to fill
        '''
        cancel_button = gtk.Button(stock=gtk.STOCK_CANCEL)
        cancel_button.connect('clicked', self.on_cancel)
        self.ok_button = gtk.Button(stock=gtk.STOCK_OK)
        self.ok_button.connect('clicked', self.on_confirm)
        align = gtk.Alignment(xalign=0.5,
                              yalign=1,
                              xscale=1)
        align.set_padding(0, 10, 0, 0)
        buttonbox = gtk.HButtonBox()
        buttonbox.set_layout(gtk.BUTTONBOX_EDGE)
        buttonbox.add(cancel_button)
        buttonbox.set_child_secondary(cancel_button, False)
        buttonbox.add(self.ok_button)
        align.add(buttonbox)
        hbox.pack_start(align, True, True)

    def refresh_backends(self):
        '''Populates the combo box containing the available backends'''
        self.combo_types.refresh()

    def on_confirm(self, widget=None):
        '''
        Notifies the dialog holding this VBox that a backend has been
        chosen

        @param widget: just to make this function usable as a signal callback.
                       Not used.
        '''
        backend_name = self.combo_types.get_selected()
        self.dialog.on_backend_added(backend_name)

    def on_cancel(self, widget=None):
        '''
        Aborts the addition of a new backend. Shows the configuration panel
        previously loaded.

        @param widget: just to make this function usable as a signal callback.
                       Not used.
        '''
        self.dialog.show_config_for_backend(None)

    def on_combo_changed(self, widget=None):
        '''
        Updates the backend description and icon.

        @param widget: just to make this function usable as a signal callback.
                       Not used.
        '''
        backend_name = self.combo_types.get_selected()
        if backend_name is None:
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
        pixbuf = self.dialog.get_pixbuf_from_icon_name(backend_name, 128)
        self.image_icon.set_from_pixbuf(pixbuf)
        self.show_all()
