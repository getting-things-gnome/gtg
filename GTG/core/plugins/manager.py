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

from GTG.core.plugins          import GnomeConfig
# not being used
#from GTG.core.plugins.engine import PluginEngine
#from GTG.core.plugins.engine import PluginAPI

import sys

try:
    import pygtk
    pygtk.require("2.0")
except:
    sys.exit(1)
try:
    import gtk
except:
    sys.exit(1)

class PluginManager:
    
    def __init__(self, parent, plugins, pengine, plugin_apis):
        self.plugins = plugins
        self.pengine = pengine
        self.plugin_apis = plugin_apis
        self.builder = gtk.Builder() 
        self.builder.add_from_file(GnomeConfig.GLADE_FILE)
        
        self.dialog = self.builder.get_object("PluginManagerDialog")
        
        # stuff to populate
        self.close_btn = self.builder.get_object("close_btn")
        self.config_btn = self.builder.get_object("config_btn")
        self.lblPluginName = self.builder.get_object("lblPluginName")
        self.lblPluginVersion = self.builder.get_object("lblPluginVersion")
        self.lblPluginAuthors = self.builder.get_object("lblPluginAuthors")
        self.txtPluginDescription = self.builder.get_object("txtPluginDescription")
        
        self.vbox_frame = self.builder.get_object("vbox_frame")
        self.box_error = self.builder.get_object("box_error")
        self.box_error.hide()
        self.lblErrorTitle = self.builder.get_object("lblErrorTitle")
        self.lblPluginMM = self.builder.get_object("lblPluginMM")
        #self.btnClose = self.builder.get_object("close_btn")
        #self.btnClose.connect('clicked', self.close, None)
        
#        # recheck the plugins with errors
#        self.pengine.recheckPluginsErrors(self.plugins, self.plugin_apis)
        
        # liststore
        self.PluginList = gtk.ListStore('gboolean', str, str, 'gboolean', 'gboolean')
        
#        for plgin in self.plugins:
#            if not plgin['error']:
#                self.PluginList.append([plgin['state'], plgin['name'], plgin['version'], True, False])
#            else:
#                self.PluginList.append([plgin['state'], plgin['name'], plgin['version'], False, True])
        # end - liststore
        
        # treeview
        self.pluginTree = self.builder.get_object("pluginTree")
        
        self.rendererToggle = gtk.CellRendererToggle()
        self.rendererToggle.set_property('activatable', True)
        self.rendererToggle.connect('toggled', self.colToggledClicked, self.PluginList)
        
        self.colToggle = gtk.TreeViewColumn("Enabled", self.rendererToggle)
        self.colToggle.add_attribute(self.rendererToggle, "active", 0)
        self.colToggle.add_attribute(self.rendererToggle, "activatable", 3)
        
        self.rendererName = gtk.CellRendererText()
        self.rendererName.set_property('foreground', 'gray')
        self.colName = gtk.TreeViewColumn("Name", self.rendererName, text=1, foreground_set=4)
        
        self.rendererVersion = gtk.CellRendererText()
        self.rendererVersion.set_property('foreground', 'gray')
        self.colVersion = gtk.TreeViewColumn("Version", self.rendererVersion, text=2, foreground_set=4)
        
        self.pluginTree.append_column(self.colToggle)
        self.pluginTree.append_column(self.colName)
        self.pluginTree.append_column(self.colVersion)
        
        self.pluginTree.set_model(self.PluginList)
        self.pluginTree.set_search_column(2)
        # end - treeview
        
        # properties
        
        self.dialog.set_transient_for(parent)
        self.config_btn.set_sensitive(False)
        
        # connect signals 
        self.dialog.connect("delete_event", self.close)
        self.close_btn.connect("clicked", self.close)
        self.pluginTree.connect("cursor-changed", self.pluginExtraInfo, self.plugins)
        self.config_btn.connect("clicked", self.plugin_configure_dialog)
        self.present()
        self.dialog.show_all()
        
        
    def present(self):
        # recheck the plugins with errors
        #doing this reset all plugin state to False
        self.pengine.recheckPluginsErrors(self.plugins, self.plugin_apis,checkall=True)
        self.PluginList.clear()
        
        for plgin in self.plugins:
            if not plgin['error']:
                self.PluginList.append([plgin['state'], plgin['name'], plgin['version'], True, False])
            else:
                self.PluginList.append([plgin['state'], plgin['name'], plgin['version'], False, True])
        
        self.dialog.present()

    def close(self, widget, response=None):
        # get the plugins that are going to be initialized and the ones
        # that are going do be desabled
        self.pengine.recheckPlugins(self.plugins, self.plugin_apis)
        self.dialog.hide()
        return True
    
    #def delete(self, widget, response=None):
    #    self.dialog.destroy()
    #    return True

    def colToggledClicked(self, cell, path, model):
        model[path][0] = not model[path][0]
        if path:
            iter = model.get_iter(path)
            for plgin in self.plugins:
                if model[path][1] == plgin['name'] and model[path][2] == plgin['version']:
                    plgin['state'] = not plgin['state']
                    #we instantly apply the plugin activation/deactivation
                    #to respect HIG
                    if plgin['state']:
                        self.pengine.activatePlugins([plgin], self.plugin_apis)
                    else:
                        self.pengine.deactivatePlugins([plgin], self.plugin_apis)
                    

    def pluginExtraInfo(self, treeview, plugins):
        path = treeview.get_cursor()[0]
        if path:
            model = treeview.get_model()
            iter = treeview.get_model().get_iter(path)
            
            for plgin in plugins:
                if (model.get_value(iter,1) == plgin['name']) and \
                        (model.get_value(iter,2) == plgin['version']):
                    self.lblPluginName.set_label("<b>" + plgin['name'] + "</b>")
                    self.lblPluginVersion.set_label(plgin['version'])
                    self.lblPluginAuthors.set_label(plgin['authors'])
                    self.txtPluginDescription.get_buffer().set_text(
                                plgin['description'].replace("\n", " ").replace(r'\n', "\n"))
                    
                    if plgin['error']:
                        # set the title label
                        cantload = "<small><b>%s</b>. \n" %GnomeConfig.CANNOTLOAD
                        if plgin['missing_modules'] and not plgin['missing_dbus']:
                            self.lblErrorTitle.set_markup(
                                    cantload+
                                    "%s</small>" %GnomeConfig.MODULEMISSING)
                                    
                        elif plgin['missing_dbus'] and not plgin['missing_modules']:
                            self.lblErrorTitle.set_markup(
                                    cantload+
                                    "%s</small>" %GnomeConfig.DBUSMISSING)
                        elif plgin['missing_modules'] and plgin['missing_dbus']:
                            self.lblErrorTitle.set_markup(
                                    cantload+
                                    "%s</small>" %GnomeConfig.MODULANDDBUS)
                        else:
                            self.lblErrorTitle.set_markup(
                                    cantload+
                                    "%s</small>" %GnomeConfig.UNKNOWN)
                            self.box_error.show_all()
                            
                        #set the missing/info
                        if plgin['missing_modules'] and not plgin['missing_dbus']:
                            missing = ""
                            for element in plgin['missing_modules']:
                                missing = missing + ", " + element
                            
                            self.lblPluginMM.set_markup("<small><b>" + missing[2:] + "</b></small>")
                            self.lblPluginMM.set_line_wrap(True)
                            self.box_error.show_all()
                        elif plgin['missing_dbus'] and not plgin['missing_modules']:
                            missing_dbus = ""
                            for element in plgin['missing_dbus']:
                                missing_dbus = missing_dbus + "; " + str(element)
                            
                            self.lblPluginMM.set_markup("<small><b>" + missing_dbus[2:] + "</b></small>")
                            self.box_error.show_all()
                        elif plgin['missing_modules'] and plgin['missing_dbus']:
                            missing = ""
                            for element in plgin['missing_modules']:
                                missing = missing + ", " + element
                            
                            missing_dbus = ""
                            for element in plgin['missing_dbus']:
                                missing_dbus = missing_dbus + "; " + str(element)
                                
                            self.lblPluginMM.set_markup("<small><b>" + missing[2:] + "</b>\n\n" + "<b>" + missing_dbus[2:] + "</b></small>")
                    else:
                        self.box_error.hide()
                        
                    try:
                        if plgin['state']:
                            if not plgin['instance']:
                                plgin['instance'] = plgin['class']()
                                
                            if plgin['instance'].is_configurable():
                                self.config_btn.set_sensitive(True)
                                self.current_plugin = plgin
                        else:
                            self.config_btn.set_sensitive(False)
                    except Exception, e:
                        self.config_btn.set_sensitive(False)
                        
    def plugin_configure_dialog(self, widget, data=None):
        self.current_plugin['instance'].configure_dialog(self.plugin_apis, self.dialog)

