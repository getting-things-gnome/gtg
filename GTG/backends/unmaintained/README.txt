These backends are unmaintained. Currently they don't work and we are looking
for new maintainers. They might eventually be deleted if no one steps up to fix
and support them.

If you are interested in taking over one of these, let us know in the bug
tracker!

---

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
