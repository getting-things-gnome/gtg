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


import os

from gi.repository import Champlain
from gi.repository import Clutter
from gi.repository import GdkPixbuf
from gi.repository import Gtk
from gi.repository import GtkChamplain
from gi.repository import GtkClutter
from gi.repository import GeocodeGlib as Geocode

from GTG.plugins.geolocalized_tasks.marker import MarkerLayer
from GTG.plugins.geolocalized_tasks.geoclue import Geoclue
from GTG.plugins.geolocalized_tasks.store_and_load_data import store_pickled_file
from GTG.plugins.geolocalized_tasks.store_and_load_data import load_pickled_file

import dbus

# Attention!!! FIXME
# FIXME During porting GTG into GTK3/PyGObject was geolocalized.glade converted
# to GtkBuilder format together with other glade XMLs.
# FIXME Since this plugin is broken, I am not going to replace galde mentions
# to GtkBuilder, it's your job ;)

FILTER_NAME = '@@GeolocalizedTasks'

class geolocalizedTasks:

    def __init__(self):
        Clutter.init([])
        self.__latitude = None
        self.__longitude = None
        self.__selected_marker = None
        self.__active_sensitive = False
        self.__marker_last_location = None

        self.__factory = Champlain.MapSourceFactory.dup_default()
        self.__set_location_context_menu = None
        self.__locations = []
        self.__task_locations = {}
        self.__tag_locations = {}
        self.__view = None
        self.__current_layer = None
        self.__menu_item_tag_sidebar = None

        self.__where = Geoclue()
        self.__where.client.connect_to_signal('LocationUpdated', self._location_updated)
        self.__where.client.Start()
        self.__distance = 15


#        self.__tag_locations_data_path = 
#        self.__task_locations_data_path =
#        self.__last_location_data_path = 

    def _get_where (self):
        return self.__where

    def _get_user_position(self):
        return [self.__latitude, self.__longitude]

    def _set_user_position(self, position):
        [latitude, longitude] = position
        self.__latitude = latitude
        self.__longitude = longitude

    def _get_factory(self):
        return self.__factory

    def _get_selected_marker(self):
        return self.__selected_marker

    def _set_selected_marker(self, marker):
        self.__selected_marker = marker

    def _get_active_sensitive(self):
        return self.__active_sensitive

    def _set_active_sensitive(self, active_sensitive):
        self.__active_sensitive = active_sensitive

    def _get_marker_last_location(self):
        return self.__marker_last_location

    def _set_marker_last_location(self, marker):
        self.__marker_last_location = marker

    def _create_context_menu(self, event, plugin_api):
        if self.__set_location_context_menu is not None:
            self.__set_location_context_menu.popdown()
            self.__set_location_context_menu = None

        view = self._get_view()
        longitude = view.x_to_longitude(event.x)
        latitude = view.y_to_latitude(event.y)

        context_menu = Gtk.Menu()

        mi = Gtk.MenuItem()
        mi.set_label("Add Location")
        mi.connect ("activate", self._on_im_here, [latitude, longitude])
        context_menu.append(mi)

        mi = Gtk.MenuItem()
        mi.set_label("Edit Location")
        mi.connect("activate", self._on_edit, plugin_api)
        context_menu.append(mi)

        if self._get_active_sensitive() is False:
            mi.set_sensitive(False)

        mi = Gtk.MenuItem()
        mi.set_label("Remove Location")
        mi.connect("activate", self._on_delete, [latitude, longitude])
        context_menu.append(mi)

        if self._get_active_sensitive() is False:
            mi.set_sensitive(False)
        else:
            self._set_active_sensitive(False)

        context_menu.show_all()

        context_menu.popup(None, None, None, None, event.button, event.time)
        self.__set_location_context_menu = context_menu

    def _get_locations(self):
        return self.__locations

    def _set_locations(self, locations):
        self.__locations = locations

    def _add_to_locations(self, marker):
        self.__locations.append(marker)

    def _remove_from_locations(self, marker):
        if marker in self.__locations:
            self.__locations.remove(marker)

    def _get_task_locations(self):

        if not self.__task_locations:
            data_path = os.path.join('plugins/geolocalized_tasks', "task_locations")
            self.__task_locations = load_pickled_file(data_path, {})
        return self.__task_locations

    def _set_task_locations(self, task_locations_dict):
        self.__task_locations = task_locations_dict

    def _add_location_to_task_locations(self, task_id, location):
        if task_id not in self.__task_locations:
            self.__task_locations[task_id] = []

        self.__task_locations[task_id].append(location)

    def _remove_location_from_task_locations(self, task_id, location):
        if task_id not in self.__task_locations:
            return

        if location not in self.__task_locations[task_id]:
            return

        self.__task_locations[task_id].remove(location)

        if self.__task_locations[task_id] is []:
            del self.__task_locations[task_id]

    def _get_tag_locations(self):
        if not self.__tag_locations:
            data_path = os.path.join('plugins/geolocalized_tasks', "tag_locations")
            self.__tag_locations = load_pickled_file(data_path, {})
        return self.__tag_locations

    def _set_tag_locations(self, tag_locations_dict):
        self.__tag_locations = tag_locations_dict

    def _add_location_to_tag_locations(self, tag_name, location):
        if tag_name not in self.__tag_locations:
            self.__tag_locations[tag_name] = []

        self.__tag_locations[tag_name].append(location)

    def _remove_location_from_tag_location(self, tag_name, location):
        if tag_name not in self.__tag_locations:
            return

        if location not in self.__tag_locations[tag_name]:
            return

        self.__tag_locations[tag_name].remove(location)

        if self.__tag_locations[tag_name] is []:
            del self.__tag_locations[tag_name]

    def _get_all_locations(self):
        tag_locations_dict = self._get_tag_locations()
        final_list_locations = []
        for tag in tag_locations_dict:
            locations = tag_locations_dict[tag]
            for location in locations:
                if location not in final_list_locations:
                    final_list_locations.append(location)
        task_locations_dict = self._get_task_locations()
        for task in task_locations_dict:
            locations = task_locations_dict[task]
            for location in locations:
                if location not in final_list_locations:
                    final_list_locations.append(location)
        return final_list_locations

    def _get_view(self):
        return self.__view

    def _set_view(self, view):
        self.__view = view

    def _get_current_layer(self):
        return self.__current_layer

    def _set_current_layer(self, layer):
        self.__current_layer = layer

    def _get_menu_item_tag_sidebar(self):
        return self.__menu_item_tag_sidebar

    def _set_menu_item_tag_sidebar(self, mi):
        self.__menu_item_tag_sidebar = mi

    def _get_toolbutton_task_toolbar(self):
        return self.__get_toolbutton_task_toolbar

    def _set_toolbutton_task_toolbar(self, btn):
        self._toolbutton_task_toolbar = btn

    def _location_updated(self, old_path, new_path):
        where = self._get_where()
        system_bus = where._system_bus
        location_object =  system_bus.get_object(where.GEOCLUE2_BUS_NAME, new_path)
        location_properties = dbus.Interface(location_object, where.PROPERTIES_INTERFACE_NAME)
        latitude = location_properties.Get(where.LOCATION_INTERFACE_NAME, "Latitude")
        longitude = location_properties.Get(where.LOCATION_INTERFACE_NAME, "Longitude")
        self._set_user_position([latitude, longitude])

    def activate(self, plugin_api):
        """
        Activates the plugin.
        """
        mi = plugin_api.add_item_to_tag_menu("Add Location", self._set_tag_location, plugin_api)
        self._set_menu_item_tag_sidebar(mi)
        #Filter
        builder = self._get_builder_from_file("preferences2.ui")
        self.__spin = builder.get_object("spin_proximityfactor")
        requester = plugin_api.get_requester()
        requester.add_filter(FILTER_NAME, self._filter_work_view)
        self.__requester = requester

    def deactivate(self, plugin_api):
        """
        Desactivates the plugin.
        """
        # everything should be removed, in case a task is currently opened
        where = self._get_where()
        where.client.Stop()

        try:
            mi = self._get_menu_item_tag_sidebar()
            plugin_api.remove_item_from_tag_menu(mi)

            tb = self._get_toolbutton_task_toolbar()
            plugin_api.remove_toolbar_item(tb)
            requester = plugin_api.get_requester()
            requester.remove_filter(FILTER_NAME)
        except:
            pass

    def onTaskOpened(self, plugin_api):
        """
            Adds the button when a task is opened
        """
        plugin_path = os.path.dirname(os.path.abspath(__file__))

        image_geolocalization_path = os.path.join(plugin_path, "icons/hicolor/24x24/geolocalization.png")
        pixbuf_geolocalization = GdkPixbuf.Pixbuf.new_from_file_at_size(image_geolocalization_path, 24, 24)

        # create the image and associate the pixbuf
        icon_geolocalization = Gtk.Image()
        icon_geolocalization.set_from_pixbuf(pixbuf_geolocalization)
        icon_geolocalization.show()

        btn = Gtk.ToolButton()
        btn.set_icon_widget(icon_geolocalization)
        btn.set_label("Set/View location")
        btn.connect('clicked', self._set_task_location, plugin_api)
        btn.show_all()

        plugin_api.add_toolbar_item(btn)
        self._set_toolbutton_task_toolbar(btn)

    def is_configurable(self):
        return True

    def configure_dialog(self, manager_dialog):
        self.on_geolocalized_preferences()

    def task_location_filter(self, tid):
        pass
#        """filters by location only one task"""
#        has_location = False
#        task = self.plugin_api.get_task(tid)
#        if task.get_status() == "Active":
#            if task.is_workable():
#                tags = task.get_tags()
#
#                # check if it has the location set
#                for tag in tags:
#                    if "location" in tag.get_all_attributes():
#                        has_location = True
#
#                if has_location:
#                    # do the actual filter
#                    for tag in tags:
#                            if tag.get_attribute("location"):
#                                position = eval(tag.get_attribute("location"))
#                                if not self.geoclue.compare_position(
#                                        position[0], position[1],
#                                        float(self.PROXIMITY_FACTOR)):
#                                    self.plugin_api.add_task_to_filter(tid)
#                                    if tid not in self.location_filter:
#                                        self.location_filter.append(tid)
#                                    return False
#        return True

    #=== GEOLOCALIZED PREFERENCES=============================================

    def _check_set_pref(self, widget, spin):
        if widget.get_active() is True:
            spin.set_sensitive(True)
        else:
            spin.set_sensitive(False)

    def _spin_value_changed(self, widget, data):
        self.__distance = widget.get_value()

    def on_geolocalized_preferences(self):
        builder = self._get_builder_from_file("preferences2.ui")
        dialog = builder.get_object("dialog")

        spin = builder.get_object("spin_proximityfactor")
        spin.set_sensitive(False)
        spin.set_range(15.00, 1000.00)

        adjust = Gtk.Adjustment(self.__distance, 1, 100, 1, 1, 1)
        spin.configure(adjust, 1, 0)
        spin_v = spin.get_value()
        spin_value = spin.set_value(spin_v)

        spin.connect("value-changed", self._spin_value_changed, None)

        check_set = builder.get_object("checkbutton")
        check_set.connect("toggled", self._check_set_pref, spin)

        btn = builder.get_object("button_ok")
        btn.connect('clicked', self._ok_preferences, check_set)

        dialog.show_all()

    def _filter_work_view(self, task):
        data_path = os.path.join('plugins/geolocalized_tasks', "last_location")
        [user_latitude, user_longitude] = load_pickled_file(data_path, [])

        user_location = Geocode.Location.new(user_latitude, user_longitude, Geocode.LOCATION_ACCURACY_STREET)

        locations = []
        final_list_locations = []

        task_id = task.get_uuid()
        tasks_dict = self._get_task_locations()
        if task_id in tasks_dict:
            locations = tasks_dict[task_id]

        for location in locations:
            final_list_locations.append(location)

        tags_dict = self._get_tag_locations()
        tags_name_list = task.get_tags_name()
        for tag_name in tags_name_list:
            if tag_name in tags_dict:
                locations = tags_dict[tag_name]
                for location in locations:
                    if location not in final_list_locations:
                        final_list_locations.append(location)

        for location in final_list_locations:
            [name, latitude, longitude] = location
            geocode_location = Geocode.Location.new(latitude, longitude, Geocode.LOCATION_ACCURACY_STREET)
            dist = Geocode.Location.get_distance_from(user_location, geocode_location)
            if (dist <= self.__distance):
                return True
        return False

#        print ("DEBUG | user location", user_location)
#        locations = self._get_all_locations()
#        print ("DEBUG | locations_list", locations)
#        final_dict = {}
#        for location in locations:
#            [name, latitude, longitude] = location
#            print ("DEBUG | locations_list 1", location)
#            geocode_location = Geocode.Location.new(latitude, longitude, Geocode.LOCATION_ACCURACY_STREET)
#            dist = Geocode.Location.get_distance_from(user_location, geocode_location)
#            print("Eliane | distance is", dist)
#            final_dict[geocode_location] = dist

#        wTree = Gtk.glade.XML(self.glade_file, "Preferences")
#        dialog = wTree.get_widget("Preferences")
#        dialog.connect("response", self.preferences_close)
#
#        check_network = wTree.get_widget("check_network")
#        check_cellphone = wTree.get_widget("check_cellphone")
#        check_gps = wTree.get_widget("check_gps")
#
#        providers = self.geoclue.get_available_providers()
#        provider_name_list = []
#
#        for provider in providers:
#            provider_name_list.append(provider['name'].lower())
#
#        if "hostip" not in provider_name_list:
#            check_network.set_active(False)
#            check_network.set_sensitive(False)
#        else:
#            if "network" in self.LOCATION_DETERMINATION_METHOD:
#                for provider in providers:
#                    status = self.geoclue.provider_status(provider['object'])
#                    if provider['name'].lower() == "hostip":
#                        if status in ["available", "acquiring"]:
#                            check_network.set_active(True)
#                            break
#                        else:
#                            check_network.set_active(False)
#                            check_network.set_sensitive(False)
#                            break
#            else:
#                for provider in providers:
#                    status = self.geoclue.provider_status(provider['object'])
#                    if provider['name'].lower() == "hostip" and\
#                            status in ["error", "unavailable"]:
#                        check_network.set_active(False)
#                        check_network.set_sensitive(False)
#                        break
#
#        if "gsmloc" not in provider_name_list:
#            check_cellphone.set_active(False)
#            check_cellphone.set_sensitive(False)
#        else:
#            if "cellphone" in self.LOCATION_DETERMINATION_METHOD:
#                for provider in providers:
#                    status = self.geoclue.provider_status(provider['object'])
#                    if provider['name'].lower() == "gsmloc":
#                        if status in ["available", "acquiring"]:
#                            check_cellphone.set_active(True)
#                        else:
#                            check_cellphone.set_active(False)
#                            check_cellphone.set_sensitive(False)
#                        break
#            else:
#                for provider in providers:
#                    status = self.geoclue.provider_status(provider['object'])
#                    if provider['name'].lower() == "gsmloc" and\
#                            status in ["error", "unavailable"]:
#                        check_cellphone.set_active(False)
#                        check_cellphone.set_sensitive(False)
#                        break
#
#        # TODO: separate gypsy from gpsd
#        if "gpsd" not in provider_name_list:
#            if "gypsy" not in provider_name_list:
#                check_gps.set_active(False)
#                check_gps.set_sensitive(False)
#        else:
#            if "gps" in self.LOCATION_DETERMINATION_METHOD:
#                for provider in providers:
#                    status = self.geoclue.provider_status(provider['object'])
#                    if provider['name'].lower() in ["gpsd", "gypsy"]:
#                        if status in ["available", "acquiring"]:
#                            check_gps.set_active(True)
#                        else:
#                            check_gps.set_active(False)
#                            check_gps.set_sensitive(False)
#                        break
#            else:
#                for provider in providers:
#                    status = self.geoclue.provider_status(provider['object'])
#                    if provider['name'].lower() in ["gpsd", "gypsy"] and\
#                            status in ["error", "unavailable"]:
#                        check_gps.set_active(False)
#                        check_gps.set_sensitive(False)
#                        break
#
#        spin_proximityfactor = wTree.get_widget("spin_proximityfactor")
#        spin_proximityfactor.set_value(float(self.PROXIMITY_FACTOR))
#        spin_proximityfactor.connect("changed",
#                                     self.spin_proximityfactor_changed)
#        self.tmp_proximityfactor = float(self.PROXIMITY_FACTOR)
#
#        dialog.show_all()

    def spin_proximityfactor_changed(self, spinbutton):
        pass
#        self.tmp_proximityfactor = spinbutton.get_value()

    def preferences_close(self, dialog, response=None):
        pass
#        if response == Gtk.ResponseType.OK:
#            self.PROXIMITY_FACTOR = float(self.tmp_proximityfactor)
#            dialog.destroy()
#        else:
#            dialog.destroy()

    #=== GEOLOCALIZED PREFERENCES==============================================

    #=== SET TASK LOCATION ====================================================
    def _get_builder_from_file(self, filename):
        builder = Gtk.Builder()
        plugin_path = os.path.dirname(os.path.abspath(__file__))
        ui_file_path = os.path.join(plugin_path, filename)
        builder.add_from_file(ui_file_path)
        return builder

    def _update_location_name(self, reverse, res, marker):
        place = reverse.resolve_finish(res)
        marker.set_text(place.get_name())

    def _on_im_here (self, widget, position):
        [latitude, longitude] = position

        marker = Champlain.Label()
        marker.set_text("...")
        marker.set_location(latitude, longitude)
        layer = self._get_current_layer()
        layer.add_marker(marker)
        marker.connect('button-press-event', self._on_marker, marker)
        self._add_to_locations(marker)

        geocodeLocation = Geocode.Location.new(latitude, longitude, Geocode.LOCATION_ACCURACY_STREET)
        reverse = Geocode.Reverse.new_for_location (geocodeLocation)
        reverse.resolve_async(None, self._update_location_name, marker)

    def _on_delete (self, widget, data):
        marker = self._get_selected_marker()
        layer = self._get_current_layer()
        layer.remove_marker(marker)
        self._remove_from_locations(marker)
        self._set_selected_marker(None)

    def _check_clicked (self, widget, tag_name):
        marker = self._get_selected_marker()
        location = [marker.get_text(), marker.get_latitude(),marker.get_longitude()]
        if widget.get_active() is True:
            self._add_location_to_tag_locations(tag_name, location)
        else:
            self._remove_location_from_tag_location(tag_name, location)

    #for edit
    def _on_edit (self, widget, plugin_api):
        builder = self._get_builder_from_file("edit_location.ui")
        dialog = builder.get_object("dialog")

        entry = builder.get_object("entry")
        marker = self._get_selected_marker()
        location_name = marker.get_text()
        entry.set_text(location_name)

        all_tags = plugin_api.get_requester().get_all_tags()

        btn = builder.get_object("button_ok")
        btn.connect('clicked', self._ok_edit, entry)

        btn = builder.get_object("button_cancel")
        btn.connect('clicked', self._cancel_edit, widget)

        scrolled_window = builder.get_object("scrolledwindow")
        grid = Gtk.Grid()
        scrolled_window.add(grid)

        tag_location_data_path = os.path.join('plugins/geolocalized_tasks', "tag_locations")
        loaded_dict = load_pickled_file(tag_location_data_path, {})
        self._set_tag_locations(loaded_dict)

        i = 0
        for tag_name in all_tags:
            if tag_name.startswith("@"):
                check = Gtk.CheckButton(tag_name)
                if tag_name in loaded_dict:
                    location = [marker.get_text(), marker.get_latitude(), marker.get_longitude()]
                    locations = loaded_dict[tag_name]
                    if location in locations:
                        check.set_active(True)
                check.connect("toggled", self._check_clicked, tag_name)
                grid.attach(check, i%4, i/4, 1, 1)
                i += 1

        scrolled_window.show_all()
        dialog.show_all()

    def _on_context_menu(self, widget, event, plugin_api):
        if (event.button == 3):
            self._create_context_menu(event, plugin_api)

        return True

    def _on_marker(self, widget, event, marker):
        if marker is self._get_marker_last_location():
            return False

        self._set_selected_marker(marker)
        self._set_active_sensitive(True)

        return False

    def _get_stored_locations(self, data_path, key):
        locations_dict = load_pickled_file(data_path, {})
        if key in locations_dict:
            return locations_dict[key]
        return []

    def _get_tag_stored_locations(self, tag_name):
        data_path = os.path.join('plugins/geolocalized_tasks', "tag_locations")
        locations_dict = load_pickled_file(data_path, {})
        self._set_tag_locations(locations_dict)
        return self._get_stored_locations(data_path, tag_name)

    def _set_tag_location(self, widget, tag, plugin_api):
        tag_name = tag.get_name()
        self._create_location_window(plugin_api, self._get_tag_stored_locations, self._close_tag, self._cancel, tag_name, tag_name)

    def _get_task_stored_locations(self, task_id):
        data_path = os.path.join('plugins/geolocalized_tasks', "task_locations")
        locations_dict = load_pickled_file(data_path, {})
        self._set_task_locations(locations_dict)
        return self._get_stored_locations(data_path, task_id)

    def _set_task_location(self, widget, plugin_api):
        task_id = plugin_api.get_selected().get_uuid()
        self._create_location_window(plugin_api, self._get_task_stored_locations, self._close_task, self._cancel, task_id, task_id)

    def _create_location_window(self, plugin_api, get_locations_fn, close_cb, cancel_cb, get_locations_data=None, close_data=None, cancel_data=None):
        builder = self._get_builder_from_file("set_locations.ui")
        dialog = builder.get_object("SetTaskLocation")

        vbox_map = builder.get_object("vbox_map")

        map = GtkChamplain.Embed()
        vbox_map.add(map)

        view = map.get_view()
        view.set_property("zoom-level", 10)
        view.set_reactive(True)

        #Factory
        source = self._get_factory().create_cached_source(Champlain.MAP_SOURCE_OSM_MAPQUEST)
        view.set_map_source(source)

        layer = Champlain.MarkerLayer()
        self._set_current_layer(layer)
        view.add_layer(layer)

        view.connect('button-release-event', self._on_context_menu, plugin_api)

        self._set_view(view)

        btn = builder.get_object("btn_zoom_in")
        btn.connect('clicked', self._zoom_in, view)

        btn = builder.get_object("btn_zoom_out")
        btn.connect('clicked', self._zoom_out, view)

        last_location_data_path = os.path.join('plugins/geolocalized_tasks', "last_location")
        [user_latitude, user_longitude] = self._get_user_position()
        if user_latitude is None and user_longitude is None:
            [user_latitude, user_longitude] = load_pickled_file(last_location_data_path, [None, None])
            self._set_user_position([user_latitude, user_longitude])

        if user_latitude is not None and user_longitude is not None:
            red = Clutter.Color.new(0xff, 0x00, 0x00, 0xbb)
            view.center_on(user_latitude, user_longitude)
            store_pickled_file(last_location_data_path, [user_latitude, user_longitude])

            #Set current user location
            marker = Champlain.Label()
            marker.set_color(red)
            marker.set_text("I am here!")
            marker.set_location(user_latitude, user_longitude)
            layer.add_marker(marker)
            marker.set_use_markup(True)
            self._set_marker_last_location(marker)

            marker.connect('button-press-event', self._on_marker, marker)

            btn = builder.get_object("btn_zoom_in")
            btn.connect('clicked', self._zoom_in, view)

            btn = builder.get_object("btn_zoom_out")
            btn.connect('clicked', self._zoom_out, view)

        locations = get_locations_fn(get_locations_data)
        for location in locations:
            [text, latitude, longitude] = location
            marker = Champlain.Label()
            marker.set_text(text)
            marker.set_location(latitude, longitude)
            layer.add_marker(marker)
            marker.connect('button-press-event', self._on_marker, marker)
            self._add_to_locations(marker)

        layer.show_all()

        btn = builder.get_object("btn_cancel")
        btn.connect('clicked', cancel_cb, cancel_data)

        btn = builder.get_object("btn_ok")
        btn.connect('clicked', close_cb, close_data)

        dialog.show_all()

    def _zoom_in(self, widget, view):
        view.zoom_in()

    def _zoom_out(self, widget, view):
        view.zoom_out()

    def _close(self, widget, data_path, dict, key):
        locations = []
        for location in self._get_locations():
            locations.append([location.get_text(), location.get_latitude(), location.get_longitude()])
        dict[key] = locations
        print(dict.keys())
        for k in dict.keys():
            print(dict[k])
        store_pickled_file (data_path, dict)

        widget.get_parent_window().destroy()
        self._clean_up()

    def _close_task(self, widget, task_id):
        data_path = os.path.join('plugins/geolocalized_tasks', 'task_locations')
        task_locations_dict = self._get_task_locations()
        self._close(widget, data_path, task_locations_dict, task_id)

    def _close_tag(self, widget, tag_name):
        data_path = os.path.join('plugins/geolocalized_tasks', 'tag_locations')
        tag_locations_dict = self._get_tag_locations()
        self._close(widget, data_path, tag_locations_dict, tag_name)

    def _cancel(self, widget, data):
        widget.get_parent_window().destroy()
        self._clean_up()

#    def _cancel_task(self, widget, data):
#        widget.get_parent_window().destroy()
#        self._clean_up()

#    def _cancel_tag(self, widget, data):
#        widget.get_parent_window().destroy()
#        self._clean_up()

    def _ok_edit (self, widget, entry):
        marker = self._get_selected_marker()
        old_name = marker.get_text()
        new_name = entry.get_text()

        if old_name != new_name:
            marker.set_text(entry.get_text())
            old_location = [old_name, marker.get_latitude(), marker.get_longitude()]
            new_location = [new_name, marker.get_latitude(), marker.get_longitude()]

            tag_locations = self._get_tag_locations()
            for key in tag_locations.keys():
                if old_location in tag_locations[key]:
                    self._remove_location_from_tag_location(key, old_location)
                    self._add_location_to_tag_locations(key, new_location)

        tag_location_data_path = os.path.join('plugins/geolocalized_tasks', "tag_locations")
        store_pickled_file(tag_location_data_path, self._get_tag_locations())
        widget.get_parent_window().destroy()

    def _cancel_edit (self, widget, data):
        widget.get_parent_window().destroy()

    def _ok_preferences (self, widget, check):
        tasks_tree = self.__requester.get_tasks_tree()
        if check.get_active():
            self.__requester.apply_global_filter(tasks_tree, FILTER_NAME)
        else:
            self.__requester.unapply_global_filter(tasks_tree, FILTER_NAME)
        widget.get_parent_window().destroy()

    def _clean_up(self):
        self._set_current_layer(None)
        self._set_view(None)
        self._set_locations([])
