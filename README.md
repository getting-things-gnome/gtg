# Getting Things GNOME!

[![Build Status](https://travis-ci.org/getting-things-gnome/gtg.svg?branch=master)](https://travis-ci.org/getting-things-gnome/gtg)

Getting Things GNOME! (GTG) is a personal tasks and TODO list items organizer
for the GNOME desktop environment inspired by the Getting Things Done (GTD)
methodology. GTG is designed with flexibility, adaptability, and ease of use
in mind so it can be used as more than just GTD software.

GTG is intended to help you track everything you need to do and need to know,
from small tasks to large projects.

## Dependencies

GTG depends on the following packages:

 * Python, version 3.0 or above
 * PyGTK
 * python-support
 * python-xdg
 * python-dbus
 * python-liblarch 
 * yelp (to read GTG documentation)

Please refer to your system documentation for information on how to install
these modules if they're not currently available.

To install the all the required packages providing the basic features on
Debian-based systems, execute the following command:
    $ sudo apt-get install python-support python-gtk2 python-gnome2 \
         python-glade2 python-xdg python-dbus python-liblarch yelp

There are additional plugins (modules for extending the user interface) and
synchronization services (modules for importing/exporting tasks from/to
external services) which needs additional packages to work correctly.

### Dependencies for Plugins

"Bugzilla" plugin dependencies:
  * python-bugz

"Export and print" plugin dependencies:
  * python-cheetah
  * pdflatex
  * pdftk
  * pdfjam

Installable on Debian-based system via
    $ sudo apt-get install python-cheetah pdftk pdfjam texlive-latex-base

"Geolocalized tasks" plugin is not maintained for a long time and needs to be
rewritten from scratch. Dependencies:
  * python-geoclue
  * python-clutter
  * python-clutter-gtk
  * python-champlain
  * python-champlain-gtk

"Hamster Time Tracker Integration" plugin needs a running instance of Hamster.

"Notification area" plugin has only an optional dependence for systems
which supports indicators:
  * python-appindicator

"Send task via email" plugin does not have any external dependencies.

"Closed tasks remover" plugin does not have any external dependencies.

"Tomboy/Gnote" plugin needs a running instance of Tomboy or Gnote.
python-dbus

"Urgency Color" plugin does not have any external dependencies.

### Dependencies for Synchronization Services

Evolution synchronization service has dependencies:
  * python-evolution
  * python-dateutil

Because of a bug in PyGTK (see https://bugs.launchpad.net/gtg/+bug/936183),
the synchronization service freezes GTG and the synchronization service can't be used.

MantisBT synchronization service has a dependency:
  * python-suds

Launchpad synchronization service has a dependency:
  * python-launchpadlib

Gnote and Tomboy synchronization services has no external dependency.

Identica and Twitter synchronization services are shipped with the local
version of Tweety library.

Remember the Milk synchronization service is shipped with a library for RTM api. It has an external dependency:
  * python-dateutil

Remember the Milk is not maintained for a long time and might be potentially harmful.

## Installing and Running

To install GTG, either unpack the tarball:

    $ tar xzvf gtg.tar.gz

or check out our bazaar branch for a development version (we try to keep those
unbroken and ready for production use):

    $ bzr branch lp:gtg

To run GTG, either execute it directly from the source folder:

    $ cd gtg/
    $ ./gtg

or install it system-wide (must install as root to install system-wide):

    $ cd gtg
    $ sudo python setup.py install # must be root to install system-wide
    $ gtg

### How To Use GTG?

Please refer to our documentation to get a thorough explanation on how GTG
works.

To do this, you will need the yelp help viewer. On Debian-based systems, you
can install yelp by executing this command:

    $ sudo apt-get install yelp

You can then view the documentation either by accessing it through GTG (press
F1 or use the help menu), or by using the command line using the following
command:

    $ yelp help:gtg

If you want to read the documentation directly from the source code, use
this command (from the source root dir):

    $ yelp docs/userdoc/C/index.page

### Using GTG from the command line

GTG provides two command line tools that allows to interact with GTG:

 * gtcli
 * gtg_new_task

gtcli provides many options to display, list or edit tasks. gtg_new_task
provides a GTG command line client that allows to easily add tasks.

If you want to know more about how to use these tools, please refer to the
tools man page.

If you have installed gtg, you can access those by executing:

    $ man gtcli
    $ man gtg_new_task

## Want to know more?

 * GTG Website: http://gtgnome.net/
 * GTG project page on Launchpad: https://launchpad.net/gtg
 * GTG Wiki: http://live.gnome.org/gtg/
 * GTG developer's documentation: http://gtg.readthedocs.org/en/latest/index.html

Feel free to join our user mailing-list to receive news about GTG. You can
register on this mailing-list from this page: https://launchpad.net/~gtg-user

Thanks for using GTG!
