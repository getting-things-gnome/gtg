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

from datetime import date

#function to convert a string of the form YYYY-MM-DD
#to a date
#If the date is not correct, the function returns None
def strtodate(stri) :
    toreturn = None
    zedate = []
    if stri :
        if '-' in stri :
            zedate = stri.split('-')
        elif '/' in stri :
            zedate = stri.split('/')
            
        if len(zedate) == 3 :
            y = zedate[0]
            m = zedate[1]
            d = zedate[2]
            if y.isdigit() and m.isdigit() and d.isdigit() :
                yy = int(y)
                mm = int(m)
                dd = int(d)
                # we catch exceptions here
                try :
                    toreturn = date(yy,mm,dd)
                except ValueError:
                    toreturn = None
    return toreturn
