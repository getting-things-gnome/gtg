# -*- coding: utf-8 -*-
# Copyright (c) 2012 - XYZ <xyz@mail.com>
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

from GTG.tools.dates import date, no_date
from math import ceil

import gtk
import os

class pluginUrgencyCoding:

    PLUGIN_NAME = 'Urgency color'
    # FIXME: Choose a definitive name for the plugin and make it
    # consistent in all the plugin files.
    DEFAULT_PREFS = {
        'reddays':30,
        'color_red':'#cfff84',
        'color_yellow':'#ffed84',
        'color_green':'#ff9784'
    }
    
    def __init__(self):
        self._plugin_api = None
        self.req = None

    def activate(self, plugin_api):
        """ Plugin is activated """
        self._plugin_api = plugin_api
        self.req = self._plugin_api.get_requester()
        self.prefs_init()
        self.prefs_load()
        # Set color function
        self._plugin_api.set_bgcolor_func(self.bgcolor)

    def bgcolor(self, node_id, standard_color):
        node = self.req.get_task(node_id)
        sdate = node.get_start_date()
        ddate = node.get_due_date()
        if (sdate != no_date != ddate):
            dayspan = (ddate - sdate).days
            reddays = ceil(3.0*dayspan/10)
            daysleft = ddate.days_left()

            if daysleft == None \
                    and ddate.__class__.__name__ != 'RealDate':
                daysleft = (ddate.offset - date.today()).days
            color = 0
            if daysleft <= dayspan:
                color = 1
            if daysleft <= reddays:
                color = 2
            # This list should be implemented in the settings
            colors = ['#cfff84','#ffed84','#ff9784']
            #print "Giving color"
            return colors[color]
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
        self.prefs_window.show_all()
        self.prefs_window.set_transient_for(manager_dialog)

    def prefs_init(self):
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'preferences.ui'))
        # Get the widgets
        self.prefs_window = self.builder.get_object('window')
        self.prefs_window.set_title(('GTG - %s preferences' % self.PLUGIN_NAME))
        self.prefs_window.set_size_request(300,-1)
        self.spinner_reddays = self.builder.get_object('spinner_reddays')
        self.colorbutton_red = self.builder.get_object('colorbutton_red')
        self.colorbutton_yellow = self.builder.get_object('colorbutton_yellow')
        self.colorbutton_green = self.builder.get_object('colorbutton_green')
        self.button_apply =  self.builder.get_object('button_apply')
        self.button_reset = self.builder.get_object('button_reset')
        SIGNAL_CONNECTIONS_DIC = {
            'on_window_close_event':
                self.on_prefs_cancel,
            'on_prefs_apply_event':
                self.on_prefs_apply,
            'on_prefs_reset_event':
                self.on_prefs_reset,
        }
        self.builder.connect_signals(SIGNAL_CONNECTIONS_DIC)

    def on_prefs_cancel(self, widget=None, data=None):
        self.prefs_window.hide()
        # Restore widgets to current saved settings
        return True

    def on_prefs_apply(self, widget=None, data=None):
        self.prefs_store()
        self.prefs_window.hide()

    def on_prefs_reset(self, widget=None, data=None):
        # Restore the default plugin settings
        self.prefs_window.hide()

    def prefs_load(self):
        data = self._plugin_api.load_configuration_object( \
            self.PLUGIN_NAME,
            'preferences')
        if not data or not isinstance(data, dict):
            self._pref_data = self.DEFAULT_PREFS
        else:
            self._pref_data = data

    def prefs_store(self):
        self._plugin_api.save_configuration_object( \
            self.PLUGIN_NAME,
            'preferences',
            self._pref_data) #FIXME: need such an attribute

# TODO:
# Make preferences load colors for color buttons
# Make preference saving work
# Implement the color fecthing from preferences in the bgcolor function
# Implement the redday factor fectrhing from the preferences in the
# bgcolor function too
