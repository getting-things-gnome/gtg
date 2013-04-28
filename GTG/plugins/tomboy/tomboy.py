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

import dbus
import os
import sys

try:
    import pygtk
    pygtk.require("2.0")
except:
    sys.exit(1)

import gtk

from GTG import _
from GTG.plugins.tomboy.combobox_enhanced import smartifyComboboxEntry


class pluginTomboy:

    def __init__(self):
        # These tokens are used to identify the beginning and the end of the
        # tomboy note point of insertion
        self.token_start = 'TOMBOY__'
        self.token_end = '|'
        self.path = os.path.dirname(os.path.abspath(__file__))
        self.findTomboyIconPath()

    # Tomboy installation is checked through the presence of its icon
    def findTomboyIconPath(self):
        TOMBOY_ICON_PATH_ENDING = "icons/hicolor/scalable/apps/tomboy.svg"
        GNOTE_ICON_PATH_ENDING = "icons/hicolor/scalable/apps/gnote.svg"
        possible_paths = [
            ("/usr/share/" + TOMBOY_ICON_PATH_ENDING, "tomboy"),
            ("/usr/share/" + GNOTE_ICON_PATH_ENDING, "gnote"),
            ("/usr/local/share/" + TOMBOY_ICON_PATH_ENDING, "tomboy"),
            ("/usr/local/share/" + GNOTE_ICON_PATH_ENDING, "gnote")]
        for path, software in possible_paths:
            if os.path.isfile(path):
                self.tomboy_icon_path = path
                self.software = software
                return True
        return False

    # Function called upon plug-in activation
    def activate(self, plugin_api):
        self.builder = gtk.Builder()

    # Returns true is Tomboy/Gnote is present, otherwise shows a dialog
    #(only once)  and returns False
    def checkTomboyPresent(self):
        if not hasattr(self, 'activated'):
            self.activated = self.findTomboyIconPath()
            # The notification to disable the plug-in to the user will be
            # showed only once
            dialog_destroy_with_parent = gtk.DIALOG_DESTROY_WITH_PARENT
            if not self.activated:
                dialog = gtk.MessageDialog(parent=self.plugin_api.get_ui().
                                           get_window(),
                                           flags=dialog_destroy_with_parent,
                                           type=gtk.MESSAGE_ERROR,
                                           buttons=gtk.BUTTONS_OK,
                                           message_format=_("Tomboy/Gnote "
                                           "not found. Please install it or "
                                           "disable the Tomboy/Gnote plugin"
                                           " in GTG"))
                dialog.run()
                dialog.destroy()
        return self.activated

    # Return a textual token to represent the Tomboy widget. It's useful
    # since the task is saved as pure text
    def widgetTotext(self, widget):
        return self.token_start + widget.tomboy_note_title + self.token_end

    # Converts all tomboy note widgets in the  equivalent text
    def onTaskClosed(self, plugin_api):
        if not hasattr(self, "activated") or not self.activated is True:
            # plugin has not been properly activated, (bug 475877 )
            # closing without executing onTaskClosed
            return
        for anchor in self.anchors:
            widgets = anchor.get_widgets()
            if anchor.get_deleted():
                # The note has been deleted, skip
                continue
            iter_start = self.textview.buff.get_iter_at_child_anchor(anchor)
            iter_end = iter_start.copy()
            iter_end.forward_char()
            if type(widgets) == list and len(widgets) != 0:
                # the anchor still contains a widget.
                widget = widgets[0]
                self.textview.buff.delete(iter_start, iter_end)
                self.textview.buff.insert(iter_start,
                                          self.widgetTotext(widget))

    # adds a item(button) to the ToolBar, with a nice icon
    def addButtonToToolbar(self, plugin_api):
        if not self.checkTomboyPresent():
            return
        tb_Taskbutton_image = gtk.Image()
        tb_Taskbutton_image_path = self.tomboy_icon_path
        tb_Taskbutton_pixbuf = gtk.gdk.\
            pixbuf_new_from_file_at_size(tb_Taskbutton_image_path, 16, 16)
        tb_Taskbutton_image.set_from_pixbuf(tb_Taskbutton_pixbuf)
        self.tb_Taskbutton = gtk.ToolButton(tb_Taskbutton_image)
        self.tb_Taskbutton.set_label(_("Add Tomboy note"))
        self.tb_Taskbutton.connect('clicked', self.onTbTaskButton,
                                   self.plugin_api)
        self.tb_Taskbutton.show_all()
        self.plugin_api.add_toolbar_item(self.tb_Taskbutton)

    # Converts all the textual tokens in tomboy note widgets
    def convertTokensToWidgets(self):
        self.anchors = []
        start_iter = self.textview.buff.get_start_iter()
        end_iter = self.textview.buff.get_end_iter()
        text = self.textview.buff.get_slice(start_iter, end_iter)
        text_offset = 0
        token_position = text.find(self.token_start)
        token_ending = text.find(self.token_end, token_position)
        while not token_position < 0 and not token_ending < 0:
            # delete the text of the token
            tomboy_note_title = text[token_position + len(self.token_start):
                                     token_ending]
            start_iter = self.textview.buff.get_iter_at_offset(text_offset +
                                                               token_position)
            end_iter = self.textview.buff.get_iter_at_offset(text_offset +
                                                             token_ending + 1)
            self.textview.buff.delete(start_iter, end_iter)
            # add the widget
            widget = self.widgetCreate(tomboy_note_title)
            anchor = self.textviewInsertWidget(widget, start_iter)
            self.anchors.append(anchor)
            # find the next
            start_iter = self.textview.buff.get_iter_at_child_anchor(anchor)
            start_iter.forward_char()
            end_iter = self.textview.buff.get_end_iter()
            text = self.textview.buff.get_slice(start_iter, end_iter)
            text_offset = start_iter.get_offset()
            token_position = text.find(self.token_start)
            token_ending = text.find(self.token_end)

    def onTaskOpened(self, plugin_api):
        self.plugin_api = plugin_api
        if not self.checkTomboyPresent() or not plugin_api.is_editor():
            return
        # NOTE: get_textview() only works in this function
        # (see GTG/core/plugins/api.py docs)
        self.textview = plugin_api.get_ui().get_textview()
        self.addButtonToToolbar(plugin_api)
        self.convertTokensToWidgets()

    def deactivate(self, plugin_api):
        try:
            self.onTaskClosed(self.plugin_api)
            self.plugin_api.remove_toolbar_item(self.tb_Taskbutton)
        except AttributeError:
            # the plugin wasn't used
            pass

    def close_dialog(self, widget, data=None):
        self.dialog.destroy()
        return True

    # opens a dbus connection to tomboy
    def getTomboyObject(self):
        bus = dbus.SessionBus()
        try:
            obj = bus.get_object("org.gnome.Tomboy",
                                 "/org/gnome/Tomboy/RemoteControl")
        except dbus.DBusException:
            DIALOG_DESTROY_WITH_PARENT = gtk.DIALOG_DESTROY_WITH_PARENT
            if not hasattr(self, "disable_flag"):
                dialog = gtk.MessageDialog(parent=self.plugin_api.get_ui().
                                           get_window(),
                                           flags=DIALOG_DESTROY_WITH_PARENT,
                                           type=gtk.MESSAGE_ERROR,
                                           buttons=gtk.BUTTONS_OK,
                                           message_format=_("%s seems to be "
                                           "installed on your system, but it "
                                           "does not provide a DBus interface"
                                           " which is required by the "
                                           "Tomboy/Gnote plugin in GTG.") %
                                           self.software.title())
                dialog.run()
                dialog.destroy()
                self.disable_flag = True
            return None
        return dbus.Interface(obj, "org.gnome.Tomboy.RemoteControl")

    # gets the list of the titles of the notes
    def getTomboyNoteTitleList(self):
        tomboy = self.getTomboyObject()
        if tomboy is None:
            return None
        return map(lambda note: str(tomboy.GetNoteTitle(note)),
                   tomboy.ListAllNotes())

    def onTbTaskButton(self, widget, plugin_api):
        title_list = self.getTomboyNoteTitleList()
        if title_list is None:
            return
        # Create the dialog
        user_interface_file = os.path.join(self.path, "tomboy.ui")
        self.builder.add_from_file(user_interface_file)
        self.dialog = self.builder.get_object("InsertNoteDialog")
        self.combobox = self.builder.get_object("titles_combobox")
        self.label_caption = self.builder.get_object("label_caption")
        self.builder.connect_signals({
            "on_btn_cancel_clicked": self.close_dialog,
            "on_btn_add_clicked": self.noteChosen,
            "on_InsertNoteDialog_close": self.close_dialog,
        })
        self.combobox_entry = smartifyComboboxEntry(self.combobox,
                                                    title_list,
                                                    self.noteChosen)
        self.dialog.show_all()

    # A title has been chosen by the user. If the note exists, it will be
    # linked, otherwise the user will have the option to create the note.
    def noteChosen(self, widget=None, data=None):
        tomboy = self.getTomboyObject()
        if tomboy is None:
            return
        supposed_title = self.combobox_entry.get_text()
        if filter(lambda x: tomboy.GetNoteTitle(x) == supposed_title,
                  tomboy.ListAllNotes()) == []:
            self.label_caption.set_text(_("That note does not exist!"))
            dialog = gtk.MessageDialog(parent=self.dialog,
                                       flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                                       type=gtk.MESSAGE_QUESTION,
                                       buttons=gtk.BUTTONS_YES_NO,
                                       message_format=_("That note does not \
exist. Do you want to create a new one?"))
            response = dialog.run()
            dialog.destroy()
            if response == gtk.RESPONSE_YES:
                tomboy.CreateNamedNote(supposed_title)
            else:
                return
        # note insertion
        mark_start = self.textview.buff.get_insert()
        iter_start = self.textview.buff.get_iter_at_mark(mark_start)
        tomboy_widget = self.widgetCreate(supposed_title)
        anchor = self.textviewInsertWidget(tomboy_widget, iter_start)
        self.anchors.append(anchor)
        self.dialog.destroy()

    # Opens a note in tomboy application via dbus
    def tomboyDisplayNote(self, widget, data=None):
        tomboy = self.getTomboyObject()
        if tomboy is None:
            return
        note = tomboy.FindNote(widget.tomboy_note_title)
        if str(note) == "":
            dialog = gtk.MessageDialog(parent=self.
                                       plugin_api.get_ui().get_window(),
                                       flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                                       type=gtk.MESSAGE_WARNING,
                                       buttons=gtk.BUTTONS_YES_NO,
                                       message_format=(_("This Tomboy note \
                                       does not exist anymore. Do you want to\
                                        create it?")))
            response = dialog.run()
            dialog.destroy()
            if response == gtk.RESPONSE_YES:
                tomboy.CreateNamedNote(widget.tomboy_note_title)
                tomboy.DisplayNote(note)
        else:
            tomboy.DisplayNote(note)

    # inserts a widget in the textview
    def textviewInsertWidget(self, widget, iter):
        anchor = self.textview.buff.create_child_anchor(iter)
        widget.show()
        self.textview.add_child_at_anchor(widget, anchor)
        return anchor

    # creates the tomboy widget
    def widgetCreate(self, tomboy_note_title):
        image = gtk.Image()
        window = self.plugin_api.get_ui().get_window()
        window.realize()
        window_style = window.get_style()
        pixbuf = gtk.gdk.\
            pixbuf_new_from_file_at_size(self.tomboy_icon_path, 16, 16)
        image.show()
        image.set_from_pixbuf(pixbuf)
        image.set_alignment(0.5, 1.0)
        label = gtk.Label()
        color = str(window_style.text[gtk.STATE_PRELIGHT])
        title = tomboy_note_title
        label.set_markup("<span underline='low' color='%s'>%s</span>" % (color,
                                                                         title)
                         )
        label.show()
        label.set_alignment(0.5, 1.0)
        eventbox = gtk.EventBox()
        eventbox.set_events(gtk.gdk.BUTTON_PRESS_MASK)
        eventbox.connect('button_press_event', self.tomboyDisplayNote)
        hbox = gtk.HBox()
        hbox.show()
        hbox.add(image)
        hbox.add(label)
        eventbox.add(hbox)
        # the eventbox should follow the colours of the textview to blend in
        # properly
        textview_style = self.textview.get_style()
        eventbox_style = eventbox.get_style().copy()
        for state in (gtk.STATE_NORMAL, gtk.STATE_PRELIGHT, gtk.STATE_ACTIVE,
                      gtk.STATE_SELECTED, gtk.STATE_INSENSITIVE):
            eventbox_style.base[state] = textview_style.base[state]
            eventbox_style.bg[state] = textview_style.bg[state]
            eventbox_style.fg[state] = textview_style.fg[state]
            eventbox_style.text[state] = textview_style.text[state]
        eventbox_style.bg[gtk.STATE_NORMAL] = \
            textview_style.base[gtk.STATE_NORMAL]
        eventbox.set_style(eventbox_style)
        eventbox.show()
        eventbox.tomboy_note_title = tomboy_note_title
        # cursor changes to a hand

        def realize_callback(widget):
            eventbox.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND2))
        eventbox.connect("realize", realize_callback)
        return eventbox
