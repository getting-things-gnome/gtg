
pyflakes:
	pyflakes GTG | grep -v 'unable to detect'

pep8:
	find . -name '*.py' -print0 | xargs -0 ./scripts/pep8.py

lint: pyflakes pep8

.PHONY: lint pyflakes pep8
