# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 - Lionel Dricot & Bertrand Rousseau
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

# Take list of Tags and give the background color that should be applied
# The returned color might be None (in which case, the default is used)


def background_color(tags, bgcolor=None):
    if not bgcolor:
        bgcolor = gtk.gdk.color_parse("#FFFFFF")
    # Compute color
    my_color = None
    color_count = 0.0
    red = 0
    green = 0
    blue = 0
    for my_tag in tags:
        my_color_str = my_tag.get_attribute("color")
        if my_color_str:
            my_color = gtk.gdk.color_parse(my_color_str)
            color_count = color_count + 1
            red = red + my_color.red
            green = green + my_color.green
            blue = blue + my_color.blue
    if color_count != 0:
        red = int(red / color_count)
        green = int(green / color_count)
        blue = int(blue / color_count)
        brightness = (red + green + blue) / 3.0
        target_brightness = (bgcolor.red + bgcolor.green + bgcolor.blue) / 3.0

        alpha = (1 - abs(brightness - target_brightness) / 65535.0) / 2.0
        red = int(red * alpha + bgcolor.red * (1 - alpha))
        green = int(green * alpha + bgcolor.green * (1 - alpha))
        blue = int(blue * alpha + bgcolor.blue * (1 - alpha))

        my_color = gtk.gdk.Color(red, green, blue).to_string()
    return my_color


def get_colored_tag_markup(req, tag_name, html=False):
    '''
    Given a tag name, returns a string containing the markup to color the
    tag name
    if html, returns a string insertable in html
    '''
    tag = req.get_tag(tag_name)
    if tag is None:
        # no task loaded with that tag, color cannot be taken
        return tag_name
    else:
        tag_color = tag.get_attribute("color")
        if tag_color:
            if html:
                format_string = '<span style="color:%s">%s</span>'
            else:
                format_string = '<span color="%s">%s</span>'
            return format_string % (tag_color, tag_name)
        else:
            return tag_name


def get_colored_tags_markup(req, tag_names):
    '''
    Calls get_colored_tag_markup for each tag_name in tag_names
    '''
    tag_markups = map(lambda t: get_colored_tag_markup(req, t), tag_names)
    tags_txt = ""
    if tag_markups:
        # reduce crashes if applied to an empty list
        tags_txt = reduce(lambda a, b: a + ", " + b, tag_markups)
    return tags_txt
