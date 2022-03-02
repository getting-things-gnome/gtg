**Getting Things GNOME!** (GTG) is a personal tasks and TODO list items organizer for the GNOME desktop environment inspired by the [*Getting Things Done* (GTD) methodology][gtd-info].
GTG is designed with flexibility, adaptability, and ease of use in mind so it can be used as more than just GTD software.
GTG is intended to help you track everything you need to do and need to know, from small tasks to large projects.

[gtd-info]: https://gettingthingsdone.com/what-is-gtd/

You are currently reading the index of the information intended for **new contributors** (beta testers, developers, packagers, etc.), found in [the project's main software development and management hub](https://github.com/getting-things-gnome/gtg).

See [our website](https://wiki.gnome.org/Apps/GTG) for the list of features and information intended for **users** (including how to install the stable release with pre-built packages).
Except if you're here to report an issue – then you can just directly create
an issue rather than continue reading.

[![Mastodon badge](https://img.shields.io/mastodon/follow/232134?domain=https%3A%2F%2Ffosstodon.org&label=Follow%20us%20on%20Mastodon&style=social)](https://fosstodon.org/@GettingThingsGNOME)
[![Twitter badge](https://img.shields.io/twitter/follow/getthingsgnome.svg?style=social&label=Follow%20us%20on%20Twitter)](https://twitter.com/GetThingsGNOME)

# Starting point for testers, bug reporters, and new contributors

* Keep reading below for basic instructions on how to get the development version of GTG running.
* See the [CONTRIBUTING.md](CONTRIBUTING.md) file to ensure you have realistic expectations regarding feature requests, and to learn how you can effectively help the project. Your involvement is what keeps this project moving forward, and we need you to play an active part in implementing desired improvements!
  * Explore the [docs/contributors/ subfolder](./docs/contributors) to see reference documentation for contributors, including coding/style conventions, how to deal with Git and submit patches, etc.

## Setting up & running the development version

### Getting the code

Execute this command to get the latest development code (if you don't have it already) and then move to that directory:

```sh
git clone https://github.com/getting-things-gnome/gtg.git && cd gtg
```

Later, when you want to update to the latest development version (assuming you are still in the "gtg" directory and did not make changes locally), you can do so with:

```sh
git pull --rebase
```

### Dependencies

* meson (>= 0.51.0)
* python3 (>= 3.8)
* python-caldav
* pycairo
* pygobject (>= 3.20)
* libLarch (>= 3.2)
* lxml
* itstool
* gettext
* Introspection (GIR) files and libraries from:
  - GLib
  - pango
  - gdk-pixbuf
  - GTK 3
  - GtkSourceView 4

You can get most of those from your distribution packages:

```sh
# On Fedora:
sudo dnf install meson python3-cairo python3-gobject gtk3 itstool gettext python3-lxml
# On Debian 10 (buster), you need to install the backported version, activate it with:
echo 'deb http://deb.debian.org/debian buster-backports main' | sudo tee -a /etc/apt/sources.list
# On Debian/Ubuntu:
sudo apt install meson python3-gi-cairo python3-gi gir1.2-pango-1.0 gir1.2-gdkpixbuf-2.0 gir1.2-gtk-3.0 itstool gettext python3-lxml libgirepository1.0-dev
```

liblarch may be harder to come by until distributions package the python3 version of it, alongside GTG 0.6+ itself.
You can get it meanwhile via PIP (commonly provided by `python3-pip` package):

```sh
pip3 install --user -e git+https://github.com/getting-things-gnome/liblarch.git#egg=liblarch
```

Alternatively, if you had checked out a specific version of liblarch that you want to test, in a parent folder for example (`../liblarch`), you could do: `pip3 install --user ../liblarch/` (you can later remove that with `pip3 uninstall liblarch` if you need to).

Optional Dependencies:
* [setproctitle](https://pypi.org/project/setproctitle/)
  (to set the process title when listing processes like `ps`)

### Test dependencies

To run the current testsuite, you need some additional packages (this list may be out of date):

```sh
# On Fedora:
sudo dnf install python3-pytest python3-pyflakes python3-spec python3-pycodestyle python3-mock
# On Ubuntu/Debian:
sudo apt install python3-pytest python3-pyflakes python3-pep8 python3-pycodestyle python3-mock python3-caldav
```

You will currently also need the optional plugin dependencies, as the tests don't automatically skip them. (Help welcome improving that!)

### Solving dependencies for plugins (optional)

There are additional plugins (modules for extending the user interface) and synchronization services (modules for importing/exporting tasks from/to external services) that might need additional packages to work correctly.

Dependencies for the "Export and print" plugin:

* python3-cheetah
* pdflatex (in the `texlive-extra-utils` package on Ubuntu and Debian)
* pdfjam (in the `texlive-extra-utils` package on Ubuntu and Debian, possibly in `texlive-pdfjam` on Fedora)
* pdftk (now called `pdftk-java` in Ubuntu, and no longer available in Fedora)

On Ubuntu and Debian you can install all that with:

```sh
# On Ubuntu/Debian:
sudo apt install python3-cheetah pdftk-java texlive-extra-utils texlive-latex-base
```

### Running the beast

In order to run the developer/git version of GTG, you need to launch the `debug.sh` script
There is a shortcut to it in the root directory where you downloaded the code, that you can execute simply with this command:

```sh
./launch.sh
```

This is the safest way to run the git version, as it does not touch your normal user data (see below).

You can use `./launch.sh -?` to get a list of options useful for development
you can append to the command, such as:
* `-d` to enable debug logs
* `-w` to enable additional [python development][pythondevmode] stuff
  like deprecation warnings
* `-p prefix-prog` to prepend `prefix-prog` to the main gtg executable script,
  useful to run under a debugger: `./launch.sh -p 'python3 -m pudb'` (with
  [pudb][pudb]) or a profiler: `./launch.sh -p 'python3 -m cProfile -o gtg.prof'`
* `-s dataset` to use the dataset called `dataset`. It'll store it inside the `tmp`
  folder of the current working directory. If it doesn't exists, it'll create
  an new clean one. There are pre-made ones you can use by replacing `dataset`
  with one of the following:
  * `bryce` - An anonymized dataset with a fair number of tasks
  * `screenshots` - Pre-made tasks that can be used to show off GTG

If you somehow need to pass arguments directly to the `gtg` binary itself,
anything after `--` is passed to gtg directly.
For example, use the following command to show the help for `gtg` itself:

```sh
./launch.sh -- --help
```

To examine the UI elements, you might be interested to use [GTKs interactive debugger][gtk-interactive], that you can use by prepending `GTK_DEBUG=interactive` like:
```sh
GTK_DEBUG=interactive ./launch.sh
```

[gtk-interactive]: https://developer.gnome.org/gtk3/stable/gtk-running.html#interactive-debugging

If there is any problem with meson (the build system) or anything else,
try deleting the build folder first and try again: `rm -rf .local_build`.
No data should be lost since it is just re-generateable build files.

[pythondevmode]: https://docs.python.org/3/library/devmode.html
[pudb]: https://pypi.org/project/pudb/

# "Where is my user data and config stored?"

It depends:

* If you are running a version installed system-wide (ex: a package provided by a Linux distribution), as GTG adheres to the [FreeDesktop XDG Base Directories specification][basedir-spec], you will typically find it spread across:
  * `${XDG_DATA_HOME:-$HOME/.local/share}/gtg` like `~/.local/share/gtg/`
  * `${XDG_CONFIG_HOME:-$HOME/.config}/gtg`    like `~/.config/gtg/`
  * `${XDG_CACHE_HOME:-$HOME/.cache}/gtg`      like `~/.cache/gtg/`
* If you are running the Flatpak package version, those directories are all in `~/.var/app/org.gnome.GTG/` (or something similar)
* If you are running `launch.sh` (the launcher from the Git/development version),
  GTG doesn't touch your normal user data, it uses the `tmp` subdirectory in your current working directory (usually the repository root, the gtg folder).
  You can pass `-s name` to use a different folder inside the `tmp` directory,
  the default being `default`.

[basedir-spec]: https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html

If you want to import a copy of your gtg data to the development version, simply run at the repository root one of the following commands:
```sh
./scripts/import_tasks_from_local.sh # local/system-wide install data
./scripts/import_tasks_from_flatpak.sh # flatpak data
```

# Viewing the user manual

Whether to learn how GTG works from a user's perspective, or to preview changes you may have made to the user manual, you will need the "Yelp" help viewer application, which you can easily install on any Linux distribution (if it is not already present).

When installed system-wide, you can then view the user manual either by accessing it through GTG (press F1 or use the Help menu) or through the command line:

```sh
yelp help:gtg
```

If you want to read the documentation directly from the source code, run this command (from the source root directory):

```sh
yelp docs/user_manual/C/index.page
```

# Other documentation

* Our wiki serves as our website: https://wiki.gnome.org/Apps/GTG
* Check out the [docs folder in the main repository](./docs/) for more
  information and documentation for contributors

## Test suite status

We need help bringing the test suite back online with updated tests (before the badge below can be moved back up in this readme file). Get in touch if you'd like to work on this.

[![Build Status](https://travis-ci.org/getting-things-gnome/gtg.svg?branch=master)](https://travis-ci.org/getting-things-gnome/gtg)
