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
import locale
import calendar
from GTG import _, ngettext

#setting the locale of gtg to the system locale 
#locale.setlocale(locale.LC_TIME, '')

class Date(object):
    def __cmp__(self, other):
        if other is None: return 1
        return cmp(self.to_py_date(), other.to_py_date())
    
    def __sub__(self, other):
        return self.to_py_date() - other.to_py_date()

    def __get_locale_string(self):
        return locale.nl_langinfo(locale.D_FMT)
        
    def xml_str(self): return str(self)
        
    def day(self):      return self.to_py_date().day
    def month(self):    return self.to_py_date().month
    def year(self):     return self.to_py_date().year

    def to_readable_string(self):
        if self.to_py_date() == NoDate().to_py_date():
            return None
        dleft = (self.to_py_date() - date.today()).days
        if dleft == 0:
            return _("Today")
        elif dleft < 0:
            abs_days = abs(dleft)
            return ngettext("Yesterday", "%(days)d days ago", abs_days) % \
                                                           {"days": abs_days}
        elif dleft > 0 and dleft <= 15:
            return ngettext("Tomorrow", "In %(days)d days", dleft) % \
                                                           {"days": dleft}
        else:
            locale_format = self.__get_locale_string()
            if calendar.isleap(date.today().year):
                year_len = 366
            else:
                year_len = 365
            if float(dleft) / year_len < 1.0:
                #if it's in less than a year, don't show the year field
                locale_format = locale_format.replace('/%Y','')
            return  self.to_py_date().strftime(locale_format)


class FuzzyDate(Date):
    def __init__(self, offset, name):
        super(FuzzyDate, self).__init__()
        self.name=name
        self.offset=offset
        
    def to_py_date(self):
        return date.today()+timedelta(self.offset)
        
    def __str__(self):
        return _(self.name)
        
    def to_readable_string(self):
    	return _(self.name)
        
    def xml_str(self):
    	return self.name
        
    def days_left(self):
        return None
        
class FuzzyDateFixed(FuzzyDate):
	def to_py_date(self):
		return self.offset

NOW = FuzzyDate(0, _('now'))
SOON = FuzzyDate(15, _('soon'))
LATER = FuzzyDateFixed(date.max, _('later'))

class RealDate(Date):
    def __init__(self, dt):
        super(RealDate, self).__init__()
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

    def __init__(self):
        super(NoDate, self).__init__()

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
    if stri == _("now") or stri == "now":
        return NOW
    elif stri == _("soon") or stri == "soon":
        return SOON
    elif stri == _("later") or stri == "later":
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

def get_canonical_date(arg):
    """
    Transform "arg" in a valid yyyy-mm-dd date or return None.
    "arg" can be a yyyy-mm-dd, yyyymmdd, mmdd, today, next week,
    next month, next year, or a weekday name.
    Literals are accepted both in english and in the locale language.
    When clashes occur the locale takes precedence.
    """
    today = date.today()
    day_names = ["monday", "tuesday", "wednesday", "thursday",
                "friday", "saturday", "sunday"]
    day_names_localized = [_(day).lower() for day in day_names]

    delta_day_names = {"today":      0,
                       "tomorrow":   1,
                       "next week":  7,
                       "next month": calendar.mdays[today.month],
                       "next year":  365 + int(calendar.isleap(today.year))}
    delta_day_names_localized = \
                      {_("today").lower():      0,
                       _("tomorrow").lower():   1,
                       _("next week").lower():  7,
                       _("next month").lower(): calendar.mdays[today.month],
                       _("next year").lower():  365 + int(calendar.isleap(today.year))}
    ### String sanitization
    arg = arg.lower()
    ### Conversion
    #yyyymmdd and mmdd
    if arg.isdigit():
        if len(arg) == 4:
            arg = str(date.today().year) + arg
        assert(len(arg) == 8)
        arg = "%s-%s-%s" % (arg[:4], arg[4:6], arg[6:])
    #today, tomorrow, next {week, months, year}
    elif arg in delta_day_names.keys() or \
         arg in delta_day_names_localized.keys():
        if arg in delta_day_names:
            delta = delta_day_names[arg]
        else:
            delta = delta_day_names_localized[arg]
        arg = (today + timedelta(days = delta)).isoformat()
    elif arg in day_names or arg in day_names_localized:
        if arg in day_names:
            arg_day = day_names.index(arg)
        else:
            arg_day = day_names_localized.index(arg)
        today_day = today.weekday()
        next_date = timedelta(days = arg_day - today_day +
                          7 * int(arg_day <= today_day)) + today
        arg = "%i-%i-%i" % (next_date.year,
                            next_date.month,
                            next_date.day)
    return strtodate(arg)
