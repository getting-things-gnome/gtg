#!/usr/bin/env python2
# -*- coding:utf-8 -*-
# -----------------------------------------------------------------------------
# Getting Things GNOME! - A personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 Lionel Dricot & Bertrand Rousseau
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

""" Check if liblarch is installed """

import sys

REQUIRED_LIBLARCH_API = "2.1"
GIT_CMD = "git clone https://github.com/liblarch/liblarch ../liblarch"


def import_liblarch(use_local=False):
    """ Check if liblarch is installed and is compatible

    If not, provide information how to obtain the newest version.
    If use_local, prioritize local (development) liblarch in ../liblarch"""

    def check_liblarch():
        """ Import liblarch and find out which one is missing """
        has_libraries = True
        missing = []
        try:
            import liblarch
            assert liblarch
        except ImportError:
            has_libraries = False
            missing.append("liblarch")

        try:
            import liblarch_gtk
            assert liblarch_gtk
        except ImportError:
            has_libraries = False
            missing.append("liblarch_gtk")

        return has_libraries, " and ".join(missing)

    if use_local:
        sys.path.insert(0, "../liblarch")

    has_libraries, missing = check_liblarch()

    if not use_local and not has_libraries:
        sys.path.append("../liblarch/")
        has_libraries, missing = check_liblarch()

    if not has_libraries:
        print """GTG can't find %s. To install missing libraries,
run the following command in the current folder:

%s

More information about liblarch: https://live.gnome.org/liblarch/""" % (
            missing, GIT_CMD)
        return False

    import liblarch
    try:
        is_liblarch_compatible = liblarch.is_compatible(REQUIRED_LIBLARCH_API)
    except:
        print """I could not recognize your liblarch module. Make sure that
you don't have stale copies of liblarch in your import path
"""
        is_liblarch_compatible = False
    if not is_liblarch_compatible:
        try:
            liblarch_version = liblarch.API
        except AttributeError:
            # Liblarch 1.0 has lowercased API variable
            liblarch_version = liblarch.api

        print """Your liblarch copy has its API at version %s
but your GTG copy need liblarch API version %s
You may fix that by downloading the last version of liblarch with

%s """ % (liblarch_version, REQUIRED_LIBLARCH_API, GIT_CMD)
        return False

    return True

if __name__ == "__main__":
    use_local = "-l" in sys.argv[1:] or "--local-liblarch" in sys.argv[1:]

    if import_liblarch(use_local):
        sys.exit(0)
    else:
        sys.exit(1)
