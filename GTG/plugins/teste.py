# -*- coding: utf-8 -*-
import gtk

from GTG.core.plugins.engine import PluginEngine


class pluginTest:

	PLUGIN_NAME = 'Test'
	PLUGIN_AUTHORS = 'Paulo Cabido <paulo.cabido@gmail.com>'
	PLUGIN_VERSION = '0.1'
	PLUGIN_DESCRIPTION = 'Plugin Description goes here. Yay!'
	PLUGIN_ENABLED = True

	def __init__(self):
		self.menu_item = gtk.MenuItem("Test Menu")
		self.menu_item.connect('activate', self.onTesteMenu)
		
		self.tb_button = gtk.ToolButton(gtk.STOCK_EXECUTE)
		self.tb_button.connect('clicked', self.onTbButton)
		
		

	# plugin engine methods
	def activate(self, plugin_api):
		# add a menu item to the menu bar
		plugin_api.AddMenuItem(self.menu_item)
		
		# add a item (button) to the ToolBar
		plugin_api.AddToolbarItem(self.tb_button)
	
	def onTaskOpened(self, plugin_api):
		# add a item (button) to the ToolBar
		self.tb_Taskbutton = gtk.ToolButton(gtk.STOCK_HELP)
		self.tb_Taskbutton.connect('clicked', self.onTbTaskButton, plugin_api)
		plugin_api.AddTaskToolbarItem(self.tb_Taskbutton)
		
	def deactivate(self, plugin_api):
		plugin_api.RemoveMenuItem(self.menu_item)
		plugin_api.RemoveToolbarItem(self.tb_button)
		
		
	# plugin features
	def onTesteMenu(self, widget):
		print "Test Menu activated. You can do an action here like open a new GUI for your plugin."
		
	def onTbButton(self, widget):
		print "Test Button (ToolBar) Clicked. You can do an action here like open a new GUI for your plugin."
		
	def onTbTaskButton(self, widget, plugin_api):
		print "Test Button (Task ToolBar) Clicked. You can do an action here like open a new GUI for your plugin."
		plugin_api.add_tag("addingtag")
		plugin_api.add_tag_attribute("@addingtag", "atrrib_teste", "teste")
	
