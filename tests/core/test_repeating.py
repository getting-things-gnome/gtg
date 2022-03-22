from datetime import datetime, date, timedelta

import pytest
from dateutil.rrule import MONTHLY, WEEKLY, DAILY, rrule

from GTG.core.repeating import RepeatingOn, Repeating
from GTG.core.datastore2 import Datastore2


@pytest.fixture
def task():
    return Datastore2().tasks.new('new Task')


@pytest.fixture
def weekold_weekly_repeating(task):
    last_week = datetime.now() - timedelta(days=7)
    rep = Repeating(task)
    rep.timestamp = last_week
    rep.add_rule(
        rrule(WEEKLY, dtstart=last_week)
    )
    return rep


@pytest.fixture
def weekold_monthly_repeating(task):
    last_week = datetime(2022, 3, 13)
    rep = Repeating(task, timestamp=last_week)
    rep.add_rule(
        rrule(MONTHLY, bymonthday=30, dtstart=last_week)
    )
    return rep


@pytest.fixture
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


def test_get_date_for_old_task(weekold_weekly_repeating):
    assert weekold_weekly_repeating.date == date.today() - timedelta(days=7)


def test_get_next_occurrence_after_due(weekold_weekly_repeating, task):
    next_rep = weekold_weekly_repeating.get_next_occurrence(task)
    assert next_rep.date >= date.today()
    assert next_rep.date == weekold_weekly_repeating.date + timedelta(days=7)


def test_get_next_occurrence_before_due(weekold_monthly_repeating, task):
    next_rep = weekold_monthly_repeating.get_next_occurrence(task)
    assert weekold_monthly_repeating.date < next_rep.date
    assert next_rep.date == datetime(2022, 4, 30).date()


def test_get_next_occurrence_on_due(daily_repeating, task):
    next_rep = daily_repeating.get_next_occurrence(task)
    assert next_rep.date > daily_repeating.date
    assert next_rep.date == date.today() + timedelta(days=1)
