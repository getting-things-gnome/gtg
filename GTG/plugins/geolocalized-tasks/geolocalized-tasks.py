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
        btn_set_location.set_label("Set/View location")
        btn_set_location.connect('clicked', self.set_task_location, plugin_api)
        plugin_api.AddTaskToolbarItem(btn_set_location)
            
    def on_geolocalized_preferences(self, widget):
        pass
    
    def set_task_location(self, widget, plugin_api, location=None):
        location = self.geoclue.get_location_info()
        self.plugin_api = plugin_api
        
        wTree = gtk.glade.XML(self.glade_file, "SetTaskLocation")
        dialog = wTree.get_widget("SetTaskLocation")
        
        btn_zoom_in = wTree.get_widget("btn_zoom_in")
        btn_zoom_out = wTree.get_widget("btn_zoom_out")
        
        self.radiobutton1 = wTree.get_widget("radiobutton1")
        self.radiobutton2 = wTree.get_widget("radiobutton2")
        self.txt_new_tag = wTree.get_widget("txt_new_tag")
        self.cmb_existing_tag = wTree.get_widget("cmb_existing_tag")
        
        tabela = wTree.get_widget("tabela_set_task")
        vbox = wTree.get_widget("vbox_map")
        vbox_opt = wTree.get_widget("vbox_opt")
        
        champlain_view = champlain.View()
        champlain_view.set_property("scroll-mode", champlain.SCROLL_MODE_KINETIC)
        #champlain_view.set_property("zoom-on-double-click", False)
        
         # get one of the task's color
        tag_attr_color = None
        for tag in plugin_api.get_tags():
            for attr in tag.get_all_attributes():
                if attr == "color":
                    tag_attr_color = self.HTMLColorToRGB(tag.get_attribute(attr))
                    break   
        
        # check if the task has a location defined
        tag_attr_location = None
        for tag in self.plugin_api.get_tags():
            for attr in tag.get_all_attributes():
                if attr == "location":
                    tag_attr_location = attr
                    break
                
        if tag_attr_location:
            location['latitude'] = tag_attr_location[0]
            location['longitude'] = tag_attr_location[1] 
        
        layer = MarkerLayer()
        try:
            if location['latitude'] and location['longitude']:
                self.marker = layer.add_marker(plugin_api.get_task_title(), location['latitude'], location['longitude'], tag_attr_color)
        except:
            pass
        
        champlain_view.add_layer(layer)
        
        embed = cluttergtk.Embed()
        embed.set_size_request(400, 300)
        
        # method that will change the marker's position
        champlain_view.set_reactive(True)
        champlain_view.connect("button-release-event", self.champlain_change_marker, champlain_view, self.marker)
        
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
        
        # connect the toolbar buttons for zoom
        btn_zoom_in.connect("clicked", self.zoom_in, champlain_view)
        btn_zoom_out.connect("clicked", self.zoom_out, champlain_view)
        dialog.connect("response", self.set_task_location_close)
        
        #if there is no location set, we want to set it
        if not tag_attr_location:
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
        
        dialog.show_all()
        
        try:
            if location['latitude'] and location['longitude']:
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
                    if self.txt_new_tag.get_text() != "":
                        print self.marker.get_position()
                       
                       # # because users sometimes make mistakes, I'll check if the tag exists
                       # tmp_tag = ""
                       # for tag in self.plugin_api.get_tags():
                       #     t = "@" + self.txt_new_tag.get_text().replace("@", "")
                       #     if tag.get_attribute("name") == t:
                       #         tmp_tag = t
                       # if tmp_tag:
                       #     self.plugin_api.add_tag_attribute(self.txt_new_tag.get_text().replace("@", ""), 
                       #                                       location,  
                       #                                       self.marker.get_position())
                       # else:
                       #     self.plugin_api.add_tag(self.txt_new_tag.get_text().replace("@", ""))
                       #     self.plugin_api.add_tag_attribute(self.txt_new_tag.get_text().replace("@", ""), 
                       #                                       location,  
                       #                                       self.marker.get_position())        
                else:
                    # radiobutton2
                    print self.marker.get_position()
                    #self.plugin_api.add_tag_attribute( self.cmb_existing_tag.get_text_column(), "location", marker.get_position() )
            
            #dialog.destroy()
        else:
            # cancel
            dialog.destroy()
    
    def champlain_change_marker(self, widget, event, view, marker):
        if event.button != 1 or event.click_count > 1:
            return False
        
        (latitude, longitude) = view.get_coords_at(int(event.x), int(event.y))
        marker.set_position(latitude, longitude)
                
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