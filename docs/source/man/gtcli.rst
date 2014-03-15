gtcli(1)
========

SYNOPSIS
--------

**gtgcli [options] COMMAND [command options]**

DESCRIPTION
-----------
gtgcli provides a handy command-line interface to GTG. It allows one to list
and modify your task directly from the command line. It also allows one to
interact with GTG using shell scripts.

OPTIONS
-------

**-h, --help**
    Prints some information about gtg's usage and options.

COMMAND OPTIONS
---------------

**new**
    Creates a new task.


**show <tid>**
    Display task with <tid> task ID.


**edit <tid>**
    Opens the GUI editor for the task with <tid> task ID.
    

**delete <tid>**
    Removes task with <tid> task ID.

**list [all|today|<filter>|<tag>]**
    List tasks corresponding to the given attributes.

**search <expression>**
    Search tasks corresponding to <expression>. Read the documentation from GTG's
    help to know more about the search query syntax.

**count [all|today|<filter>|<tag>]**
    Outputs the task count for all the task corresponding to the given attributes.

**summary [all|today|<filter>|<tag]**
    Report how many tasks starting/due each day.

**postpone <tid> <date>**
    Updates the start date of the task with <tid> task id to <date>.

**close <tid>**
    Sets state of task identified by <tid> to done.

**browser [hide|show]**
    Hides or shows the task browser window.

SEE ALSO
--------

gtg (1)

BUGS
----

Please report any bug you may experience to the **GTG** Developers, that can
be reached at https://launchpad.net/gtg

COPYRIGHT
---------

This manual page is Copyright 2012 Bertrand Rousseau
<bertrand.rousseau@gmail.com>. Permission is granted to copy, distribute
and/or modify this document under the terms of the GNU General Public License,
Version 3 or any later version published by the Free Software Foundation.
