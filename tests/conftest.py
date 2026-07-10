# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) The GTG Team
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

# Isolate the whole test suite from the user's real XDG dirs:
# some tests build real Datastores, which now persist backend
# configuration (and would otherwise write into ~/.config/gtg).
import os
import tempfile

_xdg_scratch = tempfile.mkdtemp(prefix='gtg-tests-xdg-')
for _var in ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME'):
    os.environ[_var] = os.path.join(_xdg_scratch, _var[4:].lower())

from GTG import gi_version_requires  # noqa: E402

def pytest_collection(session):
    gi_version_requires()
