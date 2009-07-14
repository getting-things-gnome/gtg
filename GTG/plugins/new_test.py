# -*- coding: utf-8 -*-
import gtk

from GTG.core.plugins.engine import PluginEngine


class NewTest:

	PLUGIN_NAME = 'Another Test'
	PLUGIN_AUTHORS = 'Example Name <developer@example.com>'
	PLUGIN_VERSION = '0.2'
	PLUGIN_DESCRIPTION = 'Yet another plugin for testing proposals. It\'s working ok. :-)'
	PLUGIN_ENABLED = False

	def __init__(self):
		# for testing proposals
		self.test = "test"

	def activate(self, plugin_api):
		# add a menu item to the menu bar
		menu_item = gtk.MenuItem("New Test Menu")
		menu_item.connect('activate', self.onTesteMenu)
		plugin_api.AddMenuItem(menu_item)
		
		# add a item (button) to the ToolBar
		tb_button = gtk.ToolButton(gtk.STOCK_NEW)
		tb_button.connect('clicked', self.onTbButton)
		plugin_api.AddToolbarItem(tb_button)
	
	def onTaskOpened(self, plugin_api):
		print "A task was opened"
		
	def deactivate(self, plugin_api):
		pass
		
	def onTesteMenu(self, widget):
		print "Test Menu activated. You can do an action here like open a new GUI for your plugin."
		
	def onTbButton(self, widget):
		print "Test Button (ToolBar) Clicked. You can do an action here like open a new GUI for your plugin."
	
