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

'''
The tomboy backend. The actual backend is all in GenericTomboy, since it's
shared with the Gnote backend.
'''

from GTG.backends.genericbackend import GenericBackend
from GTG import _
from GTG.backends.generictomboy import GenericTomboy


class Backend(GenericTomboy):
    '''
    A simple class that adds some description to the GenericTomboy class.
    It's done this way since Tomboy and Gnote backends have different
    descriptions and Dbus addresses but the same backend behind them.
    '''

    _general_description = {
        GenericBackend.BACKEND_NAME: "backend_tomboy",
        GenericBackend.BACKEND_HUMAN_NAME: _("Tomboy"),
        GenericBackend.BACKEND_AUTHORS: ["Luca Invernizzi"],
        GenericBackend.BACKEND_TYPE: GenericBackend.TYPE_READWRITE,
        GenericBackend.BACKEND_DESCRIPTION:
        _("This synchronization service can synchronize all or part of"
          " your Tomboy notes in GTG. If you decide it would be handy to"
          " have one of your notes in your TODO list, just tag it "
          "with the tag you have chosen (you'll configure it later"
          "), and it will appear in GTG."),
    }

    _static_parameters = {
        GenericBackend.KEY_ATTACHED_TAGS: {
            GenericBackend.PARAM_TYPE: GenericBackend.TYPE_LIST_OF_STRINGS,
            GenericBackend.PARAM_DEFAULT_VALUE: ["@GTG-Tomboy"]},
    }

    _BUS_ADDRESS = ("org.gnome.Tomboy",
                    "/org/gnome/Tomboy/RemoteControl",
                    "org.gnome.Tomboy.RemoteControl")
