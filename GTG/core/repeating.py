from __future__ import annotations
import copy
import datetime
from enum import Enum

from dateutil.rrule import rrule, rruleset

from GTG.core.dates import Date


class RepeatingOn(Enum):
    DUE, START, BOTH = list(range(3))


class Repeating:
    def __init__(self, task, timestamp=datetime.datetime.now(), rset=None,
                 enabled=False, repeats_on=RepeatingOn.DUE, count=1, next_tid=None):
        self._enabled = enabled

        # dateutil ruleset
        self.rset = rruleset() if rset is None else rset
        self.repeats_on = repeats_on

        self.task = task
        self.next_tid = next_tid
        self.count = count

        self.timestamp = timestamp


    def _update_date(func):
        """Decorator to update task's date if repeating is enabled"""
        def inner(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            if self.enabled:
                self.update_date(from_=from_)
        return inner


    def update_stamp(func):
        """Decorator to update timestamp"""
        def inner(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            self.timestamp = datetime.datetime.now()
        return inner


    def propagate_status(func):
        """Decorator to propagate status to children (if enabled)"""
        def inner(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            if self.enabled:
                for child in self.task.children:
                    child.repeating.enabled = True
        return inner

    
    def propagate_rrules(func):
        """Decorator to propagate rrules to children"""
        def inner(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            for child in self.task.children:
                child.repeating.set_rrules(copy.deepcopy(self.rset))
        return inner

    @property
    def enabled(self):
        return self._enabled


    @enabled.setter
    @update_stamp
    @propagate_rrules
    @propagate_status
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


    @propagate_rrules
    def set_rrules(self, rset):
        self.rset = rset


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

        # Removing the h/m/s data from the timestamp
        d = self.timestamp.date()
        dt = datetime.datetime(d.year, d.month, d.day)
        return self.rset.after(dt, True).date()


    def update_date(self, from_=datetime.date.today()) -> None:
        """Updates the due date or/and the start date with the occurrence.
        NOTE: verify if from_ is necessary."""
        dt = Date(self.date)
        if self.repeats_on_start:
            self.task.date_start = dt
        if self.repeats_on_due:
            self.task.date_due = dt


    def get_next_occurrence(self, duplicated_task) -> Repeating:
        # save next task id in previous occurrence
        self.next_tid = duplicated_task.id

        new_rset = copy.deepcopy(self.rset)
        d = self.date
        new_rset.exdate(datetime.datetime(d.year, d.month, d.day))

        return Repeating(
            duplicated_task,
            rset=new_rset,
            enabled=True,
            repeats_on=self.repeats_on,
            count=self.count + 1,
        )


    def crawl(self):
        """returns all the tids of the repeating tasks that came after"""
        tids = []
        while (tid := task.repeating.next_tid) != None:
            tids.append(tid)
            task = req.get_task(tid)
        return tids


    def __repr__(self):
        return (f'Repeating(enabled={self.enabled}, '
                f'rset={str(self.rset)},'
                f'repeats_on={self.repeats_on}, '
                f'count={self.count}, '
                f'next_tid={self.next_tid})')


class RruleNotFound(Exception):
    pass


# There's no way to get the string representation
# of a rruleset. We have to access "private" members.
def rrule_to_str(rset: rruleset) -> str:
    ret = '\n'.join([str(rrule) for rrule in rset._rrule])
    ret += "\nEXDATE:"
    for date in rset._exdate:
        ret += date.strftime("%Y%m%dT%H%M%S")+","
    return ret[:-1]
