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

import threading

from gi.repository import Gtk

from GTG.backends.backend_signals import BackendSignals
from gettext import gettext as _
from GTG.core.networkmanager import is_connection_up


class BackendInfoBar(Gtk.InfoBar):
    """
    A Gtk.InfoBar specialized for displaying errors and requests for
    interaction coming from the backends
    """

    AUTHENTICATION_MESSAGE = _("The <b>%s</b> synchronization service cannot "
                               "login with the  supplied authentication data "
                               "and has been disabled. To retry the login, "
                               "re-enable the service.")

    NETWORK_MESSAGE = _("Due to a network problem, I cannot contact "
                        "the <b>%s</b> synchronization service.")

    DBUS_MESSAGE = _("Cannot connect to DBus, I've disabled "
                     "the <b>%s</b> synchronization service.")

    def __init__(self, req, browser, app, backend_id):
        """
        Constructor, Prepares the infobar.

        @param req: a Requester object
        @param browser: a MainWindow object
        @param app: a ViewManager object
        @param backend_id: the id of the backend linked to the infobar
        """
        super().__init__()
        self.req = req
        self.browser = browser
        self.app = app
        self.backend_id = backend_id
        self.backend = self.req.get_backend(backend_id)

    def get_backend_id(self):
        """
        Getter function to return the id of the backend for which this
        Gtk.InfoBar was created
        """
        return self.backend_id

    def _populate(self):
        """Setting up gtk widgets"""
        content_box = self.get_content_area()
        content_box.set_homogeneous(False)
        self.label = Gtk.Label()
        self.label.set_hexpand(True)
        self.label.set_wrap(True)
        self.label.set_alignment(0.5, 0.5)
        self.label.set_justify(Gtk.Justification.FILL)
        content_box.append(self.label)

    def _on_error_response(self, widget, event):
        """
        Signal callback executed when the user acknowledges the error displayed
        in the infobar

        @param widget: not used, here for compatibility with signals callbacks
        @param event: the code of the gtk response
        """
        self.hide()
        if event == Gtk.ResponseType.ACCEPT:
            self.app.open_edit_backends(backend_id=self.backend_id)

    def set_error_code(self, error_code):
        """
        Sets this infobar to show an error to the user

        @param error_code: the code of the error to show. Error codes are
                           listed in BackendSignals
        """
        self._populate()
        self.connect("response", self._on_error_response)
        backend_name = self.backend.get_human_name()

        if error_code == BackendSignals.ERRNO_AUTHENTICATION:
            self.set_message_type(Gtk.MessageType.ERROR)
            self.label.set_markup(self.AUTHENTICATION_MESSAGE % backend_name)
            self.add_button(_('Configure'),
                            Gtk.ResponseType.ACCEPT)
            self.add_button(_('Ignore'), Gtk.ResponseType.CLOSE)

        elif error_code == BackendSignals.ERRNO_NETWORK:
            if not is_connection_up():
                return
            self.set_message_type(Gtk.MessageType.WARNING)
            self.label.set_markup(self.NETWORK_MESSAGE % backend_name)
            self.add_button(_('OK'), Gtk.ResponseType.CLOSE)

        elif error_code == BackendSignals.ERRNO_DBUS:
            self.set_message_type(Gtk.MessageType.WARNING)
            self.label.set_markup(self.DBUS_MESSAGE % backend_name)
            self.add_button(_('OK'), Gtk.ResponseType.CLOSE)

        self.show_all()

    def set_interaction_request(self, description, interaction_type, callback):
        """
        Sets this infobar to request an interaction from the user

        @param description: a string describing the interaction needed
        @param interaction_type: a string describing the type of interaction
                                 (yes/no, only confirm, ok/cancel...)
        @param callback: the function to call when the user provides the
                         feedback
        """
        self._populate()
        self.callback = callback
        self.set_message_type(Gtk.MessageType.INFO)
        self.label.set_markup(description)
        self.connect("response", self._on_interaction_response)
        self.interaction_type = interaction_type
        if interaction_type == BackendSignals().INTERACTION_CONFIRM:
            self.add_button(_('Confirm'), Gtk.ResponseType.ACCEPT)
        elif interaction_type == BackendSignals().INTERACTION_TEXT:
            self.add_button(_('Continue'), Gtk.ResponseType.ACCEPT)
        elif interaction_type == BackendSignals().INTERACTION_INFORM:
            self.add_button(_('OK'), Gtk.ResponseType.ACCEPT)
        self.show_all()

    def _on_interaction_response(self, widget, event):
        """
        Signal callback executed when the user gives the feedback for a
        requested interaction

        @param widget: not used, here for compatibility with signals callbacks
        @param event: the code of the gtk response
        """
        if event == Gtk.ResponseType.ACCEPT:
            if self.interaction_type == BackendSignals().INTERACTION_TEXT:
                self._prepare_textual_interaction()
            elif self.interaction_type == BackendSignals().INTERACTION_CONFIRM:
                self.hide()
                threading.Thread(target=getattr(self.backend,
                                                self.callback)).start()
            else:
                self.hide()

    def _prepare_textual_interaction(self):
        """
        Helper function. gtk calls to populate the infobar in the case of
        interaction request
        """
        title, description\
            = getattr(self.backend,
                      self.callback)("get_ui_dialog_text")
        self.dialog = Gtk.Window()  # type = Gtk.WindowType.POPUP
        self.dialog.set_title(title)
        self.dialog.set_transient_for(self.browser.window)
        self.dialog.set_destroy_with_parent(True)
        self.dialog.set_modal(True)
        #        self.dialog.set_size_request(300,170)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.dialog.set_child(vbox)
        description_label = Gtk.Label()
        description_label.set_justify(Gtk.Justification.FILL)
        description_label.set_wrap(True)
        description_label.set_markup(description)
        align = Gtk.Alignment.new(0.5, 0.5, 1, 1)
        align.set_padding(10, 0, 20, 20)
        align.set_vexpand(True)
        align.add(description_label)
        vbox.append(align)
        self.text_box = Gtk.Entry()
        self.text_box.set_size_request(-1, 40)
        align = Gtk.Alignment.new(0.5, 0.5, 1, 1)
        align.set_vexpand(True)
        align.set_padding(20, 20, 20, 20)
        align.add(self.text_box)
        vbox.append(align)
        button = Gtk.Button()
        button.set_label(_("OK"))
        button.connect("clicked", self._on_text_confirmed)
        button.set_size_request(-1, 40)
        vbox.append(button)
        self.dialog.show_all()
        self.hide()

    def _on_text_confirmed(self, widget):
        """
        Signal callback, used when the interaction needs a textual input to be
        completed (e.g, the twitter OAuth, requesting a pin)

        @param widget: not used, here for signal callback compatibility
        """
        text = self.text_box.get_text()
        self.dialog.destroy()
        threading.Thread(target=getattr(self.backend, self.callback),
                         args=("set_text", text)).start()
