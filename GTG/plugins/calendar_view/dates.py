import calendar
import datetime
import locale

__all__ = 'Date',

NOW, SOON, SOMEDAY, NODATE = list(range(4))
# strings representing fuzzy dates + no date
ENGLISH_STRINGS = {
    NOW: 'now',
    SOON: 'soon',
    SOMEDAY: 'someday',
    NODATE: '',
}

STRINGS = {
    NOW: ('now'),
    SOON: ('soon'),
    SOMEDAY: ('someday'),
    NODATE: '',
}

LOOKUP = {
    'now': NOW,
    ('now').lower(): NOW,
    'soon': SOON,
    ('soon').lower(): SOON,
    'later': SOMEDAY,
    ('later').lower(): SOMEDAY,
    'someday': SOMEDAY,
    ('someday').lower(): SOMEDAY,
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
    return datetime.date(aday.year, aday.month, aday.day)

class Date(object):
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
        elif isinstance(value, str) or isinstance(value, str):
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

    @classmethod
    def today(cls):
        """ Return date for today """
        return Date(datetime.date.today())

    @classmethod
    def tomorrow(cls):
        """ Return date for tomorrow """
        return Date(datetime.date.today() + datetime.timedelta(1))
    @classmethod
    def no_date(cls):
        """ Return date representing no (set) date """
        return Date(NODATE)

    def is_fuzzy(self):
        """
        True if the Date is one of the fuzzy values:
        now, soon, someday or no_date
        """
        return self._fuzzy is not None

    def date(self):
        """ Map date into real date, i.e. convert fuzzy dates """
        if self.is_fuzzy():
            return FUNCS[self._fuzzy]
        else:
            return self._real_date
