gtg(1)
======

SYNOPSIS
--------

**gtg [options]**

DESCRIPTION
-----------

Getting Things GNOME! is a personal tasks and TODO-list items organizer for the
GNOME desktop environment inspired by the Getting Things Done (GTD)
methodology. GTG is designed with flexibility, adaptability, and ease of use in
mind so it can be used as more than just GTD software.


GTG is intended to help you track everything you need to do and need to know,
from small tasks to large projects.

GTG uses a very handy system for creating and editing tasks. The task editor
can automatically recognize metadata such as tags and subtasks through the use
of a very simple syntax.

OPTIONS
-------

**-b, --boot-test**
    Boot-up only. Causes gtg to exit immediately after completing the first
    iteration of the main loop. Useful for boot performance testing work.

**-c, --no-crash-handler**
    Disable crash handler. Causes the Apport automatic crash reporting utility
    to not be invoked when gtg crashes; instead it will print out a normal
    python backtrace. This can be useful for debugging crash bugs, or if the
    crash handler is misbehaving.

**-d, --debug**
    Debug mode. Prints extra information to the console which may be useful for
    understanding and reporting bugs.

**-h, --help**
    Prints some information about gtg's usage and options.

**-l, --local-liblarch**
    Use local liblarch. Look for the liblarch python library in ../liblarch.
    This is mainly useful for testing purpose.

**-t TITLE, --title=TITLE**
    Set the window's title to TITLE.

**-v, --version**
    Prints version and exits.

COPYRIGHT
---------

This manual page is Copyright 2009, 2012 Luca Falavigna <dktrkranz@debian.org>
and Bertrand Rousseau <bertrand.rousseau@gmail.com>. Permission is granted
to copy, distribute and/or modify this document under the terms of the GNU
General Public License, Version 3 or any later version published by the Free
Software Foundation.
