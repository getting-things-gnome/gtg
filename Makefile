
pyflakes:
	pyflakes GTG

pep8:
	find . -name '*.py' -print0 | xargs -0 ./scripts/pep8.py
	find . -name '*.py' -print0 | xargs -0 ./scripts/pep8.py --repeat | wc -l

lint: pyflakes pep8

.PHONY: lint pyflakes pep8
