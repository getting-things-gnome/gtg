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

from GTG import _
from GTG.gtk.backends_dialog.parameters_ui import ParametersUI
from GTG.backends.backendsignals import BackendSignals


class ConfigurePanel(gtk.VBox):
    '''
    A VBox that lets you configure a backend
    '''

    def __init__(self, backends_dialog):
        '''
        Constructor, creating all the gtk widgets

        @param backends_dialog: a reference to the dialog in which this is
        loaded
        '''
        super(ConfigurePanel, self).__init__()
        self.dialog = backends_dialog
        self.should_spinner_be_shown = False
        self.task_deleted_handle = None
        self.task_added_handle = None
        self.req = backends_dialog.get_requester()
        self._create_widgets()
        self._connect_signals()

    def _connect_signals(self):
        ''' Connects the backends generated signals '''
        _signals = BackendSignals()
        _signals.connect(_signals.BACKEND_RENAMED, self.refresh_title)
        _signals.connect(_signals.BACKEND_STATE_TOGGLED,
                         self.refresh_sync_status)
        _signals.connect(_signals.BACKEND_SYNC_STARTED, self.on_sync_started)
        _signals.connect(_signals.BACKEND_SYNC_ENDED, self.on_sync_ended)

    def _create_widgets(self):
        '''
        This function fills this Vbox with widgets
        '''
        # Division of the available space in three segments:
        # top, middle and bottom
        top = gtk.HBox()
        middle = gtk.HBox()
        self._fill_top_hbox(top)
        self._fill_middle_hbox(middle)
        self.pack_start(top, False)
        self.pack_start(middle, False)
        align = gtk.Alignment(xalign=0, yalign=0, xscale=1)
        align.set_padding(10, 0, 0, 0)
        self.parameters_ui = ParametersUI(self.req)
        align.add(self.parameters_ui)
        self.pack_start(align, False)

    def _fill_top_hbox(self, hbox):
        """ Fill header with service's icon, name, and a spinner
        for inidcation of work.

        @param hbox: the gtk.HBox to fill
        """
        self.image_icon = gtk.Image()
        self.image_icon.set_size_request(48, 48)

        self.human_name_label = gtk.Label()
        self.human_name_label.set_alignment(xalign=0, yalign=0.5)

        try:
            self.spinner = gtk.Spinner()
        except AttributeError:
            # worarkound for archlinux: bug #624204
            self.spinner = gtk.HBox()
        self.spinner.connect("show", self.on_spinner_show)
        self.spinner.set_size_request(32, 32)
        align_spin = gtk.Alignment(xalign=1, yalign=0)
        align_spin.add(self.spinner)

        hbox.set_spacing(10)
        hbox.pack_start(self.image_icon, False)
        hbox.pack_start(self.human_name_label, True)
        hbox.pack_start(align_spin, False)

    def _fill_middle_hbox(self, hbox):
        '''
        Helper function to fill an hbox with a label and a button

        @param hbox: the gtk.HBox to fill
        '''
        self.sync_status_label = gtk.Label()
        self.sync_status_label.set_alignment(xalign=0.8, yalign=0.5)
        self.sync_button = gtk.Button()
        self.sync_button.connect("clicked", self.on_sync_button_clicked)
        hbox.pack_start(self.sync_status_label, True)
        hbox.pack_start(self.sync_button, True)

    def set_backend(self, backend_id):
        '''Changes the backend to configure, refreshing this view.

        @param backend_id: the id of the backend to configure
        '''
        self.backend = self.dialog.get_requester().get_backend(backend_id)
        self.refresh_title()
        self.refresh_sync_status()
        self.parameters_ui.refresh(self.backend)
        self.image_icon.set_from_pixbuf(self.dialog.get_pixbuf_from_icon_name(
                                        self.backend.get_name(), 48))

    def refresh_title(self, sender=None, data=None):
        '''
        Callback for the signal that notifies backends name changes. It changes
        the title of this view

        @param sender: not used, here only for signal callback compatibility
        @param data: not used, here only for signal callback compatibility
        '''
        markup = "<big><big><big><b>%s</b></big></big></big>" % \
            self.backend.get_human_name()
        self.human_name_label.set_markup(markup)

    def refresh_sync_button(self):
        '''
        Refreshes the state of the button that enables the backend
        '''
        self.sync_button.set_sensitive(not self.backend.is_default())
        if self.backend.is_enabled():
            label = _("Disable syncing")
        else:
            label = _("Enable syncing")
        self.sync_button.set_label(label)

    def refresh_sync_status_label(self):
        '''
        Refreshes the gtk.Label that shows the current state of this backend
        '''
        if self.backend.is_default():
            label = _("This is the default synchronization service")
        else:
            if self.backend.is_enabled():
                label = _("Syncing is enabled.")
            else:
                label = _('Syncing is <span color="red">disabled</span>.')
        self.sync_status_label.set_markup(label)

    def refresh_sync_status(self, sender=False, data=False):
        '''Signal callback function, called when a backend state
        (enabled/disabled) changes. Refreshes this view.

        @param sender: not used, here only for signal callback compatibility
        @param data: not used, here only for signal callback compatibility
        '''
        self.refresh_sync_button()
        self.refresh_sync_status_label()

    def on_sync_button_clicked(self, sender):
        '''
        Signal callback when a backend is enabled/disabled via the UI button

        @param sender: not used, here only for signal callback compatibility
        '''
        self.parameters_ui.commit_changes()
        self.req.set_backend_enabled(self.backend.get_id(),
                                     not self.backend.is_enabled())

    def on_sync_started(self, sender, backend_id):
        '''
        If the backend has started syncing tasks, update the state of the
        gtk.Spinner

        @param sender: not used, here only for signal callback compatibility
        @param backend_id: the id of the backend that emitted this signal
        '''
        if backend_id == self.backend.get_id():
            self.spinner_set_active(True)

    def on_sync_ended(self, sender, backend_id):
        '''
        If the backend has stopped syncing tasks, update the state of the
        gtk.Spinner

        @param sender: not used, here only for signal callback compatibility
        @param backend_id: the id of the backend that emitted this signal
        '''

        if backend_id == self.backend.get_id():
            self.spinner_set_active(False)

    def on_spinner_show(self, sender):
        '''This signal callback hides the spinner if it's not supposed to be
        seen. It's a workaround to let us call show_all on the whole window
        while keeping this hidden (it's the only widget that requires special
        attention)

        @param sender: not used, here only for signal callback compatibility
        '''
        if not self.should_spinner_be_shown:
            self.spinner.hide()

    def spinner_set_active(self, active):
        '''
        Enables/disables the gtk.Spinner, while showing/hiding it at the same
        time

        @param active: True if the spinner should spin
        '''
        self.should_spinner_be_shown = active
        if active:
            if isinstance(self.spinner, gtk.Spinner):
                self.spinner.start()
            self.spinner.show()
        else:
            self.spinner.hide()
            if isinstance(self.spinner, gtk.Spinner):
                self.spinner.stop()
