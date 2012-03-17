# -*- coding: utf-8 -*-
# Copyright (c) 2012 - Wolter Hellmund <wolterh6@gmail.com>
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

from math import ceil
import gtk
import os

from GTG.tools.dates import Date


class pluginUrgencyColor:

    PLUGIN_NAME = 'Urgency Color'
    DEFAULT_PREFS = {
        'reddays': 30,
        'color_green': '#cfff84',
        'color_yellow': '#ffed84',
        'color_red': '#ff9784'}

    def __init__(self):
        self._plugin_api = None
        self.req = None

    def activate(self, plugin_api):
        """ Plugin is activated """
        self._plugin_api = plugin_api
        self.req = self._plugin_api.get_requester()
        self.prefs_load()
        self.prefs_init()
        # Set color function
        self._plugin_api.set_bgcolor_func(self.bgcolor)

    def _get_color(self, colindex):
        if colindex == 0:
            return self._pref_data['color_green']
        elif colindex == 1:
            return self._pref_data['color_yellow']
        elif colindex == 2:
            return self._pref_data['color_red']
        else:
            return None

    def bgcolor(self, node_id, standard_color):
        node = self.req.get_task(node_id)
        sdate = node.get_start_date()
        ddate = node.get_due_date()
        if (sdate != Date.no_date() != ddate):
            dayspan = (ddate - sdate).days
            daysleft = ddate.days_left()

            redf = self._pref_data['reddays']
            reddays = int(ceil(redf*dayspan/100))
            color = 0
            if daysleft <= dayspan:
                color = 1
            if daysleft <= reddays:
                color = 2
            # This list should be implemented in the settings
            #print "Giving color"
            return self._get_color(color)
        else:
            # Return color for this node
            return None

    def deactivate(self, plugin_api):
        """ Plugin is deactivated """
        self._plugin_api.set_bgcolor_func()

# Preferences dialog
    def is_configurable(self):
        """Requisite function for configurable plugins"""
        return True

    def configure_dialog(self, manager_dialog):
        self._pref_data_potential = self._pref_data
        self.prefs_window.show_all()
        #self.prefs_window.set_transient_for(manager_dialog)
        pass

    def prefs_init(self):
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'preferences.ui'))

        # Get the widgets
        #   Window
        self.prefs_window = self.builder.get_object('prefs_window')
        self.prefs_window.set_title(('GTG - %s preferences' \
            % self.PLUGIN_NAME))
        self.prefs_window.set_size_request(300, -1)
        self.prefs_window.hide_on_delete()

        #   Spin button
        self.spinbutton_reddays = self.builder.get_object('spinbutton_reddays')

        #   Colorbutton - RED
        self.colorbutton_red = self.builder.get_object('colorbutton_red')

        #   Colorbutton - YELLOW
        self.colorbutton_yellow = self.builder.get_object('colorbutton_yellow')

        #   Colorbutton - GREEN
        self.colorbutton_green = self.builder.get_object('colorbutton_green')

        #   Buttons
        self.button_apply = self.builder.get_object('button_apply')
        self.button_reset = self.builder.get_object('button_reset')

        # Update widget's values
        self.prefs_update_widgets()

        # Signal connections
        SIGNAL_CONNECTIONS_DIC = {
            'on_prefs_window_delete_event':
                self.on_prefs_cancel,
            'on_prefs_apply_event':
                self.on_prefs_apply,
            'on_prefs_reset_event':
                self.on_prefs_reset,
            'on_prefs_spinbutton_reddays_changed':
                self.on_prefs_spinbutton_reddays_changed,
            'on_prefs_colorbutton_red_changed':
                self.on_prefs_colorbutton_red_changed,
            'on_prefs_colorbutton_yellow_changed':
                self.on_prefs_colorbutton_yellow_changed,
            'on_prefs_colorbutton_green_changed':
                self.on_prefs_colorbutton_green_changed}
        self.builder.connect_signals(SIGNAL_CONNECTIONS_DIC)

    def prefs_update_widgets(self):
        """ Synchronizes the widgets with the data in _pref_data """
        # Spin button
        self.spinbutton_reddays.set_value(self._pref_data['reddays'])
        # Colorbutton - RED
        self.colorbutton_red.set_color( \
            gtk.gdk.color_parse(self._pref_data['color_red']))
        # Colorbutton - YELLOW
        self.colorbutton_yellow.set_color( \
            gtk.gdk.color_parse(self._pref_data['color_yellow']))
        # Colorbutton - GREEN
        self.colorbutton_green.set_color( \
            gtk.gdk.color_parse(self._pref_data['color_green']))

    def on_prefs_cancel(self, widget=None, data=None):
        self.prefs_update_widgets()
        self.prefs_window.hide()
        return True

    def on_prefs_apply(self, widget=None, data=None):
        self._pref_data = self._pref_data_potential
        self.prefs_store()
        self.prefs_window.hide()

    def on_prefs_reset(self, widget=None, data=None):
        # Restore the default plugin settings
        self._pref_data = self._pref_data_potential = dict(self.DEFAULT_PREFS)
        self.prefs_update_widgets()

    def prefs_load(self):
        data = self._plugin_api.load_configuration_object( \
            self.PLUGIN_NAME,
            'preferences')
        if not data or not isinstance(data, dict):
            self._pref_data = dict(self.DEFAULT_PREFS)
        else:
            self._pref_data = data

    def prefs_store(self):
        self._plugin_api.save_configuration_object( \
            self.PLUGIN_NAME,
            'preferences',
            self._pref_data)

    def on_prefs_spinbutton_reddays_changed(self, widget=None, data=None):
        self._pref_data_potential['reddays'] = \
            self.spinbutton_reddays.get_value()

    def on_prefs_colorbutton_red_changed(self, widget=None, data=None):
        self._pref_data_potential['color_red'] = \
            self.colorbutton_red.get_color().to_string()

    def on_prefs_colorbutton_yellow_changed(self, widget=None, data=None):
        self._pref_data_potential['color_yellow'] = \
            self.colorbutton_yellow.get_color().to_string()

    def on_prefs_colorbutton_green_changed(self, widget=None, data=None):
        self._pref_data_potential['color_green'] = \
            self.colorbutton_green.get_color().to_string()
