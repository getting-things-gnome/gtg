import datetime
from utils import date_generator


class Week():

    numdays = 7

    def __init__(self, start=None):
        self.start_date = start
        if start:
            self.set_week_starting_on(start)

    def set_week_starting_on(self, date):
        """
        Shows the week that starts on a given @date. This date must be a
        Monday or a Sunday.

        @param date: datetime object, the date the week will start on. Must be
        a Monday or a Sunday.
        """
        assert(date.weekday() == 0 or date.weekday() == 6), \
            ("Can not start week with date %s. It is not a Monday or a Sunday"
             % date)
        self.start_date = date
        self.adjust((date - self.start_date).days)

    def week_containing_day(self, day):
        """
        Shows the week that contains a given date.  The corresponding week will
        always start on Monday.

        @param day: datetime object, the date we want the week to show.
        """
        self.start_date = day
        self.adjust(-day.weekday())

    def adjust(self, num_days):
        """
        Adjusts the start of the week by @num_days.

        @param num_days: integer, the number of days to adjust.
        """
        self.start_date += datetime.timedelta(days=num_days)
        self.days = date_generator(self.start_date, self.numdays)
        self.end_date = self.days[-1]
        return self.start_date

    def compare_to(self, other_week):
        """
        Compare one week to another, to see which one starts earlier.

        @param other_week: a Week object, the other week to be compared to.
        """
        if self == other_week:
            return 0
        return self.start_date < other_week.start_date

    def equal_to(self, week):
        """
        Returns True if weeks cover the same period of date.

        @param other_week: a Week object, the other week to be compared to.
        """
        return self.compare_to(week) == 0

    def difference(self, other_week):
        """
        Returns the number of days this week differs from the @other week.

        @param other_week: a Week object, the other week to be compared to.
        @return diff: integer, num of days the weeks differ from each other.
        """
        if self.equal_to(other_week):
            return 0
        diff = self.start_date - other_week.start_date
        return diff.days

    def label(self, format):
        """
        Generates a list of labels for the days of the current week,
        given a specific strftime @format.

        @param format: string, must follow the strftime convention.
        @return labels: list of strings, each containing the information for a
        date in the current week given the corresponding format.
        """
        labels = [x.strftime(format) for x in self.days]
        return labels

    def __str__(self):
        """ Prints a Week """
        return " - ".join(self.label(format="%D %a"))
