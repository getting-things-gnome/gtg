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
import pickle

class pluginTest:
    
    def __init__(self):
        self.token_start = 'TOM'
        self.token_end = '|'

	# plugin engine methods	
    def activate(self, plugin_api):
        self.plugin_api = plugin_api
        #        self.menu_item = gtk.MenuItem("To remove")
        #self.menu_item.connect('activate', self.onTesteMenu)
#        tb_button_image = gtk.Image()
#        tb_button_image_path = "/usr/share/icons/hicolor/16x16/apps/tomboy.png"
#        tb_button_pixbuf=gtk.gdk.\
#                pixbuf_new_from_file_at_size(tb_button_image_path, 16, 16)
#        tb_button_image.show()
#        tb_button_image.set_from_pixbuf(tb_button_pixbuf)
#        self.tb_button = gtk.ToolButton(tb_button_image)
#        self.tb_button.set_label("To remove")
#        self.tb_button.connect('clicked', self.onTbButton)
		# add a menu item to the menu bar
        #        plugin_api.add_menu_item(self.menu_item)
        		
        # saves the separator's index to later remove it
        #self.separator = plugin_api.add_toolbar_item(gtk.SeparatorToolItem())
        # add a item (button) to the ToolBar
        #plugin_api.add_toolbar_item(self.tb_button)
        pass

    def gettargets(self, wid, context, x, y, time):
        print "drop"
        print context
        print context.source_window.title
        print wid
        print context.__class__
        for t in context.targets:
            print t
        return True

    def onTaskClosed(self, plugin_api):
        textview = plugin_api.get_textview()
        for anchor in self.anchors:
            widgets =  anchor.get_widgets()
            iter_start = textview.buff.get_iter_at_child_anchor(anchor)
            iter_end = iter_start.copy()
            iter_end.forward_char()
            if type(widgets) == list and len(widgets) !=0:
                widget = widgets[0]
                textview.buff.delete(iter_start,iter_end)
                textview.buff.insert(iter_start,self.token_start+ widget.tomboy_note_title+self.token_end)

        start_iter = textview.buff.get_start_iter()
        end_iter = textview.buff.get_end_iter()
        print  "AA"+textview.buff.get_text(start_iter,end_iter)



    def onTaskOpened(self, plugin_api):
		# add a item (button) to the ToolBar, with a nice icon
        tb_Taskbutton_image = gtk.Image()
        tb_Taskbutton_image_path = "/usr/share/icons/hicolor/16x16/apps/tomboy.png"
        tb_Taskbutton_pixbuf=gtk.gdk.\
                pixbuf_new_from_file_at_size(tb_Taskbutton_image_path, 16, 16)
        tb_Taskbutton_image.set_from_pixbuf(tb_Taskbutton_pixbuf)
        tb_Taskbutton_image.show()
        self.tb_Taskbutton = gtk.ToolButton(tb_Taskbutton_image)
        self.tb_Taskbutton.set_label("Add Tomboy note")
        self.tb_Taskbutton.connect('clicked', self.onTbTaskButton, plugin_api)
        plugin_api.add_task_toolbar_item(gtk.SeparatorToolItem())
        plugin_api.add_task_toolbar_item(self.tb_Taskbutton)
        #drag and drop support
        self.TARGET_TYPE_TEXT = 80
        textview = plugin_api.get_textview()
        self.textview = textview
        textview.drag_dest_set(0, [], 0)
        textview.connect('drag_motion', self.gettargets)
        #convert tokens in text to images
        self.anchors=[]
        start_iter = textview.buff.get_start_iter()
        end_iter = textview.buff.get_end_iter()
        text = textview.buff.get_slice(start_iter,end_iter)
        text_offset = 0
        token_position = text.find(self.token_start)
        token_ending = text.find(self.token_end, token_position)
        while not token_position < 0 and not token_ending < 0:
            tomboy_note_title = text[token_position+len(self.token_start):token_ending]
            start_iter = textview.buff.get_iter_at_offset(text_offset + token_position)
            end_iter = textview.buff.get_iter_at_offset(text_offset+ token_ending+1)
            textview.buff.delete(start_iter, end_iter)
            widget =self.widgetCreate()
            widget.tomboy_note_title = tomboy_note_title
            widget.connect('clicked', self.tomboyDisplayNote)
            anchor = self.textviewInsertWidget(textview, widget, start_iter)
            self.anchors.append(anchor)
            start_iter = textview.buff.get_iter_at_child_anchor(anchor)
            start_iter.forward_char()
            end_iter = textview.buff.get_end_iter()
            text = textview.buff.get_slice(start_iter,end_iter)
            text_offset = start_iter.get_offset()
            token_position = text.find(self.token_start)
            token_ending = text.find(self.token_end)




		
    def deactivate(self, plugin_api):
        #        plugin_api.remove_menu_item(self.menu_item)
        #plugin_api.remove_toolbar_item(self.tb_button)
        #plugin_api.remove_toolbar_item(None, self.separator)
		
    #load a dialog with a String
        pass
    def loadDialog(self, msg):
        path = os.path.dirname(os.path.abspath(__file__))
        glade_file = os.path.join(path, "tomboy.glade")
        print glade_file
        wTree = gtk.glade.XML(glade_file, "InsertNoteDialog")
        self.dialog = wTree.get_widget("InsertNoteDialog")
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

    def getTomboyObject(self):
        bus = dbus.SessionBus()
        obj = bus.get_object("org.gnome.Tomboy",
                               "/org/gnome/Tomboy/RemoteControl")
        return dbus.Interface(obj, "org.gnome.Tomboy.RemoteControl")

		
    def onTbTaskButton(self, widget, plugin_api):
        path = os.path.dirname(os.path.abspath(__file__))
        glade_file = os.path.join(path, "tomboy.glade")
        print glade_file
        wTree = gtk.glade.XML(glade_file, "InsertNoteDialog")
        self.dialog = wTree.get_widget("InsertNoteDialog")
        self.dialog.connect("delete_event", self.close_dialog)
        self.dialog.connect("response", self.close_dialog)
        combobox = wTree.get_widget("combobox1")
        tomboy = self.getTomboyObject()
        map (lambda note:\
             combobox.append_text(tomboy.GetNoteTitle(note)),tomboy.ListAllNotes())
        combobox.popup()
        combobox.connect("changed", self.noteChosen)
        textview = plugin_api.get_textview()
        self.dialog.show_all()

    def noteChosen(self, widget, data=None):
        mark_start = self.textview.buff.get_insert()
        self.iter_start = self.textview.buff.get_iter_at_mark(mark_start)
        tomboy_widget =self.widgetCreate()
        tomboy_widget.tomboy_note_title = widget.get_active_text()
        tomboy_widget.connect('clicked', self.tomboyDisplayNote)
        anchor = self.textviewInsertWidget(self.textview, tomboy_widget,
                                           self.iter_start)
        self.anchors.append(anchor)

#        tv = plugin_api.get_textview()
#        iter = tv.get_insert()
#        if iter.starts_line() :
##            tv.insert_text("|",itera)
#            pass
#        else :
##            tv.insert_text(" £$",itera)
#            widget =self.widgetCreate()
#            widget.connect('clicked', self.tomboyDisplay)
#            self.textviewInsertWidget(tv, widget, iter)
#            tv.grab_focus()

    def widgetCreate(self):
        image = gtk.Image()
        image_path = "/usr/share/icons/hicolor/16x16/apps/tomboy.png"
        pixbuf=gtk.gdk.\
                pixbuf_new_from_file_at_size(image_path, 16, 16)
        image.show()
        image.set_from_pixbuf(pixbuf)
        widget= gtk.ToolButton(image)
        return widget

    def tomboyDisplayNote(self,widget):
        bus = dbus.SessionBus()
        obj = bus.get_object("org.gnome.Tomboy",
                               "/org/gnome/Tomboy/RemoteControl")
        tomboy = dbus.Interface(obj, "org.gnome.Tomboy.RemoteControl")
        # Display the title of every note
        note = tomboy.FindNote(widget.tomboy_note_title)
        tomboy.DisplayNote(note)

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
        print widget
        print str(widget)
        textview.add_child_at_anchor(widget, anchor)
        return anchor


    
