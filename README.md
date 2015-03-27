# Getting Things GNOME!

[![Build Status](https://travis-ci.org/getting-things-gnome/gtg.svg?branch=master)](https://travis-ci.org/getting-things-gnome/gtg)

Getting Things GNOME! (GTG) is a personal tasks and TODO list items organizer
for the GNOME desktop environment inspired by the Getting Things Done (GTD)
methodology. GTG is designed with flexibility, adaptability, and ease of use
in mind so it can be used as more than just GTD software.

GTG is intended to help you track everything you need to do and need to know,
from small tasks to large projects.

## INSTALLING AND RUNNING

In order to download and run GTG Developer Version, do the following steps 
(Debian-based systems):

DOWNLOAD: 
Execute this command to get the latest Developer package and then move to that directory:

    $ git clone https://github.com/getting-things-gnome/gtg.git
    $ cd gtg

RUNNING: 
At first, install python3 dependencies by typing the following command:
 
    $ sudo apt-get install python3-pip

Running of this developer version of GTG will not be possible without installing 
liblarch at first so clone and install liblarch:

    $ pip3 install -r requirements.txt

RUN:
In order to run GTG from this Developers repository, you need to launch the debug.sh script:

    $ ./gtg.sh

Getting Things GNOME launches.

If prompted, you may be required to install also python3-xdg and python3-dbus packages manually. Simply write a command:

    $ sudo apt-get install python3-xdg python3-dbus

Run the script again.


There are additional plugins (modules for extending the user interface) and
synchronization services (modules for importing/exporting tasks from/to
external services) which needs additional packages to work correctly.

### DEPENDENCIES FOR PLUGINS

"Bugzilla" plugin dependencies:
  * python3-bugz

"Export and print" plugin dependencies:
  * python3-cheetah
  * pdflatex
  * pdftk
  * pdfjam

Installable on Debian-based system via
    
    $ sudo apt-get install python3-cheetah pdftk pdfjam texlive-latex-base

"Hamster Time Tracker Integration" plugin needs a running instance of Hamster.

"Notification area" plugin has only an optional dependence for systems
which supports indicators:
  * python3-appindicator

"Send task via email" plugin does not have any external dependencies.

"Closed tasks remover" plugin does not have any external dependencies.

"Tomboy/Gnote" plugin needs a running instance of Tomboy or Gnote.
  * python3-dbus

"Urgency Color" plugin does not have any external dependencies.

### DEPENDENCIES FOR SYNCHRONIZATION SERVICES

Evolution synchronization service has dependencies:
  * python3-evolution
  * python3-dateutil

Because of a bug in PyGTK (see https://bugs.launchpad.net/gtg/+bug/936183),
the synchronization service freezes GTG and the synchronization service can't be used.

MantisBT synchronization service has a dependency:
  * python3-suds

Launchpad synchronization service has a dependency:
  * python3-launchpadlib

Gnote and Tomboy synchronization services has no external dependency.

Identica and Twitter synchronization services are shipped with the local
version of Tweety library.

Remember the Milk synchronization service is shipped with a library for RTM api. It has an external dependency:
  * python3-dateutil

Remember the Milk is not maintained for a long time and might be potentially harmful.

### HOW TO USE GTG?

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

### USING GTG FROM COMMAND LINE

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

## WANT TO KNOW MORE?

 * GTG Website: http://gtgnome.net/
 * GTG GitHub latest repository: https://github.com/getting-things-gnome/gtg
 * GTG project page on Launchpad: https://launchpad.net/gtg
 * GTG Wiki: http://live.gnome.org/gtg/
 * GTG developer's documentation: http://gtg.readthedocs.org/en/latest/index.html

Feel free to join our user mailing-list to receive news about GTG. You can
register to our mailing-list from this page: https://launchpad.net/~gtg-user

Thanks for using GTG!
