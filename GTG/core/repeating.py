import copy
import datetime
from enum import Enum

from dateutil.rrule import rrule, rruleset


class RepeatingOn(Enum):
    DUE, START, BOTH = list(range(3))


class Repeating:
    def __init__(self, task, timestamp=datetime.datetime.now(), rset=None,
                 enabled=False, repeats_on=RepeatingOn.DUE, count=1, old_tid=None):
        self._enabled = enabled

        # dateutil ruleset
        self.rset = rruleset() if rset is None else rset
        self.repeats_on = repeats_on

        self.task = task
        self.old_tid = old_tid
        self.count = count

        self.timestamp = timestamp


    def _update_date(func):
        def inner(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            if self.enabled:
                self.update_date(from_=from_)
        return inner


    def update_stamp(func):
        def inner(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            self.timestamp = datetime.datetime.now()
        return inner


    @property
    def enabled(self):
        return self._enabled


    @enabled.setter
    @update_stamp
    def enabled(self, value: bool) -> bool:
        self._enabled = value
        return self._enabled


    @property
    def repeats_on_start(self):
        return True if self.repeats_on in (RepeatingOn.START, RepeatingOn.BOTH) else False


    @property
    def repeats_on_due(self):
        return True if self.repeats_on in (RepeatingOn.DUE, RepeatingOn.BOTH) else False


    @property
    def repeats_on_both(self):
        return self.repeats_on == RepeatingOn.BOTH


    @_update_date
    def add_rule(self, rule):
        self.rset.rrule(rule)


    @property
    def date(self):
        # Rruleset doesn't seem to provide a way of counting
        # the numbers of rrules in a set. We have to use the private
        # field `_rrule`
        if len(self.rset._rrule) == 0:
            raise RruleNotFound(f'No rrule was found in ruleset')

        d = self.timestamp.date()
        dt = datetime.datetime(d.year, d.month, d.day)
        return self.rset.after(dt, True).date()


    def update_date(self, from_=datetime.date.today()):
        "Updates the due date or/and the start date with the occurrence"
        if self.repeats_on_start():
            self.task.start_date = self.date
        if self.repeats_on_due():
            self.task.due_date = self.date


    def get_next_occurrence(self, duplicated_task):
        new_rset = copy.deepcopy(self.rset)
        d = self.date
        new_rset.exdate(datetime.datetime(d.year, d.month, d.day))

        return Repeating(
            duplicated_task,
            rset=new_rset,
            enabled=True,
            repeats_on=self.repeats_on,
            count=self.count + 1,
            old_tid=self.task.id
        )


    def __repr__(self):
        return (f'Repeating(enabled={self.enabled}, '
                f'rset={str(self.rset)},'
                f'repeats_on={self.repeats_on}, '
                f'count={self.count}, '
                f'old_tid={self.old_tid})')


class RruleNotFound(Exception):
    pass
