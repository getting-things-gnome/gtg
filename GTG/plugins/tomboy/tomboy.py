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
import dbus, gobject, dbus.glib

class pluginTest:
    
    def __init__(self):
        pass

	# plugin engine methods	
    def activate(self, plugin_api):
        self.menu_item = gtk.MenuItem("To remove")
        self.menu_item.connect('activate', self.onTesteMenu)
        tb_button_image = gtk.Image()
        tb_button_image_path = "/usr/share/icons/hicolor/16x16/apps/tomboy.png"
        tb_button_pixbuf=gtk.gdk.\
                pixbuf_new_from_file_at_size(tb_button_image_path, 16, 16)
        tb_button_image.show()
        tb_button_image.set_from_pixbuf(tb_button_pixbuf)
        self.tb_button = gtk.ToolButton(tb_button_image)
        self.tb_button.set_label("To remove")
        self.tb_button.connect('clicked', self.onTbButton)
		# add a menu item to the menu bar
        plugin_api.add_menu_item(self.menu_item)
        		
        # saves the separator's index to later remove it
        self.separator = plugin_api.add_toolbar_item(gtk.SeparatorToolItem())
        # add a item (button) to the ToolBar
        plugin_api.add_toolbar_item(self.tb_button)

    def gettargets(self, wid, context, x, y, time):
        print "drop"
        print context
        print wid
        print context.__class__
        for t in context.targets:
            print t
        return True


    def onTaskOpened(self, plugin_api):
        token = 'TOM'
		# add a item (button) to the ToolBar
        self.tb_Taskbutton = gtk.ToolButton(gtk.STOCK_EXECUTE)
        self.tb_Taskbutton.set_label("Hello World")
        self.tb_Taskbutton.connect('clicked', self.onTbTaskButton, plugin_api)
        plugin_api.add_task_toolbar_item(gtk.SeparatorToolItem())
        plugin_api.add_task_toolbar_item(self.tb_Taskbutton)
        self.TARGET_TYPE_TEXT = 80
        textview = plugin_api.get_textview()
        textview.drag_dest_set(0, [], 0)
        textview.connect('drag_motion', self.gettargets)
        #find TOM
        tom_position = 0
        start_iter = textview.buff.get_start_iter()
        end_iter = textview.buff.get_end_iter()
        text = textview.buff.get_text(start_iter,end_iter)
        tom_position = text.find(token,tom_position)
        while not tom_position < 0:
            print tom_position
            if tom_position < 0:
                break
            iter_start = textview.buff.get_iter_at_offset(tom_position )# seetextv.add_mark
            iter_end = textview.buff.get_iter_at_offset(tom_position + len(token))# seetextv.add_mark
            textview.buff.delete(iter_start, iter_end)
            widget =self.widgetCreate()
            widget.connect('clicked', self.tomboyDisplay)
            self.textviewInsertWidget(textview, widget, iter_start)
            start_iter = textview.buff.get_start_iter()
            end_iter = textview.buff.get_end_iter()
            text = textview.buff.get_text(start_iter,end_iter)
            tom_position = text.find(token,tom_position+1)




		
    def deactivate(self, plugin_api):
        plugin_api.remove_menu_item(self.menu_item)
        plugin_api.remove_toolbar_item(self.tb_button)
        plugin_api.remove_toolbar_item(None, self.separator)
		
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
        #self.loadDialog("Hello World! The tag @hello_world was just added to the end of the task!")
        tv = plugin_api.get_textview()
        iter = tv.get_insert()
        if iter.starts_line() :
#            tv.insert_text("|",itera)
            pass
        else :
#            tv.insert_text(" £$",itera)
            widget =self.widgetCreate()
            widget.connect('clicked', self.tomboyDisplay)
            self.textviewInsertWidget(tv, widget, iter)
            tv.grab_focus()

    def widgetCreate(self):
        image = gtk.Image()
        image_path = "/usr/share/icons/hicolor/16x16/apps/tomboy.png"
        pixbuf=gtk.gdk.\
                pixbuf_new_from_file_at_size(image_path, 16, 16)
        image.show()
        image.set_from_pixbuf(pixbuf)
        return gtk.ToolButton(image)

    def tomboyDisplay(self,whatever=False):
        bus = dbus.SessionBus()
        obj = bus.get_object("org.gnome.Tomboy",
                               "/org/gnome/Tomboy/RemoteControl")
        tomboy = dbus.Interface(obj, "org.gnome.Tomboy.RemoteControl")
        # Display the title of every note
        for n in tomboy.ListAllNotes():
            print tomboy.GetNoteTitle(n)
            tomboy.DisplayNote(n)
            print tomboy.GetNoteContents(n)

    def textviewInsertWidget(self, textview, widget, iter):
        anchor = textview.buff.create_child_anchor(iter)
        widget.show()
        textview.add_child_at_anchor(widget, anchor)

    

