# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
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

- TagEditor is a dialog window used to edit the properties of a tag.
- TagIconSelector is a popover within that dialog to select an icon.
"""
from gi.repository import GObject, Gtk, Gdk, GdkPixbuf

from gettext import gettext as _
from GTG.gtk.browser.simple_color_selector import SimpleColorSelector
from GTG.gtk.colors import color_add, color_remove


class TagEditor(Gtk.Window):
    """Window allowing to edit a tag's properties."""

    def __init__(self, req, app, tag=None):
        super().__init__()

        self.req = req
        self.app = app
        self.tag = tag
        self.config = self.req.get_config('tag_editor')
        self.custom_colors = None
        self.tn_entry_watch_id = None
        self.tn_cb_clicked_hid = None
        self.tn_entry_clicked_hid = None
        self.tis_selection_changed_hid = None
        # Build up the window
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_title(_('Editing Tag "%s"') % tag.get_name())
        self.set_border_width(10)
        self.set_resizable(True)
        self.__build_window()
        self.__set_callbacks()
        self.set_tag(tag)
        # Make it visible
        self.show_all()

    def __build_window(self):
        """Build up the widget"""
        # toplevel widget
        self.top_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.top_vbox)
        # header line: icon, grid with name and "hide in wv"
        # FIXME
        self.hdr_align = Gtk.Alignment()
        self.top_vbox.pack_start(self.hdr_align, False, True, 0)
        self.hdr_align.set_padding(0, 5, 0, 0)
        self.hdr_box = Gtk.Box()
        self.clear_box = Gtk.Box()
        self.hdr_align.add(self.hdr_box)
        self.hdr_box.set_spacing(10)
        # Button to tag icon selector
        self.ti_bt = Gtk.Button()
        self.ti_bt_label = Gtk.Label()
        self.ti_bt.add(self.ti_bt_label)
        self.hidden_entry = Gtk.Entry()
        self.hidden_entry.set_width_chars(1)
        self.ti_bt_label.get_style_context().add_class('icon')
        self.hidden_entry.get_style_context().add_class('hidden')
        self.hdr_box.pack_start(self.ti_bt, False, False, 0)
        self.hdr_box.pack_start(self.hidden_entry, False, False, 0)
        self.ti_bt.set_size_request(64, 64)
        self.hidden_entry.set_size_request(0, 0)
        self.ti_bt.set_relief(Gtk.ReliefStyle.HALF)
        self.ti_bt_clear = Gtk.Button()
        self.ti_bt_clear.set_label(_('Remove icon'))
        self.clear_box.add(self.ti_bt_clear)

        # vbox for tag name and hid in WV
        self.tp_grid = Gtk.Grid()
        self.hdr_box.pack_start(self.tp_grid, False, True, 0)
        self.tp_grid.set_column_spacing(5)
        self.tn_entry_lbl_align = Gtk.Alignment.new(0, 0.5, 0, 0)
        self.tp_grid.add(self.tn_entry_lbl_align)
        self.tn_entry_lbl = Gtk.Label()
        self.tn_entry_lbl.set_markup("<span weight='bold'>%s</span>"
                                     % _("Name : "))
        self.tn_entry_lbl_align.add(self.tn_entry_lbl)
        self.tn_entry = Gtk.Entry()
        self.tn_entry.set_width_chars(20)
        self.tp_grid.attach(self.tn_entry, 1, 0, 1, 1)
        self.tn_cb_lbl_align = Gtk.Alignment.new(0, 0.5, 0, 0)
        self.tp_grid.attach(self.tn_cb_lbl_align, 0, 1, 1, 1)
        self.tn_cb_lbl = Gtk.Label(label=_('Show Tag in "Actionable" view:'))
        self.tn_cb_lbl_align.add(self.tn_cb_lbl)
        self.tn_cb = Gtk.CheckButton()
        self.tp_grid.attach(self.tn_cb, 1, 1, 1, 1)
        # Tag color
        self.tc_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.top_vbox.pack_start(self.clear_box, False, False, 0)
        self.top_vbox.pack_start(self.tc_vbox, False, True, 0)
        self.tc_label_align = Gtk.Alignment()
        self.tc_vbox.pack_start(self.tc_label_align, False, True, 0)
        self.tc_label_align.set_padding(25, 0, 0, 0)
        self.tc_label = Gtk.Label()
        self.tc_label_align.add(self.tc_label)
        self.tc_label.set_markup(
            "<span weight='bold'>%s</span>" % _("Select Tag Color:"))
        self.tc_label.set_alignment(0, 0.5)
        # Tag color chooser
        self.tc_cc_align = Gtk.Alignment.new(0.5, 0.5, 0, 0)
        self.tc_vbox.pack_start(self.tc_cc_align, False, False, 0)
        self.tc_cc_align.set_padding(25, 15, 10, 10)
        self.tc_cc_colsel = SimpleColorSelector()
        # self.tc_cc_colsel = Gtk.ColorChooserWidget()
        self.tc_cc_align.add(self.tc_cc_colsel)

    def set_emoji(self, widget):
        """Set emoji as icon (both in settings and button label)."""

        text = self.hidden_entry.get_text()

        if text:
            self.ti_bt_label.set_text(text)
            self.ti_bt_label.set_opacity(1)
            self.ti_bt_clear.set_sensitive(True)
        else:
            self.ti_bt_label.set_text('🏷️')
            self.ti_bt_label.set_opacity(0.4)
            self.ti_bt_clear.set_sensitive(False)

        with GObject.signal_handler_block(self.hidden_entry, self.emoji_id):
            self.hidden_entry.set_text('')

        self.tag.set_attribute('icon', text)

    def call_emoji_popup(self, widget):
        """Bring the emoji selector."""

        self.hidden_entry.do_insert_emoji(self.hidden_entry)

    def clear_icon(self, widget):
        """Remove icon."""

        self.hidden_entry.set_text('')
        self.set_emoji(None)

    def __set_callbacks(self):
        """Define the widget callbacks"""
        # Set the callbacks
        self.ti_bt.connect('clicked', self.call_emoji_popup)
        self.ti_bt_clear.connect('clicked', self.clear_icon)
        self.emoji_id = self.hidden_entry.connect('changed', self.set_emoji)

        self.tn_entry_clicked_hid = \
            self.tn_entry.connect('changed', self.on_tn_entry_changed)
        self.tn_cb_clicked_hid = \
            self.tn_cb.connect('clicked', self.on_tn_cb_clicked)
        # FIXME
        self.tc_cc_colsel.connect('color-changed', self.on_tc_colsel_changed)
        self.tc_cc_colsel.connect('color-added', self.on_tc_colsel_added)
        # self.tc_cc_colsel.connect('color-activated',
        #                           self.on_tc_colsel_activated)
        self.connect('delete-event', self.on_close)

        # allow fast closing by Escape key
        agr = Gtk.AccelGroup()
        self.add_accel_group(agr)
        key, modifier = Gtk.accelerator_parse('Escape')
        agr.connect(key, modifier, Gtk.AccelFlags.VISIBLE, self.on_close)

    def __set_default_values(self):
        """Configure the widget components with their initial default values"""
        # Disable some handlers while setting up the widget to avoid
        # interferences
        self.tn_cb.handler_block(self.tn_cb_clicked_hid)
        self.tn_entry.handler_block(self.tn_entry_clicked_hid)
        # Default icon
        markup = "<span size='small'>%s</span>" % _("Click to\nSet Icon")
        # self.ti_bt_label.set_justify(Gtk.Justification.CENTER)
        # self.ti_bt_label.set_markup(markup)
        # self.ti_bt_label.show()
        # self.__set_icon(None)
        # Unselect any previously selected icon
        # Show in WV
        self.tn_cb.set_active(True)
        # Name entry
        self.tn_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, None)
        # Color selection
        # FIXME
        self.tc_cc_colsel.unselect_color()
        # self.tc_cc_colsel.set_use_alpha(False)
        # self.tc_cc_colsel.set_rgba(self.tc_cc_colsel, None)
        # Custom colors
        self.custom_colors = self.config.get('custom_colors')
        if len(self.custom_colors) > 0:
            self.tc_cc_colsel.set_custom_colors(self.custom_colors)
        # Focus
        self.tn_entry.grab_focus()
        # Re-enable checkbutton handler_block
        self.tn_cb.handler_unblock(self.tn_cb_clicked_hid)
        self.tn_entry.handler_unblock(self.tn_entry_clicked_hid)

    # PUBLIC API #####
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
            name = tag.get_name()
            self.tn_entry.set_text(name)
            # Update visibility in Work View
            s_hidden_in_wv = (self.tag.get_attribute("nonworkview") == "True")
            self.tn_cb.set_active(not s_hidden_in_wv)
            # If available, update icon
            if (tag.get_attribute('icon') is not None):
                icon = tag.get_attribute('icon')
                #TODO: Remove if-block once we release 0.5
                if len(icon) < 6:
                    self.ti_bt_label.set_text(icon)
                    self.tag.set_attribute('icon', icon)
                    self.ti_bt_label.set_opacity(1)
                    self.ti_bt_clear.set_sensitive(True)
                else:
                    self.ti_bt_label.set_text('🏷️')
                    self.ti_bt_label.set_opacity(0.4)
                    self.ti_bt_clear.set_sensitive(False)
            else:
                self.ti_bt_label.set_text('🏷️')
                self.ti_bt_label.set_opacity(0.4)
                self.ti_bt_clear.set_sensitive(False)
            # If available, update color selection
            if (tag.get_attribute('color') is not None):
                col = tag.get_attribute('color')
                if not self.tc_cc_colsel.has_color(col):
                    self.tc_cc_colsel.add_custom_color(col)
                self.tc_cc_colsel.set_selected_color(col)
            # Re-enable checkbutton handler_block
            self.tn_cb.handler_unblock(self.tn_cb_clicked_hid)
            self.tn_entry.handler_unblock(self.tn_entry_clicked_hid)

    # CALLBACKS #####
    def watch_tn_entry_changes(self):
        """Monitors the value changes in the tag name entry. If no updates have
        been noticed after 1 second, request an update."""
        cur_value = self.get_tn_text()

        if self.tn_entry_last_recorded_value != cur_value:
            # they're different: there's been some updates, wait further
            return True
        else:
            # they're the same. We can unregister the watcher and
            # update the tag name
            self.tn_entry_watch_id = None
            if cur_value != '':
                new_name = cur_value

                self.req.rename_tag(self.tag.get_name(), new_name)
                self.tag = self.req.get_tag(new_name)

                # Select on sidebar and update values
                self.app.browser.select_on_sidebar(new_name)
                self.app.browser.reapply_filter()

            return False

    def get_tn_text(self):
        """Return text from the name input."""

        return self.tn_entry.get_text().strip().replace(' ', '')

    def on_tn_entry_changed(self, widget):
        """ Callback: checks tag name validity and start value changes
        monitoring to decide when to update a tag's name."""
        self.tn_entry_last_recorded_value = self.get_tn_text()
        # check validity
        if self.tn_entry_last_recorded_value == "":
            self.tn_entry.set_icon_from_icon_name(
                Gtk.EntryIconPosition.SECONDARY, Gtk.STOCK_DIALOG_ERROR)
        else:
            self.tn_entry.set_icon_from_icon_name(
                Gtk.EntryIconPosition.SECONDARY, None)
        # filter out change requests to reduce commit overhead
        if self.tn_entry_watch_id is None:
            # There is no watchers for the text entry. Register one.
            # Also, wait 1 second before commiting the change in order to
            # reduce rename requests
            tn_entry_changes = self.watch_tn_entry_changes
            self.tn_entry_watch_id = GObject.timeout_add(1000, tn_entry_changes)

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
                my_color = Gdk.color_parse(color)
                color = Gdk.Color(my_color.red, my_color.green, my_color.blue).to_string()
                color_add(color)
                self.tag.set_attribute('color', color)
            else:
                color_remove(self.tag.get_attribute('color'))
                self.tag.del_attribute('color')

    def on_tc_colsel_activated(self, widget, color):
        """Callback: update the tag color depending on the current color
        selection"""
        print("activated", widget, color, " <--- ignoring for now")
        return
        # color = self.tc_cc_colsel.get_rgba().to_color()
        color = color.to_color()
        if self.tag is not None:
            if color is not None:
                self.tag.set_attribute('color', color)
            else:
                self.tag.del_attribute('color')

    def on_tc_colsel_added(self, widget):
        """Callback: if a new color is added, register it in the configuration"""
        self.custom_colors = self.tc_cc_colsel.get_custom_colors()
        self.config.set("custom_colors", self.custom_colors)

    def on_close(self, widget, event, arg1=None, arg2=None, arg3=None):
        """ Callback: hide the tag editor when the close the window.

        Arguments arg1-arg3 are needed to satisfy callback when closing
        by Escape
        """
        self.app.close_tag_editor()
        return True
