# -*- coding: utf-8 -*-
# pylint: disable-msg=W0201
# -----------------------------------------------------------------------------
# Getting Things Gnome! - a personal organizer for the GNOME desktop
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

import pygtk
pygtk.require('2.0')
import gobject
import gtk
import datetime

from GTG import _
from GTG.gtk.browser import GnomeConfig
from GTG.gtk.browser.simple_color_selector import SimpleColorSelector

class TagEditor(gtk.Window):

    def __init__(self, req, vmanager, tag=None):
        self.__gobject_init__()
        self.req = req
        self.vmanager = vmanager
        self.tag = tag
        self.config = self.req.get_config('tag_editor')
        self.custom_colors = None
        self.tn_entry_watch_id = None
        self.tn_cb_clicked_hid = None
        self.tn_entry_clicked_hid = None
        # Build up the menu
        self.__build_window()
        self.set_tag(tag)
        # Make it visible
        self.show_all()

    def __build_window(self):
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_title('Edit tag')
        self.set_border_width(10)
        self.set_resizable(False)
        # toplevel widget
        self.top_vbox = gtk.VBox()
        self.add(self.top_vbox)
        # header line: icon, table with name and "hide in wv"
        self.hdr_align = gtk.Alignment()
        self.top_vbox.pack_start(self.hdr_align)
        self.hdr_align.set_padding(0, 25, 0, 0)
        self.hdr_hbox = gtk.HBox()
        self.hdr_align.add(self.hdr_hbox)
        self.hdr_hbox.set_spacing(10)
        # Button to tag icon selector
        self.ti_bt_img = gtk.Image()
        self.ti_bt = gtk.Button()
        self.ti_bt.set_sensitive(False) # FIXME: implement icon selection
        self.ti_bt_label = gtk.Label()
        self.ti_bt.add(self.ti_bt_label)
        self.hdr_hbox.pack_start(self.ti_bt)
        self.ti_bt.set_size_request(64, 64)
        self.ti_bt.set_relief(gtk.RELIEF_HALF)
        # vbox for tag name and hid in WV
        self.tp_table = gtk.Table(2,2)
        self.hdr_hbox.pack_start(self.tp_table)
        self.tp_table.set_col_spacing(0, 5)
        self.tn_entry_lbl_align = gtk.Alignment(0,0.5)
        self.tp_table.attach(self.tn_entry_lbl_align, 0, 1, 0, 1)
        self.tn_entry_lbl = gtk.Label()
        self.tn_entry_lbl.set_markup("<span weight='bold'>%s</span>" % _("Name : "))
        self.tn_entry_lbl_align.add(self.tn_entry_lbl)
        self.tn_entry = gtk.Entry()
        self.tp_table.attach(self.tn_entry, 1, 2, 0, 1)
        self.tn_entry.set_width_chars(20)
        self.tn_cb_lbl_align = gtk.Alignment(0,0.5)
        self.tp_table.attach(self.tn_cb_lbl_align, 0, 1, 1, 2)
        self.tn_cb_lbl = gtk.Label(_("Show Tag in Work View :"))
        self.tn_cb_lbl_align.add(self.tn_cb_lbl)
        self.tn_cb = gtk.CheckButton()
        self.tp_table.attach(self.tn_cb, 1, 2, 1, 2)
        # Tag color
        self.tc_vbox = gtk.VBox()
        self.top_vbox.pack_start(self.tc_vbox)
        self.tc_label_align = gtk.Alignment()
        self.tc_vbox.pack_start(self.tc_label_align)
        self.tc_label_align.set_padding(0, 0, 0, 0)
        self.tc_label = gtk.Label()
        self.tc_label_align.add(self.tc_label)
        self.tc_label.set_markup( \
            "<span weight='bold'>%s</span>" % _("Select Tag Color:"))
        self.tc_label.set_alignment(0, 0.5)
        # Tag color chooser
        self.tc_cc_align = gtk.Alignment(0.5, 0.5, 0, 0)
        self.tc_vbox.pack_start(self.tc_cc_align)
        self.tc_cc_align.set_padding(15, 15, 10, 10)
        self.tc_cc_colsel = SimpleColorSelector()
        self.tc_cc_align.add(self.tc_cc_colsel)

        # Set the callbacks
        self.ti_bt.connect('clicked', self.on_ti_bt_clicked)
        self.tn_entry_clicked_hid = \
            self.tn_entry.connect('changed', self.on_tn_entry_changed)
        self.tn_cb_clicked_hid = self.tn_cb.connect('clicked', self.on_tn_cb_clicked)
        self.tc_cc_colsel.connect('color-defined', self.on_tc_colsel_defined)
        self.tc_cc_colsel.connect('color-added', self.on_tc_colsel_added)
        self.connect('delete-event', self.on_close)
        
    def __set_default_values(self):
        # Disable some handlers while setting up the widget to avoid
        # interferences
        self.tn_cb.handler_block(self.tn_cb_clicked_hid)
        self.tn_entry.handler_block(self.tn_entry_clicked_hid)
        # Default icon
        markup = "<span size='small'>%s</span>" % _("Click To\nSet Icon")
        self.ti_bt_label.set_justify(gtk.JUSTIFY_CENTER)
        self.ti_bt_label.set_markup(markup)
        self.ti_bt_label.show()
        # Show in WV
        self.tn_cb.set_active(True)
        # Name entry
        self.tn_entry.set_text(_("Enter tag name here"))
        self.tn_entry.set_icon_from_stock(gtk.POS_RIGHT, None)
        # Color selection
        self.tc_cc_colsel.unselected_color()
        # Custom colors
        self.custom_colors = list(self.config.get('custom_colors'))
        if len(self.custom_colors) > 0:
            self.tc_cc_colsel.set_custom_colors(self.custom_colors)
        # Focus
        self.tn_entry.grab_focus()
        # Re-enable checkbutton handler_block
        self.tn_cb.handler_unblock(self.tn_cb_clicked_hid)
        self.tn_entry.handler_unblock(self.tn_entry_clicked_hid)

    ### PUBLIC API ###

    def set_tag(self, tag):
        """Update the context menu items using the tag attributes."""
        # set_active emit the 'toggle' signal, so we have to disable the handler
        # when we update programmatically
        self.__set_default_values()
        if tag is None:
            self.tag = None
        else:
            # Disable some handlers while setting up the widget to avoid
            # interferences
            self.tn_cb.handler_block(self.tn_cb_clicked_hid)
            self.tn_entry.handler_block(self.tn_entry_clicked_hid)
            self.tag = tag
            # Update entry
            name = tag.get_name()[1:]
            self.tn_entry.set_text(name)
            # Update visibility in Work View
            s_hidden_in_wv = (self.tag.get_attribute("nonworkview") == "True")
            self.tn_cb.set_active(not s_hidden_in_wv)
            # If available, update icon
            if (tag.get_attribute('icon') is not None):
                print "FIXME: GTG.gtk.browser.tag_editor: Icon setup is still not supported."
            # If available, update color selection
            if (tag.get_attribute('color') is not None):
                col = tag.get_attribute('color')
                self.tc_cc_colsel.set_selected_color(col)
            # Re-enable checkbutton handler_block
            self.tn_cb.handler_unblock(self.tn_cb_clicked_hid)
            self.tn_entry.handler_unblock(self.tn_entry_clicked_hid)

    ### CALLBACKS ###

    def watch_tn_entry_changes(self):
        cur_value = self.tn_entry.get_text()
        if self.tn_entry_last_recorded_value != cur_value:
            # they're different: there's been some updates, wait further
            return True
        else:
            # they're the same. We can unregister the watcher and
            # update the tag name
            self.tn_entry_watch_id = None
            if cur_value.strip() != '':
                self.req.rename_tag(self.tag.get_name(), "@"+cur_value)
            return False

    def on_ti_bt_clicked(self, widget):
        print "FIXME: GTG.gtk.browser.tag_editor: Icons selection is still not supported."

    def on_tn_entry_changed(self, widget):
        self.tn_entry_last_recorded_value = self.tn_entry.get_text()
        # check validity
        if self.tn_entry_last_recorded_value.strip() == "":
            self.tn_entry.set_icon_from_stock(gtk.POS_RIGHT, gtk.STOCK_DIALOG_ERROR)
        else:
            self.tn_entry.set_icon_from_stock(gtk.POS_RIGHT, None)
        # filter out change requests to reduce commit overhead
        if self.tn_entry_watch_id is None:
            # There is no watchers for the text entry. Register one.
            # Also, wait 1 second before commiting the change in order to
            # reduce rename requests
            self.tn_entry_watch_id = gobject.timeout_add(1000, self.watch_tn_entry_changes)

    def on_tn_cb_clicked(self, widget):
        if self.tag is not None:
            show_in_wv = self.tn_cb.get_active()
            hide_in_wv = not show_in_wv
            self.tag.set_attribute('nonworkview', str(hide_in_wv))

    def on_tc_colsel_defined(self, widget):
        color = self.tc_cc_colsel.get_selected_color()
        if self.tag is not None:
            if color is not None:
                self.tag.set_attribute('color', color)
            else:
                self.tag.del_attribute('color')

    def on_tc_colsel_added(self, widget):
        self.custom_colors = self.tc_cc_colsel.get_custom_colors()
        self.config.set_lst("custom_colors", [s for s in self.custom_colors])
        self.req.save_config()

    def on_close(self, widget, event):
        self.vmanager.close_tag_editor()
        return True
