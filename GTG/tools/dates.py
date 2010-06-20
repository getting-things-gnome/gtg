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

import calendar
import datetime
import locale
from GTG import _, ngettext


__all__ = 'Date',


## internal constants
# integers for special dates
TODAY, SOON, NODATE, LATER = range(4)
# strings representing special dates
STRINGS = {
  TODAY: 'today',
  SOON: 'soon',
  NODATE: '',
  LATER: 'later',
  }
# inverse of STRINGS
LOOKUP = dict([(v, k) for (k, v) in STRINGS.iteritems()])
# functions giving absolute dates for special dates
FUNCS = {
  TODAY: lambda: datetime.date.today(),
  SOON: lambda: datetime.date.today() + datetime.timedelta(15),
  NODATE: lambda: datetime.date.max - datetime.timedelta(1),
  LATER: lambda: datetime.date.max,
  }

# ISO 8601 date format
ISODATE = '%Y-%m-%d'


locale.setlocale(locale.LC_TIME, '')


class Date(object):
    """A date class that supports fuzzy dates.
    
    Date supports all the methods of the standard datetime.date class. A Date
    can be constructed with:
      * the special strings 'today', 'soon', '' (no date, default), or 'later'
      * a string containing an ISO format date: YYYY-MM-DD, or
      * a datetime.date or Date instance.
    
    """
    _date = None
    _special = None

    def __init__(self, value=''):
        if isinstance(value, datetime.date):
            self._date = value
        elif isinstance(value, Date):
            self._date = value._date
            self._special = value._special
        elif isinstance(value, str) or isinstance(value, unicode):
            try: # an ISO 8601 date
                self._date = datetime.datetime.strptime(value, ISODATE).date()
            except ValueError:
                try: # a special date
                    self.__init__(LOOKUP[value])
                except KeyError:
                    raise ValueError
        elif isinstance(value, int):
            self._date = FUNCS[value]()
            self._special = value
        else:
            raise ValueError
        assert not (self._date is None and self._special is None)

    def __add__(self, other):
        """Addition, same usage as datetime.date."""
        if isinstance(other, datetime.timedelta):
            return Date(self._date + other)
        else:
            raise NotImplementedError
    __radd__ = __add__

    def __sub__(self, other):
        """Subtraction, same usage as datetime.date."""
        if hasattr(other, '_date'):
            return self._date - other._date
        else:
            # if other is a datetime.date, this will work, otherwise let it
            # raise a NotImplementedError
            return self._date - other

    def __rsub__(self, other):
        """Subtraction, same usage as datetime.date."""
        # opposite of __sub__
        if hasattr(other, '_date'):
            return other._date - self._date
        else:
            return other - self._date

    def __cmp__(self, other):
        """Compare with other Date instance."""
        if hasattr(other, '_date'):
            return cmp(self._date, other._date)
        elif isinstance(other, datetime.date):
            return cmp(self._date, other)

    def __str__(self):
        """String representation.
        
        Date(str(d))) == d, always.
        
        """
        if self._special:
            return STRINGS[self._special]
        else:
            return self._date.isoformat()

    def __getattr__(self, name):
        """Provide access to the wrapped datetime.date."""
        try:
            return self.__dict__[name]
        except KeyError:
            return getattr(self._date, name)

    @property
    def is_special(self):
        """True if the Date is one of the special values; False if it is an
        absolute date."""
        return not self._special

    @classmethod
    def today(cls):
        """Return the special Date 'today'."""
        return Date(TODAY)

    @classmethod
    def no_date(cls):
        """Return the special Date '' (no date)."""
        return Date(NODATE)

    @classmethod
    def soon(cls):
        """Return the special Date 'soon'."""
        return Date(SOON)

    @classmethod
    def later(cls):
        """Return the special Date 'tomorrow'."""
        return Date(LATER)

    @classmethod
    def parse(cls, string):
        """Return a Date corresponding to *string*, or None.
        
        *string* may be in one of the following formats:
         * YYYY/MM/DD, YYYYMMDD, MMDD (assumes the current year),
         * any of the special values for Date, or
         * 'today', 'tomorrow', 'next week', 'next month' or 'next year' in
           English or the system locale.
        
        """
        # sanitize input
        if string is None:
            string = ''
        else:
            sting = string.lower()
        # try the default formats
        try:
            return Date(string)
        except ValueError:
            pass
        today = datetime.date.today()
        # accepted date formats
        formats = {
          '%Y/%m/%d': 0,
          '%Y%m%d': 0,
          '%m%d': 0,
          _('today'): 0,
          'tomorrow': 1,
          _('tomorrow'): 1,
          'next week': 7,
          _('next week'): 7,
          'next month': calendar.mdays[today.month],
          _('next month'): calendar.mdays[today.month],
          'next year': 365 + int(calendar.isleap(today.year)),
          _('next year'): 365 + int(calendar.isleap(today.year)),
          }
        # add week day names in the current locale
        for i in range(7):
            formats[calendar.day_name[i]] = i + 7 - today.weekday()
        result = None
        # try all of the formats
        for fmt, offset in formats.iteritems():
            try: # attempt to parse the string with known formats
                result = datetime.datetime.strptime(string, fmt)
            except ValueError: # parsing didn't work
                continue
            else: # parsing did work
                break
        if result:
            r = result.date()
            if r == datetime.date(1900, 1, 1):
                # a format like 'next week' was used that didn't get us a real
                # date value. Offset from today.
                result = today
            elif r.year == 1900:
                # a format like '%m%d' was used that got a real month and day,
                # but no year. Assume this year, or the next one if the day has
                # passed.
                if r.month >= today.month and r.day >= today.day:
                    result = datetime.date(today.year, r.month, r.day)
                else:
                    result = datetime.date(today.year + 1, r.month, r.day)
            return Date(result + datetime.timedelta(offset))
        else: # can't parse this string
            raise ValueError("can't parse a valid date from %s" % string)

    def to_readable_string(self):
        if self._special == NODATE:
            return None
        dleft = (self - datetime.date.today()).days
        if dleft == 0:
            return _('Today')
        elif dleft < 0:
            abs_days = abs(dleft)
            return ngettext('Yesterday', '%(days)d days ago', abs_days) % \
              {'days': abs_days}
        elif dleft > 0 and dleft <= 15:
            return ngettext('Tomorrow', 'In %(days)d days', dleft) % \
              {'days': dleft}
        else:
            locale_format = locale.nl_langinfo(locale.D_FMT)
            if calendar.isleap(datetime.date.today().year):
                year_len = 366
            else:
                year_len = 365
            if float(dleft) / year_len < 1.0:
                #if it's in less than a year, don't show the year field
                locale_format = locale_format.replace('/%Y','')
            return  self._date.strftime(locale_format)


#from datetime import date, timedelta
#import locale
#import calendar
#from GTG import _, ngettext

##setting the locale of gtg to the system locale 
##locale.setlocale(locale.LC_TIME, '')

#class Date(object):
#    def __cmp__(self, other):
#        if other is None: return 1
#        return cmp(self.to_py_date(), other.to_py_date())
#    
#    def __sub__(self, other):
#        return self.to_py_date() - other.to_py_date()

#    def __get_locale_string(self):
#        return locale.nl_langinfo(locale.D_FMT)
#        
#    def xml_str(self): return str(self)
#        
#    def day(self):      return self.to_py_date().day
#    def month(self):    return self.to_py_date().month
#    def year(self):     return self.to_py_date().year

#    def to_readable_string(self):
#        if self.to_py_date() == NoDate().to_py_date():
#            return None
#        dleft = (self.to_py_date() - date.today()).days
#        if dleft == 0:
#            return _("Today")
#        elif dleft < 0:
#            abs_days = abs(dleft)
#            return ngettext("Yesterday", "%(days)d days ago", abs_days) % \
#                                                           {"days": abs_days}
#        elif dleft > 0 and dleft <= 15:
#            return ngettext("Tomorrow", "In %(days)d days", dleft) % \
#                                                           {"days": dleft}
#        else:
#            locale_format = self.__get_locale_string()
#            if calendar.isleap(date.today().year):
#                year_len = 366
#            else:
#                year_len = 365
#            if float(dleft) / year_len < 1.0:
#                #if it's in less than a year, don't show the year field
#                locale_format = locale_format.replace('/%Y','')
#            return  self.to_py_date().strftime(locale_format)


#class FuzzyDate(Date):
#    def __init__(self, offset, name):
#        super(FuzzyDate, self).__init__()
#        self.name=name
#        self.offset=offset
#        
#    def to_py_date(self):
#        return date.today()+timedelta(self.offset)
#        
#    def __str__(self):
#        return _(self.name)
#        
#    def to_readable_string(self):
#    	return _(self.name)
#        
#    def xml_str(self):
#    	return self.name
#        
#    def days_left(self):
#        return None
#        
#class FuzzyDateFixed(FuzzyDate):
#	def to_py_date(self):
#		return self.offset

#NOW = FuzzyDate(0, _('now'))
#SOON = FuzzyDate(15, _('soon'))
#LATER = FuzzyDateFixed(date.max, _('later'))

#class RealDate(Date):
#    def __init__(self, dt):
#        super(RealDate, self).__init__()
#        assert(dt is not None)
#        self.proto = dt
#        
#    def to_py_date(self):
#        return self.proto
#        
#    def __str__(self):
#        return str(self.proto)

#    def days_left(self):
#        return (self.proto - date.today()).days
#      
#DATE_MAX_MINUS_ONE = date.max-timedelta(1)  # sooner than 'later'
#class NoDate(Date):

#    def __init__(self):
#        super(NoDate, self).__init__()

#    def to_py_date(self):
#        return DATE_MAX_MINUS_ONE
#    
#    def __str__(self):
#        return ''
#        
#    def days_left(self):
#        return None
#        
#    def __nonzero__(self):
#        return False 
#no_date = NoDate()

##function to convert a string of the form YYYY-MM-DD
##to a date
##If the date is not correct, the function returns None
#def strtodate(stri) :
#    if stri == _("now") or stri == "now":
#        return NOW
#    elif stri == _("soon") or stri == "soon":
#        return SOON
#    elif stri == _("later") or stri == "later":
#        return LATER
#        
#    toreturn = None
#    zedate = []
#    if stri :
#        if '-' in stri :
#            zedate = stri.split('-')
#        elif '/' in stri :
#            zedate = stri.split('/')
#            
#        if len(zedate) == 3 :
#            y = zedate[0]
#            m = zedate[1]
#            d = zedate[2]
#            if y.isdigit() and m.isdigit() and d.isdigit() :
#                yy = int(y)
#                mm = int(m)
#                dd = int(d)
#                # we catch exceptions here
#                try :
#                    toreturn = date(yy,mm,dd)
#                except ValueError:
#                    toreturn = None
#    
#    if not toreturn: return no_date
#    else: return RealDate(toreturn)
#    
#    
#def date_today():
#    return RealDate(date.today())

#def get_canonical_date(arg):
#    """
#    Transform "arg" in a valid yyyy-mm-dd date or return None.
#    "arg" can be a yyyy-mm-dd, yyyymmdd, mmdd, today, next week,
#    next month, next year, or a weekday name.
#    Literals are accepted both in english and in the locale language.
#    When clashes occur the locale takes precedence.
#    """
#    today = date.today()
#    #FIXME: there surely exist a way to get day names from the  datetime
#    #       or time module.
#    day_names = ["monday", "tuesday", "wednesday", \
#                 "thursday", "friday", "saturday", \
#                 "sunday"]
#    day_names_localized = [_("monday"), _("tuesday"), _("wednesday"), \
#                 _("thursday"), _("friday"), _("saturday"), \
#                 _("sunday")]
#    delta_day_names = {"today":      0, \
#                       "tomorrow":   1, \
#                       "next week":  7, \
#                       "next month": calendar.mdays[today.month], \
#                       "next year":  365 + int(calendar.isleap(today.year))}
#    delta_day_names_localized = \
#                      {_("today"):      0, \
#                       _("tomorrow"):   1, \
#                       _("next week"):  7, \
#                       _("next month"): calendar.mdays[today.month], \
#                       _("next year"):  365 + int(calendar.isleap(today.year))}
#    ### String sanitization
#    arg = arg.lower()
#    ### Conversion
#    #yyyymmdd and mmdd
#    if arg.isdigit():
#        if len(arg) == 4:
#            arg = str(date.today().year) + arg
#        assert(len(arg) == 8)
#        arg = "%s-%s-%s" % (arg[:4], arg[4:6], arg[6:])
#    #today, tomorrow, next {week, months, year}
#    elif arg in delta_day_names.keys() or \
#         arg in delta_day_names_localized.keys():
#        if arg in delta_day_names:
#            delta = delta_day_names[arg]
#        else:
#            delta = delta_day_names_localized[arg]
#        arg = (today + timedelta(days = delta)).isoformat()
#    elif arg in day_names or arg in day_names_localized:
#        if arg in day_names:
#            arg_day = day_names.index(arg)
#        else:
#            arg_day = day_names_localized.index(arg)
#        today_day = today.weekday()
#        next_date = timedelta(days = arg_day - today_day + \
#                          7 * int(arg_day <= today_day)) + today
#        arg = "%i-%i-%i" % (next_date.year,  \
#                            next_date.month, \
#                            next_date.day)
#    return strtodate(arg)

