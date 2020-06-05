# Things to check and do before a release

1. Update the translation template file (`ninja -C .local_build/ gtg-pot` or, if you really have a reason to do so, `ninja -C .local_build/ gtg-update-po`) and notify the GNOME translation teams well in advance to request updated translations if needed.
1. Check that code tests pass (run the `make check` command). See also the test suite [coverage testing](test suite - coverage testing.md)
2. AUTHORS and GTG/info.py files are up to date. To get the list of top contributors to a release, use `git shortlog -s -n previous_tag...new_tag_or_HEAD` (for example `git shortlog -s -n v0.3.1..HEAD`)
3. Retest all again
4. Update the NEWS file, and ideally prepare release notes and announcements in advance
5. Test creating tarballs (see further below)
6. Tag the release and create the tarballs and Flatpak packages
7. Remember to update the historical wiki page at https://wiki.gnome.org/Apps/GTG/release_names

# Release tagging (usually done by maintainers)

Tag the revision (use `git tag -a`) with `vRELEASE_NUMBER` (ex: `git tag -a v0.3.1`, `git tag -a v0.4`, etc.) when on the correct commit. `git tag` lists all the tags.

When you are absolutely sure you tagged "correctly", you can use `git push --tags`.

In GitHub and GitLab, a commit named "Release version 0.4" and tagged "v0.4", for example, will correctly show up in the "Releases" section of the repository's web interface.

# Creating tarballs tarball (intended for distros)

This is now done simply like this (assuming you ran launch.sh at least once previously):

    ninja -C .local_build/ dist

...which will create the .local_build/meson-dist/gtg-VERSIONNUMBER.tar.xz tarball.
Then we need to upload the tarball to... wherever we're supposed to upload tarballs (someone should fix these instructions).

# Flatpak package (intended for users)

Someone knowledgeable please write instructions here or as a standalone file to be linked to.
