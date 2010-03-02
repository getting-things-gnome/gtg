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
"""Reusable logging configuration.

GTG modules and plugins that wish to use logging should import the Log object:

  from GTG.core.logging import Log

...and target it with debug or info messages:

  Log.debug('Something has gone terribly wrong!')

"""
from __future__ import absolute_import
import logging


Log = logging.getLogger('gtg_logger')


def setup_logger(debug=False):
    """Configure the GTG logger."""
    # get the all-purpose GTG logger
    l = logging.getLogger('gtg_logger')
    # set a stream handler for debugging
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - " +
      "%(module)s:%(funcName)s:%(lineno)d - %(message)s")
    ch.setFormatter(formatter)
    l.addHandler(ch)
    # increase verbosity if in debug mode
    if debug:
        l.setLevel(logging.DEBUG)
        l.debug('Debug output enabled.')

