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


class geolocalizedTasks:

    def __init__(self):
        Clutter.init([])
        self.latitude = None
        self.longitude = None
        self.where = Geoclue()
        self.where.client.connect_to_signal('LocationUpdated', self._location_updated)
        self.where.client.Start()
        self.marker_to_be_deleted = None
        self.delete = False
        self.marker_last_location = None
        self.tags = None
        self.plugin_api = None

#        self.factory = Champlain.MapSourceFactory.dup_default()
        self.context = None
        self.locations = []
        self.task_id = ""
        self.dict = {}
#        self.geoclue = Geoclue.DiscoverLocation()
#        self.geoclue.connect(self.location_changed)
#
#        self.plugin_path = os.path.dirname(os.path.abspath(__file__))
#        self.glade_file = os.path.join(self.plugin_path, "geolocalized.ui")
#
#        # the preference menu for the plugin
#        self.menu_item = Gtk.MenuItem("Geolocalized-tasks Preferences")
#
#        self.PROXIMITY_FACTOR = 5  # 5 km
#        self.LOCATION_DETERMINATION_METHOD = []
#            # "network", "gps", "cellphone"
#
#        for provider in self.geoclue.get_available_providers():
#            status = self.geoclue.provider_status(provider['object'])
#            if provider['name'].lower() == "hostip":
#                if status in ["available", "acquiring"]:
#                    self.LOCATION_DETERMINATION_METHOD.append("network")
#            elif provider['name'].lower() in ["gpsd", "gypsy"]:
#                if status in ["available", "acquiring"]:
#                    self.LOCATION_DETERMINATION_METHOD.append("gps")
#            elif provider['name'].lower() == "gsmloc":
#                if status in ["available", "acquiring"]:
#                    self.LOCATION_DETERMINATION_METHOD.append("cellphone")
#
#        self.location_filter = []
#        self.task_separator = Gtk.SeparatorToolItem()

    def _location_updated(self, old_path, new_path):
        system_bus = self.where._system_bus
        location_object =  system_bus.get_object(self.where.GEOCLUE2_BUS_NAME, new_path)
        location_properties = dbus.Interface(location_object, self.where.PROPERTIES_INTERFACE_NAME)
        self.latitude = location_properties.Get(self.where.LOCATION_INTERFACE_NAME, "Latitude")
        self.longitude = location_properties.Get(self.where.LOCATION_INTERFACE_NAME, "Longitude")

    def activate(self, plugin_api):
        mi = Gtk.MenuItem()
        mi.set_label("Add Location")
        plugin_api.add_item_to_tag_menu(mi)
        mi.show_all()
#        browser = plugin_api.get_browser()
#        print (browser.tagpopup)
#        mi = Gtk.MenuItem()
#        mi.set_label("Poronga")
#        browser.tagpopup.append(mi)
#        print (browser.tagpopup)
#        browser.tagpopup.show_all()
#        pass
#        self.plugin_api = plugin_api
#
#        # toolbar button for the new Location view
#        # create the pixbuf with the icon and it's size.
#        # 24,24 is the TaskEditor's toolbar icon size
#        image_assign_location_path = os.path.join(self.plugin_path,
#                                                  "icons/hicolor/16x16/assign\
#                                                  -location.png")
#        pixbug_assign_location = GdkPixbuf.Pixbuf.new_from_file_at_size(
#            image_assign_location_path, 16, 16)
#
#        image_assign_location = Gtk.Image()
#        image_assign_location.set_from_pixbuf(pixbug_assign_location)
#        image_assign_location.show()
#
#        # the menu intem for the tag context
#        self.context_item = Gtk.ImageMenuItem("Assign a location to this tag")
#        self.context_item.set_image(image_assign_location)
#        # TODO: add a short cut to the menu
#
#        self.context_item.connect('activate',
#                                  self.on_contextmenu_tag_location, plugin_api)
#        plugin_api.add_menu_tagpopup(self.context_item)
#
#        # get the user settings from the config file
#        self.config = plugin_api.get_config()
#        if "geolocalized-tasks" in self.config.has_key:
#            if "proximity_factor" in self.config["geolocalized-tasks"]:
#                value = self.config["geolocalized-tasks"]["proximity_factor"]
#                self.PROXIMITY_FACTOR = value
#
#            if "location_determination_method" in\
#                    self.config["geolocalized-tasks"]:
#                self.LOCATION_DETERMINATION_METHOD =\
#                    self.config["geolocalized-tasks"]["location_determination\
#                                                                     _method"]
#
#        providers = self.geoclue.get_available_providers()
#        provider_name_list = []
#
#        for provider in providers:
#            provider_name_list.append(provider['name'].lower())
#
#        # verify the location determination method
#        for method in self.LOCATION_DETERMINATION_METHOD:
#            if method == "network":
#                if "hostip" in provider_name_list:
#                    for provider in providers:
#                        if provider['name'].lower() == "hostip":
#                            status = self.geoclue.provider_status(
#                                provider['object'])
#                            if status in ["error", "unavailable"]:
#                                if "network" in\
#                                        self.LOCATION_DETERMINATION_METHOD:
#                                    self.LOCATION_DETERMINATION_METHOD.remove(
#                                        "network")
#                                    break
#                else:
#                    self.LOCATION_DETERMINATION_METHOD.remove("network")
#            elif method == "gps":
#                if "gpsd" in provider_name_list or\
#                        "gypsy" in provider_name_list:
#                    for provider in providers:
#                        if provider['name'].lower() in ["gpsd", "gypsy"]:
#                            status = self.geoclue.provider_status(
#                                provider['object'])
#                            if status in ["error", "unavailable"]:
#                                if "gps" in self.LOCATION_DETERMINATION_METHOD:
#                                    self.LOCATION_DETERMINATION_METHOD.remove(
#                                        "gps")
#                                    break
#                else:
#                    self.LOCATION_DETERMINATION_METHOD.remove("gps")
#            elif method == "cellphone":
#                if "gsmloc" in provider_name_list:
#                    for provider in providers:
#                        if provider['name'].lower() == "gsmloc":
#                            status = self.geoclue.provider_status(
#                                provider['object'])
#                            if status in ["error", "unavailable"]:
#                                if "cellphone" in\
#                                        self.LOCATION_DETERMINATION_METHOD:
#                                    self.LOCATION_DETERMINATION_METHOD.remove(
#                                        "cellphone")
#                                    break
#                else:
#                    self.LOCATION_DETERMINATION_METHOD.remove("cellphone")
#
#        try:
#            if len(self.LOCATION_DETERMINATION_METHOD) == 1 and\
#                    "network" in self.LOCATION_DETERMINATION_METHOD:
#                self.geoclue.init()
#            elif len(self.LOCATION_DETERMINATION_METHOD) == 1 and\
#                    "cellphone" in self.LOCATION_DETERMINATION_METHOD:
#                self.geoclue.init(resource=(1 << 1))
#            elif len(self.LOCATION_DETERMINATION_METHOD) == 1 and\
#                    "gps" in self.LOCATION_DETERMINATION_METHOD:
#                self.geoclue.init(resource=(1 << 2))
#            else:
#                self.geoclue.init(resource=((1 << 10) - 1))
#        except Exception:
#            self.geoclue.init(resource=0)
#
#        self.location = self.geoclue.get_location_info()
#
#        # registers the filter callback method
#        plugin_api.register_filter_cb(self.task_location_filter)

    def deactivate(self, plugin_api):
        """
        Desactivates the plugin.
        """
        # everything should be removed, in case a task is currently opened
        self.where.client.Stop()
        try:
            plugin_api.remove_toolbar_item(self.btn_set_location)
            plugin_api.remove_item_from_tag_menu(mi)
        except:
                pass
#        try:
#            if self.context_item:
#                plugin_api.remove_menu_tagpopup(self.context_item)
#        except:
#            pass
#
#        try:
#            if self.config:
#                self.config["geolocalized-tasks"] = {
#                    "proximity_factor": self.PROXIMITY_FACTOR,
#                    "location_determination_method":
#                    self.LOCATION_DETERMINATION_METHOD,
#                }
#        except:
#            pass
#
#        # remove the filters
#        for tid in self.location_filter:
#            plugin_api.remove_task_from_filter(tid)
#
#        # unregister the filter callback
#        plugin_api.unregister_filter_cb(self.task_location_filter)
#
#        # remove the toolbar buttons
#        plugin_api.remove_task_toolbar_item(self.task_separator)
#        plugin_api.remove_task_toolbar_item(self.btn_set_location)

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

        self.btn_set_location = Gtk.ToolButton()
        self.btn_set_location.set_icon_widget(icon_geolocalization)
        self.btn_set_location.set_label("Set/View location")
        self.btn_set_location.connect('clicked', self.set_task_location, plugin_api)
        self.btn_set_location.show_all()

        plugin_api.add_toolbar_item(self.btn_set_location)

#        pass
#        image_geolocalization_path = os.path.join(self.plugin_path,
#                                                  "icons/hicolor/24x24/\
#                                                  geolocalization.png")
#        pixbuf_geolocalization = GdkPixbuf.Pixbuf.new_from_file_at_size(
#            image_geolocalization_path, 24, 24)
#
#        # create the image and associate the pixbuf
#        icon_geolocalization = Gtk.Image()
#        icon_geolocalization.set_from_pixbuf(pixbuf_geolocalization)
#        icon_geolocalization.show()
#
#        # toolbar button for the location_view
#        btn_location_view = Gtk.ToggleToolButton()
#        btn_location_view.set_icon_widget(icon_geolocalization)
#        btn_location_view.set_label("Location View")
#
#        self.task_separator = plugin_api.add_task_toolbar_item(
#            Gtk.SeparatorToolItem())
#
#        btn_set_location = Gtk.ToolButton()
#        btn_set_location.set_icon_widget(icon_geolocalization)
#        btn_set_location.set_label("Set/View location")
#        btn_set_location.connect('clicked', self.set_task_location, plugin_api)
#        self.btn_set_location = plugin_api.add_task_toolbar_item(
#            btn_set_location)

    def is_configurable(self):
        pass
#        return True

    def configure_dialog(self, manager_dialog):
        pass
#        self.on_geolocalized_preferences()

    def location_changed(self):
        pass
#        # TODO: This should refresh the task ang tag list
#        # update the location
#        self.location = self.geoclue.get_location_info()
#        # reset the filters
#        self.location_filter = []

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
    def on_geolocalized_preferences(self):
        pass
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

    def update_location_name(self, reverse, res, marker):
        place = reverse.resolve_finish(res)
        marker.set_text(place.get_name())
        print (marker)

    def on_im_here (self, widget, position):
        [latitude, longitude] = position

        marker = Champlain.Label()
        marker.set_text("...")
        marker.set_location(latitude, longitude)
        self.layer.add_marker(marker)
        marker.connect('button-press-event', self.on_marker, marker)
        self.locations.append(marker)

        geocodeLocation = Geocode.Location.new(latitude, longitude, Geocode.LOCATION_ACCURACY_STREET)
        reverse = Geocode.Reverse.new_for_location (geocodeLocation)
        reverse.resolve_async(None, self.update_location_name, marker)

    def on_delete (self, widget, data):
        self.layer.remove_marker(self.marker_to_be_deleted)
        self.locations.remove(self.marker_to_be_deleted)
        self.marker_to_be_deleted = None

    def check_clicked (self, widget, tag):
        if widget.get_active() is True:
            location_tag = [self.marker_to_be_deleted.get_text(), self.marker_to_be_deleted.get_latitude(), self.marker_to_be_deleted.get_longitude()]
            self.dict[tag] = [location_tag]
            self.plugin_api.get_selected().add_tag(tag)
        else:
            del self.dict[tag]
            self.plugin_api.get_selected().remove_tag(tag)

    #for edit
    def on_edit (self, widget, data):
        builder = self._get_builder_from_file("edit_task.ui")
        dialog1 = builder.get_object("dialog")
#        dialog1.set_transient_for(parent)

        entry1 = builder.get_object("entry")
        task_name = self.marker_to_be_deleted.get_text()
        entry1.set_text(task_name)

        self.show_tags = self.plugin_api.get_requester().get_all_tags()

        btn = builder.get_object("button_ok")
        btn.connect('clicked', self.ok_edit, entry1)

        btn = builder.get_object("button_cancel")
        btn.connect('clicked', self.cancel_edit, widget)

        scrolled_window = builder.get_object("scrolledwindow")
        grid = Gtk.Grid()
        scrolled_window.add(grid)

        tag_location_data_path = os.path.join('plugins/geolocalized_tasks', "tag_locations")
        self.dict = load_pickled_file(tag_location_data_path, None)
        print ('DEBUG LOAD PICLED |self.dict', self.dict)

        existent_tags = self.plugin_api.get_selected().get_tags_name()

        i = 0
        for tag in self.show_tags:
            if tag.startswith("@"):
                print ("TAG:", tag)
                check = Gtk.CheckButton(tag)
                if self.dict is not None and tag in self.dict:
                    list_tag = [self.marker_to_be_deleted.get_text(), self.marker_to_be_deleted.get_latitude(), self.marker_to_be_deleted.get_longitude()]
                    values = self.dict[tag]
                    if list_tag in values:
                        check.set_active(True)
                check.connect("toggled", self.check_clicked, tag)
                grid.attach(check, (i/(len(self.show_tags)/2)), (i%(len(self.show_tags)/2)), 1, 1)
                i += 1

        scrolled_window.show_all()
        dialog1.show_all()

    def on_context_menu(self, widget, event, data):
        if (event.button == 3):
            if (self.context is not None):
                self.context.popdown()
                self.context = None

            longitude = self.view.x_to_longitude (event.x)
            latitude = self.view.y_to_latitude (event.y)

            context = Gtk.Menu()

            mi = Gtk.MenuItem()
            mi.set_label("Add Location")
            mi.connect ("activate", self.on_im_here, [latitude, longitude])
            context.append(mi)

            mi = Gtk.MenuItem()
            mi.set_label("Edit Location")
            mi.connect("activate", self.on_edit, None)
            context.append(mi)

            if self.delete is False:
                mi.set_sensitive(False)

            mi = Gtk.MenuItem()
            mi.set_label("Remove Location")
            mi.connect("activate", self.on_delete, [latitude, longitude])
            context.append(mi)

            context.show_all()

            context.popup(None, None, None, None, event.button, event.time)
            self.context = context

            if self.delete is False:
                mi.set_sensitive(False)
            else:
                self.delete = False

        return True

    def on_marker(self, widget, event, marker):
        if marker is self.marker_last_location:
            return False

        self.marker_to_be_deleted = marker
        self.delete = True

        return False

    def set_task_location(self, widget, plugin_api, location=None):
        self.plugin_api = plugin_api
        self.task_id = plugin_api.get_selected().get_uuid()
        builder = self._get_builder_from_file("set_task_location.ui")
        dialog = builder.get_object("SetTaskLocation")
#        self.factory = Champlain.MapSourceFactory.dup_default()

        map = GtkChamplain.Embed()
        champlain_view = map.get_view()
        champlain_view.set_property("zoom-level", 10)
        champlain_view.set_reactive(True)

        #Factory
#        source = self.factory.create_cached_source(Champlain.MAP_SOURCE_OSM_MAPQUEST)
#        champlain_view.set_map_source(source)

        layer = Champlain.MarkerLayer()

        vbox_map = builder.get_object("vbox_map")
        vbox_map.pack_start(map, True, True, 1)
        champlain_view.connect('button-release-event', self.on_context_menu, vbox_map)

        self.view = champlain_view
        champlain_view.add_layer(layer)
        self.layer = layer

        btn = builder.get_object("btn_zoom_in")
        btn.connect('clicked', self.zoom_in, champlain_view)

        btn = builder.get_object("btn_zoom_out")
        btn.connect('clicked', self.zoom_out, champlain_view)

        last_location_data_path = os.path.join('plugins/geolocalized_tasks', "last_location")
        if self.latitude is None and self.longitude is None:
            [self.latitude, self.longitude] = load_pickled_file(last_location_data_path, [None, None])

        if self.latitude is not None and self.longitude is not None:
            red = Clutter.Color.new(0xff, 0x00, 0x00, 0xbb)
            champlain_view.center_on(self.latitude, self.longitude)
            store_pickled_file(last_location_data_path, [self.latitude, self.longitude])

            #Set current user location
            marker = Champlain.Label()
            marker.set_color(red)
            marker.set_text("I am here!")
            marker.set_location(self.latitude, self.longitude)
            layer.add_marker(marker)
            marker.set_use_markup(True)
            self.marker_last_location = marker

            vbox_map = builder.get_object("vbox_map")
            vbox_map.pack_start(map, True, True, 1)

            marker.connect('button-press-event', self.on_marker, marker)

            btn = builder.get_object("btn_zoom_in")
            btn.connect('clicked', self.zoom_in, champlain_view)

            btn = builder.get_object("btn_zoom_out")
            btn.connect('clicked', self.zoom_out, champlain_view)

        data_path = os.path.join('plugins/geolocalized_tasks', self.task_id)
        locations = load_pickled_file (data_path, [])
        for location in locations:
            [text, latitude, longitude] = location
            marker = Champlain.Label()
            marker.set_text(text)
            marker.set_location(latitude, longitude)
            self.layer.add_marker(marker)
            marker.connect('button-press-event', self.on_marker, marker)
            self.locations.append(marker)

            layer.add_marker(marker)

        layer.show_all()

        btn = builder.get_object("btn_cancel")
        btn.connect('clicked', self.close, dialog)

        btn = builder.get_object("btn_ok")
        btn.connect('clicked', self.close, dialog)

        dialog.show_all()

#        wTree = Gtk.glade.XML(self.glade_file, "SetTaskLocation")
#        dialog = wTree.get_widget("SetTaskLocation")
#        plugin_api.set_parent_window(dialog)
#
#        btn_zoom_in = wTree.get_widget("btn_zoom_in")
#        btn_zoom_out = wTree.get_widget("btn_zoom_out")
#
#        dialog_action_area_btn = wTree.get_widget("dialog_action_area_btn")
#        btn_ok = wTree.get_widget("btn_ok")
#        btn_cancel = wTree.get_widget("btn_cancel")
#        btn_close = wTree.get_widget("btn_close")
#
#        self.radiobutton1 = wTree.get_widget("radiobutton1")
#        self.radiobutton2 = wTree.get_widget("radiobutton2")
#        self.txt_new_tag = wTree.get_widget("txt_new_tag")
#        self.cmb_existing_tag = wTree.get_widget("cmb_existing_tag")
#
#        tabela = wTree.get_widget("tabela_set_task")
#
#        vbox_map = wTree.get_widget("vbox_map")
#        vbox_opt = wTree.get_widget("vbox_opt")
#
#        champlain_view = champlain.View()
#        champlain_view.set_property("scroll-mode",
#                                    champlain.SCROLL_MODE_KINETIC)
#        # champlain_view.set_property("zoom-on-double-click", False)
#
#        # create a list of the tags and their attributes
#        tag_list = []
#        for tag in plugin_api.get_tags():
#            tmp_tag = {}
#            for attr in tag.get_all_attributes():
#                if attr == "color":
#                    color = self.HTMLColorToRGB(tag.get_attribute(attr))
#                    tmp_tag[attr] = color
#                    tmp_tag['has_color'] = "yes"
#                elif attr == "location":
#                    tmp_tag[attr] = eval(tag.get_attribute(attr))
#                else:
#                    tmp_tag[attr] = tag.get_attribute(attr)
#            tag_list.append(tmp_tag)
#
#        # checks if there is one tag with a location
#        task_has_location = False
#        for tag in tag_list:
#            for key, item in list(tag.items()):
#                if key == "location":
#                    task_has_location = True
#                    break
#
#        # set the markers
#        layer = MarkerLayer()
#
#        self.marker_list = []
#        if task_has_location:
#            for tag in tag_list:
#                for key, item in list(tag.items()):
#                    if key == "location":
#                        color = None
#                        try:
#                            if tag['has_color'] == "yes":
#                                color = tag['color']
#                        except:
#                            # PROBLEM: the tag doesn't have color
#                            # Possibility, use a color from another tag
#                            pass
#
#                        self.marker_list.append(layer.add_marker(
#                            plugin_api.get_task_title(), tag['location'][0],
#                            tag['location'][1], color))
#        else:
#            try:
#                if self.location['longitude'] and self.location['latitude']:
#                    self.marker_list.append(layer.add_marker(
#                        plugin_api.get_task_title(),
#                        self.location['latitude'],
#                        self.location['longitude']))
#            except:
#                self.marker_list.append(layer.add_marker(
#                    plugin_api.get_task_title(), None, None))
#
#        champlain_view.add_layer(layer)
#
#        embed = GtkClutter.Embed()
#        embed.set_size_request(400, 300)
#
#        if not task_has_location:
#            # method that will change the marker's position
#            champlain_view.set_reactive(True)
#            champlain_view.connect("button-release-event",
#                                   self.champlain_change_marker,
#                                   champlain_view)
#
#        layer.show_all()
#
#        if task_has_location:
#            champlain_view.set_property("zoom-level", 9)
#        elif self.location:
#            champlain_view.set_property("zoom-level", 5)
#        else:
#            champlain_view.set_property("zoom-level", 1)
#
#        vbox_map.add(embed)
#
#        embed.realize()
#        stage = embed.get_stage()
#        champlain_view.set_size(400, 300)
#        stage.add(champlain_view)
#
#        # connect the toolbar buttons for zoom
#        btn_zoom_in.connect("clicked", self.zoom_in, champlain_view)
#        btn_zoom_out.connect("clicked", self.zoom_out, champlain_view)
#
#        if task_has_location:
#            dialog_action_area_btn.remove(btn_ok)
#            dialog_action_area_btn.remove(btn_cancel)
#            dialog.connect("response", self.task_location_close)
#        else:
#            dialog_action_area_btn.remove(btn_close)
#            # show a close button or the ok/cancel
#            dialog.connect("response", self.set_task_location_close,
#                           plugin_api)
#
#        # if there is no location set, we want to set it
#        if not task_has_location:
#            self.location_defined = False
#            if len(plugin_api.get_tags()) > 0:
#                liststore = Gtk.ListStore(str)
#                self.cmb_existing_tag.set_model(liststore)
#                for tag in plugin_api.get_tags():
#                    liststore.append([tag.get_attribute("name")])
#                self.cmb_existing_tag.set_text_column(0)
#                self.cmb_existing_tag.set_active(0)
#            else:
#                # remove radiobutton2 and the comboboxentry
#                tabela.remove(self.radiobutton1)
#                tabela.remove(self.radiobutton2)
#                tabela.remove(self.cmb_existing_tag)
#                label = Gtk.Label()
#                label.set_text("Associate with new tag: ")
#                tabela.attach(label, 0, 1, 0, 1)
#                label.show()
#        else:
#            self.location_defined = True
#            vbox_opt.remove(tabela)
#            dialog.set_title("View the task's location")
#
#        dialog.show_all()
#
#        if task_has_location:
#            champlain_view.center_on(
#                self.marker_list[0].get_property('latitude'),
#                self.marker_list[0].get_property('longitude'))
#        else:
#            try:
#                if self.location['longitude'] and self.location['latitude']:
#                    champlain_view.center_on(self.location['latitude'],
#                                             self.location['longitude'])
#            except:
#                pass

    def task_location_close(self, dialog, response=None):
        pass
#        dialog.destroy()

    def set_task_location_close(self, dialog, response=None, plugin_api=None):
        pass
#        if response == Gtk.ResponseType.OK:
#            # ok
#            # tries to get the radiobuttons value, witch may not exist
#            if not self.location_defined:
#                if self.radiobutton1.get_active():
#                    # radiobutton1
#                    if self.txt_new_tag.get_text().strip() != "":
#                        marker_position = (
#                            self.marker_list[0].get_property('latitude'),
#                            self.marker_list[0].get_property('longitude'))
#
#                        # because users sometimes make mistakes,
#                        # I'll check if the tag exists
#                        tmp_tag = ""
#                        tag_name = self.txt_new_tag.get_text().replace("@",
#                                                                       "")
#                        tag_name = "@" + tag_name
#                        for tag in plugin_api.get_tags():
#                            if tag.get_attribute("name") == tag_name:
#                                tmp_tag = tag_name
#                        if tmp_tag:
#                            plugin_api.add_tag_attribute(tag_name,
#                                                         "location",
#                                                         marker_position)
#                        else:
#                            plugin_api.insert_tag(tag_name[1:])
#                            plugin_api.add_tag_attribute(tag_name,
#                                                         "location",
#                                                         marker_position)
#                        dialog.destroy()
#                    else:
#                        # does nothing, no tag set.
#                        pass
#                else:
#                    # radiobutton2
#                    marker_position = (
#                        self.marker_list[0].get_property('latitude'),
#                        self.marker_list[0].get_property('longitude'))
#                    index = self.cmb_existing_tag.get_active()
#                    model = self.cmb_existing_tag.get_model()
#                    plugin_api.add_tag_attribute(model[index][0],
#                                                 "location", marker_position)
#                    dialog.destroy()
#        else:
#            # cancel
#            dialog.destroy()

    def champlain_change_marker(self, widget, event, view):
        pass
#        if event.button != 1 or event.click_count > 1:
#            return False
#
#        (latitude, longitude) = view.get_coords_at(int(event.x), int(event.y))
#        self.marker_list[0].set_position(latitude, longitude)

    #=== SET TASK LOCATION ====================================================

    #=== TAG VIEW CONTEXT MENU ================================================
    def on_contextmenu_tag_location(self, widget, plugin_api):
        pass
#        wTree = Gtk.glade.XML(self.glade_file, "TagLocation")
#        dialog = wTree.get_widget("TagLocation")
#        plugin_api.set_parent_window(dialog)
#
#        btn_zoom_in = wTree.get_widget("btn_zoom_in")
#        btn_zoom_out = wTree.get_widget("btn_zoom_out")
#        vbox_map = wTree.get_widget("vbox_map")
#
#        tag = plugin_api.get_tagpopup_tag()
#        dialog.set_title(tag.get_attribute("name") + "'s Location")
#
#        # get the tag's location
#        try:
#            tag_location = eval(tag.get_attribute("location"))
#        except:
#            tag_location = None
#
#        # get the tag's color
#        try:
#            tag_color = self.HTMLColorToRGB(tag.get_attribute("color"))
#        except:
#            tag_color = None
#
#        champlain_view = champlain.View()
#        champlain_view.set_property("scroll-mode",
#                                    champlain.SCROLL_MODE_KINETIC)
#
#        layer = MarkerLayer()
#
#        marker_tag = None
#        if tag_location:
#            marker_tag = layer.add_marker(tag.get_attribute("name"),
#                                          tag_location[0], tag_location[1],
#                                          tag_color)
#        else:
#            try:
#                if self.location['longitude'] and self.location['latitude']:
#                    marker_tag = layer.add_marker(tag.get_attribute("name"),
#                                                  self.location['latitude'],
#                                                  self.location['longitude'],
#                                                  tag_color)
#            except:
#                marker_tag = layer.add_marker(tag.get_attribute("name"),
#                                              None, None)
#
#        champlain_view.add_layer(layer)
#
#        embed = GtkClutter.Embed()
#        embed.set_size_request(400, 300)
#
#        champlain_view.set_reactive(True)
#        champlain_view.connect("button-release-event",
#                               self.champlain__tag_change_marker,
#                               champlain_view, marker_tag)
#
#        layer.show_all()
#
#        if tag_location:
#            champlain_view.set_property("zoom-level", 9)
#        elif self.location:
#            champlain_view.set_property("zoom-level", 5)
#        else:
#            champlain_view.set_property("zoom-level", 1)
#
#        vbox_map.add(embed)
#
#        embed.realize()
#        stage = embed.get_stage()
#        champlain_view.set_size(400, 300)
#        stage.add(champlain_view)
#
#        # connect the toolbar buttons for zoom
#        btn_zoom_in.connect("clicked", self.zoom_in, champlain_view)
#        btn_zoom_out.connect("clicked", self.zoom_out, champlain_view)
#        dialog.connect("response", self.tag_location_close, tag, marker_tag)
#
#        dialog.show_all()
#
#        if tag_location:
#            champlain_view.center_on(
#                marker_tag.get_property('latitude'),
#                marker_tag.get_property('longitude'))
#        else:
#            try:
#                if self.location['longitude'] and self.location['latitude']:
#                    champlain_view.center_on(self.location['latitude'],
#                                             self.location['longitude'])
#            except:
#                pass

    def champlain__tag_change_marker(self, widget, event, view, marker):
        pass
#        if event.button != 1 or event.click_count > 1:
#            return False
#
#        (latitude, longitude) = view.get_coords_at(int(event.x), int(event.y))
#        marker.set_position(latitude, longitude)

    def tag_location_close(self, dialog, response=None, tag=None, marker=None):
        pass
#        if response == Gtk.ResponseType.OK:
#            tag_location = str((marker.get_property('latitude'),
#                                marker.get_property('longitude')))
#            tag.set_attribute("location", tag_location)
#            dialog.destroy()
#        else:
#            dialog.destroy()

    #=== TAG VIEW CONTEXT MENU ================================================
    def zoom_in(self, widget, view):
        view.zoom_in()

    def zoom_out(self, widget, view):
        view.zoom_out()

    def close(self, widget, data):
        data_path = os.path.join('plugins/geolocalized_tasks', self.task_id)
        locations = []
        for location in self.locations:
            locations.append([location.get_text(), location.get_latitude(), location.get_longitude()])
        store_pickled_file (data_path, locations)

        widget.get_parent_window().destroy()
        self.clean_up()

    def ok_edit (self, widget, entry):
        tag_location_data_path = os.path.join('plugins/geolocalized_tasks', "tag_locations")
        store_pickled_file(tag_location_data_path, self.dict)
        self.marker_to_be_deleted.set_text(entry.get_text())
        widget.get_parent_window().destroy()

    def cancel_edit (self, widget, data):
        widget.get_parent_window().destroy()

    def clean_up(self):
        self.locations = []
        self.task_id = ""

    # http://code.activestate.com/recipes/266466/
    # original by Paul Winkler
    def HTMLColorToRGB(self, colorstring):
        pass
#        """ convert #RRGGBB to a clutter color var """
#        colorstring = colorstring.strip()
#        if colorstring[0] == '#':
#            colorstring = colorstring[1:]
#        if len(colorstring) != 6:
#            raise ValueError(
#                "input #%s is not in #RRGGBB format" % colorstring)
#        r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:]
#        r, g, b = [int(n, 16) for n in (r, g, b)]
#        return Clutter.Color(r, g, b)
