# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# -----------------------------------------------------------------------------

"""Regression tests for closed date serialization (#1338).

The 0.7 serializer only wrote the closed date of Done tasks: every
Dismissed task lost its date_closed on the first save, and a closed
task without a date is immortal for the reaper (today - no_date is
-9999 days). These tests fail on the old serializer and loader.
"""

from GTG.core.tasks import TaskStore, Status
from GTG.core.dates import Date


def roundtrip(store: TaskStore) -> TaskStore:
    new_store = TaskStore()
    new_store.from_xml(store.to_xml(), None)
    return new_store


def make_closed(store: TaskStore, title: str, status: Status):
    task = store.new(title)
    task.status = status
    task.is_active = False
    task.date_closed = Date('2026-01-15')
    return task


def test_dismissed_task_keeps_closed_date_over_roundtrip():
    store = TaskStore()
    make_closed(store, 'dismissed', Status.DISMISSED)
    loaded = roundtrip(store).data[0]
    assert loaded.date_closed == Date('2026-01-15')


def test_done_task_keeps_closed_date_over_roundtrip():
    store = TaskStore()
    make_closed(store, 'done', Status.DONE)
    loaded = roundtrip(store).data[0]
    assert loaded.date_closed == Date('2026-01-15')


def test_closed_task_without_date_is_healed_from_modified():
    store = TaskStore()
    task = make_closed(store, 'stripped', Status.DISMISSED)
    xml = store.to_xml()
    for done in xml.iter('done'):
        done.getparent().remove(done)
    loaded = TaskStore()
    loaded.from_xml(xml, None)
    healed = loaded.data[0]
    assert healed.date_closed == Date(str(task.date_modified)[:10])


def test_active_task_keeps_no_closed_date():
    store = TaskStore()
    store.new('active')
    loaded = roundtrip(store).data[0]
    assert loaded.date_closed == Date.no_date()
