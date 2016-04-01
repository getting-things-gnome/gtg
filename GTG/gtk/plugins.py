# -*- coding: utf-8 -*-
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

""" Dialog for loading plugins """

from gi.repository import Gtk, Pango

from GTG import info
from GTG.core.plugins import GnomeConfig
from GTG.core.plugins.engine import PluginEngine
from GTG.core.translations import _
from GTG.gtk import ViewConfig
from GTG.gtk import help

# columns in PluginsDialog.plugin_store
PLUGINS_COL_ID = 0
PLUGINS_COL_ENABLED = 1
PLUGINS_COL_NAME = 2
PLUGINS_COL_SHORT_DESC = 3
PLUGINS_COL_ACTIVATABLE = 4


def plugin_icon(column, cell, store, iterator, data):
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


class PluginsDialog(object):
    """ Dialog for Plugins configuration """

    def __init__(self, requester):
        self.req = requester
        self.config = self.req.get_config("plugins")
        builder = Gtk.Builder()
        builder.add_from_file(ViewConfig.PLUGINS_UI_FILE)

        self.dialog = builder.get_object("PluginsDialog")
        self.dialog.set_title(_("Plugins - %s" % info.NAME))
        self.plugin_tree = builder.get_object("PluginTree")
        self.plugin_configure = builder.get_object("plugin_configure")
        self.plugin_about = builder.get_object("PluginAboutDialog")
        self.plugin_depends = builder.get_object('PluginDepends')

        help.add_help_shortcut(self.dialog, "plugins")

        self.pengine = PluginEngine()
        # plugin config initiation
        if self.pengine.get_plugins():
            self.config.set(
                "disabled",
                [p.module_name for p in self.pengine.get_plugins("disabled")],
            )
            self.config.set(
                "enabled",
                [p.module_name for p in self.pengine.get_plugins("enabled")],
            )

        # see constants PLUGINS_COL_* for column meanings
        self.plugin_store = Gtk.ListStore(str, bool, str, str, bool)

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
        """ Initialize the PluginTree Gtk.TreeView.

        The format is modelled after the one used in gedit; see
        http://git.gnome.org/browse/gedit/tree/gedit/gedit-plugin-mapnager.c
        """
        # force creation of the Gtk.ListStore so we can reference it
        self._refresh_plugin_store()

        # renderer for the toggle column
        renderer = Gtk.CellRendererToggle()
        renderer.set_property('xpad', 6)
        renderer.connect('toggled', self.on_plugin_toggle)
        # toggle column
        column = Gtk.TreeViewColumn(None, renderer, active=PLUGINS_COL_ENABLED,
                                    activatable=PLUGINS_COL_ACTIVATABLE,
                                    sensitive=PLUGINS_COL_ACTIVATABLE)
        self.plugin_tree.append_column(column)

        # plugin name column
        column = Gtk.TreeViewColumn()
        column.set_spacing(6)
        # icon renderer for the plugin name column
        icon_renderer = Gtk.CellRendererPixbuf()
        icon_renderer.set_property('stock-size', Gtk.IconSize.SMALL_TOOLBAR)
        icon_renderer.set_property('xpad', 3)
        column.pack_start(icon_renderer, False)
        column.set_cell_data_func(icon_renderer, plugin_icon)
        # text renderer for the plugin name column
        name_renderer = Gtk.CellRendererText()
        name_renderer.set_property('ellipsize', Pango.EllipsizeMode.END)
        column.pack_start(name_renderer, True)
        column.set_cell_data_func(name_renderer, plugin_markup, self)

        self.plugin_tree.append_column(column)

        # finish setup
        self.plugin_tree.set_model(self.plugin_store)
        self.plugin_tree.set_search_column(2)

    def _refresh_plugin_store(self):
        """ Refresh status of plugins and put it in a Gtk.ListStore """
        self.plugin_store.clear()
        self.pengine.recheck_plugin_errors(True)
        for name, plugin in self.pengine.plugins.items():
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
        """ Open help for plugins """
        help.show_help("plugins")
        return True

    def on_plugin_toggle(self, widget, path):
        """Toggle a plugin enabled/disabled."""
        iterator = self.plugin_store.get_iter(path)
        plugin_id = self.plugin_store.get_value(iterator, PLUGINS_COL_ID)
        plugin = self.pengine.get_plugin(plugin_id)
        plugin.enabled = not self.plugin_store.get_value(iterator,
                                                         PLUGINS_COL_ENABLED)
        plugins_enabled = self.config.get("enabled")
        plugins_disabled = self.config.get("disabled")
        if plugin.enabled:
            self.pengine.activate_plugins([plugin])
            plugins_enabled.append(plugin.module_name)
            if plugin.module_name in plugins_disabled:
                plugins_disabled.remove(plugin.module_name)
        else:
            self.pengine.deactivate_plugins([plugin])
            plugins_disabled.append(plugin.module_name)
            if plugin.module_name in plugins_enabled:
                plugins_enabled.remove(plugin.module_name)
        self.config.set("enabled", plugins_enabled)
        self.config.set("disabled", plugins_disabled)
        self.plugin_store.set_value(iterator, PLUGINS_COL_ENABLED,
                                    plugin.enabled)
        self._update_plugin_configure(plugin)

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

        # FIXME About plugin dialog looks much more different than
        # it is in the current trunk
        # FIXME repair it!
        # FIXME Author is not usually set and is preserved from
        # previous plugin... :/
        self.plugin_about.set_program_name(plugin.full_name)
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
