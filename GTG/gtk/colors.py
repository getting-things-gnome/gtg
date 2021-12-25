# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
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

from gi.repository import Gdk
from functools import reduce
import random


def RGBA(red: float, green: float, blue: float, alpha: float = 1.0
         ) -> Gdk.RGBA:
    """
    Return a new instance of Gdk.RGBA initialized with the specified
    colors. Each color is a float from 0 (no color/black) to
    1 (full color/white).
    This is a replacement for GDK 3 Gdk.RGBA(...) quick syntax, which doesn't
    seem to exists for GDK 4.
    """
    c = Gdk.RGBA()
    c.red, c.green, c.blue, c.alpha = red, green, blue, alpha
    return c


def random_color() -> Gdk.RGBA:
    """
    Generate a new random color. Alpha is always 1.
    """
    return RGBA(random.uniform(0.0, 1.0),
                random.uniform(0.0, 1.0),
                random.uniform(0.0, 1.0),
                1.0)


def rgb_to_hex(rgba: Gdk.RGBA) -> str:
    """
    Convert an Gdk.RGBA to a string by using the hexadecimal 8-bit color
    notation, so #RRGGBB. Alpha is ignored.
    """
    return "#%02x%02x%02x" % (int(max(0, min(rgba.red, 1)) * 255),
                              int(max(0, min(rgba.green, 1)) * 255),
                              int(max(0, min(rgba.blue, 1)) * 255))


def rgba_to_hex(rgba: Gdk.RGBA) -> str:
    """
    Convert an Gdk.RGBA to a string by using the hexadecimal 8-bit color
    notation with alpha, so #RRGGBBAA.
    """
    return "#%02x%02x%02x%02x" % (int(max(0, min(rgba.red, 1)) * 255),
                                  int(max(0, min(rgba.green, 1)) * 255),
                                  int(max(0, min(rgba.red, 1)) * 255),
                                  int(max(0, min(rgba.alpha, 1)) * 255))


# Take list of Tags and give the background color that should be applied
# The returned color might be None (in which case, the default is used)

used_color = []


def background_color(tags, bgcolor=None):
    if not bgcolor:
        bgcolor = Gdk.RGBA()
        bgcolor.parse("#FFFFFF")
    # Compute color
    my_color = None
    color_count = 0.0
    red = 0
    green = 0
    blue = 0
    for my_tag in tags:
        my_color_str = my_tag.get_attribute("color")
        if my_color_str is not None and my_color_str not in used_color:
            used_color.append(my_color_str)
        if my_color_str:
            my_color = Gdk.RGBA()
            my_color.parse(my_color_str)
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

        gcolor = Gdk.RGBA()
        gcolor.red = red
        gcolor.green = green
        gcolor.blue = blue
        my_color = gcolor.to_string()
    return my_color


def get_colored_tag_markup(req, tag_name, html=False):
    """
    Given a tag name, returns a string containing the markup to color the
    tag name
    if html, returns a string insertable in html
    """
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
    """
    Calls get_colored_tag_markup for each tag_name in tag_names
    """
    tag_markups = [get_colored_tag_markup(req, t) for t in tag_names]
    tags_txt = ""
    if tag_markups:
        # reduce crashes if applied to an empty list
        tags_txt = reduce(lambda a, b: a + ", " + b, tag_markups)
    return tags_txt


def generate_tag_color():

    maxvalue = 65535
    flag = 0
    while(flag == 0):
        red = random.randint(0, maxvalue)
        green = random.randint(0, maxvalue)
        blue = random.randint(0, maxvalue)
        my_color = Gdk.Color(red, green, blue).to_string()
        if my_color not in used_color:
            flag = 1
    used_color.append(my_color)
    return my_color


def color_add(present_color):

    if present_color not in used_color:
        used_color.append(present_color)


def color_remove(present_color):

    if present_color in used_color:
        used_color.remove(present_color)
# -----------------------------------------------------------------------------
