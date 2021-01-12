> *Getting Things GNOME!* (GTG) is a personal tasks and TODO list items organizer for the GNOME desktop environment inspired by the *Getting Things Done* (GTD) methodology. GTG is designed with flexibility, adaptability, and ease of use in mind so it can be used as more than just GTD software. GTG is intended to help you track everything you need to do and need to know, from small tasks to large projects.

You are currently reading the index of the information intended for **new contributors** (beta testers, developers, packagers, etc.), found in [the project's main software development and management hub](https://github.com/getting-things-gnome/gtg).

See [our website](https://wiki.gnome.org/Apps/GTG) for the list of features and information intended for **users** (including how to install the stable release with pre-built packages).

# Starting point for testers, bug reporters, and new contributors

* Keep reading below for basic instructions on how to get the development version of GTG running.
* See the [CONTRIBUTING.md](CONTRIBUTING.md) file to ensure you have realistic expectations regarding feature requests, and to learn how you can effectively help the project. Your involvement is what keeps this project moving forward, and we need you to play an active part in implementing desired improvements!
  * Explore the docs/contributing/ subfolder to see reference documentation for contributors, including coding/style conventions, how to deal with Git and submit patches, etc.

## Setting up & running the development version

### Getting the code

Execute this command to get the latest development code (if you don't have it already) and then move to that directory:

    git clone https://github.com/getting-things-gnome/gtg.git
    cd gtg

Later, when you want to update to the latest development version (assuming you are still in the "gtg" directory and did not make changes locally), you can do so with:

    git pull --rebase

### Dependencies

* meson
* python3
* python-caldav
* pycairo
* pygobject (>= 3.20)
* libLarch (>= 3.0)
* lxml
* itstool
* gettext
* Introspection (GIR) files and libraries from:
  - GLib
  - pango
  - gdk-pixbuf
  - GTK 3

You can get most of those from your distribution packages:

    # On Fedora
    sudo dnf install meson python3-cairo python3-gobject gtk3 itstool gettext python3-lxml
    # On Debian/Ubuntu
    sudo apt install meson python3-cairo python3-gi gir1.2-pango-1.0 gir1.2-gdkpixbuf-2.0 gir1.2-gtk-3.0 itstool gettext python3-lxml

liblarch may be harder to come by until distributions package the python3 version of it, alongside GTG 0.4+ itself.
You can get it meanwhile via PIP (commonly provided by python3-pip package):

    pip3 install --user -e git+https://github.com/getting-things-gnome/liblarch.git#egg=liblarch

### Test dependencies

To run the current testsuite, you need some additional packages (this list may be out of date):

    # On Fedora:
    sudo dnf install python3-nose python3-pyflakes python3-spec python3-pycodestyle python3-mock

    # On Ubuntu/Debian:
    sudo apt install python3-nose python3-pyflakes python3-pep8 python3-pycodestyle python3-mock

You will currently also need the optional plugin dependencies, as the tests don't automatically skip them. (Help welcome improving that!)

### Solving dependencies for plugins (optional)

There are additional plugins (modules for extending the user interface) and synchronization services (modules for importing/exporting tasks from/to external services) that might need additional packages to work correctly.

Dependencies for the "Export and print" plugin:

* python3-cheetah
* pdflatex (in the "texlive-extra-utils" package on Ubuntu)
* pdfjam (in the "texlive-extra-utils" package on Ubuntu, possibly in "texlive-pdfjam" on Fedora)
* pdftk (now called pdftk-java in Ubuntu, and no longer available in Fedora)

On Ubuntu you can install all that with:

    sudo apt install python3-cheetah pdftk-java pdfjam texlive-latex-base

### Running the beast

In order to run the developer/git version of GTG, you need to launch the `debug.sh` script. There is a shortcut to it in the root directory where you downloaded the code, that you can execute simply with this command:

    ./launch.sh

This is the safest way to run the Git version, as it does not touch your normal user data (see below).

# "Where is my user data and config stored?"

It depends:

* If you are running a version installed system-wide (ex: a package provided by a Linux distribution), as GTG adheres to the FreeDesktop XDG User Directories specification, you will typically find it spread across:
  * ~/.local/share/gtg/
  * ~/.config/gtg/
  * ~/.cache/gtg/
* If you are running the Flatpak package version, those directories are all in ~/.var/app/org.gnome.Gtg/ (or something similar)
* If you are running launch.sh (the launcher from the Git/development version), GTG doesn't touch your normal user data, it uses the "tmp" subdirectory in your gtg development folder.

If you happen to move/copy data between those various instances, you will not only have to move/copy the folders and their contents, but also edit the destination's "projects.xml" file to change the path of the "tasks.xml" to match the new location (for example the traditional "/home/your_username/.local/share/gtg/tasks.xml" would become "/home/your_username/.var/app/org.gnome.Gtg/data/gtg/tasks.xml" when moving from the distro-provided GTG version to the Flatpak version).

If, for testing purposes, you want to copy your user data over to the Git version's directory and automatically fix the resulting "projects.xml" file to reference the correct path, you can run `scripts/import_my_tasks_into_debug_tasks.sh` instead of having to do it manually.

# Viewing the user manual

Whether to learn how GTG works from a user's perspective, or to preview changes you may have made to the user manual, you will need the "Yelp" help viewer application, which you can easily install on any Linux distribution (if it is not already present).

When installed system-wide, you can then view the user manual either by accessing it through GTG (press F1 or use the Help menu) or through the command line:

    yelp help:gtg

If you want to read the documentation directly from the source code, run this command (from the source root directory):

    yelp docs/user_manual/C/index.page

# Other documentation

* Our wiki serves as our website: https://wiki.gnome.org/Apps/GTG
* Check out the docs/ folder in the main repository at: https://github.com/getting-things-gnome/gtg/tree/master/docs

## Test suite status

We need help bringing the test suite back online with updated tests (before the badge below can be moved back up in this readme file). Get in touch if you'd like to work on this.

[![Build Status](https://travis-ci.org/getting-things-gnome/gtg.svg?branch=master)](https://travis-ci.org/getting-things-gnome/gtg)
