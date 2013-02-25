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


# TODO: put this in a class extending gtk.Combobox and place the file in
#      GTG.tools

import gtk
import gobject


def ifKeyPressedCallback(widget, key, callback):

    def keyPress(combobox, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == key:
            callback()
    widget.connect("key-press-event", keyPress)


def ifClipboardTextIsInListCallback(clipboard_obj, list_obj, callback):

    def clipboardCallback(clipboard_obj, text, list_obj):
        if len(filter(lambda x: x == text, list_obj)) != 0:
            callback(text)
    clipboard_obj.request_text(clipboardCallback, list_obj)


def listStoreFromList(list_obj):
    list_store = gtk.ListStore(gobject.TYPE_STRING)
    for elem in list_obj:
        iter = list_store.append()
        list_store.set(iter, 0, elem)
    return list_store


def completionFromListStore(list_store):
    completion = gtk.EntryCompletion()
    completion.set_minimum_key_length(0)
    completion.set_text_column(0)
    completion.set_inline_completion(True)
    completion.set_model(list_store)
    return completion


def smartifyComboboxEntry(combobox, list_obj, callback):
    entry = gtk.Entry()
    # check if Clipboard contains an element of the list
    clipboard = gtk.Clipboard()
    ifClipboardTextIsInListCallback(clipboard, list_obj, entry.set_text)
    # pressing Enter will cause the callback
    ifKeyPressedCallback(entry, "Return", callback)
    # wrap the combo-box if it's too long
    if len(list_obj) > 15:
        combobox.set_wrap_width(5)
    # populate the combo-box
    if len(list_obj) > 0:
        list_store = listStoreFromList(list_obj)
        entry.set_completion(completionFromListStore(list_store))
        combobox.set_model(list_store)
        combobox.set_active(0)
        entry.set_text(list_store[0][0])
    combobox.add(entry)
    combobox.connect('changed', setText, entry)
    # render the combo-box drop down menu
    cell = gtk.CellRendererText()
    combobox.pack_start(cell, True)
    combobox.add_attribute(cell, 'text', 0)
    return entry


def setText(combobox, entry):
    model = combobox.get_model()
    index = combobox.get_active()
    if index > -1:
        entry.set_text(model[index][0])
