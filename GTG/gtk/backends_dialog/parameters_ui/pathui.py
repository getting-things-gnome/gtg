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
import os.path

from GTG import _


class PathUI(gtk.HBox):
    '''Gtk widgets to show a path in a textbox, and a button to bring up a
    filesystem explorer to modify that path (also, a label to describe those)
    '''

    def __init__(self, req, backend, width):
        '''
        Creates the textbox, the button and loads the current path.

        @param req: a Requester
        @param backend: a backend object
        @param width: the width of the gtk.Label object
        '''
        super(PathUI, self).__init__()
        self.backend = backend
        self.req = req
        self._populate_gtk(width)

    def _populate_gtk(self, width):
        '''Creates the gtk.Label, the textbox and the button

        @param width: the width of the gtk.Label object
        '''
        label = gtk.Label(_("Filename:"))
        label.set_line_wrap(True)
        label.set_alignment(xalign=0, yalign=0.5)
        label.set_size_request(width=width, height=-1)
        self.pack_start(label, False)
        align = gtk.Alignment(xalign=0, yalign=0.5, xscale=1)
        align.set_padding(0, 0, 10, 0)
        self.pack_start(align, True)
        self.textbox = gtk.Entry()
        self.textbox.set_text(self.backend.get_parameters()['path'])
        self.textbox.connect('changed', self.on_path_modified)
        align.add(self.textbox)
        self.button = gtk.Button(stock=gtk.STOCK_EDIT)
        self.button.connect('clicked', self.on_button_clicked)
        self.pack_start(self.button, False)

    def commit_changes(self):
        '''Saves the changes to the backend parameter'''
        self.backend.set_parameter('path', self.textbox.get_text())

    def on_path_modified(self, sender):
        ''' Signal callback, executed when the user edits the path.
        Disables the backend. The user will re-enable it to confirm the changes
        (s)he made.

        @param sender: not used, only here for signal compatibility
        '''
        if self.backend.is_enabled() and not self.backend.is_default():
            self.req.set_backend_enabled(self.backend.get_id(), False)

    def on_button_clicked(self, sender):
        '''Shows the filesystem explorer to choose a new file

        @param sender: not used, only here for signal compatibility
        '''
        self.chooser = gtk.FileChooserDialog(
            title=None,
            action=gtk.FILE_CHOOSER_ACTION_SAVE,
            buttons=(gtk.STOCK_CANCEL,
                     gtk.RESPONSE_CANCEL,
                     gtk.STOCK_OK,
                     gtk.RESPONSE_OK))
        self.chooser.set_default_response(gtk.RESPONSE_OK)
        # set default file as the current self.path
        dirname, basename = os.path.split(self.textbox.get_text())
        self.chooser.set_current_name(basename)
        self.chosser.set_current_folder(dirname)

        # filter files
        afilter = gtk.FileFilter()
        afilter.set_name("All files")
        afilter.add_pattern("*")
        self.chooser.add_filter(afilter)
        afilter = gtk.FileFilter()
        afilter.set_name("XML files")
        afilter.add_mime_type("text/plain")
        afilter.add_pattern("*.xml")
        self.chooser.add_filter(afilter)
        response = self.chooser.run()
        if response == gtk.RESPONSE_OK:
            self.textbox.set_text(self.chooser.get_filename())
        self.chooser.destroy()
