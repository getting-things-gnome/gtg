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

import gtk, pygtk
import os, sys
from time import sleep

from xdg.BaseDirectory import *
from configobj import ConfigObj

import Geoclue

import clutter, cluttergtk
import champlain, champlaingtk 

# IMPORTANT This add's the plugin's path to python sys path
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from marker import MarkerLayer


from GTG.core.plugins.engine import PluginEngine

class geolocalizedTasks:
    PLUGIN_NAME = 'Geolocalized Tasks'
    PLUGIN_AUTHORS = 'Paulo Cabido <paulo.cabido@gmail.com>'
    PLUGIN_VERSION = '0.1'
    PLUGIN_DESCRIPTION = 'This plugin adds geolocalization to GTG!.'
    PLUGIN_ENABLED = True
    
    def __init__(self):
        self.geoclue = Geoclue.DiscoverLocation()
        self.geoclue.init()
        self.location = self.geoclue.get_location_info()
        
        self.plugin_path = os.path.dirname(os.path.abspath(__file__))
        self.glade_file = os.path.join(self.plugin_path, "geolocalized.glade")
        
        # the preference menu for the plugin
        self.menu_item = gtk.MenuItem("Geolocalized-tasks Preferences")
        
        # toolbar button for the new Location view
        # create the pixbuf with the icon and it's size.
        # 24,24 is the TaskEditor's toolbar icon size
        image_geolocalization_path = os.path.join(self.plugin_path, "icons/hicolor/24x24/geolocalization.png")
        pixbuf_geolocalization = gtk.gdk.pixbuf_new_from_file_at_size(image_geolocalization_path, 24, 24)
        
        image_assign_location_path = os.path.join(self.plugin_path, "icons/hicolor/16x16/assign-location.png")
        pixbug_assign_location = gtk.gdk.pixbuf_new_from_file_at_size(image_assign_location_path, 16, 16)
        
        # create the image and associate the pixbuf
        self.icon_geolocalization = gtk.Image()
        self.icon_geolocalization.set_from_pixbuf(pixbuf_geolocalization)
        self.icon_geolocalization.show()
        
        image_assign_location = gtk.Image()
        image_assign_location.set_from_pixbuf(pixbug_assign_location)
        image_assign_location.show()
        
        # the menu intem for the tag context
        self.context_item = gtk.ImageMenuItem("Assign a location to this tag")
        self.context_item.set_image(image_assign_location)
        # TODO: add a short cut to the menu
        
        # toolbar button for the location_view
        self.btn_location_view = gtk.ToggleToolButton()
        self.btn_location_view.set_icon_widget(self.icon_geolocalization)
        self.btn_location_view.set_label("Location View")
        
        self.PROXIMITY_FACTOR = 5  # 5 km
        self.LOCATION_ACCURACY = 3 # Locality
        self.LOCATION_DETERMINATION_METHOD = []
        for provider in self.geoclue.get_available_providers():
            if provider['position'] and (provider['provider'] != "Example Provider" and provider['provider'] != "Plazes"):
                self.LOCATION_DETERMINATION_METHOD.append(provider["provider"])
            
        
    
    def activate(self, plugin_api):
        self.menu_item.connect('activate', self.on_geolocalized_preferences, plugin_api)
        plugin_api.AddMenuItem(self.menu_item)
        
        self.context_item.connect('activate', self.on_contextmenu_tag_location, plugin_api)
        plugin_api.add_menu_tagpopup(self.context_item)
        
        # get the user settings from the config file
        self.config = plugin_api.get_config()
        if self.config.has_key("geolocalized-tasks"):
            if self.config["geolocalized-tasks"].has_key("proximity_factor"):
                self.PROXIMITY_FACTOR = self.config["geolocalized-tasks"]["proximity_factor"]
            
            if self.config["geolocalized-tasks"].has_key("accuracy"):
                self.LOCATION_ACCURACY = self.config["geolocalized-tasks"]["accuracy"]
        
            if self.config["geolocalized-tasks"].has_key("location_determination_method"):
                self.LOCATION_DETERMINATION_METHOD = self.config["geolocalized-tasks"]["location_determination_method"]
                
        # filter the tasks location for the workview
        self.filter_workview_by_location(plugin_api)
    
    def deactivate(self, plugin_api):
        plugin_api.RemoveMenuItem(self.menu_item)
        plugin_api.remove_menu_tagpopup(self.context_item)
        #plugin_api.RemoveToolbarItem(None, self.seperator_location_view)
        
        self.config["geolocalized-tasks"] = {}
        self.config["geolocalized-tasks"]["proximity_factor"] = self.PROXIMITY_FACTOR
        self.config["geolocalized-tasks"]["accuracy"] = self.LOCATION_ACCURACY
        self.config["geolocalized-tasks"]["location_determination_method"] = self.LOCATION_DETERMINATION_METHOD
    
    def onTaskOpened(self, plugin_api):
        plugin_api.AddTaskToolbarItem(gtk.SeparatorToolItem())
        
        btn_set_location = gtk.ToolButton()
        btn_set_location.set_icon_widget(self.icon_geolocalization)
        btn_set_location.set_label("Set/View location")
        btn_set_location.connect('clicked', self.set_task_location, plugin_api)
        plugin_api.AddTaskToolbarItem(btn_set_location)
    
    def filter_workview_by_location(self, plugin_api):
        # TODO: if the location has a delay in being calculated it may not exist at
        # this point
        if self.location.has_key("latitude") and self.location.has_key("longitude"):
            tasks = plugin_api.get_all_tasks()
                
            tasks_with_location = []
            tasks_without_location = []
            
            for tid in tasks:
                task = plugin_api.get_task(tid)
                tags = task.get_tags()
                for tag in tags:
                    if "location" in tag.get_all_attributes():
                        tasks_with_location.append(task)
                    else:
                        tasks_without_location.append(task)
                
            for task in tasks_with_location:
                tags = task.get_tags()
                for tag in tags:
                    if tag.get_attribute("location"):
                        position = eval(tag.get_attribute("location"))
                        if not self.geoclue.compare_position(position[0], position[1], float(self.PROXIMITY_FACTOR)):
                            plugin_api.add_task_to_workview_filter(task.get_id())
                                
                                
    #=== GEOLOCALIZED PREFERENCES===================================================    
    def on_geolocalized_preferences(self, widget, plugin_api):
        wTree = gtk.glade.XML(self.glade_file, "Preferences")
        dialog = wTree.get_widget("Preferences")
        dialog.connect("response", self.preferences_close)
        plugin_api.set_parent_window(dialog)
        
        cmb_accuracy = wTree.get_widget("cmb_accuracy")
        for i in range(len(cmb_accuracy.get_model())):
            if str(self.accuracy_to_value(cmb_accuracy.get_model()[i][0])) == str(self.LOCATION_ACCURACY):
                cmb_accuracy.set_active(i)
        cmb_accuracy.connect("changed", self.cmb_accuracy_changed)
        self.tmp_location_accuracy = self.LOCATION_ACCURACY
        
        spin_proximityfactor = wTree.get_widget("spin_proximityfactor")
        spin_proximityfactor.set_value(float(self.PROXIMITY_FACTOR))
        spin_proximityfactor.connect("changed", self.spin_proximityfactor_changed)
        self.tmp_proximityfactor = float(self.PROXIMITY_FACTOR)
        
        dialog.show_all()
        
    # converts the accuracy to a value
    def accuracy_to_value(self, accuracy):
        if not accuracy:
            return 0
        elif accuracy.lower() == "Country".lower():
            return 1
        elif accuracy.lower() == "Region".lower():
            return 2
        elif accuracy.lower() == "Locality".lower():
            return 3
        elif accuracy.lower() == "Postalcode".lower():
            return 4
        elif accuracy.lower() == "Street".lower():
            return 5
        elif accuracy.lower() == "Detailed".lower():
            return 6
        return 0 
    
    # converts the value of a accuracy to the accuracy
    def value_to_accuracy(self, value):
        if not value:
            return None
        elif value == 1:
            return "Country"
        elif value == 2:
            return "Region"
        elif value == 3:
            return "Locality"
        elif value == 4:
            return "Postalcode"
        elif value == 5:
            return "Street"
        elif value == 6:
            return "Detailed"
        return None
        
    def cmb_accuracy_changed(self, comboboxentry):
        index = comboboxentry.get_active()
        model = comboboxentry.get_model()
        self.tmp_location_accuracy = self.accuracy_to_value(model[index][0])
        
    def spin_proximityfactor_changed(self, spinbutton):
        self.tmp_proximityfactor = spinbutton.get_value()
        
    def preferences_close(self, dialog, response=None):
        if response == gtk.RESPONSE_OK:
            self.LOCATION_ACCURACY = self.tmp_location_accuracy 
            self.PROXIMITY_FACTOR = float(self.tmp_proximityfactor) 
            dialog.destroy()
        else:
            dialog.destroy()
            
    #=== GEOLOCALIZED PREFERENCES===================================================
    
    #=== SET TASK LOCATION =========================================================
    def set_task_location(self, widget, plugin_api, location=None):
        location = self.geoclue.get_location_info()
        self.plugin_api = plugin_api
        
        wTree = gtk.glade.XML(self.glade_file, "SetTaskLocation")
        dialog = wTree.get_widget("SetTaskLocation")
        self.plugin_api.set_parent_window(dialog)
        
        btn_zoom_in = wTree.get_widget("btn_zoom_in")
        btn_zoom_out = wTree.get_widget("btn_zoom_out")
        
        self.radiobutton1 = wTree.get_widget("radiobutton1")
        self.radiobutton2 = wTree.get_widget("radiobutton2")
        self.txt_new_tag = wTree.get_widget("txt_new_tag")
        self.cmb_existing_tag = wTree.get_widget("cmb_existing_tag")
        
        tabela = wTree.get_widget("tabela_set_task")
        vbox_map = wTree.get_widget("vbox_map")
        vbox_opt = wTree.get_widget("vbox_opt")
        
        champlain_view = champlain.View()
        champlain_view.set_property("scroll-mode", champlain.SCROLL_MODE_KINETIC)
        #champlain_view.set_property("zoom-on-double-click", False)
        
        # create a list of the tags and their attributes
        tag_list = []
        for tag in plugin_api.get_tags():
            tmp_tag = {}
            for attr in tag.get_all_attributes():
                if attr == "color":
                    tmp_tag[attr] = self.HTMLColorToRGB(tag.get_attribute(attr))
                    tmp_tag['has_color'] = "yes"
                elif attr == "location":
                    tmp_tag[attr] = eval(tag.get_attribute(attr))
                else:
                    tmp_tag[attr] = tag.get_attribute(attr)
            tag_list.append(tmp_tag)                 
           
        # checks if there is one tag with a location     
        task_has_location = False
        for tag in tag_list:
            for key, item in tag.items():
                if key == "location":
                    task_has_location = True
                    break
        
        # set the markers
        layer = MarkerLayer()
        
        self.marker_list = []
        if task_has_location:
            for tag in tag_list:
                for key, item in tag.items():
                    if key == "location":
                        color = None
                        try:
                            if tag['has_color'] == "yes":
                                color = tag['color']
                        except:
                            # PROBLEM: the tag doesn't have color
                            # Possibility, use a color from another tag
                            pass
                        
                        self.marker_list.append(layer.add_marker(plugin_api.get_task_title(), tag['location'][0], tag['location'][1], color))
        else:
            try:
                if location['longitude'] and location['latitude']:
                    self.marker_list.append(layer.add_marker(plugin_api.get_task_title(), location['latitude'], location['longitude']))
            except:
                self.marker_list.append(layer.add_marker(plugin_api.get_task_title(), None, None))
        
        champlain_view.add_layer(layer)
        
        embed = cluttergtk.Embed()
        embed.set_size_request(400, 300)
        
        if not task_has_location:
            # method that will change the marker's position
            champlain_view.set_reactive(True)
            champlain_view.connect("button-release-event", self.champlain_change_marker, champlain_view)
        
        layer.show_all()
        
        if task_has_location:
            champlain_view.set_property("zoom-level", 9)
        elif location:
            champlain_view.set_property("zoom-level", 5)
        else:
            champlain_view.set_property("zoom-level", 1)
            
        vbox_map.add(embed)
        
        embed.realize()
        stage = embed.get_stage()
        champlain_view.set_size(400, 300)
        stage.add(champlain_view)
        
        # connect the toolbar buttons for zoom
        btn_zoom_in.connect("clicked", self.zoom_in, champlain_view)
        btn_zoom_out.connect("clicked", self.zoom_out, champlain_view)
        dialog.connect("response", self.set_task_location_close)
        
        #if there is no location set, we want to set it
        if not task_has_location:
            self.location_defined = False
            if len(plugin_api.get_tags()) > 0:
                liststore = gtk.ListStore(str)
                self.cmb_existing_tag.set_model(liststore)
                for tag in plugin_api.get_tags():    
                    liststore.append([tag.get_attribute("name")])
                self.cmb_existing_tag.set_text_column(0)
                self.cmb_existing_tag.set_active(0)             
            else:
                #remove radiobutton2 and the comboboxentry
                tabela.remove(self.radiobutton1)
                tabela.remove(self.radiobutton2)
                tabela.remove(self.cmb_existing_tag)
                label = gtk.Label()
                label.set_text("Associate with new tag: ")
                tabela.attach(label, 0, 1, 0, 1)
                label.show()
        else:
            self.location_defined = True
            vbox_opt.remove(tabela)
            dialog.set_title("View the task's location")
        
        dialog.show_all()
        
        if task_has_location:
            marker_position = (self.marker_list[0].get_property('latitude'), self.marker_list[0].get_property('longitude'))
            champlain_view.center_on(marker_position[0], marker_position[1])
        else:
            try:
                if location['longitude'] and location['latitude']:
                    champlain_view.center_on(location['latitude'], location['longitude'])
            except:
                pass
    
    def set_task_location_close(self, dialog, response=None):
        if response == gtk.RESPONSE_OK:
            # ok
            # tries to get the radiobuttons value, witch may not exist
            if not self.location_defined:
                if self.radiobutton1.get_active():
                    # radiobutton1
                    if self.txt_new_tag.get_text().strip() != "":
                        marker_position = (self.marker_list[0].get_property('latitude'), self.marker_list[0].get_property('longitude'))
                       
                        # because users sometimes make mistakes, I'll check if the tag exists
                        tmp_tag = ""
                        for tag in self.plugin_api.get_tags():
                            t = "@" + self.txt_new_tag.get_text().replace("@", "")
                            if tag.get_attribute("name") == t:
                                tmp_tag = t
                        if tmp_tag:
                            self.plugin_api.add_tag_attribute(self.txt_new_tag.get_text().replace("@", ""), 
                                                              "location",  
                                                              marker_position)
                        else:
                            self.plugin_api.add_tag(self.txt_new_tag.get_text().replace("@", ""))
                            self.plugin_api.add_tag_attribute("@" + self.txt_new_tag.get_text().replace("@", ""), 
                                                              "location",  
                                                              marker_position)
                        dialog.destroy()
                    else:
                        self.errorDialog(dialog, "Error: No tag defined", "The tag has to be defined so that the location can be associated with it.")
                else:
                    # radiobutton2
                    marker_position = (self.marker_list[0].get_property('latitude'), self.marker_list[0].get_property('longitude'))
                    index = self.cmb_existing_tag.get_active()
                    model = self.cmb_existing_tag.get_model()
                    self.plugin_api.add_tag_attribute(model[index][0], "location", marker_position)
            dialog.destroy()
        else:
            # cancel
            dialog.destroy()
    
    def champlain_change_marker(self, widget, event, view):
        if event.button != 1 or event.click_count > 1:
            return False
        
        (latitude, longitude) = view.get_coords_at(int(event.x), int(event.y))
        self.marker_list[0].set_position(latitude, longitude)
    
    #=== SET TASK LOCATION =========================================================
        
    #=== TAG VIEW CONTEXT MENU =====================================================
    def on_contextmenu_tag_location(self, widget, plugin_api):
        location = self.geoclue.get_location_info()
        self.plugin_api_context = plugin_api
        
        wTree = gtk.glade.XML(self.glade_file, "TagLocation")
        dialog = wTree.get_widget("TagLocation")
        self.plugin_api_context.set_parent_window(dialog)
        
        btn_zoom_in = wTree.get_widget("btn_zoom_in")
        btn_zoom_out = wTree.get_widget("btn_zoom_out")
        vbox_map = wTree.get_widget("vbox_map")
        
        tag = self.plugin_api_context.get_tagpopup_tag()
        dialog.set_title(tag.get_attribute("name") + "'s Location")
        
        # get the tag's location
        try:
            tag_location = eval(tag.get_attribute("location"))
        except:
            tag_location = None
            
        # get the tag's color
        try:
            tag_color = self.HTMLColorToRGB(tag.get_attribute("color"))
        except:
            tag_color = None
        
        champlain_view = champlain.View()
        champlain_view.set_property("scroll-mode", champlain.SCROLL_MODE_KINETIC)
        
        layer = MarkerLayer()
        
        marker_tag = None
        if tag_location:
            marker_tag = layer.add_marker(tag.get_attribute("name"), tag_location[0], tag_location[1], tag_color)
        else:
            try:
                if location['longitude'] and location['latitude']:
                    marker_tag = layer.add_marker(tag.get_attribute("name"), location['latitude'], location['longitude'], tag_color)
            except:
                marker_tag = layer.add_marker(tag.get_attribute("name"), None, None)
        
        champlain_view.add_layer(layer)
        
        embed = cluttergtk.Embed()
        embed.set_size_request(400, 300)
        
        champlain_view.set_reactive(True)
        champlain_view.connect("button-release-event", self.champlain__tag_change_marker, champlain_view, marker_tag)
        
        layer.show_all()
        
        if tag_location:
            champlain_view.set_property("zoom-level", 9)
        elif location:
            champlain_view.set_property("zoom-level", 5)
        else:
            champlain_view.set_property("zoom-level", 1)      
        
        vbox_map.add(embed)
        
        embed.realize()
        stage = embed.get_stage()
        champlain_view.set_size(400, 300)
        stage.add(champlain_view)
        
        # connect the toolbar buttons for zoom
        btn_zoom_in.connect("clicked", self.zoom_in, champlain_view)
        btn_zoom_out.connect("clicked", self.zoom_out, champlain_view)
        dialog.connect("response", self.tag_location_close, tag, marker_tag)
        
        dialog.show_all()
        
        if tag_location:
            marker_position = (marker_tag.get_property('latitude'), marker_tag.get_property('longitude'))
            champlain_view.center_on(marker_position[0], marker_position[1])
        else:
            try:
                if location['longitude'] and location['latitude']:
                    champlain_view.center_on(location['latitude'], location['longitude'])
            except:
                pass
    
    def champlain__tag_change_marker(self, widget, event, view, marker):
        if event.button != 1 or event.click_count > 1:
            return False
        
        (latitude, longitude) = view.get_coords_at(int(event.x), int(event.y))
        marker.set_position(latitude, longitude)
    
    def tag_location_close(self, dialog, response=None, tag=None, marker=None):
        if response == gtk.RESPONSE_OK:
            tag_location = str((marker.get_property('latitude'), marker.get_property('longitude')))
            tag.set_attribute("location", tag_location)
            dialog.destroy()
        else:
            dialog.destroy()
    
    #=== TAG VIEW CONTEXT MENU =====================================================
    
    def zoom_in(self, widget, view):
        view.zoom_in()

    def zoom_out(self, widget, view):
        view.zoom_out()

    # http://code.activestate.com/recipes/266466/
    # original by Paul Winkler
    def HTMLColorToRGB(self, colorstring):
        """ convert #RRGGBB to a clutter color var """
        colorstring = colorstring.strip()
        if colorstring[0] == '#': colorstring = colorstring[1:]
        if len(colorstring) != 6:
            raise ValueError, "input #%s is not in #RRGGBB format" % colorstring
        r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:]
        r, g, b = [int(n, 16) for n in (r, g, b)]
        return clutter.Color(r, g, b)
    
    # error dialog
    def errorDialog(self, parent, header, msg):
         """
         Show an error message.
         """

         dialog = gtk.MessageDialog(parent,
                               flags=gtk.DIALOG_MODAL,
                               type=gtk.MESSAGE_ERROR,
                               buttons=gtk.BUTTONS_CLOSE)
         dialog.set_title("")
         dialog.set_markup("<big><b>%s</b></big>\n\n%s" % (header, msg))
         dialog.realize()
         dialog.run()
         dialog.destroy()