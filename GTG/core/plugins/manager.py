# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personnal organizer for the GNOME desktop
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

from GTG.core.plugins 		 import GnomeConfig
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
        self.plugins = plugins
        self.pengine = pengine
        self.plugin_api = plugin_api
        self.gladefile = GnomeConfig.GLADE_FILE
        self.wTree = gtk.glade.XML(self.gladefile, "PluginManagerDialog")
		
        self.dialog = self.wTree.get_widget("PluginManagerDialog")
		
        # stuff to populate
        self.lblPluginName = self.wTree.get_widget("lblPluginName")
        self.lblPluginVersion = self.wTree.get_widget("lblPluginVersion")
        self.lblPluginAuthors = self.wTree.get_widget("lblPluginAuthors")
        self.txtPluginDescription = self.wTree.get_widget("txtPluginDescription")
        
        #self.btnClose = self.wTree.get_widget("close_btn")
        #self.btnClose.connect('clicked', self.close, None)
		
        # liststore
        self.PluginList = gtk.ListStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING)
        for plgin in self.plugins:
            #print "file name :", name
            self.PluginList.append([plgin['state'], plgin['name'], plgin['version']])
        # end - liststore
		
        # treeview
        self.pluginTree = self.wTree.get_widget("pluginTree")
		
        self.rendererToggle = gtk.CellRendererToggle()
        self.rendererToggle.set_property('activatable', True)
        self.rendererToggle.connect('toggled', self.colToggledClicked, self.PluginList)
        self.colToggle = gtk.TreeViewColumn("Enabled", self.rendererToggle)
        self.colToggle.add_attribute(self.rendererToggle, "active", 0)
		
        self.rendererText = gtk.CellRendererText()
        self.colName = gtk.TreeViewColumn("Name", self.rendererText, text=1)
        self.colVersion = gtk.TreeViewColumn("Version", self.rendererText, text=2)
		
        self.pluginTree.append_column(self.colToggle)
        self.pluginTree.append_column(self.colName)
        self.pluginTree.append_column(self.colVersion)
		
        self.pluginTree.set_model(self.PluginList)
        self.pluginTree.set_search_column(2)
        # end - treeview
		
        self.dialog.set_transient_for(parent)
		
        # connect signals 
        self.dialog.connect("delete_event", self.close)
        self.dialog.connect("response", self.close)
        self.pluginTree.connect("cursor-changed", self.pluginExtraInfo, self.plugins)
		
        self.dialog.show_all()
		

    def close(self, widget, response=None):
        # get the plugins that are going to be initialized and the ones
        # that are going do be desabled
        self.pengine.recheckPlugins(self.plugins, self.plugin_api)
        self.dialog.destroy()
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

    def pluginExtraInfo(self, treeview, plugins):
        path = treeview.get_cursor()[0]
        if path:
            model = treeview.get_model()
            iter = treeview.get_model().get_iter(path)
			
            for plgin in plugins:
                if (model.get_value(iter,1) == plgin['name']) and (model.get_value(iter,2) == plgin['version']):
                    self.lblPluginName.set_label("<b>" + plgin['name'] + "</b>")
                    self.lblPluginVersion.set_label(plgin['version'])
                    self.lblPluginAuthors.set_label(plgin['authors'])
                    self.txtPluginDescription.get_buffer().set_text(plgin['description'].replace("\n", " ").replace(r'\n', "\n"))
