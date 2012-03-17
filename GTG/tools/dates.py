# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Gettings Things Gnome! - a personal organizer for the GNOME desktop
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

import calendar
import datetime
import locale

from GTG import _, ngettext

__all__ = 'Date',

NOW, SOON, SOMEDAY, NODATE = range(4)
# strings representing fuzzy dates + no date
ENGLISH_STRINGS = {
    NOW: 'now',
    SOON: 'soon',
    SOMEDAY: 'someday',
    NODATE: '',
}

STRINGS = {
    NOW: _('now'),
    SOON: _('soon'),
    SOMEDAY: _('someday'),
    NODATE: '',
}

LOOKUP = {
    'now': NOW,
    _('now').lower(): NOW,
    'soon': SOON,
    _('soon').lower(): SOON,
    'later': SOMEDAY,
    _('later').lower(): SOMEDAY,
    'someday': SOMEDAY,
    _('someday').lower(): SOMEDAY,
    '': NODATE,
}
# functions giving absolute dates for fuzzy dates + no date
FUNCS = {
    NOW: lambda: datetime.date.today(),
    SOON: lambda: datetime.date.today() + datetime.timedelta(15),
    SOMEDAY: lambda: datetime.date.max,
    NODATE: lambda: datetime.date.max - datetime.timedelta(1),
}

# ISO 8601 date format
ISODATE = '%Y-%m-%d'

def convert_datetime_to_date(dt):
    return datetime.date(dt.year, dt.month, dt.day)

class Date(object):
    """A date class that supports fuzzy dates.
    
    Date supports all the methods of the standard datetime.date class. A Date
    can be constructed with:
      * the fuzzy strings 'now', 'soon', '' (no date, default), or 'someday'
      * a string containing an ISO format date: YYYY-MM-DD, or
      * a datetime.date or Date instance.
    
    """
    _real_date = None
    _fuzzy = None

    def __init__(self, value=''):
        if value is None:
            self.__init__(NODATE)
        elif isinstance(value, datetime.date):
            self._real_date = value
        elif isinstance(value, Date):
            self._real_date = value._real_date
            self._fuzzy = value._fuzzy
        elif isinstance(value, str) or isinstance(value, unicode):
            try:
                dt = datetime.datetime.strptime(value, ISODATE).date()
                self._real_date = convert_datetime_to_date(dt)
            except ValueError:
                # it must be a fuzzy date
                try:
                    value = str(value.lower())
                    self.__init__(LOOKUP[value])
                except KeyError:
                    raise ValueError("Unknown value for date: '%s'" % value)
        elif isinstance(value, int):
            self._fuzzy = value
        else:
            raise ValueError("Unknown value for date: '%s'" % value)

    def _date(self):
        if self.is_fuzzy():
            return FUNCS[self._fuzzy]()
        else:
            return self._real_date

    def __add__(self, other):
        if isinstance(other, datetime.timedelta):
            return Date(self._date() + other)
        else:
            raise NotImplementedError
    __radd__ = __add__

    def __sub__(self, other):
        if hasattr(other, '_date'):
            return self._date() - other._date()
        else:
            return self._date() - other

    def __rsub__(self, other):
        if hasattr(other, '_date'):
            return other._date() - self._date()
        else:
            return other - self._date()

    def __cmp__(self, other):
        """ Compare with other Date instance """
        if isinstance(other, Date):
            c = cmp(self._date(), other._date())

            # Keep fuzzy dates below normal dates
            if c == 0:
                if self.is_fuzzy() and not other.is_fuzzy():
                    return 1
                elif not self.is_fuzzy() and other.is_fuzzy():
                    return -1

            return c
        elif isinstance(other, datetime.date):
            return cmp(self._date(), other)
        else:
            raise NotImplementedError

    def __str__(self):
        if self._fuzzy is not None:
            return STRINGS[self._fuzzy]
        else:
            return self._real_date.isoformat()

    def __repr__(self):
        return "GTG_Date(%s)" % str(self)

    def xml_str(self):
        """ Representation for XML - fuzzy dates are in English """
        if self._fuzzy is not None:
            return ENGLISH_STRINGS[self._fuzzy]
        else:
            return self._real_date.isoformat()

    def __nonzero__(self):
        return self._fuzzy != NODATE

    def __getattr__(self, name):
        """ Provide access to the wrapped datetime.date """
        try:
            return self.__dict__[name]
        except KeyError:
            return getattr(self._date(), name)

    def is_fuzzy(self):
        """ True if the Date is one of the fuzzy values """
        return self._fuzzy is not None

    def days_left(self):
        """ Return the difference between the date and today in dates """
        if self._fuzzy == NODATE:
            return None
        else:
            return (self._date() - datetime.date.today()).days

    @classmethod
    def today(cls):
        return Date(datetime.date.today())

    @classmethod
    def tomorrow(cls):
        return Date(datetime.date.today() + datetime.timedelta(1))

    @classmethod
    def now(cls):
        return Date(NOW)

    @classmethod
    def no_date(cls):
        return Date(NODATE)

    @classmethod
    def soon(cls):
        return Date(SOON)

    @classmethod
    def someday(cls):
        return Date(SOMEDAY)

    @classmethod
    def parse(cls, string):
        """Return a Date corresponding to string, or None.
        
        string may be in one of the following formats:
         * YYYY/MM/DD, YYYYMMDD, MMDD
         * fuzzy dates
         * 'today', 'tomorrow', 'next week', 'next month' or 'next year' in
           English or the system locale.
        """
        # sanitize input
        if string is None:
            string = ''
        else:
            string = string.lower()

        # try the default formats
        try:
            return Date(string)
        except ValueError:
            pass

        result = None
        today = datetime.date.today()

        # accepted date formats
        formats = {
          'today': 0,
          _('today').lower(): 0,
          'tomorrow': 1,
          _('tomorrow').lower(): 1,
          'next week': 7,
          _('next week').lower(): 7,
          'next month': calendar.mdays[today.month],
          _('next month').lower(): calendar.mdays[today.month],
          'next year': 365 + int(calendar.isleap(today.year)),
          _('next year').lower(): 365 + int(calendar.isleap(today.year)),
        }

        # add week day names in the current locale
        for i, (english, local) in enumerate([
            ("Monday", _("Monday")),
            ("Tuesday", _("Tuesday")),
            ("Wednesday", _("Wednesday")),
            ("Thursday", _("Thursday")),
            ("Friday", _("Friday")),
            ("Saturday", _("Saturday")),
            ("Sunday", _("Sunday")),
            ]):
            offset = i - today.weekday() + 7 * int(i <= today.weekday())
            formats[english.lower()] = offset
            formats[local.lower()] = offset

        # attempt to parse the string with known formats
        for fmt in ['%Y/%m/%d', '%Y%m%d', '%m%d']:
            try: 
                dt = datetime.datetime.strptime(string, fmt)
                result = convert_datetime_to_date(dt)
                if '%Y' not in fmt:
                    # If the day has passed, assume the next year
                    if result.month >= today.month and result.day >= today.day:
                        year = today.year
                    else:
                        year = today.year +1
                    result = result.replace(year=year)
            except ValueError:
                continue

        offset = formats.get(string, None)
        if result is None and offset is not None:
            result = today + datetime.timedelta(offset)

        if result is not None:
            return Date(result)
        else:
            raise ValueError("Can't parse date '%s'" % string)

    def to_readable_string(self):
        if self._fuzzy is not None:
            return STRINGS[self._fuzzy]

        days_left = self.days_left()
        if days_left == 0:
            return _('Today')
        elif days_left < 0:
            abs_days = abs(days_left)
            return ngettext('Yesterday', '%(days)d days ago', abs_days) % \
              {'days': abs_days}
        elif days_left > 0 and days_left <= 15:
            return ngettext('Tomorrow', 'In %(days)d days', days_left) % \
              {'days': days_left}
        else:
            locale_format = locale.nl_langinfo(locale.D_FMT)
            if calendar.isleap(datetime.date.today().year):
                year_len = 366
            else:
                year_len = 365
            if float(days_left) / year_len < 1.0:
                #if it's in less than a year, don't show the year field
                locale_format = locale_format.replace('/%Y','')
                locale_format = locale_format.replace('.%Y','.')
            return  self._real_date.strftime(locale_format)
