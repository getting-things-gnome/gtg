
pyflakes:
	pyflakes GTG

# Ignoring E301 "One blank line between things within a class", since it
# triggers false positives for normal decorator syntax.
pep8:
	find . -name '*.py' -print0 | xargs -0 ./scripts/pep8.py --ignore=E301
	find . -name '*.py' -print0 | xargs -0 ./scripts/pep8.py --ignore=E301 --repeat | wc -l

lint: pyflakes pep8

.PHONY: lint pyflakes pep8
