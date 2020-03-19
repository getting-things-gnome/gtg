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
"""Reusable logging configuration.

GTG modules and plugins that wish to use logging should import the log object::

  from GTG.core.logger import log

...and target it with debug or info messages::

  log.debug('Something has gone terribly wrong!')

"""
import logging


log = logging.getLogger('gtg')

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - "
                              + "%(module)s:%(funcName)s:%(lineno)d - "
                              + "%(message)s")
ch.setFormatter(formatter)
log.addHandler(ch)


def log_debug_enabled():
    """Return whether the logger is enabled for debug messages."""

    return log.isEnabledFor(logging.DEBUG)
