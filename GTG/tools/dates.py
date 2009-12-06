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

from datetime import date, timedelta
from GTG import _

class Date(object):
    def __cmp__(self, other):
        if other is None: return 1
        return cmp(self.to_py_date(), other.to_py_date())
    
    def __sub__(self, other):
        return self.to_py_date() - other.to_py_date()
        
    def xml_str(self): return str(self)
        
    def day(self):      return self.to_py_date().day
    def month(self):    return self.to_py_date().month
    def year(self):     return self.to_py_date().year

class FuzzyDate(Date):
    def __init__(self, offset, name):
        self.name=name
        self.offset=offset
        
    def to_py_date(self):
        return date.today()+timedelta(self.offset)
        
    def __str__(self):
        return _(self.name)
        
    def xml_str(self):
    	return self.name
        
    def days_left(self):
        return None
        
class FuzzyDateFixed(FuzzyDate):
	def to_py_date(self):
		return self.offset

NOW = FuzzyDate(0, 'now')
SOON = FuzzyDate(15, 'soon')
LATER = FuzzyDateFixed(date.max, 'later')

class RealDate(Date):
    def __init__(self, dt):
        assert(dt is not None)
        self.proto = dt
        
    def to_py_date(self):
        return self.proto
        
    def __str__(self):
        return str(self.proto)

    def days_left(self):
        return (self.proto - date.today()).days
      
DATE_MAX_MINUS_ONE = date.max-timedelta(1)  # sooner than 'later'
class NoDate(Date):
    def to_py_date(self):
        return DATE_MAX_MINUS_ONE
    
    def __str__(self):
        return ''
        
    def days_left(self):
        return None
        
    def __nonzero__(self):
        return False 
no_date = NoDate()

#function to convert a string of the form YYYY-MM-DD
#to a date
#If the date is not correct, the function returns None
def strtodate(stri) :
    if stri == "now" or stri == _("now"):
        return NOW
    elif stri == "soon" or stri == _("soon"):
        return SOON
    elif stri == "later" or  stri == _("later"):
        return LATER
        
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
    
    if not toreturn: return no_date
    else: return RealDate(toreturn)
    
    
def date_today():
    return RealDate(date.today())
