
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
from gi.repository import Gtk
from gi.repository import Gdk
import os

from GTG.core.dates import Date


@Gtk.Template(filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preferences.ui'))
class UrgencyColorPreferences(Gtk.Window):

    __gtype_name__ = 'UrgencyColorPreferences'

    PLUGIN_NAME = 'Urgency Color'
    DEFAULT_PREFS = {
        'reddays': 30,
        'color_low': '#cfff84',
        'color_normal': '#ffed84',
        'color_high': '#ff9784',
        'color_overdue': '#b8b8b8'}

    # Get the widgets
    #   Spin button
    spinbutton_reddays = Gtk.Template.Child()

    #   Colorbutton - OVERDUE
    colorbutton_overdue = Gtk.Template.Child()

    #   Colorbutton - HIGH
    colorbutton_high = Gtk.Template.Child()

    #   Colorbutton - NORMAL
    colorbutton_normal = Gtk.Template.Child()

    #   Colorbutton - LOW
    colorbutton_low = Gtk.Template.Child()

    #   Buttons
    button_apply = Gtk.Template.Child()
    button_reset = Gtk.Template.Child()

    def __init__(self, plugin_api):
        super().__init__(title=f'GTG - {self.PLUGIN_NAME} preferences')
        self._plugin_api = plugin_api
        self.prefs_load()

        # Update widget's values
        self.prefs_update_widgets()

    def prefs_update_widgets(self):
        """ Synchronizes the widgets with the data in _pref_data """
        # Spin button
        self.spinbutton_reddays.set_value(self._pref_data['reddays'])
        rgba = Gdk.RGBA()
        # Colorbutton - OVERDUE
        rgba.parse(self._pref_data['color_overdue'])
        self.colorbutton_overdue.set_rgba(rgba)
        # Colorbutton - HIGH
        rgba.parse(self._pref_data['color_high'])
        self.colorbutton_high.set_rgba(rgba)
        # Colorbutton - NORMAL
        rgba.parse(self._pref_data['color_normal'])
        self.colorbutton_normal.set_rgba(rgba)
        # Colorbutton - LOW
        rgba.parse(self._pref_data['color_low'])
        self.colorbutton_low.set_rgba(rgba)

    def on_prefs_cancel(self, widget=None, data=None):
        self.prefs_update_widgets()
        self.hide()

    def on_prefs_apply(self, widget=None, data=None):
        self._pref_data = self._pref_data_potential
        self.prefs_store()
        self._refresh_task_color()
        self.hide()

    def on_prefs_reset(self, widget=None, data=None):
        # Restore the default plugin settings
        self._pref_data = self._pref_data_potential = dict(self.DEFAULT_PREFS)
        self.prefs_update_widgets()

    def on_prefs_spinbutton_reddays_changed(self, widget=None, data=None):
        self._pref_data_potential['reddays'] = \
            self.spinbutton_reddays.get_value()

    def on_prefs_colorbutton_overdue_changed(self, widget=None, data=None):
        self._pref_data_potential['color_overdue'] = \
            self.colorbutton_overdue.get_color().to_string()

    def on_prefs_colorbutton_high_changed(self, widget=None, data=None):
        self._pref_data_potential['color_high'] = \
            self.colorbutton_high.get_color().to_string()

    def on_prefs_colorbutton_normal_changed(self, widget=None, data=None):
        self._pref_data_potential['color_normal'] = \
            self.colorbutton_normal.get_color().to_string()

    def on_prefs_colorbutton_low_changed(self, widget=None, data=None):
        self._pref_data_potential['color_low'] = \
            self.colorbutton_low.get_color().to_string()

    def prefs_load(self):
        self._pref_data = self._plugin_api.load_configuration_object(
            self.PLUGIN_NAME, "preferences",
            default_values=self.DEFAULT_PREFS)

        # CORRECT NAMES FROM OLD PREFERENCES
        # This is a dirty fix and thus should be removed in a
        # distant future, when nobody has "red", "yellow" or "green"
        # settings
        namepairs = {'red': 'high', 'yellow': 'normal', 'green': 'low'}
        for oldname, newname in namepairs.items():
            old_key, new_key = "color_" + oldname, "color_" + newname
            if old_key in self._pref_data:
                self._pref_data[new_key] = self._pref_data.pop(old_key)

    def prefs_store(self):
        self._plugin_api.save_configuration_object(
            self.PLUGIN_NAME,
            'preferences',
            self._pref_data)

    def get_data_reference(self):
        """ Get a reference to use to access plugin preference data """
        return self._pref_data


class UrgencyColorPlugin():
    def __init__(self):
        self._plugin_api = None
        self.ds = None

    def activate(self, plugin_api):
        """ Plugin is activated """
        self._plugin_api = plugin_api
        self.ds = self._plugin_api.ds
        self.prefs_window = UrgencyColorPreferences(plugin_api)
        self._pref_data = self.prefs_window.get_data_reference()
        # Set color function
        self._refresh_task_color()

    def _refresh_task_color(self):
        self._plugin_api.set_bgcolor_func(self.bgcolor)

    def _get_color(self, colindex):
        if colindex == 0:
            return self._pref_data['color_low']
        elif colindex == 1:
            return self._pref_data['color_normal']
        elif colindex == 2:
            return self._pref_data['color_high']
        elif colindex == 3:
            return self._pref_data['color_overdue']
        else:
            return None

    def _get_gradient_color(self, color1, color2, position):
        """This function returns a string in the hexadecimal form of Gdk.Color
        which corresponds to the position (a float value from 0 to 1) in the
        gradient formed by color1 & color2, both of type Gdk.Color"""
        color1 = Gdk.color_parse(color1)
        color2 = Gdk.color_parse(color2)
        R1, G1, B1 = color1.red, color1.green, color1.blue
        R2, G2, B2 = color2.red, color2.green, color2.blue
        R = R1 + (R2 - R1) * position
        G = G1 + (G2 - G1) * position
        B = B1 + (B2 - B1) * position
        return Gdk.Color.to_string(Gdk.Color(int(R), int(G), int(B)))

    def get_node_bgcolor(self, node):
        """ This method checks the urgency of a node (task) and returns its
         urgency background color"""
        sdate = node.get_start_date()
        ddate = node.get_due_date()
        daysleft = ddate.days_left()

        # Dates undefined
        if (ddate == Date.today()):
            return self._get_color(2)  # High urgency
        elif ddate != Date.no_date():  # Has a due date
            if daysleft < 0:
                return self._get_color(3)  # Overdue
            elif sdate == Date.no_date() and not ddate.is_fuzzy():
                # Normal if no start date and not fuzzy
                return self._get_color(1)

        # Fuzzy dates (now, soon, someday)
        # These can ignore the start date
        if (ddate == Date.now()):
            return self._get_color(2)
        elif (ddate == Date.soon()):
            return self._get_color(1)
        elif (ddate == Date.someday()):
            return self._get_color(0)

        # Dates fully defined. Calculate gradient color
        elif (sdate != Date.no_date() != ddate):
            dayspan = (ddate - sdate).days
            redf = self._pref_data['reddays']
            reddays = int(ceil(redf / 100.0 * dayspan))

            # Gradient variables
            grad_dayspan = dayspan - reddays
            grad_half_dayspan = grad_dayspan / 2.0

            # Default to low urgency color
            color = self._get_color(0)

            # CL : low urgency color
            # CN : normal urgency color
            # CH : high urgency color
            # CO : overdue color
            # To understand this section, it is easier to draw out a
            # timeline divided into 3 sections: CL to CN, CN to CH and
            # the reddays section. Then point out the spans of the
            # different variables (dayspan, daysleft, reddays,
            # grad_dayspan, grad_half_dayspan)
            if daysleft < 0:  # CO
                color = self._get_color(3)
            elif daysleft <= reddays:  # CH
                color = self._get_color(2)
            elif daysleft <= (dayspan - grad_half_dayspan):
                # Gradient CN to CH
                # Has to be float so division by it is non-zero
                steps = float(grad_half_dayspan)
                step = grad_half_dayspan - (daysleft - reddays)
                color = self._get_gradient_color(self._get_color(1),
                                                 self._get_color(2),
                                                 step / steps)
            elif daysleft <= dayspan:
                # Gradient CL to CN
                steps = float(grad_half_dayspan)
                step = grad_half_dayspan - (daysleft - reddays - grad_half_dayspan)
                color = self._get_gradient_color(self._get_color(0),
                                                 self._get_color(1),
                                                 step / steps)

            return color

        # Insufficient data to determine urgency
        else:
            return None

    def bgcolor(self, node, standard_color):
        color = self.get_node_bgcolor(node)

        def __get_active_child_list(node):
            """ This function recursively fetches a list
            of all the children of a task which are active
            (i.e - the subtasks which are not marked as 'Done' or 'Dismissed'
            """
            child_list = []
            for child in node.children:
                child_list += __get_active_child_list(child)
                if child.is_active:
                    child_list.append(child_id)
            return child_list

        child_list = __get_active_child_list(node)

        daysleft = None
        for child in child_list:
            if child.date_due == Date.no_date():
                continue

            daysleft_of_child = child.date_due.days_left()
            if daysleft is None:
                daysleft = daysleft_of_child
                color = self.get_node_bgcolor(child)
            elif daysleft_of_child < daysleft:
                daysleft = daysleft_of_child
                color = self.get_node_bgcolor(child)

        return color

    def deactivate(self, plugin_api):
        """ Plugin is deactivated """
        self._plugin_api.set_bgcolor_func()

# Preferences dialog
    def is_configurable(self):
        """Requisite function for configurable plugins"""
        return True

    def configure_dialog(self, manager_dialog):
        self._pref_data_potential = self._pref_data
        self.prefs_window.present()
        # self.prefs_window.set_transient_for(manager_dialog)
