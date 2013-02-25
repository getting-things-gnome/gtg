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

""" Dialog for configuring plugins """

import gtk
import pango

from GTG import _
from GTG import info
from GTG.core.plugins import GnomeConfig
from GTG.core.plugins.engine import PluginEngine
from GTG.gtk import ViewConfig

# columns in PluginsDialog.plugin_store
PLUGINS_COL_ID = 0
PLUGINS_COL_ENABLED = 1
PLUGINS_COL_NAME = 2
PLUGINS_COL_SHORT_DESC = 3
PLUGINS_COL_ACTIVATABLE = 4


def plugin_icon(column, cell, store, iterator):
    """ Callback to set the content of a PluginTree cell.

    See PluginsDialog._init_plugin_tree().
    """
    cell.set_property('icon-name', 'gtg-plugin')
    cell.set_property('sensitive',
                      store.get_value(iterator, PLUGINS_COL_ACTIVATABLE))


def plugin_error_short_text(plugin):
    """ Return small version of description of missing module dependencies
    for displaying in plugin markup """
    if not plugin.error:
        return ""

    # get lists
    modules = plugin.missing_modules
    dbus = plugin.missing_dbus

    # convert to strings
    if modules:
        modules = "<small><b>%s</b></small>" % ', '.join(modules)
    if dbus:
        ifaces = ["%s:%s" % (a, b) for (a, b) in dbus]
        dbus = "<small><b>%s</b></small>" % ', '.join(ifaces)

    # combine
    if modules and not dbus:
        text = '\n'.join((GnomeConfig.miss2, modules))
    elif dbus and not modules:
        text = '\n'.join((GnomeConfig.dmiss2, dbus))
    elif modules and dbus:
        text = '\n'.join((GnomeConfig.bmiss2, modules, dbus))
    else:
        text = ""

    return text


def plugin_error_text(plugin):
    """ Generate some helpful text about missing module dependencies. """
    if not plugin.error:
        return GnomeConfig.CANLOAD

    # describe missing dependencies
    text = "<b>%s</b>. \n" % GnomeConfig.CANNOTLOAD
    # get lists
    modules = plugin.missing_modules
    dbus = plugin.missing_dbus

    # convert to strings
    if modules:
        modules = "<small><b>%s</b></small>" % ', '.join(modules)
    if dbus:
        ifaces = ["%s:%s" % (a, b) for (a, b) in dbus]
        dbus = "<small><b>%s</b></small>" % ', '.join(ifaces)

    # combine
    if modules and not dbus:
        text += '\n'.join((GnomeConfig.MODULEMISSING, modules))
    elif dbus and not modules:
        text += '\n'.join((GnomeConfig.DBUSMISSING, dbus))
    elif modules and dbus:
        text += '\n'.join((GnomeConfig.MODULANDDBUS, modules, dbus))
    else:
        text += GnomeConfig.UNKNOWN

    return text


def plugin_markup(column, cell, store, iterator, self):

    """ Callback to set the content of a PluginTree cell.

    See PluginsDialog._init_plugin_tree().
    """
    name = store.get_value(iterator, PLUGINS_COL_NAME)
    desc = store.get_value(iterator, PLUGINS_COL_SHORT_DESC)

    plugin_id = store.get_value(iterator, PLUGINS_COL_ID)
    plugin = self.pengine.get_plugin(plugin_id)
    error_text = plugin_error_short_text(plugin)
    if error_text != "":
        text = "<b>%s</b>\n%s\n<i>%s</i>" % (name, desc, error_text)
    else:
        text = "<b>%s</b>\n%s" % (name, desc)

    cell.set_property('markup', text)
    cell.set_property('sensitive',
                      store.get_value(iterator, PLUGINS_COL_ACTIVATABLE))


class PluginsDialog:
    """ Dialog for Plugins configuration """

    def __init__(self, config_obj):
        self.config_obj = config_obj
        self.config = self.config_obj.conf_dict
        builder = gtk.Builder()
        builder.add_from_file(ViewConfig.PLUGINS_GLADE_FILE)

        self.dialog = builder.get_object("PluginsDialog")
        self.dialog.set_title(_("Plugins - %s" % info.NAME))
        self.plugin_tree = builder.get_object("PluginTree")
        self.plugin_configure = builder.get_object("plugin_configure")
        self.plugin_about = builder.get_object("PluginAboutDialog")
        self.plugin_depends = builder.get_object('PluginDepends')

        self.pengine = PluginEngine()
        # plugin config initiation, if never used
        if "plugins" in self.config:
            if "enabled" not in self.config["plugins"]:
                self.config["plugins"]["enabled"] = []

            if "disabled" not in self.config["plugins"]:
                self.config["plugins"]["disabled"] = []
        elif self.pengine.get_plugins():
            self.config["plugins"] = {}
            self.config["plugins"]["disabled"] = \
                [p.module_name for p in self.pengine.get_plugins("disabled")]
            self.config["plugins"]["enabled"] = \
                [p.module_name for p in self.pengine.get_plugins("enabled")]

        # see constants PLUGINS_COL_* for column meanings
        self.plugin_store = gtk.ListStore(str, bool, str, str, bool)

        builder.connect_signals({
                                'on_plugins_help':
                                self.on_help,
                                'on_plugins_close':
                                self.on_close,
                                'on_PluginsDialog_delete_event':
                                self.on_close,
                                'on_PluginTree_cursor_changed':
                                self.on_plugin_select,
                                'on_plugin_about':
                                self.on_plugin_about,
                                'on_plugin_configure':
                                self.on_plugin_configure,
                                'on_PluginAboutDialog_close':
                                self.on_plugin_about_close,
                                })

    def _init_plugin_tree(self):
        """ Initialize the PluginTree gtk.TreeView.

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
        column.set_cell_data_func(name_renderer, plugin_markup, self)

        self.plugin_tree.append_column(column)

        # finish setup
        self.plugin_tree.set_model(self.plugin_store)
        self.plugin_tree.set_search_column(2)

    def _refresh_plugin_store(self):
        """ Refresh status of plugins and put it in a gtk.ListStore """
        self.plugin_store.clear()
        self.pengine.recheck_plugin_errors(True)
        for name, plugin in self.pengine.plugins.iteritems():
            # activateable if there is no error
            self.plugin_store.append((name, plugin.enabled, plugin.full_name,
                                      plugin.short_description,
                                      not plugin.error))

    def activate(self):
        """ Refresh status of plugins and show the dialog """
        if len(self.plugin_tree.get_columns()) == 0:
            self._init_plugin_tree()
        else:
            self._refresh_plugin_store()
        self.dialog.show_all()

    def on_close(self, widget, data=None):
        """ Close the plugins dialog."""
        self.dialog.hide()
        return True

    @classmethod
    def on_help(cls, widget):
        """ In future, this will open help for plugins """
        return True

    def on_plugin_toggle(self, widget, path):
        """Toggle a plugin enabled/disabled."""
        iterator = self.plugin_store.get_iter(path)
        plugin_id = self.plugin_store.get_value(iterator, PLUGINS_COL_ID)
        plugin = self.pengine.get_plugin(plugin_id)
        plugin.enabled = not self.plugin_store.get_value(iterator,
                                                         PLUGINS_COL_ENABLED)
        if plugin.enabled:
            self.pengine.activate_plugins([plugin])
            self.config["plugins"]["enabled"].append(plugin.module_name)
            if plugin.module_name in self.config["plugins"]["disabled"]:
                self.config["plugins"]["disabled"].remove(plugin.module_name)
        else:
            self.pengine.deactivate_plugins([plugin])
            self.config["plugins"]["disabled"].append(plugin.module_name)
            if plugin.module_name in self.config["plugins"]["enabled"]:
                self.config["plugins"]["enabled"].remove(plugin.module_name)
        self.plugin_store.set_value(iterator, PLUGINS_COL_ENABLED,
                                    plugin.enabled)
        self._update_plugin_configure(plugin)

        self.config_obj.save()

    def on_plugin_select(self, plugin_tree):
        """ Callback when user select/unselect a plugin

        Update the button "Configure plugin" sensitivity """
        model, iterator = plugin_tree.get_selection().get_selected()
        if iterator is not None:
            plugin_id = model.get_value(iterator, PLUGINS_COL_ID)
            plugin = self.pengine.get_plugin(plugin_id)
            self._update_plugin_configure(plugin)

    def _update_plugin_configure(self, plugin):
        """ Enable the button "Configure Plugin" appropriate. """
        configurable = plugin.active and plugin.is_configurable()
        self.plugin_configure.set_property('sensitive', configurable)

    def on_plugin_configure(self, widget):
        """ Show the dialog for plugin configuration """
        _, iterator = self.plugin_tree.get_selection().get_selected()
        if iterator is None:
            return
        plugin_id = self.plugin_store.get_value(iterator, PLUGINS_COL_ID)
        plugin = self.pengine.get_plugin(plugin_id)
        plugin.instance.configure_dialog(self.dialog)

    def on_plugin_about(self, widget):
        """ Display information about a plugin. """
        _, iterator = self.plugin_tree.get_selection().get_selected()
        if iterator is None:
            return
        plugin_id = self.plugin_store.get_value(iterator, PLUGINS_COL_ID)
        plugin = self.pengine.get_plugin(plugin_id)

        self.plugin_about.set_name(plugin.full_name)
        self.plugin_about.set_version(plugin.version)
        authors = plugin.authors
        if isinstance(authors, str):
            authors = "\n".join(author.strip()
                                for author in authors.split(','))
            authors = [authors, ]
        self.plugin_about.set_authors(authors)
        description = plugin.description.replace(r'\n', "\n")
        self.plugin_about.set_comments(description)
        self.plugin_depends.set_label(plugin_error_text(plugin))
        self.plugin_about.show_all()

    def on_plugin_about_close(self, widget, data=None):

        """ Close the PluginAboutDialog. """
        self.plugin_about.hide()
        return True
