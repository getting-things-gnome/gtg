# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2009 - Lionel Dricot & Bertrand Rousseau
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
""" The Preferences Dialog for loading plugins and configuring GTG """
import os
import shutil

import gtk
import pango
from xdg.BaseDirectory import xdg_config_home

from GTG              import _
from GTG.core.plugins import GnomeConfig
from GTG.gtk          import ViewConfig


__all__ = [
  'PreferencesDialog',
  ]

# Default plugin information text
PLUGINS_DEFAULT_DESC = _("Click on a plugin to get a description here.")

# columns in PreferencesDialog.plugin_store
PLUGINS_COL_ID = 0
PLUGINS_COL_ENABLED = 1
PLUGINS_COL_NAME = 2
PLUGINS_COL_SHORT_DESC = 3
PLUGINS_COL_DESC = 4
PLUGINS_COL_ACTIVATABLE = 5

def plugin_icon(column, cell, store, iter):
    """Callback to set the content of a PluginTree cell.
    
    See PreferencesDialog._init_plugin_tree().
    
    """
    cell.set_property('icon-name', 'gtg-plugin')
    cell.set_property('sensitive', store.get_value(iter,
      PLUGINS_COL_ACTIVATABLE))


def plugin_markup(column, cell, store, iter):
    """Callback to set the content of a PluginTree cell.
    
    See PreferencesDialog._init_plugin_tree().
    
    """
    name = store.get_value(iter, PLUGINS_COL_NAME)
    desc = store.get_value(iter, PLUGINS_COL_SHORT_DESC)
    cell.set_property('markup', "<b>%s</b>\n%s" % (name, desc))
    cell.set_property('sensitive', store.get_value(iter,
      PLUGINS_COL_ACTIVATABLE))


def plugin_error_text(plugin):
    """Generate some helpful text about missing module dependencies."""
    if not plugin.error:
        return GnomeConfig.CANLOAD
    # describe missing dependencies
    text = "<b>%s</b>. \n" % GnomeConfig.CANNOTLOAD
    # get lists
    modules = plugin.missing_modules
    dbus = plugin.missing_dbus
    # convert to strings
    if len(modules) > 0:
      modules = "<small><b>%s</b></small>" % ', '.join(modules)
    if len(dbus) > 0:
      ifaces = ["%s:%s" % (a,b) for (a,b) in dbus]
      dbus = "<small><b>%s</b></small>" % ', '.join(ifaces)
      print dbus, len(dbus)
    # combine
    if len(modules) > 0 and len(dbus) == 0:
        text += '\n'.join([GnomeConfig.MODULEMISSING, '', modules])
    elif len(modules) == 0 and len(dbus) > 0:
        text += '\n'.join([GnomeConfig.DBUSMISSING, '', dbus])
    elif len(modules) > 0 and len(dbus) > 0:
        text += '\n'.join([GnomeConfig.MODULANDDBUS, '', modules, dbus])
    else:
        text += GnomeConfig.UNKNOWN
    return text


class PreferencesDialog:

    __AUTOSTART_DIRECTORY = os.path.join(xdg_config_home, "autostart")
    __AUTOSTART_FILE = "gtg.desktop"

    def __init__(self, pengine, p_apis, config_obj):
        """Constructor."""
        self.config_obj = config_obj
        self.config = self.config_obj.conf_dict
        self.builder = gtk.Builder() 
        self.builder.add_from_file(ViewConfig.PREFERENCES_GLADE_FILE)
        # store references to some objects
        widgets = {
          'dialog': 'PreferencesDialog',
          'backend_tree': 'BackendTree',
          'plugin_tree': 'PluginTree',
          'plugin_about_dialog': 'PluginAboutDialog',
          'plugin_configure': 'plugin_configure',
          'plugin_depends': 'PluginDepends',
          'plugin_config_dialog': 'PluginConfigDialog',
          'pref_autostart': 'pref_autostart',
          'pref_show_preview': 'pref_show_preview'
          }
        for attr, widget in widgets.iteritems():
            setattr(self, attr, self.builder.get_object(widget))
        # keep a reference to the parent task browser
        #FIXME: this is not needed and should be removed
#        self.tb = taskbrowser
        self.pengine = pengine
        self.p_apis = p_apis
        # initialize tree models
        self._init_backend_tree()
        # this can't happen yet, due to the order of things in
        #  TaskBrowser.__init__(). Happens in activate() instead.
        # self._init_plugin_tree()
        pref_signals_dic = self.get_signals_dict()
        self.builder.connect_signals(pref_signals_dic)

    def _init_backend_tree(self):
        """Initialize the BackendTree gtk.TreeView."""
        self._refresh_backend_store()
        # TODO

    def _refresh_backend_store(self):
        """Populate a gtk.ListStore with backend information."""
        # create and clear a gtk.ListStore for backend information
        if not hasattr(self, 'backend_store'):
            # TODO: create the liststore. It should have one column for each
            # backend.
            self.backend_store = gtk.ListStore(str)
        self.backend_store.clear()
        # TODO

    def _refresh_plugin_store(self):
        """Populate a gtk.ListStore with plugin information."""
        # create and clear a gtk.ListStore
        if not hasattr(self, 'plugin_store'):
            # see constants PLUGINS_COL_* for column meanings
            self.plugin_store = gtk.ListStore(str, 'gboolean', str, str, str,
              'gboolean',)
        self.plugin_store.clear()
        # refresh the status of all plugins
        self.pengine.recheck_plugin_errors(True)
        # repopulate the store
        for name, p in self.pengine.plugins.iteritems():
            self.plugin_store.append([name, p.enabled, p.full_name,
              p.short_description, p.description, not p.error,]) # activateable if there is no error

    def  _refresh_preferences_store(self):
        """Sets the correct value in the preferences checkboxes"""
        autostart_path = os.path.join(self.__AUTOSTART_DIRECTORY, \
                                      self.__AUTOSTART_FILE)
        self.pref_autostart.set_active(os.path.isfile(autostart_path))
        self.pref_show_preview.set_active(self.config_priv["contents_preview_enable"])


    def _init_plugin_tree(self):
        """Initialize the PluginTree gtk.TreeView.
        
        The format is modelled after the one used in gedit; see
        http://git.gnome.org/browse/gedit/tree/gedit/gedit-plugin-mapnager.c
        
        """
        # force creation of the gtk.ListStore so we can reference it
        self._refresh_plugin_store()

        # renderer for the toggle column
        renderer = gtk.CellRendererToggle()
        renderer.set_property('xpad', 6)
        renderer.connect('toggled', self.on_plugin_toggle)
        # toggle column
        column = gtk.TreeViewColumn(None, renderer, active=PLUGINS_COL_ENABLED,
          activatable=PLUGINS_COL_ACTIVATABLE,
          sensitive=PLUGINS_COL_ACTIVATABLE)
        self.plugin_tree.append_column(column)

        # plugin name column
        column = gtk.TreeViewColumn()
        column.set_spacing(6)
        # icon renderer for the plugin name column
        icon_renderer = gtk.CellRendererPixbuf()
        icon_renderer.set_property('stock-size', gtk.ICON_SIZE_SMALL_TOOLBAR)
        icon_renderer.set_property('xpad', 3)
        column.pack_start(icon_renderer, expand=False)
        column.set_cell_data_func(icon_renderer, plugin_icon)
        # text renderer for the plugin name column
        name_renderer = gtk.CellRendererText()
        name_renderer.set_property('ellipsize', pango.ELLIPSIZE_END)
        column.pack_start(name_renderer)
        column.set_cell_data_func(name_renderer, plugin_markup)

        self.plugin_tree.append_column(column)

        # finish setup
        self.plugin_tree.set_model(self.plugin_store)
        self.plugin_tree.set_search_column(2)

    ## GTK signals & related functions
    def get_signals_dict(self):
        """A dictionary of signals and functions to be connected."""
        SIGNAL_CONNECTIONS_DIC = {
#          'on_preferences_activate':
#            self.activate,
          # buttons in the dialog itself
          'on_prefs_close':
            self.on_close,
          'on_prefs_help':
            self.on_help,
          # preferences on the Tasks tab
          'on_pref_show_preview_toggled':
            self.toggle_preview,
          'on_pref_check_spelling_toggled':
            self.toggle_spellcheck,
          # buttons on the Plugins tab
          'on_PluginTree_cursor_changed':
            self.on_plugin_select,
          'on_plugin_about':
            self.on_plugin_about,
          'on_plugin_configure':
            self.on_plugin_configure,
          # the PluginAboutDialog
          'on_PluginAboutDialog_close':
            self.on_plugin_about_close,
          'on_PluginAboutDialog_response':
            self.on_plugin_about_close,
          # the PluginConfigDialog
          'on_PluginConfigClose_released':
            self.on_plugin_config_close,
          'on_PreferencesDialog_delete_event':
            self.on_close,
            'on_pref_autostart_toggled':
            self.on_autostart_toggled,
          }
        return SIGNAL_CONNECTIONS_DIC

    def activate(self, config_priv, widget=None):
        """Activate the preferences dialog."""
        self.config_priv = config_priv
        if len(self.plugin_tree.get_columns()) == 0:
            # late setup of PluginTree
            self._init_plugin_tree()
        else:
            self._refresh_plugin_store()
        self._refresh_backend_store()
        self._refresh_preferences_store()
        self.dialog.present()
        self.dialog.show_all()

    def on_close(self, widget, data = None):
        """Close the preferences dialog."""

        if len(self.pengine.plugins) > 0:
            self.config["plugins"] = {}
            self.config["plugins"]["disabled"] = \
              self.pengine.disabled_plugins().keys()
            self.config["plugins"]["enabled"] = \
              self.pengine.enabled_plugins().keys()

        self.config_obj.save()

        self.dialog.hide()
        return True

    def on_help(self, widget):
        """Provide help for the preferences dialog."""
        return True

    def on_plugin_about(self, widget):
        """Display information about a plugin."""
        (junk, iter) = self.plugin_tree.get_selection().get_selected()
        if iter == None:
            return
        plugin_id = self.plugin_store.get_value(iter, PLUGINS_COL_ID)
        p = self.pengine.plugins[plugin_id]
        pad = self.plugin_about_dialog
        pad.set_name(p.full_name)
        pad.set_version(p.version)
        authors = p.authors
        if isinstance(authors, str):
            authors = [authors, ]
        pad.set_authors(authors)
        pad.set_comments(p.description.replace(r'\n', "\n"))
        self.plugin_depends.set_label(plugin_error_text(p))
        pad.show_all()

    def on_plugin_about_close(self, widget, *args):
        """Close the PluginAboutDialog."""
        self.plugin_about_dialog.hide()

    def on_plugin_configure(self, widget):
        """Configure a plugin."""
        (junk, iter) = self.plugin_tree.get_selection().get_selected()
        plugin_id = self.plugin_store.get_value(iter, PLUGINS_COL_ID)
        # TODO: load plugin's configuration UI and insert into pc-vbox1 in
        #  position 0. Something like...
        #pcd = self.plugin_config_dialog
        #pcd.show_all()
        # ...for now, use existing code.
        self.pengine.plugins[plugin_id].instance.configure_dialog(
          self.p_apis, self.dialog)

    def on_plugin_config_close(self, widget):
        """Close the PluginConfigDialog."""
        self.plugin_config_dialog.hide()

    def on_plugin_select(self, plugin_tree):
        (model, iter) = plugin_tree.get_selection().get_selected()
        if iter is not None:
            plugin_id = model.get_value(iter, PLUGINS_COL_ID)
            self._update_plugin_configure(self.pengine.plugins[plugin_id])

    def on_plugin_toggle(self, widget, path):
        """Toggle a plugin enabled/disabled."""
        iter = self.plugin_store.get_iter(path)
        plugin_id = self.plugin_store.get_value(iter, PLUGINS_COL_ID)
        p = self.pengine.plugins[plugin_id]
        p.enabled = not self.plugin_store.get_value(iter, PLUGINS_COL_ENABLED)
        if p.enabled:
            self.pengine.activate_plugins(self.p_apis, [p])
        else:
            self.pengine.deactivate_plugins(self.p_apis, [p])
        self.plugin_store.set_value(iter, PLUGINS_COL_ENABLED, p.enabled)
        self._update_plugin_configure(p)
    
    def toggle_preview(self, widget):
        """Toggle previews in the task view on or off."""
        self.config_priv["contents_preview_enable"] = widget.get_active()
    
    def toggle_spellcheck(self, widget):
        """Toggle spell checking on or off."""
        print __name__
    
    def _update_plugin_configure(self, plugin):
        """Enable the "Configure Plugin" button if appropriate."""
        configurable = plugin.active and plugin.is_configurable()
        self.plugin_configure.set_property('sensitive', configurable)

    def on_autostart_toggled(self, widget):
        """Toggle GTG autostarting with the GNOME desktop"""
        autostart_path = os.path.join(self.__AUTOSTART_DIRECTORY, \
                                      self.__AUTOSTART_FILE)
        if widget.get_active() == False: 
            #Disable autostart, removing the file in autostart_path
            if os.path.isfile(autostart_path):
                os.remove(autostart_path)
        else:
            #Enable autostart
            #We look for the desktop file
            desktop_file_path = None
            desktop_file_directories = ["../..",
                                  "../../../applications",
                                  "../../../../../share/applications"]
            this_directory = os.path.dirname(os.path.abspath(__file__))
            for path in desktop_file_directories:
                fullpath = os.path.normpath(os.path.join(this_directory, path, \
                                                        self.__AUTOSTART_FILE))
                if os.path.isfile(fullpath):
                    desktop_file_path = fullpath
                    break
            #If we have found the desktop file, we make a link to in in
            # autostart_path. If symbolic linking is not possible
            # (that is, if we are running on Windows), then copy the file
            if desktop_file_path:
                if not os.path.exists(self.__AUTOSTART_DIRECTORY):
                    os.mkdir(self.__AUTOSTART_DIRECTORY)
                if os.path.isdir(self.__AUTOSTART_DIRECTORY) and \
                   not os.path.exists(autostart_path):
                    if hasattr(os, "symlink"):
                        os.symlink(desktop_file_path, \
                                   autostart_path)
                    else:
                        shutil.copyfile(desktop_file_path, \
                                         autostart_path)
