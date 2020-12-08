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

""" General class for representing dates in GTG.

Dates Could be normal like 2012-04-01 or fuzzy like now, soon,
someday, later or no date.

Date.parse() parses all possible representations of a date. """

from enum import Enum
import calendar
from datetime import datetime, date, timedelta
import locale

from gettext import gettext as _, ngettext

__all__ = ['Date']

NOW, SOON, SOMEDAY, NODATE = list(range(4))
# strings representing fuzzy dates + no date
ENGLISH_STRINGS = {
    NOW: 'now',
    SOON: 'soon',
    SOMEDAY: 'someday',
    NODATE: '',
}

STRINGS = {
    NOW: _('now'),
    # Translators: Used for display
    SOON: _('soon'),
    # Translators: Used for display
    SOMEDAY: _('someday'),
    NODATE: '',
}

LOOKUP = {
    'now': NOW,
    # Translators: Used in parsing, made lowercased in code
    _('now').lower(): NOW,
    'soon': SOON,
    # Translators: Used in parsing, made lowercased in code
    _('soon').lower(): SOON,
    'later': SOMEDAY,
    # Translators: Used in parsing, made lowercased in code
    _('later').lower(): SOMEDAY,
    'someday': SOMEDAY,
    # Translators: Used in parsing, made lowercased in code
    _('someday').lower(): SOMEDAY,
    '': NODATE,
}
# functions giving absolute dates for fuzzy dates + no date
FUNCS = {NOW: datetime.now,
         SOON: lambda: datetime.now() + timedelta(days=15),
         SOMEDAY: lambda: datetime.max,
         NODATE: lambda: datetime.max - timedelta(days=1)}


class Accuracy(Enum):
    datetime = 'datetime'
    date = 'date'
    fuzzy = 'fuzzy'


# ISO 8601 date format
# get date format from locale
DATE_FORMATS = [(locale.nl_langinfo(locale.D_T_FMT), Accuracy.datetime),
                ('%Y-%m-%dT%H:%M%S.%f%z', Accuracy.datetime),
                ('%Y-%m-%d %H:%M%S.%f%z', Accuracy.datetime),
                ('%Y-%m-%dT%H:%M%S.%f', Accuracy.datetime),
                ('%Y-%m-%d %H:%M%S.%f', Accuracy.datetime),
                ('%Y-%m-%dT%H:%M%S', Accuracy.datetime),
                ('%Y-%m-%d %H:%M%S', Accuracy.datetime),
                (locale.nl_langinfo(locale.D_FMT), Accuracy.date),
                ('%Y-%m-%d', Accuracy.date)]


class Date:
    """A date class that supports fuzzy dates.

    Date supports all the methods of the standard date class. A Date
    can be constructed with:
      - the fuzzy strings 'now', 'soon', '' (no date, default), or 'someday'
      - a string containing an ISO format date: YYYY-MM-DD, or
      - a date or Date instance, or
      - a string containing a locale format date.
    """
    DEFAULT_HOUR = 12
    DEFAULT_MINUTE = 0
    DEFAULT_SECOND = 0

    def __init__(self, value=None):
        self.datetime = None
        self.accuracy = None  # datetime, date, or fuzzy
        self.fuzzy = None
        if value is None or value == '':
            self.fuzzy = NODATE
            self.datetime = FUNCS[NODATE]()
            self.accuracy = Accuracy.fuzzy
        elif isinstance(value, date):
            self.accuracy = Accuracy.date
            self.datetime = datetime(
                value.year, value.month, value.day,
                self.DEFAULT_HOUR, self.DEFAULT_HOUR, self.DEFAULT_SECOND)
        elif isinstance(value, datetime):
            self.accuracy = Accuracy.datetime
            self.datetime = value
        elif isinstance(value, Date):
            # Copy internal values from other Date object
            self.accuracy = value.accuracy
            self.datetime = value.datetime
            self.fuzzy = value.fuzzy
        elif isinstance(value, str):
            done = False
            for date_format, accuracy in DATE_FORMATS:
                try:
                    self.datetime = datetime.strptime(value, date_format)
                    self.accuracy = accuracy
                    done = True
                    break
                except ValueError:
                    pass
            if not done:
                try:  # it must be a fuzzy date
                    value = LOOKUP[str(value).lower()]
                    self.fuzzy = value
                    self.datetime = FUNCS[value]
                    self.accuracy = Accuracy.fuzzy
                    done = True
                except KeyError:
                    pass
            if not done:
                raise ValueError(f"Unknown value for date: '{value}'")
        elif value in FUNCS:
            self.fuzzy = value
            self.datetime = FUNCS[value]()
            self.accuracy = Accuracy.fuzzy
        else:
            raise ValueError(f"Unknown value for date: '{value}'")

    def date(self):
        """ Map date into real date, i.e. convert fuzzy dates """
        return self.datetime.date()

    def dt_by_accuracy(self, accuracy: str = None):
        accuracy = accuracy or self.accuracy
        if self.accuracy == Accuracy.datetime:
            return self.datetime
        if self.accuracy == Accuracy.date:
            return self.date()
        return self.date()  # fuzzy ?

    def _cast_for_operation(self, other):
        if isinstance(other, timedelta):
            return self.dt_by_accuracy(), other
        other = self.__class__(other)
        accuracies = {self.accuracy, other.accuracy}
        op_accuracy = Accuracy.fuzzy if Accuracy.fuzzy in accuracies else (
            Accuracy.date if Accuracy.date in accuracies
            else Accuracy.datetime)
        return (self.dt_by_accuracy(op_accuracy),
                other.dt_by_accuracy(op_accuracy))

    def __add__(self, other):
        a, b = self._cast_for_operation(other)
        return a + b

    __radd__ = __add__

    def __sub__(self, other):
        a, b = self._cast_for_operation(other)
        return a - b

    def __rsub__(self, other):
        a, b = self._cast_for_operation(other)
        return a - b

    def __lt__(self, other):
        a, b = self._cast_for_operation(other)
        return a < b

    def __le__(self, other):
        a, b = self._cast_for_operation(other)
        return a <= b

    def __eq__(self, other):
        other = self.__class__(other)
        if self.is_fuzzy and other.is_fuzzy:
            return self.fuzzy == other.fuzzy
        a, b = self._cast_for_operation(other)
        return a == b

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        a, b = self._cast_for_operation(other)
        return a > b

    def __ge__(self, other):
        a, b = self._cast_for_operation(other)
        return a >= b

    def __str__(self):
        if self.fuzzy is not None:
            return STRINGS[self.fuzzy]
        return self.datetime.date().isoformat()

    def __repr__(self):
        return "GTG_Date(%s)" % str(self)

    def xml_str(self):
        """ Representation for XML - fuzzy dates are in English """
        if self.fuzzy is not None:
            return ENGLISH_STRINGS[self.fuzzy]
        return self.datetime.date().isoformat()

    def __bool__(self):
        return self.fuzzy != NODATE

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
        return self.fuzzy is not None

    def days_left(self):
        """ Return the difference between the date and today in dates """
        if self.fuzzy == NODATE:
            return None
        return (self.date() - date.today()).days

    @staticmethod
    def today():
        """ Return date for today """
        return Date(date.today())

    @staticmethod
    def tomorrow():
        """ Return date for tomorrow """
        return Date(date.today() + timedelta(days=1))

    @staticmethod
    def now():
        """ Return date representing fuzzy date now """
        return _GLOBAL_DATE_NOW

    @staticmethod
    def no_date():
        """ Return date representing no (set) date """
        return _GLOBAL_DATE_NODATE

    @staticmethod
    def soon():
        """ Return date representing fuzzy date soon """
        return _GLOBAL_DATE_SOON

    @staticmethod
    def someday():
        """ Return date representing fuzzy date someday """
        return _GLOBAL_DATE_SOMEDAY

    @staticmethod
    def _parse_only_month_day(string):
        """ Parse next Xth day in month """
        try:
            mday = int(string)
            if not 1 <= mday <= 31 or string.startswith('0'):
                return None
        except ValueError:
            return None

        today = date.today()
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
                result = date(next_year, next_month, mday)
            except ValueError:
                pass

        return result

    @staticmethod
    def _parse_numerical_format(string):
        """ Parse numerical formats like %Y/%m/%d, %Y%m%d or %m%d """
        result = None
        today = date.today()
        for fmt in ['%Y/%m/%d', '%Y%m%d', '%m%d']:
            try:
                result = datetime.strptime(string, fmt).date()
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

    @staticmethod
    def _parse_text_representation(string):
        """ Match common text representation for date """
        today = date.today()

        # accepted date formats
        formats = {
            'today': 0,
            # Translators: Used in parsing, made lowercased in code
            _('today').lower(): 0,
            'tomorrow': 1,
            # Translators: Used in parsing, made lowercased in code
            _('tomorrow').lower(): 1,
            'next week': 7,
            # Translators: Used in parsing, made lowercased in code
            _('next week').lower(): 7,
            'next month': calendar.mdays[today.month],
            # Translators: Used in parsing, made lowercased in code
            _('next month').lower(): calendar.mdays[today.month],
            'next year': 365 + int(calendar.isleap(today.year)),
            # Translators: Used in parsing, made lowercased in code
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
            return today + timedelta(offset)

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
            raise ValueError(f"Can't parse date '{string}'")

    def _parse_only_month_day_for_recurrency(self, string, newtask=True):
        """ Parse next Xth day in month from a certain date"""
        if not newtask:
            self += timedelta(1)
        try:
            mday = int(string)
            if not 1 <= mday <= 31 or string.startswith('0'):
                return None
        except ValueError:
            return None

        try:
            result = self.replace(day=mday)
        except ValueError:
            result = None

        if result is None or result <= self:
            if self.month == 12:
                next_month = 1
                next_year = self.year + 1
            else:
                next_month = self.month + 1
                next_year = self.year

            try:
                result = date(next_year, next_month, mday)
            except ValueError:
                pass

        return result

    def _parse_numerical_format_for_recurrency(self, string, newtask=True):
        """ Parse numerical formats like %Y/%m/%d,
        %Y%m%d or %m%d and calculated from a certain date"""
        result = None
        if not newtask:
            self += timedelta(1)
        for fmt in ['%Y/%m/%d', '%Y%m%d', '%m%d']:
            try:
                result = datetime.strptime(string, fmt).date()
                if '%Y' not in fmt:
                    # If the day has passed, assume the next year
                    if (result.month > self.month or
                        (result.month == self.month and
                         result.day >= self.day)):
                        year = self.year
                    else:
                        year = self.year + 1
                    result = result.replace(year=year)
            except ValueError:
                continue
        return result

    def _parse_text_representation_for_recurrency(self, string, newtask=False):
        """Match common text representation from a certain date(self)

        Args:
            string (str): text representation.
            newtask (bool, optional): depending on the task if it is a new one or not, the offset changes
        """
        # accepted date formats
        formats = {
            # change the offset depending on the task.
            'day': 0 if newtask else 1,
            # Translators: Used in recurring parsing, made lowercased in code
            _('day').lower(): 0 if newtask else 1,
            'other-day': 0 if newtask else 2,
            # Translators: Used in recurring parsing, made lowercased in code
            _('other-day').lower(): 0 if newtask else 2,
            'week': 0 if newtask else 7,
            # Translators: Used in recurring parsing, made lowercased in code
            _('week').lower(): 0 if newtask else 7,
            'month': 0 if newtask else calendar.mdays[self.month],
            # Translators: Used in recurring parsing, made lowercased in code
            _('month').lower(): 0 if newtask else calendar.mdays[self.month],
            'year': 0 if newtask else 365 + int(calendar.isleap(self.year)),
            # Translators: Used in recurring parsing, made lowercased in code
            _('year').lower(): 0 if newtask else 365 + int(calendar.isleap(self.year)),
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
            offset = i - self.weekday() + 7 * int(i <= self.weekday())
            formats[english.lower()] = offset
            formats[local.lower()] = offset

        offset = formats.get(string, None)
        if offset is None:
            return None
        else:
            return self + timedelta(offset)

    def parse_from_date(self, string, newtask=False):
        """parse_from_date returns the date from a string
        but counts since a given date"""
        if string is None:
            string = ''
        else:
            string = string.lower()

        try:
            return Date(string)
        except ValueError:
            pass

        result = self._parse_only_month_day_for_recurrency(string, newtask)
        if result is None:
            result = self._parse_numerical_format_for_recurrency(string, newtask)
        if result is None:
            result = self._parse_text_representation_for_recurrency(string, newtask)

        if result is not None:
            return Date(result)
        else:
            raise ValueError(f"Can't parse date '{string}'")

    def to_readable_string(self):
        """ Return nice representation of date.

        Fuzzy dates => localized version
        Close dates => Today, Tomorrow, In X days
        Other => with locale dateformat, stripping year for this year
        """
        if self.fuzzy is not None:
            return STRINGS[self.fuzzy]

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
            if calendar.isleap(date.today().year):
                year_len = 366
            else:
                year_len = 365
            if float(days_left) / year_len < 1.0:
                # if it's in less than a year, don't show the year field
                locale_format = locale_format.replace('/%Y', '')
                locale_format = locale_format.replace('.%Y', '.')
            return self.datetime.strftime(locale_format)


_GLOBAL_DATE_NOW = Date(NOW)
_GLOBAL_DATE_SOON = Date(SOON)
_GLOBAL_DATE_NODATE = Date(NODATE)
_GLOBAL_DATE_SOMEDAY = Date(SOMEDAY)
