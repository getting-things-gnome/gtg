# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 - Lionel Dricot & Bertrand Rousseau
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

"""
tag_editor: this module contains two classes: TagIconSelector and TagEditor.

TagEditor implement a dialog window that can be used to edit the properties
of a tag.

TagIconSelector is intended as a floating window that allows to select an icon
for a tag.
"""

import pygtk
pygtk.require('2.0')
import gobject
import gtk
import gtk.gdk as gdk

from GTG import _
from GTG.tools.logger import Log
from GTG.gtk.browser.simple_color_selector import SimpleColorSelector


class TagIconSelector(gtk.Window):
    """
    TagIconSelector is intended as a floating window that allows to select
    an icon for a tag. It display a list of icon in a popup window.
    """

    def __init__(self):
        self.__gobject_init__(type=gtk.WINDOW_POPUP)
        gtk.Window.__init__(self)
        self.loaded = False
        self.selected_icon = None
        self.symbol_model = None
        # Build up the window
        self.__build_window()
        # Make it visible
        self.hide_all()

    def __build_window(self):
        """Build up the widget"""
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_POPUP_MENU)
        vbox = gtk.VBox()
        self.add(vbox)
        # icon list
        scld_win = gtk.ScrolledWindow()
        scld_win.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        scld_win.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        vbox.pack_start(scld_win, expand=True, fill=True)
        self.symbol_iv = gtk.IconView()
        self.symbol_iv.set_pixbuf_column(0)
        self.symbol_iv.set_property("columns", 7)
        self.symbol_iv.set_property("item-width", 32)
        # IconView size:
        # --------------
        #  it seems that with the above parameters, a row width is about:
        #  item_count * (32px (item) + 6px (dflt padding) + 2px (spacing?)) \
        #      + 2*6px (dflt widget margin)
        #  The same goes for row height, but being right for this value is less
        #  important due to the vertical scrollbar.
        #  The IcVw size should fit the width of 7 cols and height of ~4 lines.
        self.symbol_iv.set_size_request(40 * 7 + 12, 38 * 4)
        scld_win.add(self.symbol_iv)
        # icon remove button
        img = gtk.Image()
        img.set_from_stock(gtk.STOCK_REMOVE, gtk.ICON_SIZE_BUTTON)
        self.remove_bt = gtk.Button()
        self.remove_bt.set_image(img)
        self.remove_bt.set_label(_("Remove selected icon"))
        vbox.pack_start(self.remove_bt, fill=False, expand=False)
        # set the callbacks
        self.symbol_iv.connect("selection-changed", self.on_selection_changed)
        self.remove_bt.connect("clicked", self.on_remove_bt_clicked)

    def __focus_out(self, widget, event):
        """Hides the window if the user clicks out of it"""
        win_ptr = self.window.get_pointer()
        win_size = self.get_size()
        if not(0 <= win_ptr[0] <= win_size[0] and
               0 <= win_ptr[1] <= win_size[1]):
            self.close_selector()

    def __load_icon(self):
        """
        Loads emblem icons from the current icon theme

        Sometimes an icon can't be loaded because of a bug in system
        libraries, e.g. bug #1079587. Gracefuly degradate and skip
        the loading of a corrupted icon.
        """
        self.symbol_model = gtk.ListStore(gtk.gdk.Pixbuf, str)
        for icon in gtk.icon_theme_get_default().list_icons(context="Emblems"):
            try:
                img = gtk.icon_theme_get_default().load_icon(icon, 16, 0)
                self.symbol_model.append([img, icon])
            except gobject.GError:
                Log.error("Failed to load icon '%s'" % icon)
        self.symbol_iv.set_model(self.symbol_model)
        self.loaded = True

    ### PUBLIC IF ###
    def set_remove_enabled(self, enable):
        """Disable/enable the remove button"""
        self.remove_bt.set_sensitive(enable)

    ### callbacks ###
    def on_selection_changed(self, widget):
        """Callback: update the model according to the selected icon. Also
        notifies the parent widget."""
        my_path = self.symbol_iv.get_selected_items()
        if len(my_path) > 0:
            my_iter = self.symbol_model.get_iter(my_path[0])
            self.selected_icon = self.symbol_model.get_value(my_iter, 1)
        else:
            self.selected_icon = None
        self.emit('selection-changed')
        self.close_selector()

    def on_remove_bt_clicked(self, widget):
        """Callback: unselect the current icon"""
        self.selected_icon = None
        self.emit('selection-changed')
        self.close_selector()

    ### PUBLIC IF ###
    def show_at_position(self, pos_x, pos_y):
        """Displays the window at a specific point on the screen"""
        if not self.loaded:
            self.__load_icon()
        self.move(pos_x, pos_y)
        self.show_all()
        # some window managers ignore move before you show a window. (which
        # ones? question by invernizzi)
        self.move(pos_x, pos_y)
        self.grab_add()
        # We grab the pointer in the calendar
        gdk.pointer_grab(self.window, True,
                         gdk.BUTTON1_MASK | gdk.MOD2_MASK)
        self.connect('button-press-event', self.__focus_out)

    def close_selector(self):
        """Hides the window"""
        self.hide()
        gtk.gdk.pointer_ungrab()
        self.grab_remove()

    def get_selected_icon(self):
        """Returns the selected icon. None if no icon is selected."""
        return self.selected_icon

    def unselect_icon(self):
        """Unselects all icon in the iconview."""
        self.symbol_iv.unselect_all()


gobject.type_register(TagIconSelector)
gobject.signal_new("selection-changed", TagIconSelector,
                   gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())


class TagEditor(gtk.Window):
    """Window allowing to edit a tag's properties."""

    def __init__(self, req, vmanager, tag=None):
        gtk.Window.__init__(self)
        self.__gobject_init__()
        self.req = req
        self.vmanager = vmanager
        self.tag = tag
        self.config = self.req.get_config('tag_editor')
        self.custom_colors = None
        self.tn_entry_watch_id = None
        self.tn_cb_clicked_hid = None
        self.tn_entry_clicked_hid = None
        self.tis_selection_changed_hid = None
        self.tag_icon_selector = None
        # Build up the window
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_title('Edit tag')
        self.set_border_width(10)
        self.set_resizable(False)
        self.__build_window()
        self.__set_callbacks()
        self.set_tag(tag)
        # Make it visible
        self.show_all()

    def __build_window(self):
        """Build up the widget"""
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
        self.ti_bt = gtk.Button()
        self.ti_bt_label = gtk.Label()
        self.ti_bt.add(self.ti_bt_label)
        self.hdr_hbox.pack_start(self.ti_bt)
        self.ti_bt.set_size_request(64, 64)
        self.ti_bt.set_relief(gtk.RELIEF_HALF)
        # vbox for tag name and hid in WV
        self.tp_table = gtk.Table(2, 2)
        self.hdr_hbox.pack_start(self.tp_table)
        self.tp_table.set_col_spacing(0, 5)
        self.tn_entry_lbl_align = gtk.Alignment(0, 0.5)
        self.tp_table.attach(self.tn_entry_lbl_align, 0, 1, 0, 1)
        self.tn_entry_lbl = gtk.Label()
        self.tn_entry_lbl.set_markup("<span weight='bold'>%s</span>"
                                     % _("Name : "))
        self.tn_entry_lbl_align.add(self.tn_entry_lbl)
        self.tn_entry = gtk.Entry()
        self.tp_table.attach(self.tn_entry, 1, 2, 0, 1)
        self.tn_entry.set_width_chars(20)
        self.tn_cb_lbl_align = gtk.Alignment(0, 0.5)
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
        self.tc_label.set_markup(
            "<span weight='bold'>%s</span>" % _("Select Tag Color:"))
        self.tc_label.set_alignment(0, 0.5)
        # Tag color chooser
        self.tc_cc_align = gtk.Alignment(0.5, 0.5, 0, 0)
        self.tc_vbox.pack_start(self.tc_cc_align)
        self.tc_cc_align.set_padding(15, 15, 10, 10)
        self.tc_cc_colsel = SimpleColorSelector()
        self.tc_cc_align.add(self.tc_cc_colsel)
        # Icon selector
        self.tag_icon_selector = TagIconSelector()

    def __set_callbacks(self):
        """Define the widget callbacks"""
        # Set the callbacks
        self.ti_bt.connect('clicked', self.on_ti_bt_clicked)
        self.tis_selection_changed_hid = \
            self.tag_icon_selector.connect('selection-changed',
                                           self.on_tis_selection_changed)
        self.tn_entry_clicked_hid = \
            self.tn_entry.connect('changed', self.on_tn_entry_changed)
        self.tn_cb_clicked_hid = self.tn_cb.connect('clicked',
                                                    self.on_tn_cb_clicked)
        self.tc_cc_colsel.connect('color-changed', self.on_tc_colsel_changed)
        self.tc_cc_colsel.connect('color-added', self.on_tc_colsel_added)
        self.connect('delete-event', self.on_close)

        # allow fast closing by Escape key
        agr = gtk.AccelGroup()
        self.add_accel_group(agr)
        key, modifier = gtk.accelerator_parse('Escape')
        agr.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.on_close)

    def __set_default_values(self):
        """Configure the widget components with their initial default values"""
        # Disable some handlers while setting up the widget to avoid
        # interferences
        self.tn_cb.handler_block(self.tn_cb_clicked_hid)
        self.tn_entry.handler_block(self.tn_entry_clicked_hid)
        self.tag_icon_selector.handler_block(self.tis_selection_changed_hid)
        # Default icon
        markup = "<span size='small'>%s</span>" % _("Click To\nSet Icon")
        self.ti_bt_label.set_justify(gtk.JUSTIFY_CENTER)
        self.ti_bt_label.set_markup(markup)
        self.ti_bt_label.show()
        self.__set_icon(None)
        # Unselect any previously selected icon
        self.tag_icon_selector.unselect_icon()
        # Show in WV
        self.tn_cb.set_active(True)
        # Name entry
        self.tn_entry.set_text(_("Enter tag name here"))
        self.tn_entry.set_icon_from_stock(gtk.ENTRY_ICON_SECONDARY, None)
        # Color selection
        self.tc_cc_colsel.unselect_color()
        # Custom colors
        self.custom_colors = list(self.config.get('custom_colors'))
        if len(self.custom_colors) > 0:
            self.tc_cc_colsel.set_custom_colors(self.custom_colors)
        # Focus
        self.tn_entry.grab_focus()
        # Re-enable checkbutton handler_block
        self.tn_cb.handler_unblock(self.tn_cb_clicked_hid)
        self.tn_entry.handler_unblock(self.tn_entry_clicked_hid)
        self.tag_icon_selector.handler_unblock(self.tis_selection_changed_hid)

    def __set_icon(self, icon):
        """Set the icon in the related button widget. Restore the label when
        when no icon is selected."""
        if icon is not None:
            for i in self.ti_bt:
                self.ti_bt.remove(i)
            ti_bt_img = gtk.image_new_from_icon_name(icon,
                                                     gtk.ICON_SIZE_BUTTON)
            ti_bt_img.show()
            self.ti_bt.add(ti_bt_img)
        else:
            for i in self.ti_bt:
                self.ti_bt.remove(i)
            self.ti_bt.add(self.ti_bt_label)

    ### PUBLIC API ###
    def set_tag(self, tag):
        """Update the context menu items using the tag attributes."""
        # set_active emit the 'toggle' signal, so we have to disable
        # the handler when we update programmatically
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
            if tag.is_search_tag():
                name = tag.get_name()
            else:
                name = tag.get_name()[1:]
            self.tn_entry.set_text(name)
            # Update visibility in Work View
            s_hidden_in_wv = (self.tag.get_attribute("nonworkview") == "True")
            self.tn_cb.set_active(not s_hidden_in_wv)
            # If available, update icon
            if (tag.get_attribute('icon') is not None):
                icon = tag.get_attribute('icon')
                self.__set_icon(icon)
            # If available, update color selection
            if (tag.get_attribute('color') is not None):
                col = tag.get_attribute('color')
                if not self.tc_cc_colsel.has_color(col):
                    self.tc_cc_colsel.add_custom_color(col)
                self.tc_cc_colsel.set_selected_color(col)
            # Re-enable checkbutton handler_block
            self.tn_cb.handler_unblock(self.tn_cb_clicked_hid)
            self.tn_entry.handler_unblock(self.tn_entry_clicked_hid)

    ### CALLBACKS ###
    def watch_tn_entry_changes(self):
        """Monitors the value changes in the tag name entry. If no updates have
        been noticed after 1 second, request an update."""
        cur_value = self.tn_entry.get_text()
        if self.tn_entry_last_recorded_value != cur_value:
            # they're different: there's been some updates, wait further
            return True
        else:
            # they're the same. We can unregister the watcher and
            # update the tag name
            self.tn_entry_watch_id = None
            if cur_value.strip() != '':
                if self.tag.is_search_tag():
                    new_name = cur_value
                else:
                    new_name = "@" + cur_value
                self.req.rename_tag(self.tag.get_name(), new_name)
            return False

    def on_tis_selection_changed(self, widget):
        """Callback: update tag attributes whenever an icon is (un)selected."""
        icon = self.tag_icon_selector.get_selected_icon()
        if icon is not None:
            self.tag.set_attribute("icon", icon)
            self.__set_icon(icon)
        else:
            self.tag.del_attribute("icon")
            self.__set_icon(None)

    def on_ti_bt_clicked(self, widget):
        """Callback: displays the tag icon selector widget next
        to the button."""
        rect = self.ti_bt.get_allocation()
        pos_x, pos_y = \
            self.ti_bt.window.get_origin()
        self.tag_icon_selector.show_at_position(
            pos_x + rect.x + rect.width + 2,
            pos_y + rect.y)
        if self.tag.get_attribute('icon') is not None:
            self.tag_icon_selector.set_remove_enabled(True)
        else:
            self.tag_icon_selector.set_remove_enabled(False)

    def on_tn_entry_changed(self, widget):
        """ Callback: checks tag name validity and start value changes
        monitoring to decide when to update a tag's name."""
        self.tn_entry_last_recorded_value = self.tn_entry.get_text()
        # check validity
        if self.tn_entry_last_recorded_value.strip() == "":
            self.tn_entry.set_icon_from_stock(gtk.ENTRY_ICON_SECONDARY,
                                              gtk.STOCK_DIALOG_ERROR)
        else:
            self.tn_entry.set_icon_from_stock(gtk.ENTRY_ICON_SECONDARY, None)
        # filter out change requests to reduce commit overhead
        if self.tn_entry_watch_id is None:
            # There is no watchers for the text entry. Register one.
            # Also, wait 1 second before commiting the change in order to
            # reduce rename requests
            tn_entry_changes = self.watch_tn_entry_changes
            self.tn_entry_watch_id = gobject.timeout_add(1000,
                                                         tn_entry_changes)

    def on_tn_cb_clicked(self, widget):
        """Callback: toggle the nonworkview property according to the related
        widget's state."""
        if self.tag is not None:
            show_in_wv = self.tn_cb.get_active()
            hide_in_wv = not show_in_wv
            self.tag.set_attribute('nonworkview', str(hide_in_wv))

    def on_tc_colsel_changed(self, widget):
        """Callback: update the tag color depending on the current color
        selection"""
        color = self.tc_cc_colsel.get_selected_color()
        if self.tag is not None:
            if color is not None:
                self.tag.set_attribute('color', color)
            else:
                self.tag.del_attribute('color')

    def on_tc_colsel_added(self, widget):
        """Callback: if a new color is added, we register it in the
        configuration"""
        self.custom_colors = self.tc_cc_colsel.get_custom_colors()
        self.config.set_lst("custom_colors", [s for s in self.custom_colors])
        self.req.save_config()

    def on_close(self, widget, event, arg1=None, arg2=None, arg3=None):
        """ Callback: hide the tag editor when the close the window.

        Arguments arg1-arg3 are needed to satisfy callback when closing
        by Escape
        """
        self.vmanager.close_tag_editor()
        return True
