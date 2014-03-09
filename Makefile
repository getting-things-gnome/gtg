# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
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

PEP8=pep8
PYFLAKES=pyflakes

check: tests pep8 pyflakes

# Run all of the tests.
tests:
	./run-tests

# Get rid of stale files or files made during testing.
clean:
	rm -rf tmp
	rm -rf doc/api
	find . -name '*.pyc' -print0 | xargs -0 rm -f
	find . -name '*~' -print0 | xargs -0 rm -f
	find . -name '.*.swp' -print0 | xargs -0 rm -f

# Check for common & easily catchable Python mistakes.
pyflakes:
	$(PYFLAKES) gtg gtcli gtg_new_task GTG

# Check for coding standard violations.
pep8:
	$(PEP8) --statistics --count gtg gtcli gtg_new_task GTG

# Check for coding standard violations & flakes.
lint: pyflakes pep8

.PHONY: tests check lint pyflakes pep8 clean
