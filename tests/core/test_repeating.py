from datetime import datetime, date, timedelta

import pytest
from dateutil.rrule import MONTHLY, WEEKLY, DAILY, rrule

from GTG.core.repeating import RepeatingOn, Repeating


@pytest.fixture
def ds():
    return Datastore2()


@pytest.fixture
def weekold_weekly_repeating():
    last_week = datetime.now() - timedelta(days=7)
    rep = Repeating(None)
    rep.timestamp = last_week
    rep.add_rule(
        rrule(WEEKLY, dtstart=last_week)
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
    'rrule, expected',
    [
        (rrule(DAILY), date.today()),
        (rrule(WEEKLY), date.today()),
        (rrule(MONTHLY, dtstart=date.today() + timedelta(days=10)),
            date.today() + timedelta(days=10)),
        (rrule(WEEKLY, dtstart=datetime.now() - timedelta(days=6)),
            date.today() + timedelta(days=1))
    ]
)
def test_get_date(rrule, expected):
    rep = Repeating(None)
    rep.add_rule(
        rrule
    )
    assert expected == rep.date


def test_get_date_for_old_task(weekold_weekly_repeating):
    assert weekold_weekly_repeating.date == date.today() - timedelta(days=7)
