import gtk, pygtk
import os

import Geoclue

import clutter
import cluttergtk
import gobject
import champlain
import champlaingtk


from GTG.core.plugins.engine import PluginEngine

class geolocalizedTasks:
    PLUGIN_NAME = 'Geolocalized Tasks'
    PLUGIN_AUTHORS = 'Paulo Cabido <paulo.cabido@gmail.com>'
    PLUGIN_VERSION = '0.1'
    PLUGIN_DESCRIPTION = 'This plugin adds geolocalization to GTG!.'
    PLUGIN_ENABLED = True
    
    def __init__(self):
        self.plugin_path = os.path.dirname(os.path.abspath(__file__))
        self.glade_file = os.path.join(self.plugin_path, "geolocalized.glade")
        
        # the preference menu for the plugin
        self.menu_item = gtk.MenuItem("Geolocalized Task Preferences")
        self.menu_item.connect('activate', self.on_geolocalized_preferences)
        
        self.geoclue = Geoclue.DiscoverLocation()
        self.geoclue.init()
    
    def activate(self, plugin_api):
        plugin_api.AddMenuItem(self.menu_item)
    
    def deactivate(self, plugin_api):
        plugin_api.RemoveMenuItem(self.menu_item)
    
    def onTaskOpened(self, plugin_api):
        plugin_api.AddTaskToolbarItem(gtk.SeparatorToolItem())
        
        # create the pixbuf with the icon and it's size.
        # 24,24 is the TaskEditor's toolbar icon size
        path = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(path, "map.png")
        pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(icon_path , 24, 24)
        
        # create the image and associate the pixbuf
        icon_map = gtk.Image()
        icon_map.set_from_pixbuf(pixbuf)
        icon_map.show()
        
        # define the icon for the button
        btn_set_location = gtk.ToolButton()
        btn_set_location.set_icon_widget(icon_map)
        btn_set_location.set_label("Set location")
        btn_set_location.connect('clicked', self.set_task_location, plugin_api)
        plugin_api.AddTaskToolbarItem(btn_set_location)
        
        #TODO: image for the button
        # only add this button if the task has a position defined
        tags = plugin_api.get_tags()
        view_location = False
        for tag in tags:
            for attr in tag.get_all_attributes():
                if attr == "position":
                    view_location = True
                    break
        
        if view_location:
            btn_view_location = gtk.ToolButton(gtk.STOCK_ZOOM_100) #STOCK_ZOOM_FIT
            btn_view_location.set_label("View location")
            btn_view_location.connect('clicked', self.view_task_location, plugin_api.get_task_title(), plugin_api.get_tags())
            plugin_api.AddTaskToolbarItem(btn_view_location)
            
    def on_geolocalized_preferences(self, widget):
        pass
    
    def champlain_change_marker(self, widget, event, view, marker):
        if event.button != 1 or event.click_count > 1:
            return False
        
        (latitude, longitude) = view.get_coords_at(int(event.x), int(event.y))
        marker.set_position(latitude, longitude)
    
    def set_task_location(self, widget, plugin_api, location=None):
        location = self.geoclue.get_location_info()
        
        wTree = gtk.glade.XML(self.glade_file, "SetTaskLocation")
        dialog = wTree.get_widget("SetTaskLocation")
        
        vbox = wTree.get_widget("vbox1")
        
        champlain_view = champlain.View()
        champlain_view.set_property("scroll-mode", champlain.SCROLL_MODE_KINETIC)
        # because I can't get the number of clicks
        # FIXED! :D
        #champlain_view.set_property("zoom-on-double-click", False)
        
         # get one of the task's color
        tag_attr_color = None
        for tag in plugin_api.get_tags():
            for attr in tag.get_all_attributes():
                if attr == "color":
                    tag_attr_color = self.HTMLColorToRGB(tag.get_attribute(attr))
                    break   
        
        layer = MarkerLayer()
        try:
            if location['latitude'] and location['longitude']:
                marker = layer.add_marker(plugin_api.get_task_title(), location['latitude'], location['longitude'], tag_attr_color)
        except:
            pass
        
        champlain_view.add_layer(layer)
        
        embed = cluttergtk.Embed()
        embed.set_size_request(400, 300)
        # method that will change the marker's position
        champlain_view.set_reactive(True)
        champlain_view.connect("button-release-event", self.champlain_change_marker, champlain_view, marker)
        
        layer.show_all()
        
        try:
            if location['latitude'] and location['longitude']:
                champlain_view.set_property("zoom-level", 9)
        except:
            champlain_view.set_property("zoom-level", 1)
            
        vbox.add(embed)
        
        embed.realize()
        stage = embed.get_stage()
        champlain_view.set_size(400, 300)
        stage.add(champlain_view)
        
        dialog.show_all()
        
        try:
            if location['latitude'] and location['longitude']:
                champlain_view.center_on(location['latitude'], location['longitude'])
        except:
            pass
        
    # a dialog to view the task's location
    def view_task_location(self, widget, title, tags):
        wTree = gtk.glade.XML(self.glade_file, "ViewTaskLocation")
        dialog = wTree.get_widget("ViewTaskLocation")
        
        vbox = wTree.get_widget("vbox1")
        
        champlain_view = champlain.View()
        champlain_view.set_property("scroll-mode", champlain.SCROLL_MODE_KINETIC)
        
        # connect the window signals
        # get the tag with the location attributes
        tag_attr_location = []
        for tag in tags:
            for attr in tag.get_all_attributes():
                if attr == "location":
                    tag_attr_location = attr
                    break
        
        # get one of the task's color
        tag_attr_color = None
        for tag in tags:
            for attr in tag.get_all_attributes():
                if attr == "color":
                    tag_attr_color = self.HTMLColorToRGB(tag.get_attribute(attr))
                    break          
        
        # add the champlain view to the window
        champlain_view = champlain.View()
        champlain_view.set_property("scroll-mode", champlain.SCROLL_MODE_KINETIC)
        
        layer = MarkerLayer()
        layer.add_marker(title, tag_attr_location[0], tag_attr_location[1], tag_attr_color)
        
        champlain_view.add_layer(layer)
        
        embed = cluttergtk.Embed()
        embed.set_size_request(400, 300)
        
        layer.show_all()
        
        champlain_view.set_property("zoom-level", 10)
            
        vbox.add(embed)
        
        embed.realize()
        stage = embed.get_stage()
        champlain_view.set_size(400, 300)
        stage.add(champlain_view)
        
        dialog.show_all()
        
        champlain_view.center_on(tag_attr_position[0], tag_attr_position[1])

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



class MarkerLayer(champlain.Layer):

    def __init__(self):
        champlain.Layer.__init__(self)
        # a marker can also be set in RGB with ints
        self.gray = clutter.Color(51, 51, 51)
        
        #RGBA
        self.white = clutter.Color(0xff, 0xff, 0xff, 0xff)
        self.black = clutter.Color(0x00, 0x00, 0x00, 0xff)
        
        self.hide()
        
    def add_marker(self, text, latitude, longitude, bg_color=None, text_color=None, font="Airmole 8"):
        if not text_color:
            text_color = self.white
            
        if not bg_color:
            bg_color = self.gray
        
        marker = champlain.marker_new_with_text(text, font, text_color, bg_color)

        #marker.set_position(38.575935, -7.921326)
        marker.set_position(latitude, longitude)
        self.add(marker)
        return marker