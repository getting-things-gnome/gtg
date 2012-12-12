# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2012 - Lionel Dricot & Bertrand Rousseau
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

# Run all of the tests.
check:
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
	pyflakes gtg gtcli gtg_new_task GTG

# Check for coding standard violations.
pep8:
	(echo gtg; echo gtcli;  echo gtg_new_task ; find . -name '*.py' -print ) | \
	xargs ./scripts/pep8.py --repeat
	(echo gtg; echo gtcli;  echo gtg_new_task ; find . -name '*.py' -print ) | \
	xargs ./scripts/pep8.py --repeat | wc -l

# Pylint code
pylint:
	pylint gtg gtcli gtg_new_task GTG

# Build API documentation.
apidocs:
	pydoctor --add-package GTG --make-html --html-output=doc/api \
		--project-name=GTG --project-url=http://gtg.fritalk.com/

edit-apidocs:
	pydoctor --add-package GTG --make-html --html-output=doc/api \
		--project-name=GTG --project-url=http://gtg.fritalk.com/ \
	        --verbose-about=epydoc2stan2 --verbose-about=epydoc2stan2 \
		--verbose-about=server --verbose-about=server --local-only \
		--server --edit

# Check for coding standard violations & flakes.
lint: pyflakes pep8 pylint

.PHONY: check lint pyflakes pep8 apidocs edit-apidocs clean

# Ignore the exit code in pyflakes, so that pep8 is always run when "make lint"
.IGNORE: pyflakes
