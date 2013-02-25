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

import clutter
import champlain


class MarkerLayer(champlain.Layer):

    def __init__(self):
        champlain.Layer.__init__(self)
        # a marker can also be set in RGB with ints
        self.gray = clutter.Color(51, 51, 51)

        # RGBA
        self.white = clutter.Color(0xff, 0xff, 0xff, 0xff)
        self.black = clutter.Color(0x00, 0x00, 0x00, 0xff)

        self.hide()

    def add_marker(self, text, latitude, longitude, bg_color=None,
                   text_color=None, font="Airmole 8"):
        if not text_color:
            text_color = self.white

        if not bg_color:
            bg_color = self.gray

        marker = champlain.marker_new_with_text(text, font, text_color,
                                                bg_color)

        # marker.set_position(38.575935, -7.921326)
        if latitude and longitude:
            marker.set_position(latitude, longitude)
        self.add(marker)
        return marker
