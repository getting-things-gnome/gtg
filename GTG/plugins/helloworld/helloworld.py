# -*- coding: utf-8 -*-
# Copyright (c) 2009 - Paulo Cabido <paulo.cabido@gmail.com>
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

import gtk, pygtk
import os

class pluginTest:
    
    def __init__(self):
        self.menu_item = gtk.MenuItem("Hello World Plugin")
        self.menu_item.connect('activate', self.onTesteMenu)
        
        self.tb_button = gtk.ToolButton(gtk.STOCK_INFO)
        self.tb_button.set_label("Hello World")
        self.tb_button.connect('clicked', self.onTbButton)
        self.separator = gtk.SeparatorToolItem()
        self.task_separator = None
        self.tb_Taskbutton = None
        

    # plugin engine methods    
    def activate(self, plugin_api):
        # add a menu item to the menu bar
        plugin_api.add_menu_item(self.menu_item)
                
        # saves the separator's index to later remove it
        plugin_api.add_toolbar_item(self.separator)
        # add a item (button) to the ToolBar
        plugin_api.add_toolbar_item(self.tb_button)

    def onTaskOpened(self, plugin_api):
        # add a item (button) to the ToolBar
        tb_Taskbutton = gtk.ToolButton(gtk.STOCK_EXECUTE)
        tb_Taskbutton.set_label("Hello World")
        tb_Taskbutton.connect('clicked', self.onTbTaskButton, plugin_api)
        self.task_separator = plugin_api.add_task_toolbar_item(gtk.SeparatorToolItem())
        self.tb_Taskbutton = plugin_api.add_task_toolbar_item(tb_Taskbutton)
        
    def deactivate(self, plugin_api):
        plugin_api.remove_menu_item(self.menu_item)
        plugin_api.remove_toolbar_item(self.tb_button)
        plugin_api.remove_toolbar_item(self.separator)
        #everything should be removed, in case a task is currently opened
        plugin_api.remove_task_toolbar_item(self.task_separator)
        plugin_api.remove_task_toolbar_item(self.tb_Taskbutton)
        
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
    
