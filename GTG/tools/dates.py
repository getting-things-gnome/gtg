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

""" General class for representing dates in GTG.

Dates Could be normal like 2012-04-01 or fuzzy like now, soon,
someday, later or no date.

Date.parse() parses all possible representations of a date. """

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
    NOW: datetime.date.today(),
    SOON: datetime.date.today() + datetime.timedelta(15),
    SOMEDAY: datetime.date.max,
    NODATE: datetime.date.max - datetime.timedelta(1),
}

# ISO 8601 date format
ISODATE = '%Y-%m-%d'
# get date format from locale
locale_format = locale.nl_langinfo(locale.D_FMT)


def convert_datetime_to_date(aday):
    """ Convert python's datetime to date.
    Strip unusable time information. """
    return datetime.date(aday.year, aday.month, aday.day)


class Date(object):
    """A date class that supports fuzzy dates.

    Date supports all the methods of the standard datetime.date class. A Date
    can be constructed with:
      - the fuzzy strings 'now', 'soon', '' (no date, default), or 'someday'
      - a string containing an ISO format date: YYYY-MM-DD, or
      - a datetime.date or Date instance, or
      - a string containing a locale format date.
    """
    _real_date = None
    _fuzzy = None

    def __init__(self, value=''):
        self._parse_init_value(value)

    def _parse_init_value(self, value):
        """ Parse many possible values and setup date """
        if value is None:
            self._parse_init_value(NODATE)
        elif isinstance(value, datetime.date):
            self._real_date = value
        elif isinstance(value, Date):
            # Copy internal values from other Date object
            self._real_date = value._real_date
            self._fuzzy = value._fuzzy
        elif isinstance(value, str) or isinstance(value, unicode):
            try:
                da_ti = datetime.datetime.strptime(value, locale_format).date()
                self._real_date = convert_datetime_to_date(da_ti)
            except ValueError:
                try:
                    # allow both locale format and ISO format
                    da_ti = datetime.datetime.strptime(value, ISODATE).date()
                    self._real_date = convert_datetime_to_date(da_ti)
                except ValueError:
                    # it must be a fuzzy date
                    try:
                        value = str(value.lower())
                        self._parse_init_value(LOOKUP[value])
                    except KeyError:
                        raise ValueError("Unknown value for date: '%s'"
                                         % value)
        elif isinstance(value, int):
            self._fuzzy = value
        else:
            raise ValueError("Unknown value for date: '%s'" % value)

    def date(self):
        """ Map date into real date, i.e. convert fuzzy dates """
        if self.is_fuzzy():
            return FUNCS[self._fuzzy]
        else:
            return self._real_date

    def __add__(self, other):
        if isinstance(other, datetime.timedelta):
            return Date(self.date() + other)
        else:
            raise NotImplementedError
    __radd__ = __add__

    def __sub__(self, other):
        if hasattr(other, 'date'):
            return self.date() - other.date()
        else:
            return self.date() - other

    def __rsub__(self, other):
        if hasattr(other, 'date'):
            return other.date() - self.date()
        else:
            return other - self.date()

    def __cmp__(self, other):
        """ Compare with other Date instance """
        if isinstance(other, Date):
            comparison = cmp(self.date(), other.date())

            # Keep fuzzy dates below normal dates
            if comparison == 0:
                if self.is_fuzzy() and not other.is_fuzzy():
                    return 1
                elif not self.is_fuzzy() and other.is_fuzzy():
                    return -1

            return comparison
        elif isinstance(other, datetime.date):
            return cmp(self.date(), other)
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
            return getattr(self.date(), name)

    def is_fuzzy(self):
        """
        True if the Date is one of the fuzzy values:
        now, soon, someday or no_date
        """
        return self._fuzzy is not None

    def days_left(self):
        """ Return the difference between the date and today in dates """
        if self._fuzzy == NODATE:
            return None
        else:
            return (self.date() - datetime.date.today()).days

    @classmethod
    def today(cls):
        """ Return date for today """
        return Date(datetime.date.today())

    @classmethod
    def tomorrow(cls):
        """ Return date for tomorrow """
        return Date(datetime.date.today() + datetime.timedelta(1))

    @classmethod
    def now(cls):
        """ Return date representing fuzzy date now """
        return Date(NOW)

    @classmethod
    def no_date(cls):
        """ Return date representing no (set) date """
        return Date(NODATE)

    @classmethod
    def soon(cls):
        """ Return date representing fuzzy date soon """
        return Date(SOON)

    @classmethod
    def someday(cls):
        """ Return date representing fuzzy date someday """
        return Date(SOMEDAY)

    @classmethod
    def _parse_only_month_day(cls, string):
        """ Parse next Xth day in month """
        try:
            mday = int(string)
            if not 1 <= mday <= 31 or string.startswith('0'):
                return None
        except ValueError:
            return None

        today = datetime.date.today()
        try:
            result = today.replace(day=mday)
        except ValueError:
            result = None

        if result is None or result <= today:
            if today.month == 12:
                next_month = 1
                next_year = today.year + 1
            else:
                next_month = today.month + 1
                next_year = today.year

            try:
                result = datetime.date(next_year, next_month, mday)
            except ValueError:
                pass

        return result

    @classmethod
    def _parse_numerical_format(cls, string):
        """ Parse numerical formats like %Y/%m/%d, %Y%m%d or %m%d """
        result = None
        today = datetime.date.today()
        for fmt in ['%Y/%m/%d', '%Y%m%d', '%m%d']:
            try:
                da_ti = datetime.datetime.strptime(string, fmt)
                result = convert_datetime_to_date(da_ti)
                if '%Y' not in fmt:
                    # If the day has passed, assume the next year
                    if result.month > today.month or \
                        (result.month == today.month and
                         result.day >= today.day):
                        year = today.year
                    else:
                        year = today.year + 1
                    result = result.replace(year=year)
            except ValueError:
                continue
        return result

    @classmethod
    def _parse_text_representation(cls, string):
        """ Match common text representation for date """
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

        offset = formats.get(string, None)
        if offset is None:
            return None
        else:
            return today + datetime.timedelta(offset)

    @classmethod
    def parse(cls, string):
        """Return a Date corresponding to string, or None.

        string may be in one of the following formats:
            - YYYY/MM/DD, YYYYMMDD, MMDD, D
            - fuzzy dates
            - 'today', 'tomorrow', 'next week', 'next month' or 'next year' in
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

        # do several parsing
        result = cls._parse_only_month_day(string)
        if result is None:
            result = cls._parse_numerical_format(string)
        if result is None:
            result = cls._parse_text_representation(string)

        # Announce the result
        if result is not None:
            return Date(result)
        else:
            raise ValueError("Can't parse date '%s'" % string)

    def to_readable_string(self):
        """ Return nice representation of date.

        Fuzzy dates => localized version
        Close dates => Today, Tomorrow, In X days
        Other => with locale dateformat, stripping year for this year
        """
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
                # if it's in less than a year, don't show the year field
                locale_format = locale_format.replace('/%Y', '')
                locale_format = locale_format.replace('.%Y', '.')
            return self._real_date.strftime(locale_format)
