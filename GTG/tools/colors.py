# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2009 - Lionel Dricot & Bertrand Rousseau
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
import gtk

#Take list of Tags and give the background color that should be applied
#The returned color might be None (in which case, the default is used)
def background_color(tags, bgcolor=None):
    alpha = 0.5
    if not bgcolor:
        bgcolor = gtk.gdk.color_parse("#FFFFFF")
    # Compute color
    my_color = None
    color_count = 0.0
    color_dict  = {"red":0,"green":0,"blue":0}
    for my_tag in tags:
        my_color_str = my_tag.get_attribute("color")
        if my_color_str :
            my_color = gtk.gdk.color_parse(my_color_str)
            color_count = color_count + 1
            color_dict["red"] = color_dict["red"] + my_color.red
            color_dict["green"] = color_dict["green"] + my_color.green
            color_dict["blue"] = color_dict["blue"] + my_color.blue
    if color_count != 0:
        red = alpha*(color_dict["red"] / color_count) + (1-alpha)*bgcolor.red
        green = alpha*(color_dict["green"] / color_count) + (1-alpha)*bgcolor.green
        blue = alpha*(color_dict["blue"] / color_count) + (1-alpha)*bgcolor.blue
        my_color = gtk.gdk.Color(int(red), int(green), int(blue))
    return my_color
