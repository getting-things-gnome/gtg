from datetime import datetime, date, timedelta

import pytest
from dateutil.rrule import MONTHLY, WEEKLY, DAILY, rrule

from GTG.core.repeating import RepeatingOn, Repeating
from GTG.core.datastore2 import Datastore2


def get_task():
    return Datastore2().tasks.new('new task')


def weekold_weekly_repeating():
    task = get_task()
    last_week = datetime.now() - timedelta(days=7)
    rep = Repeating(task)
    rep.timestamp = last_week
    rep.add_rule(
        rrule(WEEKLY, dtstart=last_week)
    )
    return rep


def weekold_monthly_repeating():
    task = get_task()
    last_week = datetime(2022, 3, 13)
    rep = Repeating(task, timestamp=last_week)
    rep.add_rule(
        rrule(MONTHLY, bymonthday=30, dtstart=last_week)
    )
    return rep


def daily_repeating(task):
    today = date.today()
    td = datetime(today.year, today.month, today.day)
    rep = Repeating(task)
    rep.add_rule(
        rrule(DAILY, dtstart=td)
    )
    return rep



def test_repeats_on():
    rep = Repeating(None)
    # By default tasks should be set to repeat on due dates
    assert not rep.repeats_on_start
    assert rep.repeats_on_due
    assert not rep.repeats_on_both

    rep = Repeating(None, repeats_on=RepeatingOn.START)
    assert rep.repeats_on_start
    assert not rep.repeats_on_due
    assert not rep.repeats_on_both

    rep = Repeating(None, repeats_on=RepeatingOn.BOTH)
    assert rep.repeats_on_start
    assert rep.repeats_on_due
    assert rep.repeats_on_both


def test_count():
    rep = Repeating(None)
    # Count should always start at 1 (even if repeating no enabled)
    assert rep.count == 1


def test_enabled():
    rep = Repeating(None)
    assert rep.enabled == False

    rep.enabled = True
    assert rep.enabled == True

    rep.enabled = False
    assert rep.enabled == False


def test_update_date():
    pass


@pytest.mark.parametrize(
    'rule,expected',
    [
        (rrule(DAILY), date.today()),
        (rrule(WEEKLY), date.today()),
        (rrule(MONTHLY, dtstart=datetime.today() + timedelta(days=10)),
            date.today() + timedelta(days=10)),
        (rrule(WEEKLY, dtstart=datetime.now() - timedelta(days=6)),
            date.today() + timedelta(days=1)),
    ]
)
def test_get_date(rule, expected):
    rep = Repeating(None)
    rep.add_rule(
        rule
    )
    assert expected == rep.date


@pytest.mark.parametrize(
    'rep,expected',
    [
        (weekold_weekly_repeating(), date.today() - timedelta(days=7))
    ]
)
def test_get_date_for_old_task(rep, expected):
    assert rep.date == expected


@pytest.mark.parametrize(
    'rep,expected',
    [
        (weekold_weekly_repeating(), weekold_weekly_repeating().date + timedelta(days=7))
    ]
)
def test_get_next_occurrence_after_due(rep, expected):
    next_rep = rep.get_next_occurrence(get_task())
    assert next_rep.date >= date.today()
    assert next_rep.date == expected


@pytest.mark.parametrize(
    'rep,expected',
    [
        (weekold_monthly_repeating(), datetime(2022, 4, 30).date())
    ]
)
def test_get_next_occurrence_before_due(rep, expected):
    next_rep = rep.get_next_occurrence(get_task())
    assert rep.date < next_rep.date
    assert next_rep.date == expected


@pytest.mark.parametrize(
    'rep,expected',
    [
        (daily_repeating(get_task()), date.today() + timedelta(days=1))
    ]
)
def test_get_next_occurrence_on_due(rep, expected):
    next_rep = rep.get_next_occurrence(get_task())
    assert next_rep.date > rep.date
    assert next_rep.date == date.today() + timedelta(days=1)
