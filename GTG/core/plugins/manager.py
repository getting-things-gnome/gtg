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
import gobject

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
    
    def __init__(self, parent, plugins, pengine, plugin_api):
        print "PM %s" %self
        self.ploum = "ploum"
        self.plugins = plugins
        self.pengine = pengine
        self.plugin_api = plugin_api
        self.gladefile = GnomeConfig.GLADE_FILE
        self.wTree = gtk.glade.XML(self.gladefile, "PluginManagerDialog")
        
        self.dialog = self.wTree.get_widget("PluginManagerDialog")
        
        # stuff to populate
        self.close_btn = self.wTree.get_widget("close_btn")
        self.config_btn = self.wTree.get_widget("config_btn")
        self.lblPluginName = self.wTree.get_widget("lblPluginName")
        self.lblPluginVersion = self.wTree.get_widget("lblPluginVersion")
        self.lblPluginAuthors = self.wTree.get_widget("lblPluginAuthors")
        self.txtPluginDescription = self.wTree.get_widget("txtPluginDescription")
        
        self.vbox_frame = self.wTree.get_widget("vbox_frame")
        self.box_error = self.wTree.get_widget("box_error")
        self.box_error.hide()
        self.lblErrorTitle = self.wTree.get_widget("lblErrorTitle")
        self.lblPluginMM = self.wTree.get_widget("lblPluginMM")
        #self.btnClose = self.wTree.get_widget("close_btn")
        #self.btnClose.connect('clicked', self.close, None)
        
        # recheck the plugins with errors
        self.pengine.recheckPluginsErrors(self.plugins, self.plugin_api)
        
        # liststore
        self.PluginList = gtk.ListStore('gboolean', str, str, 'gboolean', 'gboolean')
        
        for plgin in self.plugins:
            if not plgin['error']:
                self.PluginList.append([plgin['state'], plgin['name'], plgin['version'], True, False])
            else:
                self.PluginList.append([plgin['state'], plgin['name'], plgin['version'], False, True])
        # end - liststore
        
        # treeview
        self.pluginTree = self.wTree.get_widget("pluginTree")
        
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
        
        self.dialog.show_all()
        

    def close(self, widget, response=None):
        # get the plugins that are going to be initialized and the ones
        # that are going do be desabled
#        if self.pengine:
#            self.pengine.recheckPlugins(self.plugins, self.plugin_api)
        print "calling close on %s" %self
        self.dialog.destroy()
        return True

    def colToggledClicked(self, cell, path, model):
        if path and model[path]:
            model[path][0] = not model[path][0]
            iter = model.get_iter(path)
            for plgin in self.plugins:
                if model[path][1] == plgin['name'] and model[path][2] == plgin['version']:
                    plgin['state'] = not plgin['state']
                    #we instantly apply the plugin activation/deactivation
                    #to respect HIG
                    if plgin['state'] :
                        self.pengine.activatePlugins([plgin], self.plugin_api)
                    else :
                        self.pengine.deactivatePlugins([plgin], self.plugin_api)
                    
                    

    def pluginExtraInfo(self, treeview, plugins):
        path = treeview.get_cursor()[0]
        if path:
            model = treeview.get_model()
            iter = treeview.get_model().get_iter(path)
            for plgin in plugins:
                if (model.get_value(iter,1) == plgin['name']) \
                    and (model.get_value(iter,2) == plgin['version']):
                    
                    self.lblPluginName.set_label("<b>" + plgin['name'] + "</b>")
                    self.lblPluginVersion.set_label(plgin['version'])
                    self.lblPluginAuthors.set_label(plgin['authors'])
                    self.txtPluginDescription.get_buffer().set_text(\
                                plgin['description'].replace("\n", " ").replace(r'\n', "\n"))
                    
                    if plgin['error']:
                        # set the title label
                        if plgin['missing_modules'] and \
                                            not plgin['missing_dbus']:
                            self.lblErrorTitle.set_markup(\
                               "<small><b>The plugin can not be loaded</b>. \n"
                                "Some modules are missing:</small>")
                        elif plgin['missing_dbus'] and not plgin['missing_modules']:
                            self.lblErrorTitle.set_markup(\
                                "<small><b>The plugin can not be loaded</b>. \n"
                                "Some remote dbus objects are missing:</small>")
                        elif plgin['missing_modules'] and plgin['missing_dbus']:
                            self.lblErrorTitle.set_markup("<small><b>The plugin can not be loaded</b>. \n"
                                                          "Some modules and remote dbus objects are missing:</small>")
                        else:
                            self.lblErrorTitle.set_markup("<small><b>The plugin can not be loaded</b>. \n"
                                                          "Unknown error while loading the plugin.</small>")
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
        self.current_plugin['instance'].configure_dialog(self.plugin_api)

