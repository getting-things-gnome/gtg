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
import threading

from GTG import _
from GTG.backends.backendsignals import BackendSignals
from GTG.tools.networkmanager import is_connection_up


class CustomInfoBar(gtk.InfoBar):
    '''
    A gtk.InfoBar specialized for displaying errors and requests for
    interaction coming from the backends
    '''

    AUTHENTICATION_MESSAGE = _("The <b>%s</b> synchronization service cannot "
                               "login with the  supplied authentication data "
                               "and has been disabled. To retry the login, "
                               "re-enable the service.")

    NETWORK_MESSAGE = _("Due to a network problem, I cannot contact "
                        "the <b>%s</b> synchronization service.")

    DBUS_MESSAGE = _("Cannot connect to DBus, I've disabled "
                     "the <b>%s</b> synchronization service.")

    def __init__(self, req, browser, vmanager, backend_id):
        '''
        Constructor, Prepares the infobar.

        @param req: a Requester object
        @param browser: a TaskBrowser object
        @param vmanager: a ViewManager object
        @param backend_id: the id of the backend linked to the infobar
        '''
        super(CustomInfoBar, self).__init__()
        self.req = req
        self.browser = browser
        self.vmanager = vmanager
        self.backend_id = backend_id
        self.backend = self.req.get_backend(backend_id)

    def get_backend_id(self):
        '''
        Getter function to return the id of the backend for which this
        gtk.InfoBar was created
        '''
        return self.backend_id

    def _populate(self):
        '''Setting up gtk widgets'''
        content_hbox = self.get_content_area()
        content_hbox.set_homogeneous(False)
        self.label = gtk.Label()
        self.label.set_line_wrap(True)
        self.label.set_alignment(0.5, 0.5)
        self.label.set_justify(gtk.JUSTIFY_FILL)
        content_hbox.pack_start(self.label, True, True)

    def _on_error_response(self, widget, event):
        '''
        Signal callback executed when the user acknowledges the error displayed
        in the infobar

        @param widget: not used, here for compatibility with signals callbacks
        @param event: the code of the gtk response
        '''
        self.hide()
        if event == gtk.RESPONSE_ACCEPT:
            self.vmanager.configure_backend(backend_id=self.backend_id)

    def set_error_code(self, error_code):
        '''
        Sets this infobar to show an error to the user

        @param error_code: the code of the error to show. Error codes are
                           listed in BackendSignals
        '''
        self._populate()
        self.connect("response", self._on_error_response)
        backend_name = self.backend.get_human_name()

        if error_code == BackendSignals.ERRNO_AUTHENTICATION:
            self.set_message_type(gtk.MESSAGE_ERROR)
            self.label.set_markup(self.AUTHENTICATION_MESSAGE % backend_name)
            self.add_button(_('Configure synchronization service'),
                            gtk.RESPONSE_ACCEPT)
            self.add_button(_('Ignore'), gtk.RESPONSE_CLOSE)

        elif error_code == BackendSignals.ERRNO_NETWORK:
            if not is_connection_up():
                return
            self.set_message_type(gtk.MESSAGE_WARNING)
            self.label.set_markup(self.NETWORK_MESSAGE % backend_name)
            # FIXME: use gtk stock button instead
            self.add_button(_('Ok'), gtk.RESPONSE_CLOSE)

        elif error_code == BackendSignals.ERRNO_DBUS:
            self.set_message_type(gtk.MESSAGE_WARNING)
            self.label.set_markup(self.DBUS_MESSAGE % backend_name)
            self.add_button(_('Ok'), gtk.RESPONSE_CLOSE)

        self.show_all()

    def set_interaction_request(self, description, interaction_type, callback):
        '''
        Sets this infobar to request an interaction from the user

        @param description: a string describing the interaction needed
        @param interaction_type: a string describing the type of interaction
                                 (yes/no, only confirm, ok/cancel...)
        @param callback: the function to call when the user provides the
                         feedback
        '''
        self._populate()
        self.callback = callback
        self.set_message_type(gtk.MESSAGE_INFO)
        self.label.set_markup(description)
        self.connect("response", self._on_interaction_response)
        self.interaction_type = interaction_type
        if interaction_type == BackendSignals().INTERACTION_CONFIRM:
            self.add_button(_('Confirm'), gtk.RESPONSE_ACCEPT)
        elif interaction_type == BackendSignals().INTERACTION_TEXT:
            self.add_button(_('Continue'), gtk.RESPONSE_ACCEPT)
        self.show_all()

    def _on_interaction_response(self, widget, event):
        '''
        Signal callback executed when the user gives the feedback for a
        requested interaction

        @param widget: not used, here for compatibility with signals callbacks
        @param event: the code of the gtk response
        '''
        if event == gtk.RESPONSE_ACCEPT:
            if self.interaction_type == BackendSignals().INTERACTION_TEXT:
                self._prepare_textual_interaction()
                print "done"
            elif self.interaction_type == BackendSignals().INTERACTION_CONFIRM:
                self.hide()
                threading.Thread(target=getattr(self.backend,
                                                self.callback)).start()

    def _prepare_textual_interaction(self):
        '''
        Helper function. gtk calls to populate the infobar in the case of
        interaction request
        '''
        title, description\
            = getattr(self.backend,
                      self.callback)("get_ui_dialog_text")
        self.dialog = gtk.Window()  # type = gtk.WINDOW_POPUP)
        self.dialog.set_title(title)
        self.dialog.set_transient_for(self.browser.window)
        self.dialog.set_destroy_with_parent(True)
        self.dialog.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.dialog.set_modal(True)
        #        self.dialog.set_size_request(300,170)
        vbox = gtk.VBox()
        self.dialog.add(vbox)
        description_label = gtk.Label()
        description_label.set_justify(gtk.JUSTIFY_FILL)
        description_label.set_line_wrap(True)
        description_label.set_markup(description)
        align = gtk.Alignment(0.5, 0.5, 1, 1)
        align.set_padding(10, 0, 20, 20)
        align.add(description_label)
        vbox.pack_start(align)
        self.text_box = gtk.Entry()
        self.text_box.set_size_request(-1, 40)
        align = gtk.Alignment(0.5, 0.5, 1, 1)
        align.set_padding(20, 20, 20, 20)
        align.add(self.text_box)
        vbox.pack_start(align)
        button = gtk.Button(stock=gtk.STOCK_OK)
        button.connect("clicked", self._on_text_confirmed)
        button.set_size_request(-1, 40)
        vbox.pack_start(button, False)
        self.dialog.show_all()
        self.hide()

    def _on_text_confirmed(self, widget):
        '''
        Signal callback, used when the interaction needs a textual input to be
        completed (e.g, the twitter OAuth, requesting a pin)

        @param widget: not used, here for signal callback compatibility
        '''
        text = self.text_box.get_text()
        self.dialog.destroy()
        threading.Thread(target=getattr(self.backend, self.callback),
                         args=("set_text", text)).start()
