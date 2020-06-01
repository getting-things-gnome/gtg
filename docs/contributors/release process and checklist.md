# Things to check and do before a release

1. Update the translation template file (`ninja -C .local_build/ gtg-pot` or, if you really have a reason to do so, `ninja -C .local_build/ gtg-update-po`) and notify the GNOME translation teams well in advance to request updated translations if needed.
1. Check that code tests pass (run the `make check` command). See also the test suite [coverage testing](test suite - coverage testing.md)
2. AUTHORS and GTG/info.py files are up to date. To get the list of top contributors to a release, use `git shortlog -s -n previous_tag...new_tag_or_HEAD` (for example `git shortlog -s -n v0.3.1..HEAD`)
3. Retest all again
4. Update the NEWS file, and ideally prepare release notes and announcements in advance
5. Test creating tarballs (see further below)
6. Tag the release and create the tarballs and Flatpak packages

# Release tagging (usually done by maintainers)

Tag the revision (use `git tag -a`) with `vRELEASE_NUMBER` (ex: `git tag -a v0.3.1`, `git tag -a v0.4`) when on the correct commit. `git tag` lists all the tags. Update the historical wiki page at https://wiki.gnome.org/Apps/GTG/release_names.

When you are absolutely sure you tagged "correctly", you can use `git push --tags`.

# Creating tarballs tarball (intended for distros)

Use sanity scripts to test creating a tarball. They will tell you missing files in the tarball.

    make clean
    ./scripts/tarball_integrity.py
    ./scripts/build_integrity.py

You can install GTG into an empty folder so you exactly see what will be installed and what will not.

    python3 setup.py install --prefix=./temp_folder

Create a tarball and upload it to... wherever we're supposed to upload tarballs (someone should fix these instructions):

    python3 setup.py sdist

# Flatpak package (intended for users)

Someone knowledgeable please write instructions here or as a standalone file to be linked to.
