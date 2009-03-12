# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personnal organizer for the GNOME desktop
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

#This code was contributed to Conseil but I don't remember by who.
#This class open an URL with the best browser available according
#To your desktop.

import os as _os
import sys as _sys

try:
    import gnome as _gnome
    _has_gnome = True
except ImportError:
    _has_gnome = False

def _spawn_executable(close_stdout = False, close_stderr = False, *args):
    pid = _os.fork()
    if pid == 0:
        # Child process
        
        # Close stdout and/or stderr
        null = _os.open('/dev/null', _os.O_WRONLY)
        if close_stdout: _os.dup2(null, 1)
        if close_stderr: _os.dup2(null, 2)
        _os.close(null)
        
        # Run it
        try:
            _os.execlp(args[0], *args)
        except OSError:
            _sys.exit(127)
    else:
        status = _os.waitpid(pid, 0)[1]
        return _os.WIFEXITED(status) and (_os.WEXITSTATUS(status) == 0)

def _test_executable(*args):
    return _spawn_executable(True, True, *args)

def _spawn_quiet(*args):
    return _spawn_executable(True, False, *args)

_has_xdg = _test_executable('xdg-open', '--help')
_has_exo = _test_executable('exo-open', '--help')

def openurl(url):
    if _has_xdg: # freedesktop is the best choice :p
        return _spawn_quiet('xdg-open', url)
    elif _has_gnome: # shouldn't also check for gnome-open ?
        return _gnome.url_show(url)
    elif _has_exo: # for xfce
        return _spawn_quiet('exo-open', url)
    # add your favorite desktop here ;)
    
    return False
