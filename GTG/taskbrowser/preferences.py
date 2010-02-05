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
import gtk
import pango

from GTG                     import _
from GTG.taskbrowser         import GnomeConfig
#from GTG.core.plugins.engine import PluginEngine
#from GTG.core.plugins.api    import PluginAPI


__all__ = [
  'PreferencesDialog',
  ]


PLUGINS_COL_ID = 0
PLUGINS_COL_STATE = 1
PLUGINS_COL_NAME = 2
PLUGINS_COL_DESC = 3
PLUGINS_COL_ACTIVATABLE = 4


def plugin_icon(column, cell, store, iter):
    """Callback to set the content of a PluginTree cell.
    
    See PreferencesDialog._init_plugin_tree().
    
    """
    cell.set_property('stock-id', gtk.STOCK_CONNECT)
    cell.set_property('sensitive', store.get_value(iter,
      PLUGINS_COL_ACTIVATABLE))


def plugin_markup(column, cell, store, iter):
    """Callback to set the content of a PluginTree cell.
    
    See PreferencesDialog._init_plugin_tree().
    
    """
    name = store.get_value(iter, PLUGINS_COL_NAME)
    desc = store.get_value(iter, PLUGINS_COL_DESC)
    cell.set_property('markup', "<b>%s</b>\n%s" % (name, desc))
    cell.set_property('sensitive', store.get_value(iter,
      PLUGINS_COL_ACTIVATABLE))


class PreferencesDialog:
    def __init__(self, taskbrowser):
        # store references to some objects
        widgets = {
          'dialog': 'PreferencesDialog',
          'backend_tree': 'BackendTree',
          'plugin_tree': 'PluginTree',
          'plugin_about_dialog': 'PluginAboutDialog',
          'plugin_configure': 'plugin_configure',
          'plugin_depends': 'PluginDepends'
#          'plugin_config_dialog': 'PluginConfigDialog',
          }
        for attr, widget in widgets.iteritems():
            setattr(self, attr, taskbrowser.builder.get_object(widget))
        # keep a reference to the parent task browser
        self.tb = taskbrowser
        # initialize tree models
        self._init_backend_tree()
        # self._init_plugin_tree()

    def _init_backend_tree(self):
        self._refresh_backend_store()
        # TODO

    def _refresh_backend_store(self):
        # create and clear a gtk.ListStore for backend information
        if not hasattr(self, 'backend_store'):
            # TODO
            self.backend_store = gtk.ListStore(str)
        self.backend_store.clear()
        # TODO

    def _refresh_plugin_store(self):
        # create and clear a gtk.ListStore for plugin information
        if not hasattr(self, 'plugin_store'):
            # see constants PLUGINS_COL_* for column meanings
            self.plugin_store = gtk.ListStore(str, 'gboolean', str, str,
              'gboolean',)
        self.plugin_store.clear()
        # refresh the status of all plugins
        self.tb.pengine.recheckPluginsErrors(self.tb.plugins, self.tb.p_apis,
          checkall=True)
        # repopulate the ListStore
        for p in self.tb.plugins:
            self.plugin_store.append([p['plugin'], p['state'], p['name'],
              p['description'],
              not p['error'],]) # activateable if there is no error

    def _init_plugin_tree(self):
        """Initialize the PluginTree gtk.TreeView.
        
        The format is modelled after the one used in gedit; see
        http://git.gnome.org/browse/gedit/tree/gedit/gedit-plugin-manager.c
        
        """
        # force creation of the gtk.ListStore so we can reference it
        self._refresh_plugin_store()

        # renderer for the toggle column
        renderer = gtk.CellRendererToggle()
        renderer.set_property('xpad', 6)
        renderer.connect('toggled', self.on_plugin_toggle)
        # toggle column
        column = gtk.TreeViewColumn(None, renderer, active=PLUGINS_COL_STATE,
          activatable=PLUGINS_COL_ACTIVATABLE,
          sensitive=PLUGINS_COL_ACTIVATABLE)
        self.plugin_tree.append_column(column)

        # plugin name column
        column = gtk.TreeViewColumn()
        column.set_spacing(6)
        # icon renderer for the plugin name column
        icon_renderer = gtk.CellRendererPixbuf()
        icon_renderer.set_property('stock-size', gtk.ICON_SIZE_SMALL_TOOLBAR)
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
          'on_preferences_activate':
            self.activate,
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
          }
        return SIGNAL_CONNECTIONS_DIC

    def activate(self, widget):
        """Activate the preferences dialog."""
        if len(self.plugin_tree.get_columns()) == 0:
            # late setup of PluginTree
            self._init_plugin_tree()
        else:
            self._refresh_plugin_store()
        self._refresh_backend_store()
        self.dialog.present()
        self.dialog.show_all()

    def on_close(self, widget):
        """Close the preferences dialog."""
        self.dialog.hide()
        return True

    def on_help(self, widget):
        """Provide help for the preferences dialog."""
        return True

    def on_plugin_about(self, widget):
        """Display information about a plugin."""
        (junk, iter) = self.plugin_tree.get_selection().get_selected()
        plugin_id = self.plugin_store.get_value(iter, PLUGINS_COL_ID)
        # TODO: turn the plugins list into a dict. Would rather do:
        #  p = self.tb.pm.get_plugin_by_name(plugin_id)
        for i in range(len(self.tb.plugins)):
            if self.tb.plugins[i]['plugin'] == plugin_id:
                p = self.tb.plugins[i]
                break
        # p contains data on the currently selected plugin.
        pad = self.plugin_about_dialog
        pad.set_name(p['name'])
        pad.set_version(p['version'])
        pad.set_authors(p['authors'])
        pad.set_comments(p['description'])
        # TODO: display dependencies here per PluginManager.pluginExtraInfo()
        self.plugin_depends.set_label("Here is some <b>bold</b> text\nand a line break.")
        pad.show_all()

    def on_plugin_about_close(self, widget):
        """Close the PluginAboutDialog."""
        self.plugin_about_dialog.hide()

    def on_plugin_configure(self, widget):
        """Configure a plugin."""
        print __name__

    def on_plugin_select(self, plugin_tree):
        (model, iter) = plugin_tree.get_selection().get_selected()
        if iter is not None:
            enabled = model.get_value(iter, PLUGINS_COL_STATE)
            self.plugin_configure.set_property('sensitive', enabled)

    def on_plugin_toggle(self, widget, path):
        """Toggle a plugin enabled/disabled."""
        iter = self.plugin_store.get_iter(path)
        plugin_id = self.plugin_store.get_value(iter, PLUGINS_COL_ID)
        enabled = self.plugin_store.get_value(iter, PLUGINS_COL_STATE)
        # see complaint above in on_plugin_about()...
        for i in range(len(self.tb.plugins)):
            if self.tb.plugins[i]['plugin'] == plugin_id:
                p = self.tb.plugins[i]
                break
        # ...end complaint
        if enabled:
            self.tb.pengine.activatePlugins([p], self.tb.plugin_apis)
        else:
            self.tb.pengine.deactivatePlugins([p], self.tb.plugin_apis)

    def toggle_preview(self, widget):
        """Toggle previews in the task view on or off."""
        print __name__

    def toggle_spellcheck(self, widget):
        """Toggle spell checking on or off."""
        print __name__

