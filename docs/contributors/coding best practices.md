For general information about contributing to GTG, first see CONTRIBUTING.md (in
the root directory of our development code repository) and then the other guides
in this `docs/contributing/` directory, including the Git workflow tips to
facilitate the submission process for your code.

Note: GTG is a Python 3 application. New code must not be written in Python 2.


# Test suite (a.k.a. ensuring you didn't break everything)

Ideally, in the spirit of [test-driven development](https://en.wikipedia.org/wiki/Test-driven_development), you should write tests for the features you write or refactor.

Unit tests live in ``tests/``.

When you're ready to commit your changes (or even while you are making them),
you should probably run the units tests to see if all is fine 
(or at least that you did not introduce more problems than before):

    $ make check=python3
    ./run-tests
    ...........
    ----------------------------------------------------------------------
    Ran 11 tests in 0.063s
    OK

As our project has a tox.ini file, if you have the "tox" Python testing package
installed, you can also run the "tox" command to run tests.


You can also manually test your changes with debugging data, by doing:

    ./gtg.sh

Running ``gtg.sh`` will prevent GTG from messing with your real data.
Instead, it will create/store data in ``./tmp/default/``.


# Checking the coding style

You should also avoid adding any 'flakes', simple Python mistakes caught by
[Pyflakes](https://pypi.python.org/pypi/pyflakes).

For style, we follow Python's [PEP 8](http://www.python.org/dev/peps/pep-0008/).
Like the Pitivi project, we apply one exception to the PEP 8 standard though:
**we don't limit our line lengths to 80 characters**. It's not the 90's anymore.
We share Pitivi's philosophy:

> When deciding whether or not you should split your line when it exceeds
> 79 characters, ask yourself: "Does it truly improve legibility?"
> 
> What this translates to is:
> 
> - Avoid having very long lines.
> - When the contents only slightly exceeds the 80 chars limit,
>   consider keeping it on one line. Otherwise it just hurts legibility and
>   gives a weird "shape" to the code.

Python code is by nature pretty compact. Often, with Python+GTK code, the line
lengths are just _a bit_ over 80 characters. So our rule of thumb in GTG is,
if it's under 90-100 characters, keep it on one line if it improves legibility.
This is why, in the example below, we use "--max-line-length=100 --ignore=E128".

There are various code quality & style checkers that let you check compliance.
The "pycodestyle" (previously known as "pep8") tool can be installed
from your Linux distribution's package repositories, or via:

    pip install pycodestyle

You can run the various code style checkers individually like this:

    $ pyflakes GTG/
    
    $ find . -name '*.py' -print0 | xargs -0 pycodestyle --repeat --max-line-length=100 --ignore=E128

These will output a list of various stylistic or quality issues in the code.
If you just want the number of style issues, you could do this for example:

    $ find . -name '*.py' -print0 | xargs -0 pycodestyle --repeat --max-line-length=100 --ignore=E128 | wc -l

Please leave the number of issues in the code smaller than when you found it ;)

If you want to run all the code quality & style checkers at once, run this:

    $ make lint=python3


# Commenting-out code

Avoid leaving commented out code in the codebase, it is NOT GOOD PRACTICE!
Or at least, if some code must be left commented out, include a comment
with `# TODO` or `# FIXME`, explaining why it was disabled.

Some common reasons why one might create commented code are:

a.  I was unsure of my fix
b.  I wasn't sure what the original code was supposed to do
c.  I needed to disable it to work around some problem
d.  I removed or broke other code that this code depends on
e.  I started implementing something but haven't finished it yet
f.  I need this for debugging problems that might still exist

Obviously none of these are great situations to be in, but it happens.

Ideally, commenting out a line of code should be a signal to yourself
that one of these things has happened, that you probably should ask for help
before merging it to master, and it should stay in a branch for now.

But that may not always be possible.  So more practically, when
commenting out code please ALWAYS explain why you commented it out.
This enables other developers (who may know the code better) to figure
out and solve the problem.

So instead of this:

    #foo.animate(x)

consider doing it like this:

    #FIXME:  If x is None, it causes animate() to crash.  But x should
    #never be None, so this *should* always work.  I can't reproduce the
    #crash so can't tell what makes x None.  Leaving it disabled for now
    #until someone can reproduce it and investigate.  (LP: #12345)
    #
    #foo.animate(x)

Avoid committing commented out code (or print statements) used for debugging.
Use a graphical tool like gitg to select only the relevant lines to commit,
or use GTG's built-in logging system (which has various debug levels).
So instead of this:

    #print "Testing: ", 1, 2, 3

...you could do this:

    log.debug("Testing %d %d %d %s", 1, 2, 3, "Go!")

Historically, there has been code left commented out in the codebase for
various reasons. As you run across such code, please help us tidy the
codebase by either commenting why it's disabled, or removing it.


# GTG API Style

Whenever possible, prefer using task_id/tagname instead of passing task/tag
objects directly.  In experimentation it's been found that passing and
using the objects directly is very expensive.  Looking in a list of
objects is *much* slower than looking in a list of Strings.

If you create a method, try that that method take a task_id/tagname as
argument and return a task_id/tagname. (of course, don't apply this
blindly).

As a rule of thumb, if you put objects in a list for whatever purpose,
it should light a big warning sign ! It probably means than you have to
use the task_id/tagname instead.

The req.get_task/get_tag methods are pretty cheap (access to a
dictionary with Strings as keys) and, anyway, I discovered that a lot of
functions can already be done without the object at all if you are
consistent.

In existing tag/task object, don't hesitate to port existing functions
that does not respect that philosophy but should. (this work should take
place in gtg-refactor branch).


# Copyright

Modules should begin with the following header (updated to the current year):

```
# -----------------------------------------------------------------------------
# Gettings Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2020 - the GTG contributors
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
```
