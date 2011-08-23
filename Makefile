# Just dump action to pack GTG correctly at Launchpad PPA
build:

# Run all of the tests.
check:
	./run-tests

# Get rid of stale files or files made during testing.
clean:
	rm -rf _trial_temp
	rm -rf debug_data
	rm -rf doc/api
	find . -name '*.pyc' -print0 | xargs -0 rm -f
	find . -name '*~' -print0 | xargs -0 rm -f

# Check for common & easily catchable Python mistakes.
pyflakes:
	pyflakes GTG

# Check for coding standard violations.
pep8:
	find . -name '*.py' -print0 | xargs -0 ./scripts/pep8.py --ignore E221,E222
	find . -name '*.py' -print0 | xargs -0 ./scripts/pep8.py --ignore E221,E222 --repeat | wc -l

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
lint: pyflakes pep8

.PHONY: check lint pyflakes pep8 apidocs edit-apidocs clean

#Ignore the exit code in pyflakes, so that pep8 is always run when "make lint"
.IGNORE: pyflakes
