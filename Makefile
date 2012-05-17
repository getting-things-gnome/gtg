
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
	xargs ./scripts/pep8.py --ignore E221,E222
	(echo gtg; echo gtcli;  echo gtg_new_task ; find . -name '*.py' -print ) | \
	xargs ./scripts/pep8.py --ignore E221,E222 --repeat | wc -l

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

#Ignore the exit code in pyflakes, so that pep8 is always run when "make lint"
.IGNORE: pyflakes
