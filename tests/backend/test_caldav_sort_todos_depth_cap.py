# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) - The Getting Things GNOME Team
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

"""Backend.__sort_todos must not silently drop a todo whose parent chain
never resolves within the batch (a RELATED-TO cycle, or a parent UID
pointing outside the batch): the depth-cap safety valve (#1373) used to
`break` and leave such todos un-yielded forever, so they were never
created on the first CalDAV import."""

from unittest import TestCase
from unittest.mock import Mock

import vobject

from GTG.backends.backend_caldav import Backend, UID_FIELD
from GTG.core.datastore import Datastore

VTODO_ROOT = """BEGIN:VTODO\r
CREATED:20201212T092155Z\r
DTSTAMP:20201212T172830Z\r
STATUS:NEEDS-ACTION\r
SUMMARY:root\r
UID:ROOT\r
END:VTODO\r\n"""

# CYCLE-A and CYCLE-B each name the other as parent: neither ever becomes
# reachable from a root, so the un-patched generator never yields either.
VTODO_CYCLE_A = """BEGIN:VTODO\r
CREATED:20201212T092155Z\r
DTSTAMP:20201212T172830Z\r
RELATED-TO;RELTYPE=PARENT:CYCLE-B\r
STATUS:NEEDS-ACTION\r
SUMMARY:cycle a\r
UID:CYCLE-A\r
END:VTODO\r\n"""

VTODO_CYCLE_B = """BEGIN:VTODO\r
CREATED:20201212T092155Z\r
DTSTAMP:20201212T172830Z\r
RELATED-TO;RELTYPE=PARENT:CYCLE-A\r
STATUS:NEEDS-ACTION\r
SUMMARY:cycle b\r
UID:CYCLE-B\r
END:VTODO\r\n"""

# DANGLING names a parent UID that is not present anywhere in this batch
# (e.g. on another calendar, or already deleted server-side).
VTODO_DANGLING = """BEGIN:VTODO\r
CREATED:20201212T092155Z\r
DTSTAMP:20201212T172830Z\r
RELATED-TO;RELTYPE=PARENT:NOT-IN-THIS-BATCH\r
STATUS:NEEDS-ACTION\r
SUMMARY:dangling\r
UID:DANGLING\r
END:VTODO\r\n"""


def _get_todo(raw):
    todo = Mock()
    todo.instance.vtodo = vobject.readOne(raw)
    todo.parent.name = 'My Calendar'
    return todo


class SortTodosDepthCapTest(TestCase):

    @staticmethod
    def _backend():
        parameters = {'pid': 'favorite', 'service-url': 'x',
                      'username': 'u', 'password': 'p', 'period': 1,
                      'is-first-run': True}
        backend = Backend(parameters)
        backend.register_datastore(Datastore())
        return backend

    def test_two_cycle_is_flushed_not_dropped(self):
        todos = [_get_todo(VTODO_ROOT), _get_todo(VTODO_CYCLE_A),
                 _get_todo(VTODO_CYCLE_B)]
        backend = self._backend()
        yielded = list(backend._Backend__sort_todos(todos))
        self.assertEqual({UID_FIELD.get_dav(t) for t in yielded},
                         {'ROOT', 'CYCLE-A', 'CYCLE-B'})

    def test_dangling_parent_is_flushed_not_dropped(self):
        todos = [_get_todo(VTODO_ROOT), _get_todo(VTODO_DANGLING)]
        backend = self._backend()
        yielded = list(backend._Backend__sort_todos(todos))
        self.assertEqual({UID_FIELD.get_dav(t) for t in yielded},
                         {'ROOT', 'DANGLING'})

    def test_ordinary_hierarchy_is_unaffected(self):
        # Control: a normal, fully-resolvable batch must still come back
        # whole and must never hit the depth cap at all.
        todos = [_get_todo(VTODO_ROOT)]
        backend = self._backend()
        yielded = list(backend._Backend__sort_todos(todos))
        self.assertEqual([UID_FIELD.get_dav(t) for t in yielded], ['ROOT'])
