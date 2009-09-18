# -*- coding: utf-8 -*-
# Copyright (c) 2009 - Luca Invernizzi <invernizzi.l@gmail.com>
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

import gtk
import os
import dbus
from GTG import _


class pluginTomboy:

    def __init__(self):
        self.token_start = 'TOMBOY__'
        self.token_end = '|'
        self.path = os.path.dirname(os.path.abspath(__file__))

    # Plug-in engine methods
    def activate(self, plugin_api):
        self.plugin_api = plugin_api

    def widgetTotext(self, widget):
        return self.token_start+ widget.tomboy_note_title+self.token_end

    # Converts all tomboy note widgets in the
    # equivalent text
    def onTaskClosed(self, plugin_api):
        for anchor in self.anchors:
            widgets = anchor.get_widgets()
            if anchor.get_deleted():
                #The note has been deleted, go
                continue
            iter_start = self.textview.buff.get_iter_at_child_anchor(anchor)
            iter_end = iter_start.copy()
            iter_end.forward_char()
            if type(widgets) == list and len(widgets) !=0:
                #the anchor point contains a widget.
                widget = widgets[0]
                self.textview.buff.delete(iter_start, iter_end)
                self.textview.buff.insert(iter_start,
                                          self.widgetTotext(widget))

    def onTaskOpened(self, plugin_api):
        #get_textview() only works here(from GTG/core/plugins/api.py docs)
        self.textview = plugin_api.get_textview()
        # add a item(button) to the ToolBar, with a nice icon
        tb_Taskbutton_image = gtk.Image()
        tb_Taskbutton_image_path =\
            "/usr/share/icons/hicolor/16x16/apps/tomboy.png"
        tb_Taskbutton_pixbuf=gtk.gdk.\
                pixbuf_new_from_file_at_size(tb_Taskbutton_image_path, 16, 16)
        tb_Taskbutton_image.set_from_pixbuf(tb_Taskbutton_pixbuf)
        tb_Taskbutton_image.show()
        self.tb_Taskbutton = gtk.ToolButton(tb_Taskbutton_image)
        self.tb_Taskbutton.set_label(_("Add Tomboy note"))
        self.tb_Taskbutton.connect('clicked', self.onTbTaskButton, plugin_api)
        plugin_api.add_task_toolbar_item(gtk.SeparatorToolItem())
        plugin_api.add_task_toolbar_item(self.tb_Taskbutton)
        #convert tokens in text to images
        self.anchors=[]
        start_iter = self.textview.buff.get_start_iter()
        end_iter = self.textview.buff.get_end_iter()
        text = self.textview.buff.get_slice(start_iter, end_iter)
        text_offset = 0
        token_position = text.find(self.token_start)
        token_ending = text.find(self.token_end, token_position)
        while not token_position < 0 and not token_ending < 0:
            #delete the widget
            tomboy_note_title = text[token_position + len(self.token_start):
                                     token_ending]
            start_iter = self.textview.buff.get_iter_at_offset(text_offset +
                                                               token_position)
            end_iter = self.textview.buff.get_iter_at_offset(text_offset+
                                                             token_ending+1)
            self.textview.buff.delete(start_iter, end_iter)
            #add the widget
            widget =self.widgetCreate(tomboy_note_title)
            anchor = self.textviewInsertWidget(widget, start_iter)
            self.anchors.append(anchor)
            #find the next
            start_iter = self.textview.buff.get_iter_at_child_anchor(anchor)
            start_iter.forward_char()
            end_iter = self.textview.buff.get_end_iter()
            text = self.textview.buff.get_slice(start_iter, end_iter)
            text_offset = start_iter.get_offset()
            token_position = text.find(self.token_start)
            token_ending = text.find(self.token_end)

    def deactivate(self, plugin_api):
        #nothing to remove
        pass

    def close_dialog(self, widget, data=None):
        self.dialog.destroy()
        return True

    def getTomboyObject(self):
        bus = dbus.SessionBus()
        obj = bus.get_object("org.gnome.Tomboy",
                               "/org/gnome/Tomboy/RemoteControl")
        return dbus.Interface(obj, "org.gnome.Tomboy.RemoteControl")

    def getTomboyNoteTitleList(self):
        tomboy = self.getTomboyObject()
        return map(lambda note: tomboy.GetNoteTitle(note),
                   tomboy.ListAllNotes())

    def onTbTaskButton(self, widget, plugin_api):
        title_list = self.getTomboyNoteTitleList()
        #Create the dialog
        glade_file = os.path.join(self.path, "tomboy.glade")
        wTree = gtk.glade.XML(glade_file, "InsertNoteDialog")
        #objects
        self.dialog = wTree.get_widget("InsertNoteDialog")
        btn_add = wTree.get_widget("btn_add")
        btn_cancel = wTree.get_widget("btn_cancel")
        self.combobox = wTree.get_widget("titles_combobox")
        self.label_caption = wTree.get_widget("label_caption")
        title_entry = gtk.Entry()
        clipboard = gtk.Clipboard()
        #connects
        self.dialog.connect("delete_event", self.close_dialog)
        btn_cancel.connect("clicked", self.close_dialog)
        btn_add.connect("clicked", self.noteChosen)

        def comboKeyPress(combobox, event):
            keyname = gtk.gdk.keyval_name(event.keyval)
            if keyname == "Return":
                self.noteChosen()
        title_entry.connect("key-press-event", comboKeyPress)
        #clipboard management(if a note title is in the clipboard,
        # put that into the combobox
        def clipboardCallback(clipboard, text, title_el):
            title_entry= title_el[0]
            title_list= title_el[1]
            if len(filter(lambda x: x == text, title_list)) != 0:
                title_entry.set_text(text)
        clipboard.request_text(clipboardCallback, [title_entry, title_list])
        self.combobox.add(title_entry)
        #populate the combo-box
        if title_list:
            completion = gtk.EntryCompletion()
            note_list_store = gtk.ListStore(str)
            for title in title_list:
                iter = note_list_store.append()
                note_list_store.set(iter, 0, title)
            title_entry.set_completion(completion)
            completion.set_model(note_list_store)
            completion.set_inline_completion(True)
            completion.set_text_column(0)
        self.dialog.show_all()

    def noteChosen(self, widget=None, data=None):
        tomboy = self.getTomboyObject()
        supposed_title = self.combobox.get_active_text()
        if filter(lambda x: tomboy.GetNoteTitle(x)==supposed_title,
                  tomboy.ListAllNotes()) == []:
            self.label_caption.set_text(_("That note does not exist!"))
            return
        mark_start = self.textview.buff.get_insert()
        iter_start = self.textview.buff.get_iter_at_mark(mark_start)
        tomboy_widget =self.widgetCreate(supposed_title)
        anchor = self.textviewInsertWidget(tomboy_widget, iter_start)
        self.anchors.append(anchor)
        self.dialog.destroy()

    def tomboyDisplayNote(self, widget):
        tomboy = self.getTomboyObject()
        note = tomboy.FindNote(widget.tomboy_note_title)
        tomboy.DisplayNote(note)

    def textviewInsertWidget(self, widget, iter):
        anchor = self.textview.buff.create_child_anchor(iter)
        widget.show()
        self.textview.add_child_at_anchor(widget, anchor)
        return anchor

    def widgetCreate(self, tomboy_note_title):
        image = gtk.Image()
        image_path = "/usr/share/icons/hicolor/16x16/apps/tomboy.png"
        pixbuf=gtk.gdk.\
                pixbuf_new_from_file_at_size(image_path, 16, 16)
        image.show()
        image.set_from_pixbuf(pixbuf)
        widget= gtk.Button()
        widget.set_image(image)
        widget.tomboy_note_title = tomboy_note_title
        widget.set_label(tomboy_note_title)
        widget.connect('clicked', self.tomboyDisplayNote)
        return widget
