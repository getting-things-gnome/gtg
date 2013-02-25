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

'''
This file contains BackendsDialog, a class that manages the window that
lets you add and configure backends.
This window is divided in two:
    - a treeview of the currently loaded backends (the ones added by the user)
    - a big space, that can be filled by the configuration panel or the add
    panel (these are called also "views" in this class)
'''

import gtk

from webbrowser import open as openurl

from GTG.gtk import ViewConfig
from GTG.core import CoreConfig
from GTG.gtk.backends_dialog.backendstree import BackendsTree
from GTG.gtk.backends_dialog.addpanel import AddPanel
from GTG.gtk.backends_dialog.configurepanel import ConfigurePanel
from GTG.backends import BackendFactory
from GTG.tools.logger import Log
from GTG import _
from GTG.backends.genericbackend import GenericBackend
from GTG import info


class BackendsDialog(object):
    '''
    BackendsDialog manages a window that lets you manage and configure
    synchronization service.
    It can display two "views", or "panels":
        - the backend configuration view
        - the backend adding view
    '''

    def __init__(self, req):
        '''
        Initializes the gtk objects and signals.
        @param req: a Requester object
        '''
        self.req = req
        self.icon_theme = None
        self._configure_icon_theme()
        # Declare subsequently loaded widget
        self.dialog = None
        self.treeview_window = None
        self.central_pane = None
        self.add_button = None
        self.remove_button = None
        self.backends_tv = None
        self.config_panel = None
        self.add_panel = None
        # Load from Glade
        builder = gtk.Builder()
        self._load_widgets_from_glade(builder)
        # Load and setup other widgets
        self.dialog.set_title(_("Synchronization Services - %s" % info.NAME))
        self._create_widgets_for_add_panel()
        self._create_widgets_for_conf_panel()
        self._setup_signal_connections(builder)
        self._create_widgets_for_treeview()

########################################
### INTERFACE WITH THE VIEWMANAGER #####
########################################
    def activate(self):
        '''Shows this window, refreshing the current view'''
        self.dialog.show_all()
        self.backends_tv.refresh()
        self.backends_tv.select_backend()
        self.dialog.present()

    def on_close(self, widget, data=None):
        '''
        Hides this window, saving the backends configuration.

        @param widget: not used, here only for using this as signal callback
        @param data: same as widget, disregard the content
        '''
        self.dialog.hide()
        self.req.save_datastore()
        return True

########################################
### HELPER FUNCTIONS ###################
########################################
    def get_requester(self):
        '''
        Helper function: returns the requester.
        It's used by the "views" displayed by this class (backend editing and
        adding views) to access the requester
        '''
        return self.req

    def get_pixbuf_from_icon_name(self, name, height):
        '''
        Helper function: returns a pixbuf of an icon given its name in the
        loaded icon theme

        @param name: the name of the icon
        @param height: the height of the returned pixbuf
        @param width:  the width of the returned pixbuf

        @returns gtk.gdk.Pixbuf: a pixbuf containing the wanted icon, or None
        (if the icon is not present)
        '''
        icon_info = self.icon_theme.lookup_icon(name, height, 0)
        if icon_info is None:
            return None
        else:
            return gtk.icon_theme_get_default().load_icon(name, height, 0)

    def _show_panel(self, panel_name):
        '''
        Helper function to switch between panels.

        @param panel_name: the name of the wanted panel. Choose between
                        "configuration" or "add"
        '''
        if panel_name == "configuration":
            panel_to_remove = self.add_panel
            panel_to_add = self.config_panel
            side_is_enabled = True
        elif panel_name == "add":
            panel_to_remove = self.config_panel
            panel_to_add = self.add_panel
            side_is_enabled = False
        else:
            Log.error("panel name unknown")
            return
        # Central pane
        # NOTE: self.central_pane is the gtk.Container in which we load panels
        if panel_to_remove in self.central_pane:
            self.central_pane.remove(panel_to_remove)
        if not panel_to_add in self.central_pane:
            self.central_pane.add(panel_to_add)
        self.central_pane.show_all()
        # Side treeview
        # disabled if we're adding a new backend
        try:
            # when this is called upon initialization of this class, the
            # backends_tv object has not been created yet.
            self.add_button.set_sensitive(side_is_enabled)
            self.remove_button.set_sensitive(side_is_enabled)
            self.backends_tv.set_sensitive(side_is_enabled)
        except AttributeError:
            pass

########################################
### WIDGETS AND SIGNALS ################
########################################
    def _load_widgets_from_glade(self, builder):
        '''
        Loads widgets from the glade file

        @param builder: a gtk.Builder
        '''
        builder.add_from_file(ViewConfig.BACKENDS_GLADE_FILE)
        widgets = {
            'dialog': 'backends_dialog',
            'treeview_window': 'treeview_window',
            'central_pane': 'central_pane',
            'add_button': 'add_button',
            'remove_button': 'remove_button',
        }
        for attr, widget in widgets.iteritems():
            setattr(self, attr, builder.get_object(widget))

    def _setup_signal_connections(self, builder):
        '''
        Creates some GTK signals connections

        @param builder: a gtk.Builder
        '''
        signals = {
            'on_add_button_clicked': self.on_add_button,
            'on_BackendsDialog_delete_event': self.on_close,
            'on_close_button_clicked': self.on_close,
            'on_remove_button_clicked': self.on_remove_button,
            'on_help_button_clicked': lambda w:
            openurl("help:gtg/gtg-add-sync"),
        }
        builder.connect_signals(signals)

    def _configure_icon_theme(self):
        '''
        Inform gtk on the location of the backends icons (which is in
        the GTG directory tree, and not in the default location for icons
        '''
        self.icon_theme = gtk.icon_theme_get_default()
        for directory in CoreConfig().get_icons_directories():
            self.icon_theme.prepend_search_path(directory)

    def _create_widgets_for_treeview(self):
        '''
        Creates the widgets for the lateral treeview displaying the
        backends the user has added
        '''
        self.backends_tv = BackendsTree(self)
        self.treeview_window.add(self.backends_tv)

    def _create_widgets_for_conf_panel(self):
        '''simply creates the panel to configure backends'''
        self.config_panel = ConfigurePanel(self)

    def _create_widgets_for_add_panel(self):
        '''simply creates the panel to add backends'''
        self.add_panel = AddPanel(self)

########################################
### EVENT HANDLING #####################
########################################
    def on_backend_selected(self, backend_id):
        '''
        When a backend in the treeview gets selected, show
        its configuration pane

        @param backend_id: the id of the selected backend
        '''
        if backend_id:
            self._show_panel("configuration")
            self.config_panel.set_backend(backend_id)
            backend = self.req.get_backend(backend_id)
            self.remove_button.set_sensitive(not backend.is_default())

    def on_add_button(self, widget=None, data=None):
        '''
        When the add button is pressed, the add panel is shown

        @param widget: not used, here only for using this as signal callback
        @param data: same as widget, disregard the content
        '''
        self._show_panel("add")
        self.add_panel.refresh_backends()

    def on_backend_added(self, backend_name):
        '''
        When a backend is added, it is created and registered in the Datastore.
        Also, the configuration panel is shown.

        @param backend_name: the name of the type of the backend to add
                             (identified as BACKEND_NAME in the Backend class)
        '''
        # Create Backend
        backend_dic = BackendFactory().get_new_backend_dict(backend_name)
        if backend_dic:
            backend_dic[GenericBackend.KEY_ENABLED] = False
            self.req.register_backend(backend_dic)
        # Restore UI
        self._show_panel("configuration")

    def show_config_for_backend(self, backend_id):
        '''
        Selects a backend in the lateral treeview

        @param backend_id: the id of the backend that must be selected
        '''
        self.backends_tv.select_backend(backend_id)

    def on_remove_button(self, widget=None, data=None):
        '''
        When the remove button is pressed, a confirmation dialog is shown,
        and if the answer is positive, the backend is deleted.
        '''
        backend_id = self.backends_tv.get_selected_backend_id()
        if backend_id is None:
            # no backend selected
            return
        backend = self.req.get_backend(backend_id)
        dialog = gtk.MessageDialog(
            parent=self.dialog,
            flags=gtk.DIALOG_DESTROY_WITH_PARENT,
            type=gtk.MESSAGE_QUESTION,
            buttons=gtk.BUTTONS_YES_NO,
            message_format=_("Do you really want to remove the '%s' "
                             "synchronization service?") %
            backend.get_human_name())
        response = dialog.run()
        dialog.destroy()
        if response == gtk.RESPONSE_YES:
            # delete the backend and remove it from the lateral treeview
            self.req.remove_backend(backend_id)
            self.backends_tv.remove_backend(backend_id)
