===================
Contributing to GTG
===================

GTG uses Git_ for versioning. It might be useful to take a look at this `Git tutorial`_ first.

.. _Git: https://git-scm.com/
.. _`Git tutorial`: https://learnxinyminutes.com/docs/git/


Getting the code
================

Get the latest version of the code on GitHub_. We suggest forking the master branch at first.
Then clone the forked master to your local::

    $ git clone https://github.com/YOUR_GITHUB_USERNAME/gtg.git

Launch GTG with debugging data (so it doesn't mess with your data)::

    $ cd path/to/gtg
    $ ./gtg.sh

.. _GitHub: https://github.com/getting-things-gnome/gtg

Choosing a feature to work on
=============================

If you are a happy user of GTG and nothing bothers you but you would like to contribute you can:

* choose a bug from our `Love bugs list`_ and try to solve
* ask people on IRC channel #gtg on irc://irc.gimp.org/#gtg
* ask on our `mailing list`_

.. _`Love bugs list`: https://github.com/getting-things-gnome/gtg/labels/love
.. _`mailing list`: https://launchpad.net/~gtg-user


Working on the feature in a branch
==================================

You have your local copy of the code (see "Getting the code"). Now, create a
local branch of your local branch (yes, it is)::

    $ cd path/to/gtg
    $ git checkout -b cool-new-feature

When working with GitHub, it's a good idea to keep your local *master* branch as
a pristine copy of master on GitHub.

Hack, add and commit your changes::

    $ git add names_of_changed_files
    $ git commit -m "description of your changes"

Repeat as much as you want. Don't hesitate to abuse the local commits. Think of
*commit* like *quick save* in a video game :)

Run the units tests to see if all is fine::

    $ make check=python3
    ./run-tests
    ...........
    ----------------------------------------------------------------------
    Ran 11 tests in 0.063s

    OK

Modify CHANGELOG to reflect your changes. If it's your first contribution, add
yourself in the AUTHORS file with your email address.

If the master has been updated while you were hacking, you should update your
local master branch, and merge modification in **your** branch::

    $ git checkout master
    $ git pull origin master
    $ git checkout cool-new-feature
    $ git merge master


When you have done some changes or solved a bug, add and commit the changes.
Afterwards, you need to push your work to your own fork on GitHub (where cool-new-feature
is the name of your local branch which you changed.)::

    $ git push origin cool-new-feature

If you have made changes and pushed them to your forked master branch on GitHub,
you can do a pull request to merge your work with the original GTG master.
To do this, go to your account on GitHub and click on "New Pull Request".

Create a pull request and comment on the corresponding bug. (Open one if
there is none). Add the tag *toreview* to the bug in GitHub. This is very
important and ensures we are not letting a patch rotting.

You can file a bug at https://github.com/getting-things-gnome/gtg/issues/new

If your branch is solving specific reported issue, please include the number of the issue
in the commit message or the pull request description. This will enable others to 
quickly navigate to the issue being solved.

For more detailed information, see the `HACKING`_ guide included in the GTG code.

.. _`HACKING`: https://github.com/getting-things-gnome/gtg/blob/master/HACKING

