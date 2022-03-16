from datetime import datetime
from enum import Enum


class RepeatingOn(Enum):
    DUE, START, BOTH = list(range(3))


class Repeating:
    def __init__(self, enabled=False, ruleset=None, repeats_on=RepeatingOn.DUE, count=0, old_tid=None):
        self.enabled = enabled

        # dateutil ruleset
        self.rset = ruleset
        self.repeats_on = repeats_on

        self.old_tid = old_tid
        self.count = count

        self.timestamp = datetime.now()


    def set_ruleset(ruleset):
        self.rset = ruleset
        self.update_date()


    @property
    def repeats_on_start(self):
        return True if self.repeats_on in (RepeatingOn.START, RepeatingOn.BOTH) else False


    @property
    def repeats_on_due(self):
        return True if self.repeats_on in (RepeatingOn.DUE, RepeatingOn.BOTH) else False


    def update_date(self):
        "Updates the due date or/and the start date with the occurrence"
        if self.repeats_on_start():
            self.task.start_date = self.rset.after(date, True)
        if self.repeats_on_due():
            self.task.due_date = self.rset.after(date, True)


    def __repr__(self):
        return (f'Repeating(enabled={self.enabled}, '
                f'repeats_on={self.repeats_on}, '
                f'ruleset={self.rset}, '
                f'count={self.count}, '
                f'old_tid={self.old_tid})')
