# -*- coding: utf-8 -*-
import gtk, pygtk
import os

class pluginTest:

    PLUGIN_NAME = 'Hello World'
    PLUGIN_AUTHORS = 'Paulo Cabido <paulo.cabido@gmail.com>'
    PLUGIN_VERSION = '0.1.1'
    PLUGIN_DESCRIPTION = 'Plugin Description goes here. Helo World!'
    PLUGIN_ENABLED = False

    def __init__(self):
        self.menu_item = gtk.MenuItem("Hello World Plugin")
        self.menu_item.connect('activate', self.onTesteMenu)
		
        self.tb_button = gtk.ToolButton(gtk.STOCK_INFO)
        self.tb_button.set_label("Hello World")
        self.tb_button.connect('clicked', self.onTbButton)
		

	# plugin engine methods	
    def activate(self, plugin_api):
		# add a menu item to the menu bar
        plugin_api.AddMenuItem(self.menu_item)
        		
        # saves the separator's index to later remove it
        self.separator = plugin_api.AddToolbarItem(gtk.SeparatorToolItem())
        # add a item (button) to the ToolBar
        plugin_api.AddToolbarItem(self.tb_button)

    def onTaskOpened(self, plugin_api):
		# add a item (button) to the ToolBar
        self.tb_Taskbutton = gtk.ToolButton(gtk.STOCK_EXECUTE)
        self.tb_Taskbutton.set_label("Hello World")
        self.tb_Taskbutton.connect('clicked', self.onTbTaskButton, plugin_api)
        plugin_api.AddTaskToolbarItem(gtk.SeparatorToolItem())
        plugin_api.AddTaskToolbarItem(self.tb_Taskbutton)
		
    def deactivate(self, plugin_api):
        plugin_api.RemoveMenuItem(self.menu_item)
        plugin_api.RemoveToolbarItem(self.tb_button)
        plugin_api.RemoveToolbarItem(None, self.separator)
		
    #load a dialog with a String
    def loadDialog(self, msg):
        path = os.path.dirname(os.path.abspath(__file__))
        glade_file = os.path.join(path, "hello_world.glade")
        wTree = gtk.glade.XML(glade_file, "helloworld")
        self.dialog = wTree.get_widget("helloworld")
        lblHelloWorld = wTree.get_widget("lbl_helloworld")
        lblHelloWorld.set_text(msg)
        
        self.dialog.connect("delete_event", self.close_dialog)
        self.dialog.connect("response", self.close_dialog)
        
        self.dialog.show_all()
    
    def close_dialog(self, widget, data=None):
    	self.dialog.destroy()
        return True    
	
	# plugin features
    def onTesteMenu(self, widget):
        self.loadDialog("Hello World! From the MenuBar! :-)")
		
    def onTbButton(self, widget):
        self.loadDialog("Hello World! From the ToolBar! :-)")
		
    def onTbTaskButton(self, widget, plugin_api):
        self.loadDialog("Hello World! The tag @hello_world was just added to the end of the task!")
        plugin_api.add_tag("hello_world")
		#plugin_api.add_tag_attribute("@addingtag", "atrrib_teste", "teste")
        
    def teste(self):
        print "TESTE!"
	
