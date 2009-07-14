
# Run all of the tests.
check:
	./run-tests

# Get rid of stale files or files made during testing.
clean:
	rm -rf _trial_temp
	rm -rf debug_data
	find . -name '*.pyc' -print0 | xargs -0 rm -f
	find . -name '*~' -print0 | xargs -0 rm -f

# Check for common & easily catchable Python mistakes.
pyflakes:
	pyflakes GTG

# Check for coding standard violations.
pep8:
	find . -name '*.py' -print0 | xargs -0 ./scripts/pep8.py
	find . -name '*.py' -print0 | xargs -0 ./scripts/pep8.py --repeat | wc -l

# Check for coding standard violations & flakes.
lint: pyflakes pep8

.PHONY: check lint pyflakes pep8
