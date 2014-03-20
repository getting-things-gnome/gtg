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

install:
	pip3 install -r requirements.txt

# Run all of the tests.
tests:
	./run-tests

# Remove all temporary files
clean:
	rm -rf tmp
	find -type f -name '*~' -or -name '.*.sw*' -print | xargs rm -f
	find -type f -name '*.pyc' -print | xargs rm -f
	find -type d -name '__pycache__' -print | xargs rm -rf

# Check for common & easily catchable Python mistakes.
pyflakes:
	$(PYFLAKES) GTG

# Check for coding standard violations.
pep8:
	$(PEP8) --statistics --count GTG

# Check for coding standard violations & flakes.
lint: pyflakes pep8

.PHONY: install tests check lint pyflakes pep8 clean
