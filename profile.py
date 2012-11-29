#!/usr/bin/env python2
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

import GTG.gtg
import cProfile
import pstats
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-d", "--debug",
               action="store_true", dest="debug", help="enable debug output")
(options, args) = parser.parse_args()

cProfile.run("GTG.gtg.main(options, args)", filename="gtg.profile")

p = pstats.Stats('gtg.profile')
p.sort_stats('cumulative').print_stats(15)
p.sort_stats('time').print_stats(15)
p.sort_stats('calls').print_stats(15)
