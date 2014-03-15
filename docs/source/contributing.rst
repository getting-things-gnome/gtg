===================
Contributing to GTG
===================

GTG uses Bazaar_ for versioning. It might be useful to read `Bazaar's tutorial`_ first.

.. _Bazaar: http://bazaar.canonical.com/
.. _`Bazaar's tutorial`: http://doc.bazaar.canonical.com/latest/en/mini-tutorial/

Dependencies
============

You need to have python-configobj installed

Getting the code
================

Get the latest version of the code on Launchpad_::

    $ bzr branch lp:gtg trunk

Although if you're thinking of contributing more than one patch, you might want to do::

    $ bzr init-repo gtg
    $ cd gtg
    $ bzr branch lp:gtg trunk

This will share revision data between branches, reducing storage costs & network time.


Launch gtg with debugging data (so it doesn't mess with your data)::

    $ cd trunk
    $ ./scripts/debug.sh

.. _Launchpad: https://launchpad.net

Choosing a feature to work on
=============================

If you are a happy user of GTG and nothing bothers you but you would like to contribute you can:

* choose a `LOVE bug`_ which are easier to solve
* ask people on IRC channel #gtg on irc://irc.gimp.org/#gtg
* ask on our `mailing list`_

.. _`LOVE bug`: https://bugs.launchpad.net/gtg/+bugs?field.status%3Alist=NEW&field.status%3Alist=CONFIRMED&field.status%3Alist=TRIAGED&field.status%3Alist=INPROGRESS&assignee_option=none&field.tag=love
.. _`mailing list`: https://launchpad.net/~gtg-user


Working on the feature in a branch
==================================

You have your local copy of the code (see "Getting the code"). Now, create a
local branch of your local branch (yes, it is)::

    $ cd ..
    $ bzr branch trunk cool-new-feature

(your *trunk* folder is branched in a new *cool-new-feature* folder)

When working with Bazaar, it's a good idea to keep your local *trunk* branch as
a pristine copy of trunk on Launchpad.

Hack and commit your changes::

    bzr commit -m "description of my change"

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

If the trunk has been updated while you were hacking, you should update your
local trunk branch, and merge modification in **your** branch::

    $ cd ../trunk
    $ bzr pull trunk
    $ cd ../cool-new-feature
    $ bzr merge ../trunk

If you have conflicts, you must solve them. Refer to `conflicts guide`_.

.. _`conflicts guide`: http://doc.bazaar.canonical.com/bzr.0.92/en/user-guide/conflicts.html

Once you don't have any conflict anymore, you must commit the changes related
to the merge. Use a clear commit message, like::

    Updating branch by merging the last trunk version.

Pushing your work to your own branch on Launchpad (where *ploum* is your
Launchpad username)::

    $ bzr push lp:~ploum/gtg/cool-new-feature

Alternatively, if you want other gtg users to be able to write to your branch,
push it in the gtg-user group (you have to be part of it)::

    $ bzr push lp:~gtg-user/gtg/ploum_branch

Ask for a merge request and comment on the corresponding bug. (Open one if
there is none). Add the tag *toreview* to the bug in Launchpad. This is very
important and ensures we are not letting a patch rotting.

You can file a bug at https://bugs.launchpad.net/gtg/+filebug.

To ask for a merge request, run::

$ cd cool-new-feature
$ bzr lp-open

This will open the branch's web page on Launchpad. From there, click *Propose for merging*.

If your branch is solving specific reported bugs, please also register your
branch to these bugs (there is an link for that in each bug report page). It
allows to link together all related resources (which in turn is useful to dig
out precious information from all the discussions that happened around those
bugs).

For more detailed information, see the `HACKING`_ guide included in the GTG code.

.. _`HACKING`: http://bazaar.launchpad.net/~gtg/gtg/trunk/annotate/head%3A/HACKING

Troubleshooting
===============

If you have a problem with SSH keys while uploading to Launchpad, look at this `SuperUser question`_.

.. _`SuperUser question`: http://superuser.com/questions/161337/big-ssh-problem
